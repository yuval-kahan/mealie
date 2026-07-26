from datetime import datetime

from pydantic import UUID4, ConfigDict, Field

from mealie.schema._mealie import MealieModel
from mealie.schema._mealie.mealie_model import UpdatedAtField


class ShoppingWebsiteBase(MealieModel):
    name: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., min_length=1, max_length=2000)
    page_food: str | None = Field(None, max_length=4000)
    offered_foods: list[str] = Field(default_factory=list)


class ShoppingWebsiteCreate(ShoppingWebsiteBase): ...


class ShoppingWebsiteUpdate(ShoppingWebsiteBase): ...


class ShoppingWebsiteOut(ShoppingWebsiteBase):
    id: UUID4
    group_id: UUID4
    household_id: UUID4
    user_id: UUID4
    created_at: datetime | None = None
    updated_at: datetime | None = UpdatedAtField(default=None)
    recipe_ids: list[UUID4] = Field(default_factory=list)
    shopping_list_ids: list[UUID4] = Field(default_factory=list)
    has_image: bool = False
    image_version: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ShoppingWebsiteAIRequest(MealieModel):
    url: str = Field(..., min_length=1, max_length=2000)


class ShoppingWebsiteImageURLRequest(MealieModel):
    url: str = Field(..., min_length=1, max_length=4000)


class ShoppingWebsiteBrowserPageRequest(ShoppingWebsiteAIRequest):
    page_title: str | None = Field(None, max_length=500)
    page_text: str = Field(..., min_length=1, max_length=250000)


class ShoppingWebsiteEntityLinksUpdate(MealieModel):
    website_ids: list[UUID4] = Field(default_factory=list)


class ShoppingWebsiteDeletePreview(MealieModel):
    recipe_ids: list[UUID4] = Field(default_factory=list)
    recipe_names: list[str] = Field(default_factory=list)
    shopping_list_ids: list[UUID4] = Field(default_factory=list)
    shopping_list_names: list[str] = Field(default_factory=list)
