"""add book reading state and restaurant ratings

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-07-22 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

revision = "e4f5a6b7c8d9"
down_revision: str | None = "d3e4f5a6b7c8"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.add_column("restaurants", sa.Column("google_rating", sa.Float(), nullable=True))
    op.add_column("restaurants", sa.Column("google_review_count", sa.Integer(), nullable=True))
    op.add_column("restaurants", sa.Column("google_maps_url", sa.String(length=2000), nullable=True))
    op.add_column("restaurants", sa.Column("our_rating", sa.Float(), nullable=True))

    op.create_table(
        "uploaded_book_reading_states",
        sa.Column("id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("book_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("group_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("user_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("current_page", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_page_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_chapter_id", sa.String(length=160), nullable=True),
        sa.Column("reading_percent", sa.Float(), nullable=False, server_default="0"),
        sa.Column("completed_chapters_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("total_chapters", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("highlights_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("preferences_json", sa.Text(), nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(["book_id"], ["uploaded_books.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("book_id", "user_id", name="uploaded_book_reading_states_book_user_key"),
    )
    op.create_index(
        "ix_uploaded_book_reading_states_book_id",
        "uploaded_book_reading_states",
        ["book_id"],
        unique=False,
    )
    op.create_index(
        "ix_uploaded_book_reading_states_group_id",
        "uploaded_book_reading_states",
        ["group_id"],
        unique=False,
    )
    op.create_index(
        "ix_uploaded_book_reading_states_user_id",
        "uploaded_book_reading_states",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_uploaded_book_reading_states_created_at",
        "uploaded_book_reading_states",
        ["created_at"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_uploaded_book_reading_states_created_at", table_name="uploaded_book_reading_states")
    op.drop_index("ix_uploaded_book_reading_states_user_id", table_name="uploaded_book_reading_states")
    op.drop_index("ix_uploaded_book_reading_states_group_id", table_name="uploaded_book_reading_states")
    op.drop_index("ix_uploaded_book_reading_states_book_id", table_name="uploaded_book_reading_states")
    op.drop_table("uploaded_book_reading_states")

    op.drop_column("restaurants", "our_rating")
    op.drop_column("restaurants", "google_maps_url")
    op.drop_column("restaurants", "google_review_count")
    op.drop_column("restaurants", "google_rating")
