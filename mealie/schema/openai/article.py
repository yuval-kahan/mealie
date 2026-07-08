from pydantic import Field

from ._base import OpenAIBase


class OpenAIArticle(OpenAIBase):
    is_article: bool = Field(
        True,
        description="False when the input is not a usable article or article-like educational text.",
    )
    title: str = Field("", description="Article title.")
    summary: str = Field("", description="Short summary of the article.")
    content: str = Field("", description="Full article content, preserving all meaningful information.")
    source: str = Field("", description="Source URL, site, book, publication, show, or other origin when known.")
    author: str = Field("", description="Author, chef, publication, or creator when known.")
    categories: list[str] = Field(default_factory=list, description="Article categories.")
    tags: list[str] = Field(default_factory=list, description="Specific searchable article tags.")


class OpenAIArticleSearchItem(OpenAIBase):
    id: str = Field("", description="Article id from the provided catalog.")
    score: float = Field(0, ge=0, le=1, description="Relevance score from 0 to 1.")
    reason: str = Field("", description="Short reason this article matches the user's search.")


class OpenAIArticleSearchResponse(OpenAIBase):
    results: list[OpenAIArticleSearchItem] = Field(default_factory=list)
