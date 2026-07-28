"""add site types, pantry history, and product knowledge

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-07-28 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

revision = "a6b7c8d9e0f1"
down_revision: str | None = "f5a6b7c8d9e0"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    with op.batch_alter_table("shopping_websites") as batch_op:
        batch_op.add_column(
            sa.Column("is_recipe_site", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column("is_shopping_site", sa.Boolean(), nullable=False, server_default=sa.true())
        )

    op.create_table(
        "pantry_search_history",
        sa.Column("id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("group_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("household_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("user_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("use_ai", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("target_language", sa.String(length=80), nullable=True),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pantry_search_history_group_id", "pantry_search_history", ["group_id"], unique=False)
    op.create_index(
        "ix_pantry_search_history_household_id",
        "pantry_search_history",
        ["household_id"],
        unique=False,
    )
    op.create_index("ix_pantry_search_history_user_id", "pantry_search_history", ["user_id"], unique=False)
    op.create_index("ix_pantry_search_history_created_at", "pantry_search_history", ["created_at"], unique=False)

    op.create_table(
        "product_knowledge",
        sa.Column("id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("group_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("household_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("user_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=2000), nullable=True),
        sa.Column("categories_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("tags_json", sa.Text(), nullable=False, server_default="[]"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_knowledge_group_id", "product_knowledge", ["group_id"], unique=False)
    op.create_index("ix_product_knowledge_household_id", "product_knowledge", ["household_id"], unique=False)
    op.create_index("ix_product_knowledge_user_id", "product_knowledge", ["user_id"], unique=False)
    op.create_index("ix_product_knowledge_created_at", "product_knowledge", ["created_at"], unique=False)


def downgrade():
    op.drop_index("ix_product_knowledge_created_at", table_name="product_knowledge")
    op.drop_index("ix_product_knowledge_user_id", table_name="product_knowledge")
    op.drop_index("ix_product_knowledge_household_id", table_name="product_knowledge")
    op.drop_index("ix_product_knowledge_group_id", table_name="product_knowledge")
    op.drop_table("product_knowledge")

    op.drop_index("ix_pantry_search_history_created_at", table_name="pantry_search_history")
    op.drop_index("ix_pantry_search_history_user_id", table_name="pantry_search_history")
    op.drop_index("ix_pantry_search_history_household_id", table_name="pantry_search_history")
    op.drop_index("ix_pantry_search_history_group_id", table_name="pantry_search_history")
    op.drop_table("pantry_search_history")

    with op.batch_alter_table("shopping_websites") as batch_op:
        batch_op.drop_column("is_shopping_site")
        batch_op.drop_column("is_recipe_site")
