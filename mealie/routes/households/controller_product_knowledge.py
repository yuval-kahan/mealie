import json
import re

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import UUID4

from mealie.db.models.household.product_knowledge import ProductKnowledge
from mealie.routes._base import controller
from mealie.routes._base.base_controllers import BaseUserController
from mealie.schema.household.product_knowledge import (
    ProductKnowledgeAIRequest,
    ProductKnowledgeCreate,
    ProductKnowledgeOut,
    ProductKnowledgeUpdate,
)
from mealie.schema.openai.product_knowledge import OpenAIProductKnowledge
from mealie.schema.response.responses import ErrorResponse
from mealie.services.openai import OpenAIService

router = APIRouter(prefix="/households/product-knowledge", tags=["Households: Product Knowledge"])

SPACE_RE = re.compile(r"\s+")


def normalize_terms(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        item = SPACE_RE.sub(" ", str(value).strip())[:100]
        key = item.casefold()
        if item and key not in seen:
            seen.add(key)
            result.append(item)
    return result[:40]


@controller(router)
class ProductKnowledgeController(BaseUserController):
    def _ai_enabled(self) -> bool:
        settings = self.session.execute(
            sa.text("SELECT id, default_provider_id FROM ai_provider_settings WHERE group_id = :group_id"),
            {"group_id": self.repos.uuid_to_str(self.group_id)},
        ).mappings().one_or_none()
        if not settings or not settings["default_provider_id"]:
            return False
        return bool(
            self.session.execute(
                sa.text("SELECT 1 FROM ai_providers WHERE id = :provider_id AND settings_id = :settings_id LIMIT 1"),
                {"provider_id": settings["default_provider_id"], "settings_id": settings["id"]},
            ).scalar()
        )

    def _to_out(self, item: ProductKnowledge) -> ProductKnowledgeOut:
        return ProductKnowledgeOut(
            id=item.id,
            group_id=item.group_id,
            household_id=item.household_id,
            user_id=item.user_id,
            title=item.title,
            summary=item.summary,
            content=item.content,
            source=item.source,
            categories=json.loads(item.categories_json or "[]"),
            tags=json.loads(item.tags_json or "[]"),
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    def _get_or_404(self, item_id: UUID4) -> ProductKnowledge:
        item = self.session.execute(
            sa.select(ProductKnowledge).where(
                ProductKnowledge.id == item_id,
                ProductKnowledge.group_id == self.group_id,
            )
        ).scalar_one_or_none()
        if item is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        return item

    def _apply(
        self,
        item: ProductKnowledge,
        data: ProductKnowledgeCreate | ProductKnowledgeUpdate,
    ) -> None:
        item.title = SPACE_RE.sub(" ", data.title.strip())[:255]
        item.summary = (data.summary or "").strip() or None
        item.content = data.content.strip()
        item.source = (data.source or "").strip() or None
        item.categories_json = json.dumps(normalize_terms(data.categories), ensure_ascii=False)
        item.tags_json = json.dumps(normalize_terms(data.tags), ensure_ascii=False)

    def _create(self, data: ProductKnowledgeCreate) -> ProductKnowledgeOut:
        item = ProductKnowledge(
            group_id=self.group_id,
            household_id=self.household_id,
            user_id=self.user.id,
            title=data.title.strip(),
            content=data.content.strip(),
            session=self.session,
        )
        self._apply(item, data)
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return self._to_out(item)

    @router.get("", response_model=list[ProductKnowledgeOut])
    def get_all(
        self,
        search: str | None = Query(None),
        categories: list[str] | None = Query(None),
        tags: list[str] | None = Query(None),
    ) -> list[ProductKnowledgeOut]:
        statement = sa.select(ProductKnowledge).where(ProductKnowledge.group_id == self.group_id)
        query = (search or "").strip()
        if query:
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            statement = statement.where(
                sa.or_(
                    ProductKnowledge.title.ilike(pattern, escape="\\"),
                    ProductKnowledge.summary.ilike(pattern, escape="\\"),
                    ProductKnowledge.content.ilike(pattern, escape="\\"),
                    ProductKnowledge.categories_json.ilike(pattern, escape="\\"),
                    ProductKnowledge.tags_json.ilike(pattern, escape="\\"),
                )
            )
        rows = self.session.execute(
            statement.order_by(ProductKnowledge.created_at.desc(), ProductKnowledge.title.asc())
        ).scalars().all()
        category_set = {value.casefold() for value in categories or []}
        tag_set = {value.casefold() for value in tags or []}
        result: list[ProductKnowledgeOut] = []
        for row in rows:
            item = self._to_out(row)
            if category_set and not category_set.intersection(value.casefold() for value in item.categories):
                continue
            if tag_set and not tag_set.intersection(value.casefold() for value in item.tags):
                continue
            result.append(item)
        return result

    @router.post("", response_model=ProductKnowledgeOut, status_code=status.HTTP_201_CREATED)
    def create_one(self, data: ProductKnowledgeCreate) -> ProductKnowledgeOut:
        return self._create(data)

    @router.post("/ai-create", response_model=ProductKnowledgeOut, status_code=status.HTTP_201_CREATED)
    async def create_with_ai(self, data: ProductKnowledgeAIRequest) -> ProductKnowledgeOut:
        if not self._ai_enabled():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("OpenAI services are not enabled"),
            )
        target_language = (data.target_language or "").strip()
        message = f"Topic or product: {data.topic.strip()}"
        if target_language:
            message = f"Target language: {target_language}\n\n{message}"
        openai_service = OpenAIService(self.repos)
        response = await openai_service.get_response(
            openai_service.get_prompt("products.explain-product"),
            message,
            response_schema=OpenAIProductKnowledge,
        )
        if not response or not response.title.strip() or not response.content.strip():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("The AI provider did not return a usable product explanation"),
            )
        return self._create(
            ProductKnowledgeCreate(
                title=response.title,
                summary=response.summary or None,
                content=response.content,
                source=response.source or None,
                categories=response.categories,
                tags=response.tags,
            )
        )

    @router.get("/{item_id}", response_model=ProductKnowledgeOut)
    def get_one(self, item_id: UUID4) -> ProductKnowledgeOut:
        return self._to_out(self._get_or_404(item_id))

    @router.put("/{item_id}", response_model=ProductKnowledgeOut)
    def update_one(self, item_id: UUID4, data: ProductKnowledgeUpdate) -> ProductKnowledgeOut:
        item = self._get_or_404(item_id)
        self._apply(item, data)
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return self._to_out(item)

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_one(self, item_id: UUID4) -> None:
        item = self._get_or_404(item_id)
        self.session.delete(item)
        self.session.commit()
