"""add recipe library sections

Revision ID: e0f1a2b3c4d5
Revises: d9e0f1a2b3c4
Create Date: 2026-08-01 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op


revision = "e0f1a2b3c4d5"
down_revision: str | None = "d9e0f1a2b3c4"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    with op.batch_alter_table("recipes") as batch_op:
        batch_op.add_column(
            sa.Column("recipe_section", sa.String(length=64), nullable=False, server_default="recipes")
        )
        batch_op.create_index("ix_recipes_recipe_section", ["recipe_section"], unique=False)

    op.execute(
        sa.text(
            """
            UPDATE recipes
            SET recipe_section = 'book'
            WHERE id IN (
                SELECT DISTINCT recipee_id
                FROM api_extras
                WHERE key_name = 'uploadedBookSourceId'
            )
            """
        )
    )


def downgrade():
    with op.batch_alter_table("recipes") as batch_op:
        batch_op.drop_index("ix_recipes_recipe_section")
        batch_op.drop_column("recipe_section")
