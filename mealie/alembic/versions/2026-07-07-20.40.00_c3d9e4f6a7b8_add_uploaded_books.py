"""add uploaded books

Revision ID: c3d9e4f6a7b8
Revises: b5c9d1a8f0e6
Create Date: 2026-07-07 20:40:00.000000

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

# revision identifiers, used by Alembic.
revision = "c3d9e4f6a7b8"
down_revision: str | None = "b5c9d1a8f0e6"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.create_table(
        "uploaded_books",
        sa.Column("id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("group_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("household_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("user_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("file_name", sa.String(), nullable=False),
        sa.Column("original_file_name", sa.String(), nullable=False),
        sa.Column("extension", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=True),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("created_at", mealie.db.migration_types.NaiveDateTime(), nullable=True),
        sa.Column("update_at", mealie.db.migration_types.NaiveDateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("uploaded_books", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_uploaded_books_created_at"), ["created_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_uploaded_books_group_id"), ["group_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_uploaded_books_household_id"), ["household_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_uploaded_books_user_id"), ["user_id"], unique=False)


def downgrade():
    with op.batch_alter_table("uploaded_books", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_uploaded_books_user_id"))
        batch_op.drop_index(batch_op.f("ix_uploaded_books_household_id"))
        batch_op.drop_index(batch_op.f("ix_uploaded_books_group_id"))
        batch_op.drop_index(batch_op.f("ix_uploaded_books_created_at"))

    op.drop_table("uploaded_books")
