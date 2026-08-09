"""add notebooks and library preferences

Revision ID: f2a3b4c5d6e7
Revises: e0f1a2b3c4d5
Create Date: 2026-08-09 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

revision = "f2a3b4c5d6e7"
down_revision: str | None = "e0f1a2b3c4d5"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.create_table(
        "notebooks",
        sa.Column("id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("group_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("household_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("user_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("color", sa.String(length=32), nullable=False, server_default="#ef8a1f"),
        sa.Column("icon", sa.String(length=64), nullable=False, server_default="notebook"),
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("settings_json", sa.Text(), nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notebooks_group_id", "notebooks", ["group_id"], unique=False)
    op.create_index("ix_notebooks_household_id", "notebooks", ["household_id"], unique=False)
    op.create_index("ix_notebooks_user_id", "notebooks", ["user_id"], unique=False)
    op.create_index("ix_notebooks_is_favorite", "notebooks", ["is_favorite"], unique=False)
    op.create_index("ix_notebooks_is_pinned", "notebooks", ["is_pinned"], unique=False)
    op.create_index("ix_notebooks_position", "notebooks", ["position"], unique=False)

    op.create_table(
        "notebook_nodes",
        sa.Column("id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("notebook_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("parent_id", mealie.db.migration_types.GUID(), nullable=True),
        sa.Column("group_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("household_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("user_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("node_type", sa.String(length=32), nullable=False, server_default="page"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content_html", sa.Text(), nullable=False, server_default=""),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_collapsed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("color", sa.String(length=32), nullable=True),
        sa.Column("tags_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("categories_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("highlight_categories_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("settings_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("content_version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["notebook_id"], ["notebooks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["notebook_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "notebook_id",
        "parent_id",
        "group_id",
        "household_id",
        "user_id",
        "node_type",
        "position",
        "is_favorite",
        "is_pinned",
    ):
        op.create_index(f"ix_notebook_nodes_{column}", "notebook_nodes", [column], unique=False)

    op.create_table(
        "notebook_revisions",
        sa.Column("id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("node_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("user_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content_html", sa.Text(), nullable=False, server_default=""),
        sa.Column("settings_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("content_version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["node_id"], ["notebook_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notebook_revisions_node_id", "notebook_revisions", ["node_id"], unique=False)
    op.create_index("ix_notebook_revisions_user_id", "notebook_revisions", ["user_id"], unique=False)
    op.create_index("ix_notebook_revisions_created_at", "notebook_revisions", ["created_at"], unique=False)

    with op.batch_alter_table("shopping_lists") as batch_op:
        batch_op.add_column(sa.Column("list_kind", sa.String(length=32), nullable=False, server_default="shopping"))
        batch_op.create_index("ix_shopping_lists_list_kind", ["list_kind"], unique=False)

    with op.batch_alter_table("shopping_list_items") as batch_op:
        batch_op.add_column(sa.Column("quality_rating", sa.Integer(), nullable=True))

    with op.batch_alter_table("product_knowledge") as batch_op:
        batch_op.add_column(sa.Column("quality_rating", sa.Integer(), nullable=True))

    with op.batch_alter_table("recipes") as batch_op:
        batch_op.add_column(sa.Column("show_in_recipes", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("show_in_book", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("show_in_sauce", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.create_index("ix_recipes_show_in_recipes", ["show_in_recipes"], unique=False)
        batch_op.create_index("ix_recipes_show_in_book", ["show_in_book"], unique=False)
        batch_op.create_index("ix_recipes_show_in_sauce", ["show_in_sauce"], unique=False)

    recipes_table = sa.table(
        "recipes",
        sa.column("recipe_section", sa.String()),
        sa.column("show_in_recipes", sa.Boolean()),
        sa.column("show_in_book", sa.Boolean()),
        sa.column("show_in_sauce", sa.Boolean()),
    )
    op.execute(
        sa.update(recipes_table)
        .where(recipes_table.c.recipe_section == "recipes")
        .values(show_in_recipes=True)
    )
    op.execute(
        sa.update(recipes_table)
        .where(recipes_table.c.recipe_section == "book")
        .values(show_in_book=True, show_in_recipes=False)
    )
    op.execute(
        sa.update(recipes_table)
        .where(recipes_table.c.recipe_section == "sauce")
        .values(show_in_sauce=True, show_in_recipes=False)
    )


def downgrade():
    with op.batch_alter_table("recipes") as batch_op:
        batch_op.drop_index("ix_recipes_show_in_sauce")
        batch_op.drop_index("ix_recipes_show_in_book")
        batch_op.drop_index("ix_recipes_show_in_recipes")
        batch_op.drop_column("show_in_sauce")
        batch_op.drop_column("show_in_book")
        batch_op.drop_column("show_in_recipes")

    with op.batch_alter_table("product_knowledge") as batch_op:
        batch_op.drop_column("quality_rating")

    with op.batch_alter_table("shopping_list_items") as batch_op:
        batch_op.drop_column("quality_rating")

    with op.batch_alter_table("shopping_lists") as batch_op:
        batch_op.drop_index("ix_shopping_lists_list_kind")
        batch_op.drop_column("list_kind")

    op.drop_table("notebook_revisions")
    op.drop_table("notebook_nodes")
    op.drop_table("notebooks")
