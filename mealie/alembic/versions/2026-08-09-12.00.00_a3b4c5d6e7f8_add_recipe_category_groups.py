"""add recipe category groups

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-08-09 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op


revision = "a3b4c5d6e7f8"
down_revision: str | None = "f2a3b4c5d6e7"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    with op.batch_alter_table("categories") as batch_op:
        batch_op.add_column(
            sa.Column("is_recipe_group", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.create_index("ix_categories_is_recipe_group", ["is_recipe_group"], unique=False)


def downgrade():
    with op.batch_alter_table("categories") as batch_op:
        batch_op.drop_index("ix_categories_is_recipe_group")
        batch_op.drop_column("is_recipe_group")
