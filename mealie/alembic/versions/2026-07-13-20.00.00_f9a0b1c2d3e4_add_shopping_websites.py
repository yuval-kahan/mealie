"""add shopping websites

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2026-07-13 20:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

revision = "f9a0b1c2d3e4"
down_revision: str | None = "e8f9a0b1c2d3"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.create_table(
        "shopping_websites",
        sa.Column("id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("group_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("household_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("user_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=2000), nullable=False),
        sa.Column("page_food", sa.Text(), nullable=True),
        sa.Column("offered_foods_json", sa.Text(), nullable=False, server_default="[]"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "url", name="shopping_websites_group_url_key"),
    )
    op.create_index("ix_shopping_websites_group_id", "shopping_websites", ["group_id"], unique=False)
    op.create_index("ix_shopping_websites_household_id", "shopping_websites", ["household_id"], unique=False)
    op.create_index("ix_shopping_websites_user_id", "shopping_websites", ["user_id"], unique=False)
    op.create_index("ix_shopping_websites_created_at", "shopping_websites", ["created_at"], unique=False)


def downgrade():
    op.drop_index("ix_shopping_websites_created_at", table_name="shopping_websites")
    op.drop_index("ix_shopping_websites_user_id", table_name="shopping_websites")
    op.drop_index("ix_shopping_websites_household_id", table_name="shopping_websites")
    op.drop_index("ix_shopping_websites_group_id", table_name="shopping_websites")
    op.drop_table("shopping_websites")
