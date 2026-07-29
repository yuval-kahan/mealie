from datetime import datetime

from pydantic import UUID4, ConfigDict, Field

from mealie.schema._mealie import MealieModel
from mealie.schema._mealie.mealie_model import UpdatedAtField


class ProductKnowledgeBase(MealieModel):
    title: str = Field(..., min_length=1, max_length=255)
    summary: str | None = None
    content: str = Field(..., min_length=1)
    source: str | None = Field(None, max_length=2000)
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class ProductKnowledgeCreate(ProductKnowledgeBase): ...


class ProductKnowledgeUpdate(ProductKnowledgeBase): ...


class ProductKnowledgeOut(ProductKnowledgeBase):
    id: UUID4
    group_id: UUID4
    household_id: UUID4
    user_id: UUID4
    image_source_url: str | None = None
    has_image: bool = False
    image_version: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = UpdatedAtField(default=None)

    model_config = ConfigDict(from_attributes=True)


class ProductKnowledgeAIRequest(MealieModel):
    topic: str = Field(..., min_length=1, max_length=4000)
    target_language: str | None = Field(None, max_length=80)


class ProductKnowledgeImageURLRequest(MealieModel):
    url: str = Field(..., min_length=8, max_length=4000)
