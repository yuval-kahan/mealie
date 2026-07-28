import json
from datetime import datetime
from typing import Literal

from pydantic import UUID4, ConfigDict, Field, computed_field, model_validator

from mealie.schema._mealie import MealieModel
from mealie.schema._mealie.mealie_model import UpdatedAtField


class UploadedBookOut(MealieModel):
    id: UUID4
    group_id: UUID4
    household_id: UUID4
    user_id: UUID4
    name: str
    file_name: str
    original_file_name: str
    extension: str
    content_type: str | None = None
    size: int = 0
    book_metadata_json: str = Field("{}", exclude=True)
    classification_status: str = "not_started"
    classification_error: str | None = None
    classification_updated_at: datetime | None = None
    is_translated_book: bool = False
    translated_from_book_id: UUID4 | None = None
    translated_book_id: UUID4 | None = None
    translation_language: str | None = None
    translation_status: str = "not_started"
    translation_pages_per_chunk: int = 10
    translation_page_start: int | None = None
    translation_page_end: int | None = None
    translation_total_chunks: int = 0
    translation_completed_chunks: int = 0
    translation_failed_chunks: int = 0
    translation_retry_count: int = 0
    translation_error: str | None = None
    translation_chunk_status: str | None = None
    translation_started_at: datetime | None = None
    translation_completed_at: datetime | None = None
    extraction_status: str = "not_started"
    extraction_pages_per_chunk: int = 10
    extraction_translate_language: str | None = None
    extraction_page_start: int | None = None
    extraction_page_end: int | None = None
    extraction_total_chunks: int = 0
    extraction_completed_chunks: int = 0
    extraction_failed_chunks: int = 0
    extraction_retry_count: int = 0
    extraction_recipes_found: int = 0
    extraction_recipes_created: int = 0
    extraction_error: str | None = None
    extraction_chunk_status: str | None = None
    extraction_started_at: datetime | None = None
    extraction_completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = UpdatedAtField(default=None)

    model_config = ConfigDict(from_attributes=True)

    @computed_field  # type: ignore[misc]
    @property
    def book_metadata(self) -> dict:
        try:
            value = json.loads(self.book_metadata_json or "{}")
            return value if isinstance(value, dict) else {}
        except (TypeError, ValueError):
            return {}


class UploadedBookReaderPreferences(MealieModel):
    font_size: int = Field(18, ge=12, le=36)
    font_family: str = Field("serif", pattern="^(serif|sans-serif|dyslexic)$")
    line_height: float = Field(1.75, ge=1.2, le=2.6)
    word_spacing: float = Field(0, ge=0, le=12)
    page_width: int = Field(980, ge=600, le=1500)


class UploadedBookReaderNote(MealieModel):
    id: str = Field(..., min_length=1, max_length=80)
    title: str = Field("", max_length=200)
    text: str = Field(..., min_length=1, max_length=4000)
    page: int = Field(0, ge=0, le=100000)
    page_index: int = Field(0, ge=0, le=100000)
    chapter_id: str | None = Field(None, max_length=160)
    created_at: str | None = Field(None, max_length=80)


class UploadedBookReaderHighlight(MealieModel):
    id: str = Field(..., min_length=1, max_length=80)
    text: str = Field(..., min_length=1, max_length=2000)
    page: int = Field(0, ge=0, le=100000)
    page_index: int = Field(0, ge=0, le=100000)
    chapter_id: str | None = Field(None, max_length=160)
    start: int = Field(..., ge=0, le=2000000)
    end: int = Field(..., ge=0, le=2000000)
    created_at: str | None = Field(None, max_length=80)

    @model_validator(mode="after")
    def validate_offsets(self):
        if self.end <= self.start:
            raise ValueError("Highlight end must be greater than start")
        return self


class UploadedBookReadingStateUpdate(MealieModel):
    current_page: int = Field(0, ge=0, le=100000)
    current_page_index: int = Field(0, ge=0, le=100000)
    current_chapter_id: str | None = Field(None, max_length=160)
    reading_percent: float = Field(0, ge=0, le=100)
    completed_chapters: list[str] = Field(default_factory=list, max_length=1000)
    total_chapters: int = Field(0, ge=0, le=1000)
    notes: list[UploadedBookReaderNote] = Field(default_factory=list, max_length=500)
    highlights: list[UploadedBookReaderHighlight] = Field(default_factory=list, max_length=500)
    preferences: UploadedBookReaderPreferences = Field(default_factory=UploadedBookReaderPreferences)


class UploadedBookReadingStateOut(UploadedBookReadingStateUpdate):
    id: UUID4
    book_id: UUID4
    user_id: UUID4
    updated_at: datetime | None = UpdatedAtField(default=None)


