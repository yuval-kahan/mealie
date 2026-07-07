from datetime import datetime

from pydantic import UUID4, ConfigDict, Field

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
    is_translated_book: bool = False
    translated_from_book_id: UUID4 | None = None
    translated_book_id: UUID4 | None = None
    translation_language: str | None = None
    translation_status: str = "not_started"
    translation_pages_per_chunk: int = 10
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


class UploadedBookExtractRequest(MealieModel):
    pages_per_chunk: int = Field(10, ge=1, le=100)
    translate_language: str = "Hebrew"


class UploadedBookTranslateRequest(MealieModel):
    pages_per_chunk: int = Field(10, ge=1, le=100)
    target_language: str = Field("Hebrew", min_length=2, max_length=80)
