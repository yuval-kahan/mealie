from datetime import datetime

from pydantic import UUID4, ConfigDict, Field, model_validator

from mealie.schema._mealie import MealieModel
from mealie.schema._mealie.mealie_model import UpdatedAtField


class ShoppingWebsiteBase(MealieModel):
    name: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., min_length=1, max_length=2000)
    page_food: str | None = Field(None, max_length=4000)
    offered_foods: list[str] = Field(default_factory=list)
    is_recipe_site: bool = False
    is_shopping_site: bool = True

    @model_validator(mode="after")
    def validate_site_types(self):
        if not self.is_recipe_site and not self.is_shopping_site:
            raise ValueError("Select at least one website type")
        return self


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
    is_recipe_site: bool | None = None
    is_shopping_site: bool | None = None


class ShoppingWebsiteDiscoveryRequest(MealieModel):
    prompt: str = Field(..., min_length=2, max_length=4000)
    limit: int = Field(8, ge=1, le=20)


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
