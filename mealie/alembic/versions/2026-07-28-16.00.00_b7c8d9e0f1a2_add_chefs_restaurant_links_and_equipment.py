"""add chefs, restaurant links, and equipment metadata

Revision ID: b7c8d9e0f1a2
Revises: a6b7c8d9e0f1
Create Date: 2026-07-28 16:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

revision = "b7c8d9e0f1a2"
down_revision: str | None = "a6b7c8d9e0f1"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.create_table(
        "chefs",
        sa.Column("id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("group_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("household_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("user_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("aliases_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("rank", sa.String(length=32), nullable=False, server_default="good"),
        sa.Column("country", sa.String(length=120), nullable=True),
        sa.Column("cuisines_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("specialties_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("biography", sa.Text(), nullable=True),
        sa.Column("career_summary", sa.Text(), nullable=True),
        sa.Column("awards_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("notable_restaurants_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("book_titles_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("website_url", sa.String(length=2000), nullable=True),
        sa.Column("instagram_url", sa.String(length=2000), nullable=True),
        sa.Column("has_michelin_restaurant", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("michelin_star_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("michelin_summary", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "name", name="chefs_group_name_key"),
    )
    op.create_index("ix_chefs_group_id", "chefs", ["group_id"], unique=False)
    op.create_index("ix_chefs_household_id", "chefs", ["household_id"], unique=False)
    op.create_index("ix_chefs_user_id", "chefs", ["user_id"], unique=False)
    op.create_index("ix_chefs_rank", "chefs", ["rank"], unique=False)

    op.create_table(
        "chefs_to_restaurants",
        sa.Column("chef_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("restaurant_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.ForeignKeyConstraint(["chef_id"], ["chefs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("chef_id", "restaurant_id"),
    )
    op.create_table(
        "chefs_to_uploaded_books",
        sa.Column("chef_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("uploaded_book_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.ForeignKeyConstraint(["chef_id"], ["chefs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_book_id"], ["uploaded_books.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("chef_id", "uploaded_book_id"),
    )
    op.create_table(
        "restaurants_to_uploaded_books",
        sa.Column("restaurant_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("uploaded_book_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_book_id"], ["uploaded_books.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("restaurant_id", "uploaded_book_id"),
    )

    with op.batch_alter_table("restaurants") as batch_op:
        batch_op.add_column(sa.Column("michelin_star_count", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("is_michelin_listed", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("chef_names_json", sa.Text(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("book_titles_json", sa.Text(), nullable=False, server_default="[]"))

    with op.batch_alter_table("tools") as batch_op:
        batch_op.add_column(sa.Column("category", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("image_source_url", sa.String(length=2000), nullable=True))
        batch_op.add_column(sa.Column("ai_enriched", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.create_index("ix_tools_category", ["category"], unique=False)


def downgrade():
    with op.batch_alter_table("tools") as batch_op:
        batch_op.drop_index("ix_tools_category")
        batch_op.drop_column("ai_enriched")
        batch_op.drop_column("image_source_url")
        batch_op.drop_column("description")
        batch_op.drop_column("category")

    with op.batch_alter_table("restaurants") as batch_op:
        batch_op.drop_column("book_titles_json")
        batch_op.drop_column("chef_names_json")
        batch_op.drop_column("is_michelin_listed")
        batch_op.drop_column("michelin_star_count")

    op.drop_table("restaurants_to_uploaded_books")
    op.drop_table("chefs_to_uploaded_books")
    op.drop_table("chefs_to_restaurants")
    op.drop_index("ix_chefs_rank", table_name="chefs")
    op.drop_index("ix_chefs_user_id", table_name="chefs")
    op.drop_index("ix_chefs_household_id", table_name="chefs")
    op.drop_index("ix_chefs_group_id", table_name="chefs")
    op.drop_table("chefs")
