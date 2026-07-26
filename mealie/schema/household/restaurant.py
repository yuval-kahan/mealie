from datetime import datetime
from typing import Literal, Self

from pydantic import UUID4, ConfigDict, Field, model_validator

from mealie.schema._mealie import MealieModel
from mealie.schema._mealie.mealie_model import UpdatedAtField

RestaurantRecommendationStatus = Literal[
    "strongly_recommended",
    "recommended",
    "neutral",
    "not_recommended",
    "strongly_not_recommended",
]
RestaurantVisitStatus = Literal["not_tried", "tried"]


class RestaurantBase(MealieModel):
    name: str = Field(..., min_length=1, max_length=255)
    website_url: str | None = Field(None, max_length=2000)
    cuisine_types: list[str] = Field(default_factory=list)
    addresses: list[str] = Field(default_factory=list)
    phone: str | None = Field(None, max_length=120)
    price_range: str | None = Field(None, max_length=120)
    description: str | None = Field(None, max_length=8000)
    notes: str | None = Field(None, max_length=8000)
    michelin_info: str | None = Field(None, max_length=500)
    google_rating: float | None = Field(None, ge=0, le=5)
    google_review_count: int | None = Field(None, ge=0, le=100000000)
    google_maps_url: str | None = Field(None, max_length=2000)
    our_rating: float | None = Field(None, ge=0, le=5)
    recommendation_status: RestaurantRecommendationStatus = "recommended"
    visit_status: RestaurantVisitStatus = "not_tried"


class RestaurantCreate(RestaurantBase): ...


class RestaurantUpdate(RestaurantBase): ...


class RestaurantOut(RestaurantBase):
    id: UUID4
    group_id: UUID4
    household_id: UUID4
    user_id: UUID4
    created_at: datetime | None = None
    updated_at: datetime | None = UpdatedAtField(default=None)

    model_config = ConfigDict(from_attributes=True)


class RestaurantAIRequest(MealieModel):
    name: str | None = Field(None, max_length=255)
    url: str | None = Field(None, max_length=2000)

    @model_validator(mode="after")
    def require_name_or_url(self) -> Self:
        if not (self.name or "").strip() and not (self.url or "").strip():
            raise ValueError("Restaurant name or URL is required")
        return self


class RestaurantBrowserPageRequest(MealieModel):
    url: str = Field(..., min_length=1, max_length=2000)
    page_title: str | None = Field(None, max_length=500)
    page_text: str = Field(..., min_length=1, max_length=250000)
