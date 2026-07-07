"""add recipe ai search index

Revision ID: b5c9d1a8f0e6
Revises: f8a1c3d9e2b4
Create Date: 2026-07-07 20:25:00.000000

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

# revision identifiers, used by Alembic.
revision = "b5c9d1a8f0e6"
down_revision: str | None = "f8a1c3d9e2b4"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.create_table(
        "recipe_ai_search_index",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recipe_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("group_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("recipe_slug", sa.String(), nullable=False),
        sa.Column("recipe_name", sa.String(), nullable=True),
        sa.Column("recipe_updated_at", mealie.db.migration_types.NaiveDateTime(), nullable=True),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("catalog_json", sa.Text(), nullable=False),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("search_vector", sa.Text(), nullable=False),
        sa.Column("created_at", mealie.db.migration_types.NaiveDateTime(), nullable=True),
        sa.Column("update_at", mealie.db.migration_types.NaiveDateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recipe_id", name="recipe_ai_search_index_recipe_id_key"),
    )
    with op.batch_alter_table("recipe_ai_search_index", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_recipe_ai_search_index_content_hash"), ["content_hash"], unique=False)
        batch_op.create_index(batch_op.f("ix_recipe_ai_search_index_created_at"), ["created_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_recipe_ai_search_index_group_id"), ["group_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_recipe_ai_search_index_recipe_id"), ["recipe_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_recipe_ai_search_index_recipe_slug"), ["recipe_slug"], unique=False)


def downgrade():
    with op.batch_alter_table("recipe_ai_search_index", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_recipe_ai_search_index_recipe_slug"))
        batch_op.drop_index(batch_op.f("ix_recipe_ai_search_index_recipe_id"))
        batch_op.drop_index(batch_op.f("ix_recipe_ai_search_index_group_id"))
        batch_op.drop_index(batch_op.f("ix_recipe_ai_search_index_created_at"))
        batch_op.drop_index(batch_op.f("ix_recipe_ai_search_index_content_hash"))

    op.drop_table("recipe_ai_search_index")
