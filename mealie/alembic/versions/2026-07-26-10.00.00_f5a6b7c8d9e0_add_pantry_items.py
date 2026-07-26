"""add pantry items

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-07-26 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

revision = "f5a6b7c8d9e0"
down_revision: str | None = "e4f5a6b7c8d9"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.create_table(
        "pantry_items",
        sa.Column("id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("group_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("household_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("user_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=120), nullable=True),
        sa.Column("category", sa.String(length=160), nullable=True),
        sa.Column("note", sa.String(length=1000), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "name", name="pantry_items_group_name_key"),
    )
    op.create_index("ix_pantry_items_group_id", "pantry_items", ["group_id"], unique=False)
    op.create_index("ix_pantry_items_household_id", "pantry_items", ["household_id"], unique=False)
    op.create_index("ix_pantry_items_user_id", "pantry_items", ["user_id"], unique=False)
    op.create_index("ix_pantry_items_category", "pantry_items", ["category"], unique=False)
    op.create_index("ix_pantry_items_created_at", "pantry_items", ["created_at"], unique=False)


def downgrade():
    op.drop_index("ix_pantry_items_created_at", table_name="pantry_items")
    op.drop_index("ix_pantry_items_category", table_name="pantry_items")
    op.drop_index("ix_pantry_items_user_id", table_name="pantry_items")
    op.drop_index("ix_pantry_items_household_id", table_name="pantry_items")
    op.drop_index("ix_pantry_items_group_id", table_name="pantry_items")
    op.drop_table("pantry_items")
