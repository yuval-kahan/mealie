from pydantic import Field

from mealie.schema._mealie import MealieModel

from .recipe import RecipeSummary


class RecipeAISearchRequest(MealieModel):
    query: str = Field(..., min_length=2, max_length=4000)
    limit: int = Field(10, ge=1, le=50)


class RecipeAISearchResult(MealieModel):
    recipe: RecipeSummary
    reason: str = ""
    score: int | None = Field(None, ge=0, le=100)


class RecipeAISearchResponse(MealieModel):
    query: str
    items: list[RecipeAISearchResult] = Field(default_factory=list)
    recipe_count: int = 0
