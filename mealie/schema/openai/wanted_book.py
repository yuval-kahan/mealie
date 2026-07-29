from pydantic import Field

from ._base import OpenAIBase


class OpenAIWantedBook(OpenAIBase):
    is_book: bool = Field(..., description="True only when the supplied page or request describes a real book.")
    title: str = Field("", description="The book title without shop boilerplate.")
    subtitle: str | None = None
    authors: list[str] = Field(default_factory=list)
    isbn_10: str | None = None
    isbn_13: str | None = None
    publisher: str | None = None
    published_year: int | None = None
    summary: str | None = None
    source_url: str | None = None
    cover_image_url: str | None = None
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
