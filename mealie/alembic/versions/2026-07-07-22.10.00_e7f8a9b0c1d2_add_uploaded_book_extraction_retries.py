"""add uploaded book extraction retry tracking

Revision ID: e7f8a9b0c1d2
Revises: d4e5f6a7b8c9
Create Date: 2026-07-07 22:10:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e7f8a9b0c1d2"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    with op.batch_alter_table("uploaded_books", schema=None) as batch_op:
        batch_op.add_column(sa.Column("extraction_failed_chunks", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("extraction_retry_count", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("extraction_chunk_status", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("uploaded_books", schema=None) as batch_op:
        batch_op.drop_column("extraction_chunk_status")
        batch_op.drop_column("extraction_retry_count")
        batch_op.drop_column("extraction_failed_chunks")
