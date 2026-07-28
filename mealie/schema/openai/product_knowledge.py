from pydantic import Field

from ._base import OpenAIBase


class OpenAIProductKnowledge(OpenAIBase):
    title: str = Field(..., description="Clear product or ingredient name in the requested language.")
    summary: str = Field("", description="Short practical summary.")
    content: str = Field(
        ...,
        description="Detailed, structured Markdown explanation suitable for a cooking reference library.",
    )
    source: str = Field("", description="Optional concise source or source note when one is known.")
    categories: list[str] = Field(default_factory=list, description="Broad cooking-reference categories.")
    tags: list[str] = Field(default_factory=list, description="Specific searchable product and cooking terms.")
