from datetime import datetime
from typing import Self

from pydantic import UUID4, ConfigDict, Field, model_validator

from mealie.schema._mealie import MealieModel
from mealie.schema._mealie.mealie_model import UpdatedAtField


class WantedBookBase(MealieModel):
    title: str = Field(..., min_length=1, max_length=500)
    subtitle: str | None = Field(None, max_length=1000)
    authors: list[str] = Field(default_factory=list)
    isbn_10: str | None = Field(None, max_length=32)
    isbn_13: str | None = Field(None, max_length=32)
    publisher: str | None = Field(None, max_length=255)
    published_year: int | None = Field(None, ge=1, le=9999)
    summary: str | None = Field(None, max_length=20000)
    source_url: str | None = Field(None, max_length=2000)
    cover_source_url: str | None = Field(None, max_length=2000)
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    notes: str | None = Field(None, max_length=8000)


class WantedBookCreate(WantedBookBase): ...


class WantedBookUpdate(WantedBookBase): ...


class WantedBookOut(WantedBookBase):
    id: UUID4
    group_id: UUID4
    household_id: UUID4
    user_id: UUID4
    has_image: bool = False
    image_version: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = UpdatedAtField(default=None)

    model_config = ConfigDict(from_attributes=True)


class WantedBookAIRequest(MealieModel):
    prompt: str | None = Field(None, max_length=12000)
    url: str | None = Field(None, max_length=2000)

    @model_validator(mode="after")
    def require_input(self) -> Self:
        if not (self.prompt or "").strip() and not (self.url or "").strip():
            raise ValueError("A book description or URL is required")
        return self


class WantedBookBrowserPageRequest(WantedBookAIRequest):
    page_title: str | None = Field(None, max_length=1000)
    page_text: str = Field(..., min_length=1, max_length=250000)
    page_image_url: str | None = Field(None, max_length=4000)


class WantedBookImageURLRequest(MealieModel):
    url: str = Field(..., min_length=8, max_length=4000)
