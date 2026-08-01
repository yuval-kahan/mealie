import json
import re
import shutil
from urllib.parse import urlsplit, urlunsplit

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from pydantic import UUID4
from starlette.responses import FileResponse

from mealie.db.models.household.shopping_list import ShoppingList
from mealie.db.models.household.shopping_website import (
    RecipeShoppingWebsite,
    ShoppingListShoppingWebsite,
    ShoppingWebsite,
)
from mealie.db.models.recipe.recipe import RecipeModel
from mealie.routes._base import controller
from mealie.routes._base.base_controllers import BaseUserController
from mealie.schema.household.shopping_website import (
    ShoppingWebsiteAIRequest,
    ShoppingWebsiteBrowserPageRequest,
    ShoppingWebsiteCreate,
    ShoppingWebsiteDeletePreview,
    ShoppingWebsiteDiscoveryRequest,
    ShoppingWebsiteEntityLinksUpdate,
    ShoppingWebsiteImageURLRequest,
    ShoppingWebsiteOut,
    ShoppingWebsiteUpdate,
)
from mealie.schema.openai.shopping_website import OpenAIShoppingWebsite, OpenAIShoppingWebsiteSuggestions
from mealie.schema.response.responses import ErrorResponse
from mealie.services.entity_image_service import EntityImageService
from mealie.services.openai import OpenAIService
from mealie.services.recipe.recipe_service import RecipeService

router = APIRouter(prefix="/households/shopping-websites", tags=["Households: Shopping Websites"])

HTML_SCRIPT_STYLE_RE = re.compile(r"<(script|style).*?</\1>", re.IGNORECASE | re.DOTALL)
HTML_TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"[ \t]+")
MAX_PAGE_BYTES = 2 * 1024 * 1024
MAX_PAGE_TEXT = 250000


def normalize_terms(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        item = SPACE_RE.sub(" ", str(value).strip())[:120]
        key = item.casefold()
        if item and key not in seen:
            seen.add(key)
            normalized.append(item)
    return normalized[:60]


def normalize_url(value: str) -> str:
    raw = value.strip()
    parts = urlsplit(raw)
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse.respond("A valid HTTP or HTTPS website address is required"),
        )
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, ""))


