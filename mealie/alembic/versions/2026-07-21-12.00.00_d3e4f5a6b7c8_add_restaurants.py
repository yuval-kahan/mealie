"""add restaurants

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-07-21 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

revision = "d3e4f5a6b7c8"
down_revision: str | None = "c2d3e4f5a6b7"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.create_table(
        "restaurants",
        sa.Column("id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("group_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("household_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("user_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("website_url", sa.String(length=2000), nullable=True),
        sa.Column("cuisine_types_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("addresses_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("phone", sa.String(length=120), nullable=True),
        sa.Column("price_range", sa.String(length=120), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("michelin_info", sa.String(length=500), nullable=True),
        sa.Column("recommendation_status", sa.String(length=32), nullable=False, server_default="recommended"),
        sa.Column("visit_status", sa.String(length=32), nullable=False, server_default="not_tried"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "name", name="restaurants_group_name_key"),
    )
    op.create_index("ix_restaurants_group_id", "restaurants", ["group_id"], unique=False)
    op.create_index("ix_restaurants_household_id", "restaurants", ["household_id"], unique=False)
    op.create_index("ix_restaurants_user_id", "restaurants", ["user_id"], unique=False)
    op.create_index("ix_restaurants_recommendation_status", "restaurants", ["recommendation_status"], unique=False)
    op.create_index("ix_restaurants_visit_status", "restaurants", ["visit_status"], unique=False)
    op.create_index("ix_restaurants_created_at", "restaurants", ["created_at"], unique=False)


def downgrade():
    op.drop_index("ix_restaurants_created_at", table_name="restaurants")
    op.drop_index("ix_restaurants_visit_status", table_name="restaurants")
    op.drop_index("ix_restaurants_recommendation_status", table_name="restaurants")
    op.drop_index("ix_restaurants_user_id", table_name="restaurants")
    op.drop_index("ix_restaurants_household_id", table_name="restaurants")
    op.drop_index("ix_restaurants_group_id", table_name="restaurants")
    op.drop_table("restaurants")
