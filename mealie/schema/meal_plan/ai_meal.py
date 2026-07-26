from enum import StrEnum
from uuid import UUID

from pydantic import Field

from mealie.schema._mealie import MealieModel
from mealie.schema.recipe.recipe import RecipeSummary

from .new_meal import PlanEntryType


class AIMealPeriod(StrEnum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"


class AIMealCourse(StrEnum):
    starter = "starter"
    main = "main"
    side = "side"
    dessert = "dessert"


class AIMealCourseCounts(MealieModel):
    starter: int = Field(1, ge=0, le=100)
    main: int = Field(1, ge=0, le=100)
    side: int = Field(1, ge=0, le=100)
    dessert: int = Field(1, ge=0, le=100)

    def count_for(self, course: AIMealCourse) -> int:
        return int(getattr(self, course.value))


class AIMealSuggestRequest(MealieModel):
    meal_period: AIMealPeriod
    request: str = Field(min_length=2, max_length=1000)
    anchor_recipe_id: UUID | None = None
    anchor_course: AIMealCourse = AIMealCourse.main
    course_counts: AIMealCourseCounts = Field(default_factory=AIMealCourseCounts)
    category_names: list[str] = Field(default_factory=list, max_length=25)
    tag_names: list[str] = Field(default_factory=list, max_length=25)


class AIMealSuggestionItem(MealieModel):
    course: AIMealCourse
    entry_type: PlanEntryType
    recipe: RecipeSummary
    reason: str = ""


class AIMealSuggestResponse(MealieModel):
    title: str = ""
    explanation: str = ""
    recipe_count: int = 0
    items: list[AIMealSuggestionItem] = Field(default_factory=list)
