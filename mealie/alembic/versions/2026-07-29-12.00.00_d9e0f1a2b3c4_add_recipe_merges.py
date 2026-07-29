"""add reversible recipe merges

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-07-29 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

revision = "d9e0f1a2b3c4"
down_revision: str | None = "c8d9e0f1a2b3"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    with op.batch_alter_table("recipes") as batch_op:
        batch_op.add_column(
            sa.Column("is_merge_archived", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column("is_merged_recipe", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.create_index("ix_recipes_is_merge_archived", ["is_merge_archived"], unique=False)
        batch_op.create_index("ix_recipes_is_merged_recipe", ["is_merged_recipe"], unique=False)

    op.create_table(
        "recipe_merge_sources",
        sa.Column("merged_recipe_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("source_recipe_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["merged_recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("merged_recipe_id", "source_recipe_id"),
    )
    op.create_index(
        "ix_recipe_merge_sources_source_recipe_id",
        "recipe_merge_sources",
        ["source_recipe_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_recipe_merge_sources_source_recipe_id", table_name="recipe_merge_sources")
    op.drop_table("recipe_merge_sources")

    with op.batch_alter_table("recipes") as batch_op:
        batch_op.drop_index("ix_recipes_is_merged_recipe")
        batch_op.drop_index("ix_recipes_is_merge_archived")
        batch_op.drop_column("is_merged_recipe")
        batch_op.drop_column("is_merge_archived")
