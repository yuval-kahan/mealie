from datetime import datetime
from typing import Any, Literal

from pydantic import UUID4, ConfigDict, Field, model_validator

from mealie.schema._mealie import MealieModel
from mealie.schema._mealie.mealie_model import UpdatedAtField
from mealie.schema.openai._base import OpenAIBase

NotebookNodeType = Literal["section_group", "section", "page"]


class NotebookHighlightCategory(MealieModel):
    id: str = Field(..., min_length=1, max_length=80)
    name: str = Field(..., min_length=1, max_length=80)
    color: str = Field("#fff59d", min_length=4, max_length=32)


class NotebookBase(MealieModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=5000)
    color: str = Field("#ef8a1f", min_length=4, max_length=32)
    icon: str = Field("notebook", min_length=1, max_length=64)
    is_favorite: bool = False
    is_pinned: bool = False
    position: int = Field(0, ge=0, le=1_000_000)
    settings: dict[str, Any] = Field(default_factory=dict)


class NotebookCreate(NotebookBase):
    create_starter_page: bool = True


class NotebookUpdate(NotebookBase): ...


class NotebookSummary(NotebookBase):
    id: UUID4
    group_id: UUID4
    household_id: UUID4
    user_id: UUID4
    node_count: int = 0
    page_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = UpdatedAtField(default=None)

    model_config = ConfigDict(from_attributes=True)


class NotebookNodeBase(MealieModel):
    parent_id: UUID4 | None = None
    node_type: NotebookNodeType = "page"
    title: str = Field(..., min_length=1, max_length=255)
    content_html: str = Field("", max_length=5_000_000)
    position: int = Field(0, ge=0, le=1_000_000)
    is_collapsed: bool = False
    is_favorite: bool = False
    is_pinned: bool = False
    color: str | None = Field(None, max_length=32)
    tags: list[str] = Field(default_factory=list, max_length=100)
    categories: list[str] = Field(default_factory=list, max_length=100)
    highlight_categories: list[NotebookHighlightCategory] = Field(default_factory=list, max_length=30)
    settings: dict[str, Any] = Field(default_factory=dict)


class NotebookNodeCreate(NotebookNodeBase): ...


class NotebookNodeUpdate(MealieModel):
    parent_id: UUID4 | None = None
    node_type: NotebookNodeType | None = None
    title: str | None = Field(None, min_length=1, max_length=255)
    content_html: str | None = Field(None, max_length=5_000_000)
    position: int | None = Field(None, ge=0, le=1_000_000)
    is_collapsed: bool | None = None
    is_favorite: bool | None = None
    is_pinned: bool | None = None
    color: str | None = Field(None, max_length=32)
    tags: list[str] | None = Field(None, max_length=100)
    categories: list[str] | None = Field(None, max_length=100)
    highlight_categories: list[NotebookHighlightCategory] | None = Field(None, max_length=30)
    settings: dict[str, Any] | None = None
    expected_version: int | None = Field(None, ge=1)


class NotebookNodeOut(NotebookNodeBase):
    id: UUID4
    notebook_id: UUID4
    group_id: UUID4
    household_id: UUID4
    user_id: UUID4
    content_version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = UpdatedAtField(default=None)

    model_config = ConfigDict(from_attributes=True)


class NotebookDetail(NotebookSummary):
    nodes: list[NotebookNodeOut] = Field(default_factory=list)


class NotebookNodeMoveRequest(MealieModel):
    parent_id: UUID4 | None = None
    position: int = Field(0, ge=0, le=1_000_000)


class NotebookNodeBulkMoveRequest(MealieModel):
    node_ids: list[UUID4] = Field(..., min_length=1, max_length=500)
    parent_id: UUID4 | None = None
    start_position: int = Field(0, ge=0, le=1_000_000)

    @model_validator(mode="after")
    def unique_nodes(self):
        if len(set(self.node_ids)) != len(self.node_ids):
            raise ValueError("Duplicate node ids are not allowed")
        return self


class NotebookRevisionOut(MealieModel):
    id: UUID4
    node_id: UUID4
    user_id: UUID4
    title: str
    content_html: str
    settings: dict[str, Any] = Field(default_factory=dict)
    content_version: int
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class NotebookSearchResult(MealieModel):
    notebook_id: UUID4
    notebook_title: str
    node_id: UUID4
    node_title: str
    node_type: NotebookNodeType
    excerpt: str = ""
    updated_at: datetime | None = UpdatedAtField(default=None)


class NotebookTOCRequest(MealieModel):
    language: str = Field("en-US", min_length=2, max_length=32)
    pages_per_chunk: int = Field(8, ge=2, le=20)


class NotebookTOCEntry(OpenAIBase):
    node_id: str = Field(..., description="The exact notebook page id supplied in the input.")
    title: str = Field(..., description="A concise, meaningful title for this page.")
    section_title: str = Field(..., description="A short chapter or section heading that groups related pages.")
    summary: str = Field(..., description="A one-sentence description of the page contents.")


class NotebookTOCChunk(OpenAIBase):
    entries: list[NotebookTOCEntry] = Field(
        default_factory=list,
        description="One entry for every supplied notebook page, in the same order.",
    )


class NotebookTOCResponse(MealieModel):
    toc_node: NotebookNodeOut
    chunk_count: int
    provider_count: int
