"""add uploaded book metadata

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
Create Date: 2026-07-09 23:30:00.000000

"""

import sqlalchemy as sa
from alembic import op


revision = "e8f9a0b1c2d3"
down_revision: str | None = "d7e8f9a0b1c2"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    with op.batch_alter_table("uploaded_books", schema=None) as batch_op:
        batch_op.add_column(sa.Column("book_metadata_json", sa.Text(), nullable=False, server_default="{}"))
        batch_op.add_column(
            sa.Column("classification_status", sa.String(), nullable=False, server_default="not_started")
        )
        batch_op.add_column(sa.Column("classification_error", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("classification_updated_at", sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table("uploaded_books", schema=None) as batch_op:
        batch_op.drop_column("classification_updated_at")
        batch_op.drop_column("classification_error")
        batch_op.drop_column("classification_status")
        batch_op.drop_column("book_metadata_json")
