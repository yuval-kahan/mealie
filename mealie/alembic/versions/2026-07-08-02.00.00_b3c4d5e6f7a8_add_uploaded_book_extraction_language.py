"""add uploaded book extraction language

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-07-08 02:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b3c4d5e6f7a8"
down_revision: str | None = "a2b3c4d5e6f7"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    with op.batch_alter_table("uploaded_books", schema=None) as batch_op:
        batch_op.add_column(sa.Column("extraction_translate_language", sa.String(), nullable=True))


def downgrade():
    with op.batch_alter_table("uploaded_books", schema=None) as batch_op:
        batch_op.drop_column("extraction_translate_language")
