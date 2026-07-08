from datetime import datetime

from pydantic import UUID4, ConfigDict, Field

from mealie.schema._mealie import MealieModel
from mealie.schema._mealie.mealie_model import UpdatedAtField


class ArticleBase(MealieModel):
    title: str = Field(..., min_length=1, max_length=255)
    summary: str | None = None
    content: str = Field(..., min_length=1)
    source: str | None = Field(None, max_length=1000)
    author: str | None = Field(None, max_length=255)
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class ArticleCreate(ArticleBase): ...


class ArticleUpdate(ArticleBase): ...


class ArticleOut(ArticleBase):
    id: UUID4
    group_id: UUID4
    household_id: UUID4
    user_id: UUID4
    slug: str
    created_at: datetime | None = None
    updated_at: datetime | None = UpdatedAtField(default=None)

    model_config = ConfigDict(from_attributes=True)


class ArticleAIRequest(MealieModel):
    text: str | None = Field(None, max_length=250000)
    url: str | None = Field(None, max_length=2000)
    translate_language: str | None = None


class ArticleAISearchRequest(MealieModel):
    query: str = Field(..., min_length=1, max_length=4000)
    limit: int = Field(10, ge=1, le=50)


class ArticleAISearchItem(MealieModel):
    id: UUID4
    score: float = Field(0, ge=0, le=1)
    reason: str = ""


class ArticleAISearchResponse(MealieModel):
    items: list[ArticleAISearchItem] = Field(default_factory=list)
