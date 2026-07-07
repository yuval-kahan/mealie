"""add uploaded book translation tracking

Revision ID: f1a2b3c4d5e6
Revises: e7f8a9b0c1d2
Create Date: 2026-07-08 00:20:00.000000

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

# revision identifiers, used by Alembic.
revision = "f1a2b3c4d5e6"
down_revision: str | None = "e7f8a9b0c1d2"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    with op.batch_alter_table("uploaded_books", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_translated_book", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("translated_from_book_id", mealie.db.migration_types.GUID(), nullable=True))
        batch_op.add_column(sa.Column("translated_book_id", mealie.db.migration_types.GUID(), nullable=True))
        batch_op.add_column(sa.Column("translation_language", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("translation_status", sa.String(), nullable=False, server_default="not_started"))
        batch_op.add_column(sa.Column("translation_pages_per_chunk", sa.Integer(), nullable=False, server_default="10"))
        batch_op.add_column(sa.Column("translation_total_chunks", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("translation_completed_chunks", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("translation_failed_chunks", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("translation_retry_count", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("translation_error", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("translation_chunk_status", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("translation_started_at", mealie.db.migration_types.NaiveDateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("translation_completed_at", mealie.db.migration_types.NaiveDateTime(), nullable=True)
        )
        batch_op.create_index("ix_uploaded_books_translated_from_book_id", ["translated_from_book_id"])
        batch_op.create_foreign_key(
            "fk_uploaded_books_translated_from_book_id",
            "uploaded_books",
            ["translated_from_book_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_uploaded_books_translated_book_id",
            "uploaded_books",
            ["translated_book_id"],
            ["id"],
        )


def downgrade():
    with op.batch_alter_table("uploaded_books", schema=None) as batch_op:
        batch_op.drop_constraint("fk_uploaded_books_translated_book_id", type_="foreignkey")
        batch_op.drop_constraint("fk_uploaded_books_translated_from_book_id", type_="foreignkey")
        batch_op.drop_index("ix_uploaded_books_translated_from_book_id")
        batch_op.drop_column("translation_completed_at")
        batch_op.drop_column("translation_started_at")
        batch_op.drop_column("translation_chunk_status")
        batch_op.drop_column("translation_error")
        batch_op.drop_column("translation_retry_count")
        batch_op.drop_column("translation_failed_chunks")
        batch_op.drop_column("translation_completed_chunks")
        batch_op.drop_column("translation_total_chunks")
        batch_op.drop_column("translation_pages_per_chunk")
        batch_op.drop_column("translation_status")
        batch_op.drop_column("translation_language")
        batch_op.drop_column("translated_book_id")
        batch_op.drop_column("translated_from_book_id")
        batch_op.drop_column("is_translated_book")
