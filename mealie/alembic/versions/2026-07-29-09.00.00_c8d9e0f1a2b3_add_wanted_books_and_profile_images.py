"""add wanted books and profile image metadata

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-07-29 09:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

revision = "c8d9e0f1a2b3"
down_revision: str | None = "b7c8d9e0f1a2"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.create_table(
        "wanted_books",
        sa.Column("id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("group_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("household_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("user_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("subtitle", sa.String(length=1000), nullable=True),
        sa.Column("authors_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("isbn_10", sa.String(length=32), nullable=True),
        sa.Column("isbn_13", sa.String(length=32), nullable=True),
        sa.Column("publisher", sa.String(length=255), nullable=True),
        sa.Column("published_year", sa.Integer(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(length=2000), nullable=True),
        sa.Column("cover_source_url", sa.String(length=2000), nullable=True),
        sa.Column("categories_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("tags_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("dedupe_key", sa.String(length=600), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "dedupe_key", name="wanted_books_group_dedupe_key"),
    )
    op.create_index("ix_wanted_books_group_id", "wanted_books", ["group_id"], unique=False)
    op.create_index("ix_wanted_books_household_id", "wanted_books", ["household_id"], unique=False)
    op.create_index("ix_wanted_books_user_id", "wanted_books", ["user_id"], unique=False)
    op.create_index("ix_wanted_books_isbn_10", "wanted_books", ["isbn_10"], unique=False)
    op.create_index("ix_wanted_books_isbn_13", "wanted_books", ["isbn_13"], unique=False)
    op.create_index("ix_wanted_books_dedupe_key", "wanted_books", ["dedupe_key"], unique=False)

    with op.batch_alter_table("product_knowledge") as batch_op:
        batch_op.add_column(sa.Column("image_source_url", sa.String(length=2000), nullable=True))

    with op.batch_alter_table("chefs") as batch_op:
        batch_op.add_column(sa.Column("wikipedia_url", sa.String(length=2000), nullable=True))


def downgrade():
    with op.batch_alter_table("chefs") as batch_op:
        batch_op.drop_column("wikipedia_url")

    with op.batch_alter_table("product_knowledge") as batch_op:
        batch_op.drop_column("image_source_url")

    op.drop_index("ix_wanted_books_dedupe_key", table_name="wanted_books")
    op.drop_index("ix_wanted_books_isbn_13", table_name="wanted_books")
    op.drop_index("ix_wanted_books_isbn_10", table_name="wanted_books")
    op.drop_index("ix_wanted_books_user_id", table_name="wanted_books")
    op.drop_index("ix_wanted_books_household_id", table_name="wanted_books")
    op.drop_index("ix_wanted_books_group_id", table_name="wanted_books")
    op.drop_table("wanted_books")
