"""add video mise en place preference

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-07-18 14:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "c2d3e4f5a6b7"
down_revision: str | None = "b1c2d3e4f5a6"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.add_column(
        "videos",
        sa.Column("include_mise_en_place", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.execute(sa.text("UPDATE video_download_settings SET save_subtitles = false"))


def downgrade():
    op.drop_column("videos", "include_mise_en_place")
