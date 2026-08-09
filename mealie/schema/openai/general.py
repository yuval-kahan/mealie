from pydantic import Field

from ._base import OpenAIBase


class OpenAIText(OpenAIBase):
    text: str = Field(..., description="A simple response message")


class OpenAIImageSearchQuery(OpenAIBase):
    key: str = Field(..., description="The exact item key supplied in the request")
    query: str = Field(..., description="A concise English public image search query")


class OpenAIImageSearchQueries(OpenAIBase):
    queries: list[OpenAIImageSearchQuery] = Field(default_factory=list)


class OpenAIImageSuitability(OpenAIBase):
    suitable: bool = Field(..., description="Whether the supplied image clearly matches the requested item")
    reason: str = Field("", description="A short explanation for the decision")


class OpenAIBookClassification(OpenAIBase):
    summary: str = ""
    cuisines: list[str] = Field(default_factory=list)
    difficulty: str = "unspecified"
    book_type: str = "cookbook"
    teaching_level: str = "reference"
    author_or_chef: str = ""
    restaurant: str = ""
    michelin_related: bool = False
    techniques: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    language: str = ""


class OpenAICookbookChapter(OpenAIBase):
    title: str
    recipe_slugs: list[str] = Field(default_factory=list)


class OpenAICookbookPlan(OpenAIBase):
    title: str
    introduction: str = ""
    chapters: list[OpenAICookbookChapter] = Field(default_factory=list)