class UploadedBookExtractRequest(MealieModel):
    pages_per_chunk: int = Field(10, ge=1, le=100)
    translate_language: str = "Hebrew"
    page_start: int | None = Field(None, ge=1)
    page_end: int | None = Field(None, ge=1)
    auto_recipe_images: bool = True
    include_item_images: bool = True
    include_ai_tips: bool = True
    create_shopping_lists: bool = True
    organize_shopping_lists_with_ai: bool = True
    allow_duplicate_recipes: bool = False


class UploadedBookRecipeCatalogRequest(MealieModel):
    query: str = Field("", max_length=500)
    target_language: str = Field("Hebrew", min_length=2, max_length=80)
    refresh: bool = False


class UploadedBookRecipeCandidate(MealieModel):
    id: str
    title: str
    source_title: str
    chapter: str | None = None
    page_start: int = Field(..., ge=1)
    page_end: int = Field(..., ge=1)
    reason: str | None = None
    imported_recipe_slug: str | None = None


class UploadedBookRecipeCatalogResponse(MealieModel):
    book_id: UUID4
    query: str = ""
    source: Literal["contents", "headings", "full_text", "hybrid"]
    candidates: list[UploadedBookRecipeCandidate] = Field(default_factory=list)
    generated_at: str | None = None
    used_ai: bool = False
    warning: str | None = None


class UploadedBookRecipeCatalogImportRequest(MealieModel):
    candidate_ids: list[str] = Field(..., min_length=1, max_length=500)
    target_language: str = Field("Hebrew", min_length=2, max_length=80)
    auto_recipe_images: bool = True
    include_item_images: bool = True
    include_ai_tips: bool = True
    create_shopping_lists: bool = True
    organize_shopping_lists_with_ai: bool = True
    allow_duplicate_recipes: bool = False


class UploadedBookTranslateRequest(MealieModel):
    pages_per_chunk: int = Field(10, ge=1, le=100)
    target_language: str = Field("Hebrew", min_length=2, max_length=80)
    page_start: int | None = Field(None, ge=1)
    page_end: int | None = Field(None, ge=1)
    include_linked_recipes: bool = True
    extract_recipes: bool = False
    auto_recipe_images: bool = True
    include_item_images: bool = True
    include_ai_tips: bool = True
    create_shopping_lists: bool = True
    organize_shopping_lists_with_ai: bool = True


class UploadedBookCoverURLRequest(MealieModel):
    url: str = Field(..., min_length=8, max_length=4000)


class UploadedBookManualTranslationPageRequest(MealieModel):
    page: int = Field(..., ge=1, le=100000)
    text: str = Field(..., min_length=1, max_length=200000)


class UploadedBookRecipeSummary(MealieModel):
    id: UUID4
    slug: str
    name: str
    source: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UploadedBookRecipeDeleteRequest(MealieModel):
    recipe_ids: list[UUID4] = Field(default_factory=list, max_length=5000)
    delete_recipes: bool = True
    delete_shopping_lists: bool = True

    @model_validator(mode="after")
    def validate_delete_targets(self):
        if not self.delete_recipes and not self.delete_shopping_lists:
            raise ValueError("At least one delete target must be selected")
        return self


class UploadedBookRecipeDeleteResponse(MealieModel):
    deleted_count: int = 0
    deleted_shopping_list_count: int = 0
    remaining_count: int = 0
    skipped_count: int = 0
    deleted_recipe_ids: list[UUID4] = Field(default_factory=list)
    deleted_shopping_list_ids: list[UUID4] = Field(default_factory=list)


class UploadedBookDeletePreview(MealieModel):
    recipe_ids: list[UUID4] = Field(default_factory=list)
    recipe_names: list[str] = Field(default_factory=list)
    shopping_list_ids: list[UUID4] = Field(default_factory=list)
    shopping_list_names: list[str] = Field(default_factory=list)


class AICookbookGenerateRequest(MealieModel):
    mode: Literal["preset", "prompt"] = "preset"
    preset: str | None = Field(None, max_length=120)
    prompt: str | None = Field(None, max_length=2000)
    title: str | None = Field(None, max_length=255)
    max_recipes_per_volume: int = Field(100, ge=5, le=200)
    max_estimated_pages_per_volume: int = Field(300, ge=40, le=1000)

    @model_validator(mode="after")
    def validate_selection(self):
        if self.mode == "preset" and not (self.preset or "").strip():
            raise ValueError("A preset is required")
        if self.mode == "preset" and (self.prompt or "").strip():
            raise ValueError("Preset and custom prompt cannot be used together")
        if self.mode == "prompt" and not (self.prompt or "").strip():
            raise ValueError("A prompt is required")
        if self.mode == "prompt" and (self.preset or "").strip():
            raise ValueError("Preset and custom prompt cannot be used together")
        return self