def clean_html_text(value: str) -> str:
    value = HTML_SCRIPT_STYLE_RE.sub(" ", value)
    value = re.sub(r"</(p|div|h[1-6]|li|br|nav|section)>", "\n", value, flags=re.IGNORECASE)
    value = HTML_TAG_RE.sub(" ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    value = SPACE_RE.sub(" ", value)
    return value.strip()[:MAX_PAGE_TEXT]


@controller(router)
class ShoppingWebsitesController(BaseUserController):
    @property
    def image_service(self) -> EntityImageService:
        return EntityImageService(self.folders.DATA_DIR)

    def _image_path(self, website: ShoppingWebsite):
        return self.image_service.image_path("shopping-websites", website.group_id, website.id)

    def _ai_enabled(self) -> bool:
        settings = (
            self.session.execute(
                sa.text("SELECT id, default_provider_id FROM ai_provider_settings WHERE group_id = :group_id"),
                {"group_id": self.repos.uuid_to_str(self.group_id)},
            )
            .mappings()
            .one_or_none()
        )
        if not settings or not settings["default_provider_id"]:
            return False
        return bool(
            self.session.execute(
                sa.text("SELECT 1 FROM ai_providers WHERE id = :provider_id AND settings_id = :settings_id LIMIT 1"),
                {"provider_id": settings["default_provider_id"], "settings_id": settings["id"]},
            ).scalar()
        )

    def _to_out(self, website: ShoppingWebsite) -> ShoppingWebsiteOut:
        image_path = self._image_path(website)
        try:
            image_stat = image_path.stat()
        except FileNotFoundError:
            image_stat = None
        return ShoppingWebsiteOut(
            id=website.id,
            group_id=website.group_id,
            household_id=website.household_id,
            user_id=website.user_id,
            name=website.name,
            url=website.url,
            page_food=website.page_food,
            offered_foods=json.loads(website.offered_foods_json or "[]"),
            is_recipe_site=website.is_recipe_site,
            is_shopping_site=website.is_shopping_site,
            created_at=website.created_at,
            updated_at=website.updated_at,
            recipe_ids=[link.recipe_id for link in website.recipe_links],
            shopping_list_ids=[link.shopping_list_id for link in website.shopping_list_links],
            has_image=bool(image_stat and image_stat.st_size > 0),
            image_version=str(image_stat.st_mtime_ns) if image_stat else None,
        )

    def _get_or_404(self, website_id: UUID4) -> ShoppingWebsite:
        website = self.session.execute(
            sa.select(ShoppingWebsite).where(
                ShoppingWebsite.id == website_id,
                ShoppingWebsite.group_id == self.group_id,
            )
        ).scalar_one_or_none()
        if website is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        return website

    def _validated_website_ids(self, website_ids: list[UUID4]) -> list[UUID4]:
        unique_ids = list(dict.fromkeys(website_ids))
        if not unique_ids:
            return []
        found_ids = list(
            self.session.execute(
                sa.select(ShoppingWebsite.id).where(
                    ShoppingWebsite.group_id == self.group_id,
                    ShoppingWebsite.id.in_(unique_ids),
                )
            ).scalars()
        )
        if len(found_ids) != len(unique_ids):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="One or more shopping websites were not found")
        return found_ids

    def _linked_entities(self, website_id: UUID4) -> ShoppingWebsiteDeletePreview:
        recipe_rows = self.session.execute(
            sa.select(RecipeModel.id, RecipeModel.name)
            .join(RecipeShoppingWebsite, RecipeShoppingWebsite.recipe_id == RecipeModel.id)
            .where(
                RecipeShoppingWebsite.shopping_website_id == website_id,
                RecipeModel.group_id == self.group_id,
            )
            .order_by(RecipeModel.name)
        ).all()
        shopping_list_rows = self.session.execute(
            sa.select(ShoppingList.id, ShoppingList.name)
            .join(ShoppingListShoppingWebsite, ShoppingListShoppingWebsite.shopping_list_id == ShoppingList.id)
            .where(
                ShoppingListShoppingWebsite.shopping_website_id == website_id,
                ShoppingList.group_id == self.group_id,
            )
            .order_by(ShoppingList.name)
        ).all()
        return ShoppingWebsiteDeletePreview(
            recipe_ids=[row.id for row in recipe_rows],
            recipe_names=[row.name for row in recipe_rows],
            shopping_list_ids=[row.id for row in shopping_list_rows],
            shopping_list_names=[row.name or "" for row in shopping_list_rows],
        )

    def _apply(self, website: ShoppingWebsite, data: ShoppingWebsiteCreate | ShoppingWebsiteUpdate) -> None:
        website.name = data.name.strip()
        website.url = normalize_url(data.url)
        website.page_food = (data.page_food or "").strip() or None
        website.offered_foods_json = json.dumps(normalize_terms(data.offered_foods), ensure_ascii=False)
        website.is_recipe_site = data.is_recipe_site
        website.is_shopping_site = data.is_shopping_site

    async def _fetch_url_text(self, url: str) -> str:
        chunks: list[bytes] = []
        total = 0
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            async with client.stream("GET", url, headers={"User-Agent": "Mealie Shopping Websites/1.0"}) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    remaining = MAX_PAGE_BYTES - total
                    if remaining <= 0:
                        break
                    chunks.append(chunk[:remaining])
                    total += min(len(chunk), remaining)
        return clean_html_text(b"".join(chunks).decode("utf-8", errors="replace"))

    async def _analyze(
        self,
        url: str,
        page_text: str,
        page_title: str | None = None,
        is_recipe_site: bool | None = None,
        is_shopping_site: bool | None = None,
    ) -> ShoppingWebsiteCreate:
        if not self._ai_enabled():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("OpenAI services are not enabled"),
            )
        normalized_url = normalize_url(url)
        message_parts = [
            f"Website URL: {normalized_url}",
            "Required metadata language: Hebrew. Keep only the official site/business name in its established form.",
        ]
        if page_title:
            message_parts.append(f"Page title: {page_title.strip()}")
        message_parts.extend(["", page_text[:MAX_PAGE_TEXT]])
        openai_service = OpenAIService(self.repos)
        response = await openai_service.get_response(
            openai_service.get_prompt("websites.parse-shopping-website"),
            "\n".join(message_parts),
            response_schema=OpenAIShoppingWebsite,
        )
        if not response or not response.is_food_website or not response.name.strip():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("The provided page does not look like a food recipe or shopping website"),
            )
        resolved_recipe_site = response.is_recipe_site if is_recipe_site is None else is_recipe_site
        resolved_shopping_site = response.is_shopping_site if is_shopping_site is None else is_shopping_site
        if not resolved_recipe_site and not resolved_shopping_site:
            resolved_recipe_site = response.is_recipe_site
            resolved_shopping_site = response.is_shopping_site
        if not resolved_recipe_site and not resolved_shopping_site:
            resolved_shopping_site = True
        return ShoppingWebsiteCreate(
            name=response.name.strip(),
            url=normalized_url,
            page_food=response.page_food.strip() or None,
            offered_foods=normalize_terms(response.offered_foods),
            is_recipe_site=resolved_recipe_site,
            is_shopping_site=resolved_shopping_site,
        )

    def _create_or_update(self, data: ShoppingWebsiteCreate) -> ShoppingWebsiteOut:
        normalized_url = normalize_url(data.url)
        website = self.session.execute(
            sa.select(ShoppingWebsite).where(
                ShoppingWebsite.group_id == self.group_id,
                ShoppingWebsite.url == normalized_url,
            )
        ).scalar_one_or_none()
        if website is None:
            website = ShoppingWebsite(
                group_id=self.group_id,
                household_id=self.household_id,
                user_id=self.user.id,
                name=data.name.strip(),
                url=normalized_url,
                session=self.session,
            )
        self._apply(website, data.model_copy(update={"url": normalized_url}))
        self.session.add(website)
        self.session.commit()
        self.session.refresh(website)
        return self._to_out(website)

    @router.get("", response_model=list[ShoppingWebsiteOut])
    def get_all(self, search: str | None = Query(None)) -> list[ShoppingWebsiteOut]:
        query = (search or "").strip().casefold()
        if query in {"undefined", "null"}:
            query = ""
        statement = sa.select(ShoppingWebsite).where(ShoppingWebsite.group_id == self.group_id)
        if query:
            escaped_query = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped_query}%"
            statement = statement.where(
                sa.or_(
                    ShoppingWebsite.name.ilike(pattern, escape="\\"),
                    ShoppingWebsite.url.ilike(pattern, escape="\\"),
                    ShoppingWebsite.page_food.ilike(pattern, escape="\\"),
                    ShoppingWebsite.offered_foods_json.ilike(pattern, escape="\\"),
                )
            )
        websites = (
            self.session.execute(statement.order_by(ShoppingWebsite.created_at.desc(), ShoppingWebsite.name.asc()))
            .scalars()
            .all()
        )
        return [self._to_out(website) for website in websites]

    @router.post("", response_model=ShoppingWebsiteOut, status_code=status.HTTP_201_CREATED)
    def create(self, data: ShoppingWebsiteCreate) -> ShoppingWebsiteOut:
        return self._create_or_update(data)

    @router.post("/ai-create", response_model=ShoppingWebsiteOut, status_code=status.HTTP_201_CREATED)
    async def create_with_ai(self, data: ShoppingWebsiteAIRequest) -> ShoppingWebsiteOut:
        normalized_url = normalize_url(data.url)
        page_text = await self._fetch_url_text(normalized_url)
        if not page_text:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail=ErrorResponse.respond("The website returned no text")
            )
        return self._create_or_update(
            await self._analyze(
                normalized_url,
                page_text,
                is_recipe_site=data.is_recipe_site,
                is_shopping_site=data.is_shopping_site,
            )
        )

    @router.post("/ai-discover", response_model=list[ShoppingWebsiteCreate])
    async def discover_with_ai(self, data: ShoppingWebsiteDiscoveryRequest) -> list[ShoppingWebsiteCreate]:
        if not self._ai_enabled():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("OpenAI services are not enabled"),
            )
        openai_service = OpenAIService(self.repos)
        response = await openai_service.get_response(
            openai_service.get_prompt("websites.discover-shopping-websites"),
            (
                f"User request: {data.prompt.strip()}\nMaximum results: {data.limit}\n"
                "Required metadata language: Hebrew. Keep official site/business names in their established form."
            ),
            response_schema=OpenAIShoppingWebsiteSuggestions,
        )
        suggestions: list[ShoppingWebsiteCreate] = []
        seen_urls: set[str] = set()
        for item in (response.items if response else [])[: data.limit]:
            if not item.is_food_website or not item.name.strip() or not item.url:
                continue
            try:
                normalized_url = normalize_url(item.url)
            except HTTPException:
                continue
            if normalized_url in seen_urls:
                continue
            seen_urls.add(normalized_url)
            is_recipe_site = bool(item.is_recipe_site)
            is_shopping_site = bool(item.is_shopping_site)
            if not is_recipe_site and not is_shopping_site:
                is_shopping_site = True
            suggestions.append(
                ShoppingWebsiteCreate(
                    name=item.name.strip(),
                    url=normalized_url,
                    page_food=item.page_food.strip() or None,
                    offered_foods=normalize_terms(item.offered_foods),
                    is_recipe_site=is_recipe_site,
                    is_shopping_site=is_shopping_site,
                )
            )
        return suggestions

    @router.post("/browser-page", response_model=ShoppingWebsiteOut, status_code=status.HTTP_201_CREATED)
    async def create_from_browser_page(self, data: ShoppingWebsiteBrowserPageRequest) -> ShoppingWebsiteOut:
        return self._create_or_update(
            await self._analyze(
                data.url,
                data.page_text,
                data.page_title,
                data.is_recipe_site,
                data.is_shopping_site,
            )
        )

    @router.put("/links/recipe/{recipe_id}", response_model=list[ShoppingWebsiteOut])
    def update_recipe_links(
        self,
        recipe_id: UUID4,
        data: ShoppingWebsiteEntityLinksUpdate,
    ) -> list[ShoppingWebsiteOut]:
        recipe_exists = self.session.execute(
            sa.select(RecipeModel.id).where(RecipeModel.id == recipe_id, RecipeModel.group_id == self.group_id)
        ).scalar_one_or_none()
        if recipe_exists is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Recipe not found")
        website_ids = self._validated_website_ids(data.website_ids)
        self.session.execute(sa.delete(RecipeShoppingWebsite).where(RecipeShoppingWebsite.recipe_id == recipe_id))
        self.session.add_all(
            [RecipeShoppingWebsite(recipe_id=recipe_id, shopping_website_id=website_id) for website_id in website_ids]
        )
        self.session.commit()
        websites = self.session.execute(
            sa.select(ShoppingWebsite).where(ShoppingWebsite.id.in_(website_ids)).order_by(ShoppingWebsite.name)
        ).scalars().all()
        return [self._to_out(website) for website in websites]

    @router.put("/links/shopping-list/{shopping_list_id}", response_model=list[ShoppingWebsiteOut])
    def update_shopping_list_links(
        self,
        shopping_list_id: UUID4,
        data: ShoppingWebsiteEntityLinksUpdate,
    ) -> list[ShoppingWebsiteOut]:
        shopping_list_exists = self.session.execute(
            sa.select(ShoppingList.id).where(
                ShoppingList.id == shopping_list_id,
                ShoppingList.group_id == self.group_id,
            )
        ).scalar_one_or_none()
        if shopping_list_exists is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Shopping list not found")
        website_ids = self._validated_website_ids(data.website_ids)
        self.session.execute(
            sa.delete(ShoppingListShoppingWebsite).where(
                ShoppingListShoppingWebsite.shopping_list_id == shopping_list_id
            )
        )
        self.session.add_all(
            [
                ShoppingListShoppingWebsite(shopping_list_id=shopping_list_id, shopping_website_id=website_id)
                for website_id in website_ids
            ]
        )
        self.session.commit()
        websites = self.session.execute(
            sa.select(ShoppingWebsite).where(ShoppingWebsite.id.in_(website_ids)).order_by(ShoppingWebsite.name)
        ).scalars().all()
        return [self._to_out(website) for website in websites]

    @router.get("/{website_id}/delete-preview", response_model=ShoppingWebsiteDeletePreview)
    def delete_preview(self, website_id: UUID4) -> ShoppingWebsiteDeletePreview:
        self._get_or_404(website_id)
        return self._linked_entities(website_id)

    @router.get("/{website_id}", response_model=ShoppingWebsiteOut)
    def get_one(self, website_id: UUID4) -> ShoppingWebsiteOut:
        return self._to_out(self._get_or_404(website_id))

    @router.put("/{website_id}", response_model=ShoppingWebsiteOut)
    def update(self, website_id: UUID4, data: ShoppingWebsiteUpdate) -> ShoppingWebsiteOut:
        website = self._get_or_404(website_id)
        self._apply(website, data)
        self.session.add(website)
        self.session.commit()
        self.session.refresh(website)
        return self._to_out(website)

    @router.get("/{website_id}/image", response_class=FileResponse)
    def get_image(self, website_id: UUID4) -> FileResponse:
        website = self._get_or_404(website_id)
        path = self._image_path(website)
        if not path.exists():
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        return FileResponse(
            path,
            media_type="image/webp",
            content_disposition_type="inline",
            headers={"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff"},
        )

    @router.post("/{website_id}/image", response_model=ShoppingWebsiteOut)
    async def upload_image(self, website_id: UUID4, image: UploadFile = File(...)) -> ShoppingWebsiteOut:
        website = self._get_or_404(website_id)
        content = await image.read(12 * 1024 * 1024 + 1)
        await image.close()
        try:
            await self.image_service.save_content(self._image_path(website), content)
        except ValueError as error:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond(str(error)),
            ) from error
        return self._to_out(website)

    @router.post("/{website_id}/image-url", response_model=ShoppingWebsiteOut)
    async def save_image_url(
        self,
        website_id: UUID4,
        data: ShoppingWebsiteImageURLRequest,
    ) -> ShoppingWebsiteOut:
        website = self._get_or_404(website_id)
        try:
            await self.image_service.save_url(self._image_path(website), data.url)
        except (ValueError, httpx.HTTPError) as error:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond(str(error)),
            ) from error
        return self._to_out(website)

    @router.post("/{website_id}/image-auto", response_model=ShoppingWebsiteOut)
    async def find_image(self, website_id: UUID4) -> ShoppingWebsiteOut:
        website = self._get_or_404(website_id)
        try:
            await self.image_service.discover_and_save_page_image(self._image_path(website), website.url)
        except (ValueError, httpx.HTTPError) as error:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond(str(error)),
            ) from error
        return self._to_out(website)

    @router.delete("/{website_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete(
        self,
        website_id: UUID4,
        delete_recipes: bool = Query(False),
        delete_shopping_lists: bool = Query(False),
    ) -> None:
        website = self._get_or_404(website_id)
        linked = self._linked_entities(website_id)
        if delete_recipes and linked.recipe_ids:
            recipe_slugs = list(
                self.session.execute(
                    sa.select(RecipeModel.slug).where(
                        RecipeModel.id.in_(linked.recipe_ids),
                        RecipeModel.group_id == self.group_id,
                    )
                ).scalars()
            )
            RecipeService(self.repos, self.user, self.household, translator=self.translator).delete_many(recipe_slugs)
        if delete_shopping_lists and linked.shopping_list_ids:
            self.repos.group_shopping_lists.delete_many(linked.shopping_list_ids)
        image_dir = self._image_path(website).parent
        self.session.delete(website)
        self.session.commit()
        shutil.rmtree(image_dir, ignore_errors=True)
