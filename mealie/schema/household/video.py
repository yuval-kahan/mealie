from datetime import datetime
from typing import Literal

from pydantic import UUID4, ConfigDict, Field, field_validator

from mealie.schema._mealie import MealieModel
from mealie.schema._mealie.mealie_model import UpdatedAtField

VideoQuality = Literal["best", "2160", "1080", "720", "480"]
VideoContainer = Literal["mp4", "mkv", "webm"]
VideoCodec = Literal["auto", "h264", "h265", "vp9", "av1"]
AudioQuality = Literal["best", "320", "256", "192", "128", "96"]


class VideoDownloadSettingsBase(MealieModel):
    download_by_default: bool = True
    quality: VideoQuality = "best"
    container: VideoContainer = "mp4"
    codec: VideoCodec = "auto"
    audio_only: bool = False
    audio_quality: AudioQuality = "best"
    save_subtitles: bool = False
    save_thumbnail: bool = True
    save_metadata: bool = True
    fallback_to_lower_quality: bool = True


class VideoDownloadSettingsOut(VideoDownloadSettingsBase):
    id: UUID4 | None = None
    model_config = ConfigDict(from_attributes=True)


class VideoCreate(MealieModel):
    url: str = Field(..., min_length=1, max_length=2000)
    title: str | None = Field(None, max_length=500)
    description: str | None = Field(None, max_length=50000)
    process_with_ai: bool = True
    download_video: bool | None = None
    create_recipe: bool = True
    create_shopping_list: bool = True
    organize_shopping_list: bool = True
    include_ai_tips: bool = True
    include_mise_en_place: bool = True
    target_language: str | None = Field(None, max_length=64)


class VideoBrowserPageRequest(VideoCreate):
    page_title: str | None = Field(None, max_length=500)


class VideoUpdate(MealieModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(None, max_length=50000)
    creator: str | None = Field(None, max_length=255)
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @field_validator("categories", "tags")
    @classmethod
    def normalize_terms(cls, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            item = " ".join(str(value).split()).strip()[:120]
            if item and item.casefold() not in seen:
                seen.add(item.casefold())
                result.append(item)
        return result[:60]


class VideoOut(MealieModel):
    id: UUID4
    group_id: UUID4
    household_id: UUID4
    user_id: UUID4
    title: str
    url: str
    description: str | None = None
    original_description: str | None = None
    platform: str | None = None
    creator: str | None = None
    duration_seconds: int | None = None
    published_at: str | None = None
    language: str | None = None
    thumbnail_url: str | None = None
    thumbnail_file_name: str | None = None
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    process_with_ai: bool = True
    download_enabled: bool = True
    create_recipe: bool = True
    create_shopping_list: bool = True
    organize_shopping_list: bool = True
    include_ai_tips: bool = True
    include_mise_en_place: bool = True
    target_language: str | None = None
    processing_status: str
    processing_progress: int = 0
    processing_error: str | None = None
    local_file_name: str | None = None
    local_format: str | None = None
    local_resolution: str | None = None
    local_file_size: int | None = None
    recipe_detected: bool = False
    recipe_ids: list[UUID4] = Field(default_factory=list)
    recipe_slugs: list[str] = Field(default_factory=list)
    shopping_list_ids: list[UUID4] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = UpdatedAtField(default=None)
    has_local_media: bool = False
    has_local_thumbnail: bool = False

    model_config = ConfigDict(from_attributes=True)


class VideoDeletePreview(MealieModel):
    recipe_ids: list[UUID4] = Field(default_factory=list)
    recipe_names: list[str] = Field(default_factory=list)
    shopping_list_ids: list[UUID4] = Field(default_factory=list)
    shopping_list_names: list[str] = Field(default_factory=list)
