from pydantic import Field

from ._base import OpenAIBase
from .recipe import OpenAIRecipe


class OpenAIVideoAnalysis(OpenAIBase):
    is_food_video: bool = Field(..., description="True when the video is materially about food, cooking, or a recipe.")
    title: str = Field(
        "",
        description="A concise factual title. Preserve the original title when it is already useful.",
    )
    description: str = Field(
        "",
        description="A concise factual description based only on the audiovisual stream and supplied metadata.",
    )
    categories: list[str] = Field(default_factory=list, description="Short, useful food-video categories.")
    tags: list[str] = Field(default_factory=list, description="Short, useful discovery tags.")
    contains_complete_recipe: bool = Field(
        False,
        description=(
            "True only when the audiovisual material has a usable title, ingredients, and preparation instructions."
        ),
    )
    recipe: OpenAIRecipe | None = Field(
        None,
        description=(
            "The complete structured recipe found by inspecting the video's visual and audio streams. "
            "Use null unless contains_complete_recipe is true."
        ),
    )
