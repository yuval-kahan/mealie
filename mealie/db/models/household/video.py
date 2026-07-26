from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint, orm
from sqlalchemy.orm import Mapped, mapped_column

from .._model_base import BaseMixins, FilterableColumn, SqlAlchemyBase
from .._model_utils import guid
from .._model_utils.auto_init import auto_init

if TYPE_CHECKING:
    from ..group import Group
    from ..users import User
    from .household import Household


class RecipeVideo(SqlAlchemyBase):
    __tablename__ = "recipe_videos"

    id = None
    created_at = None
    update_at = None
    updated_at = None

    recipe_id: Mapped[guid.GUID] = mapped_column(
        guid.GUID,
        ForeignKey("recipes.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    video_id: Mapped[guid.GUID] = mapped_column(
        guid.GUID,
        ForeignKey("videos.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    video: Mapped["Video"] = orm.relationship("Video", back_populates="recipe_links")


class ShoppingListVideo(SqlAlchemyBase):
    __tablename__ = "shopping_list_videos"

    id = None
    created_at = None
    update_at = None
    updated_at = None

    shopping_list_id: Mapped[guid.GUID] = mapped_column(
        guid.GUID,
        ForeignKey("shopping_lists.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    video_id: Mapped[guid.GUID] = mapped_column(
        guid.GUID,
        ForeignKey("videos.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    video: Mapped["Video"] = orm.relationship("Video", back_populates="shopping_list_links")


class Video(SqlAlchemyBase, BaseMixins):
    __tablename__ = "videos"
    __table_args__ = (UniqueConstraint("group_id", "url", name="videos_group_url_key"),)

    id: FilterableColumn[guid.GUID] = mapped_column(guid.GUID, primary_key=True, default=guid.GUID.generate)
    group_id: FilterableColumn[guid.GUID] = mapped_column(
        guid.GUID, ForeignKey("groups.id"), nullable=False, index=True
    )
    group: Mapped[Optional["Group"]] = orm.relationship("Group")
    household_id: FilterableColumn[guid.GUID] = mapped_column(
        guid.GUID, ForeignKey("households.id"), nullable=False, index=True
    )
    household: Mapped[Optional["Household"]] = orm.relationship("Household")
    user_id: FilterableColumn[guid.GUID] = mapped_column(guid.GUID, ForeignKey("users.id"), nullable=False, index=True)
    user: Mapped[Optional["User"]] = orm.relationship("User")

    title: FilterableColumn[str] = mapped_column(String(500), nullable=False)
    url: FilterableColumn[str] = mapped_column(String(2000), nullable=False)
    description: FilterableColumn[str | None] = mapped_column(Text, nullable=True)
    original_description: FilterableColumn[str | None] = mapped_column(Text, nullable=True)
    platform: FilterableColumn[str | None] = mapped_column(String(120), nullable=True)
    creator: FilterableColumn[str | None] = mapped_column(String(255), nullable=True)
    duration_seconds: FilterableColumn[int | None] = mapped_column(Integer, nullable=True)
    published_at: FilterableColumn[str | None] = mapped_column(String(64), nullable=True)
    language: FilterableColumn[str | None] = mapped_column(String(64), nullable=True)
    thumbnail_url: FilterableColumn[str | None] = mapped_column(String(2000), nullable=True)
    thumbnail_file_name: FilterableColumn[str | None] = mapped_column(String(500), nullable=True)
    categories_json: FilterableColumn[str] = mapped_column(Text, nullable=False, default="[]")
    tags_json: FilterableColumn[str] = mapped_column(Text, nullable=False, default="[]")
    metadata_json: FilterableColumn[str] = mapped_column(Text, nullable=False, default="{}")

    download_enabled: FilterableColumn[bool] = mapped_column(Boolean, nullable=False, default=True)
    processing_status: FilterableColumn[str] = mapped_column(String(40), nullable=False, default="pending", index=True)
    processing_progress: FilterableColumn[int] = mapped_column(Integer, nullable=False, default=0)
    processing_error: FilterableColumn[str | None] = mapped_column(Text, nullable=True)
    cancel_requested: FilterableColumn[bool] = mapped_column(Boolean, nullable=False, default=False)
    local_file_name: FilterableColumn[str | None] = mapped_column(String(500), nullable=True)
    local_format: FilterableColumn[str | None] = mapped_column(String(32), nullable=True)
    local_resolution: FilterableColumn[str | None] = mapped_column(String(64), nullable=True)
    local_file_size: FilterableColumn[int | None] = mapped_column(BigInteger, nullable=True)
    transcript: FilterableColumn[str | None] = mapped_column(Text, nullable=True)
    recipe_detected: FilterableColumn[bool] = mapped_column(Boolean, nullable=False, default=False)

    process_with_ai: FilterableColumn[bool] = mapped_column(Boolean, nullable=False, default=True)
    create_recipe: FilterableColumn[bool] = mapped_column(Boolean, nullable=False, default=True)
    create_shopping_list: FilterableColumn[bool] = mapped_column(Boolean, nullable=False, default=True)
    organize_shopping_list: FilterableColumn[bool] = mapped_column(Boolean, nullable=False, default=True)
    include_ai_tips: FilterableColumn[bool] = mapped_column(Boolean, nullable=False, default=True)
    include_mise_en_place: FilterableColumn[bool] = mapped_column(Boolean, nullable=False, default=True)
    target_language: FilterableColumn[str | None] = mapped_column(String(64), nullable=True)

    recipe_links: Mapped[list[RecipeVideo]] = orm.relationship(
        RecipeVideo,
        back_populates="video",
        cascade="all, delete, delete-orphan",
        lazy="selectin",
    )
    shopping_list_links: Mapped[list[ShoppingListVideo]] = orm.relationship(
        ShoppingListVideo,
        back_populates="video",
        cascade="all, delete, delete-orphan",
        lazy="selectin",
    )

    @auto_init()
    def __init__(self, **_) -> None:
        pass


class VideoDownloadSettings(SqlAlchemyBase, BaseMixins):
    __tablename__ = "video_download_settings"
    __table_args__ = (UniqueConstraint("user_id", name="video_download_settings_user_key"),)

    id: FilterableColumn[guid.GUID] = mapped_column(guid.GUID, primary_key=True, default=guid.GUID.generate)
    group_id: FilterableColumn[guid.GUID] = mapped_column(
        guid.GUID, ForeignKey("groups.id"), nullable=False, index=True
    )
    household_id: FilterableColumn[guid.GUID] = mapped_column(
        guid.GUID, ForeignKey("households.id"), nullable=False, index=True
    )
    user_id: FilterableColumn[guid.GUID] = mapped_column(
        guid.GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    download_by_default: FilterableColumn[bool] = mapped_column(Boolean, nullable=False, default=True)
    quality: FilterableColumn[str] = mapped_column(String(20), nullable=False, default="best")
    container: FilterableColumn[str] = mapped_column(String(20), nullable=False, default="mp4")
    codec: FilterableColumn[str] = mapped_column(String(20), nullable=False, default="auto")
    audio_only: FilterableColumn[bool] = mapped_column(Boolean, nullable=False, default=False)
    audio_quality: FilterableColumn[str] = mapped_column(String(20), nullable=False, default="best")
    save_subtitles: FilterableColumn[bool] = mapped_column(Boolean, nullable=False, default=False)
    save_thumbnail: FilterableColumn[bool] = mapped_column(Boolean, nullable=False, default=True)
    save_metadata: FilterableColumn[bool] = mapped_column(Boolean, nullable=False, default=True)
    fallback_to_lower_quality: FilterableColumn[bool] = mapped_column(Boolean, nullable=False, default=True)

    @auto_init()
    def __init__(self, **_) -> None:
        pass
