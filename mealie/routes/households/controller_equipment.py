import shutil

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from pydantic import UUID4
from slugify import slugify
from sqlalchemy.orm import selectinload
from starlette.responses import FileResponse

from mealie.db.models.recipe.tool import Tool
from mealie.routes._base import controller
from mealie.routes._base.base_controllers import BaseUserController
from mealie.schema.household.equipment import (
    EquipmentAICreateRequest,
    EquipmentCreate,
    EquipmentImageURLRequest,
    EquipmentOut,
    EquipmentRecipeSummary,
    EquipmentUpdate,
)
from mealie.schema.openai.chef import OpenAIEquipment
from mealie.schema.response.responses import ErrorResponse
from mealie.services.entity_image_service import EntityImageService
from mealie.services.equipment_service import normalize_equipment_name
from mealie.services.item_image_service import ItemImageRequest, ItemImageService
from mealie.services.openai import OpenAIService

router = APIRouter(prefix="/households/equipment", tags=["Households: Equipment"])


@controller(router)
class EquipmentController(BaseUserController):
    @property
    def item_image_service(self) -> ItemImageService:
        return ItemImageService(self.group_id, self.repos)

    @property
    def entity_image_service(self) -> EntityImageService:
        return EntityImageService(self.folders.DATA_DIR)

    def _image_path(self, tool: Tool):
        return self.item_image_service.get_image_path("tool", tool.name)

    def _statement(self):
        return (
            sa.select(Tool)
            .options(selectinload(Tool.recipes))
            .where(Tool.group_id == self.group_id)
        )

    def _get_or_404(self, tool_id: UUID4) -> Tool:
        tool = self.session.execute(self._statement().where(Tool.id == tool_id)).scalar_one_or_none()
        if tool is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        return tool

    def _to_out(self, tool: Tool) -> EquipmentOut:
        image_path = self._image_path(tool)
        try:
            image_stat = image_path.stat()
        except FileNotFoundError:
            image_stat = None
        recipes = sorted(tool.recipes, key=lambda recipe: recipe.name.casefold())
        return EquipmentOut(
            id=tool.id,
            group_id=tool.group_id,
            name=normalize_equipment_name(tool.name),
            slug=tool.slug,
            category=tool.category,
            description=tool.description,
            image_source_url=tool.image_source_url,
            image_name=tool.name,
            ai_enriched=tool.ai_enriched,
            has_image=bool(image_stat and image_stat.st_size > 0),
            image_version=str(image_stat.st_mtime_ns) if image_stat else None,
            recipe_count=len(recipes),
            recipes=[EquipmentRecipeSummary(slug=recipe.slug, name=recipe.name) for recipe in recipes],
        )

    def _save(self, data: EquipmentCreate, *, ai_enriched: bool = False) -> Tool:
        name = normalize_equipment_name(data.name)
        if not name:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("A tool name is required"),
            )

        tool_slug = slugify(name)
        tool = self.session.execute(
            self._statement().where(Tool.slug == tool_slug)
        ).scalar_one_or_none()
        if tool is None:
            tool = Tool(
                session=self.session,
                group_id=self.group_id,
                name=name,
                households_with_tool=[],
            )
        tool.category = (data.category or "").strip()[:120] or tool.category
        tool.description = (data.description or "").strip() or tool.description
        tool.ai_enriched = bool(ai_enriched or tool.ai_enriched)
        self.session.add(tool)
        self.session.commit()
        return self._get_or_404(tool.id)

    async def _analyze(self, data: EquipmentAICreateRequest) -> OpenAIEquipment:
        openai_service = OpenAIService(self.repos)
        if not (openai_service.provider_settings and openai_service.provider_settings.ai_enabled):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("OpenAI services are not enabled"),
            )
        response = await openai_service.get_response(
            openai_service.get_prompt("equipment.classify-equipment"),
            "\n\n".join(
                part
                for part in (
                    f"User request:\n{data.prompt.strip()}",
                    f"Candidate tool name: {data.name.strip()}" if (data.name or "").strip() else "",
                    "Return the canonical tool name, category, and explanation in Hebrew.",
                )
                if part
            ),
            response_schema=OpenAIEquipment,
        )
        if not response or not response.is_kitchen_tool:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("The supplied item does not look like kitchen equipment"),
            )
        if not normalize_equipment_name(response.name or data.name):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("The AI provider did not return a usable tool name"),
            )
        return response

    async def _enrich(self, tool: Tool, *, find_image: bool = True) -> None:
        openai_service = OpenAIService(self.repos)
        if not (openai_service.provider_settings and openai_service.provider_settings.ai_enabled):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("OpenAI services are not enabled"),
            )
        recipe_names = [recipe.name for recipe in tool.recipes[:20]]
        response = await openai_service.get_response(
            openai_service.get_prompt("equipment.classify-equipment"),
            f"Tool name: {tool.name}\nUsed by recipes: {', '.join(recipe_names)}",
            response_schema=OpenAIEquipment,
        )
        if not response or not response.is_kitchen_tool:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("The supplied item does not look like kitchen equipment"),
            )
        tool.category = response.category.strip()[:120] or "כלים נוספים"
        tool.description = response.description.strip() or None
        tool.ai_enriched = True
        self.session.add(tool)
        self.session.commit()
        if find_image and not self._image_path(tool).exists():
            try:
                await self._save_best_image(tool, response.image_search_query)
            except (ValueError, httpx.HTTPError):
                self.logger.warning("Could not find a public image for tool %s", tool.name)

    async def _save_best_image(
        self,
        tool: Tool,
        preferred_query: str | None = None,
        *,
        verify_with_ai: bool = False,
    ) -> None:
        context = " ".join(
            part
            for part in (
                tool.category,
                tool.description,
                ", ".join(recipe.name for recipe in tool.recipes[:12]),
            )
            if part
        )
        source_url = await self.item_image_service.find_and_replace(
            ItemImageRequest("tool", tool.name, context or None),
            preferred_query=preferred_query,
            verify_with_ai=verify_with_ai,
        )
        if not source_url:
            raise ValueError("No usable equipment image was found")
        tool.image_source_url = source_url
        self.session.add(tool)
        self.session.commit()

    @router.get("", response_model=list[EquipmentOut])
    def get_all(
        self,
        search: str | None = Query(None),
        category: str | None = Query(None),
    ) -> list[EquipmentOut]:
        statement = self._statement()
        query = (search or "").strip()
        if query:
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            statement = statement.where(
                sa.or_(
                    Tool.name.ilike(pattern, escape="\\"),
                    Tool.category.ilike(pattern, escape="\\"),
                    Tool.description.ilike(pattern, escape="\\"),
                )
            )
        if category:
            statement = statement.where(Tool.category == category)
        rows = self.session.execute(statement.order_by(Tool.category.asc(), Tool.name.asc())).scalars().all()
        return [self._to_out(row) for row in rows]

    @router.post("", response_model=EquipmentOut, status_code=status.HTTP_201_CREATED)
    def create(self, data: EquipmentCreate) -> EquipmentOut:
        return self._to_out(self._save(data))

    @router.post("/ai-create", response_model=EquipmentOut, status_code=status.HTTP_201_CREATED)
    async def create_with_ai(self, data: EquipmentAICreateRequest) -> EquipmentOut:
        response = await self._analyze(data)
        tool = self._save(
            EquipmentCreate(
                name=response.name or data.name or "",
                category=response.category,
                description=response.description,
            ),
            ai_enriched=True,
        )
        if not self._image_path(tool).exists():
            try:
                await self._save_best_image(tool, response.image_search_query)
            except (ValueError, httpx.HTTPError):
                self.logger.warning("Could not find a public image for tool %s", tool.name)
        return self._to_out(self._get_or_404(tool.id))

    @router.put("/{tool_id}", response_model=EquipmentOut)
    def update(self, tool_id: UUID4, data: EquipmentUpdate) -> EquipmentOut:
        tool = self._get_or_404(tool_id)
        tool.category = (data.category or "").strip()[:120] or None
        tool.description = (data.description or "").strip() or None
        self.session.add(tool)
        self.session.commit()
        return self._to_out(self._get_or_404(tool.id))

    @router.post("/{tool_id}/enrich-ai", response_model=EquipmentOut)
    async def enrich_with_ai(self, tool_id: UUID4) -> EquipmentOut:
        tool = self._get_or_404(tool_id)
        await self._enrich(tool)
        return self._to_out(self._get_or_404(tool.id))

    @router.post("/enrich-missing", response_model=list[EquipmentOut])
    async def enrich_missing(self, limit: int = Query(20, ge=1, le=50)) -> list[EquipmentOut]:
        rows = list(
            self.session.execute(
                self._statement().where(
                    sa.or_(Tool.ai_enriched.is_(False), Tool.category.is_(None))
                ).order_by(Tool.name.asc()).limit(limit)
            ).scalars()
        )
        for tool in rows:
            try:
                await self._enrich(tool)
            except HTTPException as error:
                self.logger.warning("Could not enrich tool %s: %s", tool.name, error.detail)
            except Exception:
                self.logger.exception("Could not enrich tool %s", tool.name)
        return [self._to_out(self._get_or_404(tool.id)) for tool in rows]

    @router.get("/{tool_id}/image", response_class=FileResponse)
    def get_image(self, tool_id: UUID4) -> FileResponse:
        tool = self._get_or_404(tool_id)
        path = self._image_path(tool)
        if not path.exists():
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        return FileResponse(path, media_type="image/webp", content_disposition_type="inline")

    @router.post("/{tool_id}/image", response_model=EquipmentOut)
    async def upload_image(self, tool_id: UUID4, image: UploadFile = File(...)) -> EquipmentOut:
        tool = self._get_or_404(tool_id)
        content = await image.read(12 * 1024 * 1024 + 1)
        await image.close()
        try:
            await self.entity_image_service.save_content(self._image_path(tool), content)
        except ValueError as error:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ErrorResponse.respond(str(error))) from error
        return self._to_out(tool)

    @router.post("/{tool_id}/image-url", response_model=EquipmentOut)
    async def save_image_url(self, tool_id: UUID4, data: EquipmentImageURLRequest) -> EquipmentOut:
        tool = self._get_or_404(tool_id)
        try:
            tool.image_source_url = await self.entity_image_service.save_url(self._image_path(tool), data.url)
        except (ValueError, httpx.HTTPError) as error:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ErrorResponse.respond(str(error))) from error
        self.session.add(tool)
        self.session.commit()
        return self._to_out(tool)

    @router.post("/{tool_id}/image-auto", response_model=EquipmentOut)
    async def find_image(self, tool_id: UUID4) -> EquipmentOut:
        tool = self._get_or_404(tool_id)
        try:
            await self._save_best_image(tool, verify_with_ai=True)
        except (ValueError, httpx.HTTPError) as error:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ErrorResponse.respond(str(error))) from error
        return self._to_out(self._get_or_404(tool.id))

    @router.delete("/{tool_id}/image", status_code=status.HTTP_204_NO_CONTENT)
    def delete_image(self, tool_id: UUID4) -> None:
        tool = self._get_or_404(tool_id)
        shutil.rmtree(self._image_path(tool).parent, ignore_errors=True)
        tool.image_source_url = None
        self.session.add(tool)
        self.session.commit()
