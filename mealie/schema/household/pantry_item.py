from datetime import datetime

from pydantic import UUID4, ConfigDict, Field

from mealie.schema._mealie import MealieModel
from mealie.schema._mealie.mealie_model import UpdatedAtField
from mealie.schema.recipe.recipe import RecipeSummary


class PantryItemBase(MealieModel):
    name: str = Field(..., min_length=1, max_length=255)
    quantity: float | None = Field(None, ge=0, le=1000000000)
    unit: str | None = Field(None, max_length=120)
    category: str | None = Field(None, max_length=160)
    note: str | None = Field(None, max_length=1000)


class PantryItemCreate(PantryItemBase): ...


class PantryItemUpdate(PantryItemBase): ...


class PantryItemOut(PantryItemBase):
    id: UUID4
    group_id: UUID4
    household_id: UUID4
    user_id: UUID4
    created_at: datetime | None = None
    updated_at: datetime | None = UpdatedAtField(default=None)

    model_config = ConfigDict(from_attributes=True)


class PantryRecipeSuggestionRequest(MealieModel):
    use_ai: bool = False
    available_text: str | None = Field(None, max_length=8000)
    limit: int = Field(12, ge=1, le=50)


class PantryRecipeSuggestion(MealieModel):
    recipe: RecipeSummary
    matched_items: list[str] = Field(default_factory=list)
    missing_ingredients: list[str] = Field(default_factory=list)
    reason: str = ""
    score: int = Field(0, ge=0, le=100)


class PantryRecipeSuggestionResponse(MealieModel):
    items: list[PantryRecipeSuggestion] = Field(default_factory=list)
    available_items: list[str] = Field(default_factory=list)
    recipe_count: int = 0
