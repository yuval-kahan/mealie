from datetime import datetime
from typing import Literal, Self

from pydantic import UUID4, ConfigDict, Field, model_validator

from mealie.schema._mealie import MealieModel
from mealie.schema._mealie.mealie_model import UpdatedAtField

ChefRank = Literal["world_class", "excellent", "good", "medium", "emerging"]


class ChefRelatedRestaurant(MealieModel):
    id: UUID4
    name: str
    michelin_star_count: int = 0


class ChefRelatedBook(MealieModel):
    id: UUID4
    name: str
    is_translated_book: bool = False


class ChefBase(MealieModel):
    name: str = Field(..., min_length=1, max_length=255)
    aliases: list[str] = Field(default_factory=list)
    rank: ChefRank = "good"
    country: str | None = Field(None, max_length=120)
    cuisines: list[str] = Field(default_factory=list)
    specialties: list[str] = Field(default_factory=list)
    biography: str | None = Field(None, max_length=20000)
    career_summary: str | None = Field(None, max_length=20000)
    awards: list[str] = Field(default_factory=list)
    notable_restaurants: list[str] = Field(default_factory=list)
    book_titles: list[str] = Field(default_factory=list)
    website_url: str | None = Field(None, max_length=2000)
    wikipedia_url: str | None = Field(None, max_length=2000)
    instagram_url: str | None = Field(None, max_length=2000)
    has_michelin_restaurant: bool = False
    michelin_star_count: int = Field(0, ge=0, le=99)
    michelin_summary: str | None = Field(None, max_length=8000)
    notes: str | None = Field(None, max_length=8000)
    restaurant_ids: list[UUID4] = Field(default_factory=list)
    uploaded_book_ids: list[UUID4] = Field(default_factory=list)


class ChefCreate(ChefBase): ...


class ChefUpdate(ChefBase): ...


class ChefOut(ChefBase):
    id: UUID4
    group_id: UUID4
    household_id: UUID4
    user_id: UUID4
    restaurants: list[ChefRelatedRestaurant] = Field(default_factory=list)
    uploaded_books: list[ChefRelatedBook] = Field(default_factory=list)
    has_image: bool = False
    image_version: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = UpdatedAtField(default=None)

    model_config = ConfigDict(from_attributes=True)


class ChefAIRequest(MealieModel):
    prompt: str | None = Field(None, max_length=12000)
    name: str | None = Field(None, max_length=255)
    url: str | None = Field(None, max_length=2000)

    @model_validator(mode="after")
    def require_input(self) -> Self:
        if not (self.prompt or "").strip() and not (self.name or "").strip() and not (self.url or "").strip():
            raise ValueError("Chef prompt, name, or URL is required")
        return self


class ChefBrowserPageRequest(ChefAIRequest):
    page_title: str | None = Field(None, max_length=1000)
    page_text: str = Field(..., min_length=1, max_length=250000)
    page_image_url: str | None = Field(None, max_length=4000)


class ChefImageURLRequest(MealieModel):
    url: str = Field(..., min_length=8, max_length=4000)
