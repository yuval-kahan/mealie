"""add uploaded book page ranges

Revision ID: d7e8f9a0b1c2
Revises: c4d5e6f7a8b9
Create Date: 2026-07-08 04:00:00.000000

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "d7e8f9a0b1c2"
down_revision: str | None = "c4d5e6f7a8b9"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    with op.batch_alter_table("uploaded_books", schema=None) as batch_op:
        batch_op.add_column(sa.Column("translation_page_start", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("translation_page_end", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("extraction_page_start", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("extraction_page_end", sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table("uploaded_books", schema=None) as batch_op:
        batch_op.drop_column("extraction_page_end")
        batch_op.drop_column("extraction_page_start")
        batch_op.drop_column("translation_page_end")
        batch_op.drop_column("translation_page_start")
