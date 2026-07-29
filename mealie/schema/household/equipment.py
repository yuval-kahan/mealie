from pydantic import UUID4, Field

from mealie.schema._mealie import MealieModel


class EquipmentRecipeSummary(MealieModel):
    slug: str
    name: str


class EquipmentOut(MealieModel):
    id: UUID4
    group_id: UUID4
    name: str
    slug: str
    category: str | None = None
    description: str | None = None
    image_source_url: str | None = None
    ai_enriched: bool = False
    has_image: bool = False
    image_version: str | None = None
    recipe_count: int = 0
    recipes: list[EquipmentRecipeSummary] = Field(default_factory=list)


class EquipmentCreate(MealieModel):
    name: str = Field(..., min_length=1, max_length=255)
    category: str | None = Field(None, max_length=120)
    description: str | None = Field(None, max_length=4000)


class EquipmentAICreateRequest(MealieModel):
    prompt: str = Field(..., min_length=2, max_length=8000)
    name: str | None = Field(None, max_length=255)


class EquipmentUpdate(MealieModel):
    category: str | None = Field(None, max_length=120)
    description: str | None = Field(None, max_length=4000)


class EquipmentImageURLRequest(MealieModel):
    url: str = Field(..., min_length=8, max_length=4000)
