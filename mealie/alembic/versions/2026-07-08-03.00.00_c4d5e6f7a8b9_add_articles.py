"""add articles

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-07-08 03:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

# revision identifiers, used by Alembic.
revision = "c4d5e6f7a8b9"
down_revision: str | None = "b3c4d5e6f7a8"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


ARTICLE_INDEXES = [
    ("ix_articles_created_at", ["created_at"]),
    ("ix_articles_group_id", ["group_id"]),
    ("ix_articles_household_id", ["household_id"]),
    ("ix_articles_slug", ["slug"]),
    ("ix_articles_user_id", ["user_id"]),
]


def _table_exists(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _index_names(table_name: str) -> set[str]:
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}


def upgrade():
    if not _table_exists("articles"):
        op.create_table(
            "articles",
            sa.Column("id", mealie.db.migration_types.GUID(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("update_at", sa.DateTime(), nullable=True),
            sa.Column("group_id", mealie.db.migration_types.GUID(), nullable=False),
            sa.Column("household_id", mealie.db.migration_types.GUID(), nullable=False),
            sa.Column("user_id", mealie.db.migration_types.GUID(), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("slug", sa.String(), nullable=False),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("source", sa.String(), nullable=True),
            sa.Column("author", sa.String(), nullable=True),
            sa.Column("categories_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("tags_json", sa.Text(), nullable=False, server_default="[]"),
            sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
            sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("group_id", "slug", name="articles_group_slug_key"),
        )

    existing_indexes = _index_names("articles")
    for index_name, columns in ARTICLE_INDEXES:
        if index_name not in existing_indexes:
            op.create_index(index_name, "articles", columns, unique=False)


def downgrade():
    if not _table_exists("articles"):
        return

    existing_indexes = _index_names("articles")
    for index_name, _ in reversed(ARTICLE_INDEXES):
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name="articles")
    op.drop_table("articles")
