"""add uploaded book ai extraction status

Revision ID: d4e5f6a7b8c9
Revises: c3d9e4f6a7b8
Create Date: 2026-07-07 21:20:00.000000

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision: str | None = "c3d9e4f6a7b8"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    with op.batch_alter_table("uploaded_books", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("extraction_status", sa.String(), nullable=False, server_default="not_started")
        )
        batch_op.add_column(sa.Column("extraction_pages_per_chunk", sa.Integer(), nullable=False, server_default="10"))
        batch_op.add_column(sa.Column("extraction_total_chunks", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("extraction_completed_chunks", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("extraction_recipes_found", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("extraction_recipes_created", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("extraction_error", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column("extraction_started_at", mealie.db.migration_types.NaiveDateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("extraction_completed_at", mealie.db.migration_types.NaiveDateTime(), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("uploaded_books", schema=None) as batch_op:
        batch_op.drop_column("extraction_completed_at")
        batch_op.drop_column("extraction_started_at")
        batch_op.drop_column("extraction_error")
        batch_op.drop_column("extraction_recipes_created")
        batch_op.drop_column("extraction_recipes_found")
        batch_op.drop_column("extraction_completed_chunks")
        batch_op.drop_column("extraction_total_chunks")
        batch_op.drop_column("extraction_pages_per_chunk")
        batch_op.drop_column("extraction_status")
