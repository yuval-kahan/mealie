"""add uploaded book library categories and exact reader position

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-08-11 15:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

from mealie.db.models._model_utils.guid import GUID


revision = "c5d6e7f8a9b0"
down_revision: str | None = "b4c5d6e7f8a9"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.create_table(
        "uploaded_book_categories",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("group_id", GUID(), nullable=False),
        sa.Column("household_id", GUID(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("parent_category_id", GUID(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_protected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["parent_category_id"], ["uploaded_book_categories.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_uploaded_book_categories_group_id", "uploaded_book_categories", ["group_id"])
    op.create_index(
        "ix_uploaded_book_categories_household_id", "uploaded_book_categories", ["household_id"]
    )
    op.create_index(
        "ix_uploaded_book_categories_parent_category_id",
        "uploaded_book_categories",
        ["parent_category_id"],
    )

    with op.batch_alter_table("uploaded_books") as batch_op:
        batch_op.add_column(sa.Column("category_id", GUID(), nullable=True))
        batch_op.create_foreign_key(
            "uploaded_books_category_id_fkey",
            "uploaded_book_categories",
            ["category_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_uploaded_books_category_id", ["category_id"], unique=False)

    with op.batch_alter_table("uploaded_book_reading_states") as batch_op:
        batch_op.add_column(sa.Column("scroll_offset", sa.Float(), nullable=False, server_default="0"))


def downgrade():
    with op.batch_alter_table("uploaded_book_reading_states") as batch_op:
        batch_op.drop_column("scroll_offset")

    with op.batch_alter_table("uploaded_books") as batch_op:
        batch_op.drop_index("ix_uploaded_books_category_id")
        batch_op.drop_constraint("uploaded_books_category_id_fkey", type_="foreignkey")
        batch_op.drop_column("category_id")

    op.drop_index("ix_uploaded_book_categories_parent_category_id", table_name="uploaded_book_categories")
    op.drop_index("ix_uploaded_book_categories_household_id", table_name="uploaded_book_categories")
    op.drop_index("ix_uploaded_book_categories_group_id", table_name="uploaded_book_categories")
    op.drop_table("uploaded_book_categories")
