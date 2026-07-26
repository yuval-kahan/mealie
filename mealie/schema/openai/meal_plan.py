from typing import Literal

from pydantic import Field

from ._base import OpenAIBase


class OpenAIMealCourse(OpenAIBase):
    course: Literal["starter", "main", "side", "dessert"]
    slug: str = Field(..., description="The exact slug of an existing recipe from the supplied catalog.")
    reason: str = Field("", description="A short explanation of why this recipe fits the complete meal.")


class OpenAIMealPlanResponse(OpenAIBase):
    title: str = Field("", description="A short name for the complete meal.")
    explanation: str = Field("", description="A concise explanation of why the courses work together.")
    courses: list[OpenAIMealCourse] = Field(
        default_factory=list,
        description="The requested number of compatible existing recipes for each meal course.",
    )
