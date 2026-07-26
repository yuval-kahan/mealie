"""add video library and download preferences

Revision ID: b1c2d3e4f5a6
Revises: a0b1c2d3e4f5
Create Date: 2026-07-18 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

revision = "b1c2d3e4f5a6"
down_revision: str | None = "a0b1c2d3e4f5"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.create_table(
        "videos",
        sa.Column("id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("group_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("household_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("user_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("url", sa.String(length=2000), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("original_description", sa.Text(), nullable=True),
        sa.Column("platform", sa.String(length=120), nullable=True),
        sa.Column("creator", sa.String(length=255), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("published_at", sa.String(length=64), nullable=True),
        sa.Column("language", sa.String(length=64), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=2000), nullable=True),
        sa.Column("thumbnail_file_name", sa.String(length=500), nullable=True),
        sa.Column("categories_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("tags_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("metadata_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("download_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("processing_status", sa.String(length=40), server_default="pending", nullable=False),
        sa.Column("processing_progress", sa.Integer(), server_default="0", nullable=False),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("cancel_requested", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("local_file_name", sa.String(length=500), nullable=True),
        sa.Column("local_format", sa.String(length=32), nullable=True),
        sa.Column("local_resolution", sa.String(length=64), nullable=True),
        sa.Column("local_file_size", sa.BigInteger(), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("recipe_detected", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("process_with_ai", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("create_recipe", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("create_shopping_list", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("organize_shopping_list", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("include_ai_tips", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("target_language", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "url", name="videos_group_url_key"),
    )
    for column in ("group_id", "household_id", "user_id", "processing_status", "created_at"):
        op.create_index(f"ix_videos_{column}", "videos", [column], unique=False)

    op.create_table(
        "video_download_settings",
        sa.Column("id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("group_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("household_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("user_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("download_by_default", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("quality", sa.String(length=20), server_default="best", nullable=False),
        sa.Column("container", sa.String(length=20), server_default="mp4", nullable=False),
        sa.Column("codec", sa.String(length=20), server_default="auto", nullable=False),
        sa.Column("audio_only", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("audio_quality", sa.String(length=20), server_default="best", nullable=False),
        sa.Column("save_subtitles", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("save_thumbnail", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("save_metadata", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("fallback_to_lower_quality", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="video_download_settings_user_key"),
    )
    for column in ("group_id", "household_id", "user_id", "created_at"):
        op.create_index(f"ix_video_download_settings_{column}", "video_download_settings", [column], unique=False)

    op.create_table(
        "recipe_videos",
        sa.Column("recipe_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("video_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("recipe_id", "video_id"),
    )
    op.create_index("ix_recipe_videos_recipe_id", "recipe_videos", ["recipe_id"], unique=False)
    op.create_index("ix_recipe_videos_video_id", "recipe_videos", ["video_id"], unique=False)

    op.create_table(
        "shopping_list_videos",
        sa.Column("shopping_list_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("video_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.ForeignKeyConstraint(["shopping_list_id"], ["shopping_lists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("shopping_list_id", "video_id"),
    )
    op.create_index("ix_shopping_list_videos_list_id", "shopping_list_videos", ["shopping_list_id"], unique=False)
    op.create_index("ix_shopping_list_videos_video_id", "shopping_list_videos", ["video_id"], unique=False)


def downgrade():
    op.drop_table("shopping_list_videos")
    op.drop_table("recipe_videos")
    op.drop_table("video_download_settings")
    op.drop_table("videos")
