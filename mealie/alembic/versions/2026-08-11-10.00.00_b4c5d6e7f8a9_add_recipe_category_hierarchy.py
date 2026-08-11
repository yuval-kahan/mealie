"""add recipe category hierarchy

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-08-11 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

from mealie.db.models._model_utils.guid import GUID


revision = "b4c5d6e7f8a9"
down_revision: str | None = "a3b4c5d6e7f8"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    with op.batch_alter_table("categories") as batch_op:
        batch_op.add_column(
            sa.Column("recipe_group_section", sa.String(length=64), nullable=False, server_default="recipes")
        )
        batch_op.add_column(sa.Column("parent_category_id", GUID(), nullable=True))
        batch_op.create_foreign_key(
            "categories_parent_category_id_fkey",
            "categories",
            ["parent_category_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_categories_recipe_group_section", ["recipe_group_section"], unique=False)
        batch_op.create_index("ix_categories_parent_category_id", ["parent_category_id"], unique=False)


def downgrade():
    with op.batch_alter_table("categories") as batch_op:
        batch_op.drop_index("ix_categories_parent_category_id")
        batch_op.drop_index("ix_categories_recipe_group_section")
        batch_op.drop_constraint("categories_parent_category_id_fkey", type_="foreignkey")
        batch_op.drop_column("parent_category_id")
        batch_op.drop_column("recipe_group_section")
