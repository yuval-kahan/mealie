"""repair uploaded book category timestamp column

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-08-11 18:00:00.000000
"""

import sqlalchemy as sa
from alembic import op


revision = "d6e7f8a9b0c1"
down_revision: str | None = "c5d6e7f8a9b0"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def _column_names() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns("uploaded_book_categories")}


def upgrade():
    columns = _column_names()
    if "update_at" in columns:
        return

    with op.batch_alter_table("uploaded_book_categories") as batch_op:
        if "updated_at" in columns:
            batch_op.alter_column(
                "updated_at",
                new_column_name="update_at",
                existing_type=sa.DateTime(),
                existing_nullable=True,
            )
        else:
            batch_op.add_column(sa.Column("update_at", sa.DateTime(), nullable=True))


def downgrade():
    columns = _column_names()
    if "update_at" not in columns or "updated_at" in columns:
        return

    with op.batch_alter_table("uploaded_book_categories") as batch_op:
        batch_op.alter_column(
            "update_at",
            new_column_name="updated_at",
            existing_type=sa.DateTime(),
            existing_nullable=True,
        )
