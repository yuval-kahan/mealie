from pydantic import Field

from ._base import OpenAIBase


class OpenAIRecipeSearchItem(OpenAIBase):
    slug: str = Field(
        ...,
        description="The exact slug of an existing recipe from the provided catalog.",
    )

    reason: str = Field(
        "",
        description="A short explanation of why this recipe matches the user's request.",
    )

    score: int = Field(
        0,
        ge=0,
        le=100,
        description="Relevance score from 0 to 100.",
    )


class OpenAIRecipeSearchResponse(OpenAIBase):
    results: list[OpenAIRecipeSearchItem] = Field(
        default_factory=list,
        description="Matching existing recipes from the provided catalog, ordered by relevance.",
    )
