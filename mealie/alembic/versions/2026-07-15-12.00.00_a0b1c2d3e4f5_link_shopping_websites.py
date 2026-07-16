"""link shopping websites to recipes and shopping lists

Revision ID: a0b1c2d3e4f5
Revises: f9a0b1c2d3e4
Create Date: 2026-07-15 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

revision = "a0b1c2d3e4f5"
down_revision: str | None = "f9a0b1c2d3e4"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.create_table(
        "recipe_shopping_websites",
        sa.Column("recipe_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("shopping_website_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shopping_website_id"], ["shopping_websites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("recipe_id", "shopping_website_id"),
    )
    op.create_index(
        "ix_recipe_shopping_websites_recipe_id",
        "recipe_shopping_websites",
        ["recipe_id"],
        unique=False,
    )
    op.create_index(
        "ix_recipe_shopping_websites_website_id",
        "recipe_shopping_websites",
        ["shopping_website_id"],
        unique=False,
    )

    op.create_table(
        "shopping_list_shopping_websites",
        sa.Column("shopping_list_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("shopping_website_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.ForeignKeyConstraint(["shopping_list_id"], ["shopping_lists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shopping_website_id"], ["shopping_websites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("shopping_list_id", "shopping_website_id"),
    )
    op.create_index(
        "ix_shopping_list_shopping_websites_list_id",
        "shopping_list_shopping_websites",
        ["shopping_list_id"],
        unique=False,
    )
    op.create_index(
        "ix_shopping_list_shopping_websites_website_id",
        "shopping_list_shopping_websites",
        ["shopping_website_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_shopping_list_shopping_websites_website_id",
        table_name="shopping_list_shopping_websites",
    )
    op.drop_index(
        "ix_shopping_list_shopping_websites_list_id",
        table_name="shopping_list_shopping_websites",
    )
    op.drop_table("shopping_list_shopping_websites")
    op.drop_index("ix_recipe_shopping_websites_website_id", table_name="recipe_shopping_websites")
    op.drop_index("ix_recipe_shopping_websites_recipe_id", table_name="recipe_shopping_websites")
    op.drop_table("recipe_shopping_websites")
