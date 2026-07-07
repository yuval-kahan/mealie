"""add recipe source fields

Revision ID: f8a1c3d9e2b4
Revises: 2187537c52b8
Create Date: 2026-07-07 20:10:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f8a1c3d9e2b4"
down_revision: str | None = "2187537c52b8"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def is_postgres() -> bool:
    return op.get_context().dialect.name == "postgresql"


def upgrade():
    with op.batch_alter_table("recipes", schema=None) as batch_op:
        batch_op.add_column(sa.Column("source", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("created_by", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("source_normalized", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("created_by_normalized", sa.String(), nullable=True))
        batch_op.create_index(batch_op.f("ix_recipes_source_normalized"), ["source_normalized"], unique=False)
        batch_op.create_index(batch_op.f("ix_recipes_created_by_normalized"), ["created_by_normalized"], unique=False)

    if is_postgres():
        with op.batch_alter_table("recipes", schema=None) as batch_op:
            batch_op.create_index(
                "ix_recipes_source_normalized_gin",
                ["source_normalized"],
                unique=False,
                postgresql_using="gin",
                postgresql_ops={"source_normalized": "gin_trgm_ops"},
            )
            batch_op.create_index(
                "ix_recipes_created_by_normalized_gin",
                ["created_by_normalized"],
                unique=False,
                postgresql_using="gin",
                postgresql_ops={"created_by_normalized": "gin_trgm_ops"},
            )


def downgrade():
    if is_postgres():
        with op.batch_alter_table("recipes", schema=None) as batch_op:
            batch_op.drop_index("ix_recipes_created_by_normalized_gin")
            batch_op.drop_index("ix_recipes_source_normalized_gin")

    with op.batch_alter_table("recipes", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_recipes_created_by_normalized"))
        batch_op.drop_index(batch_op.f("ix_recipes_source_normalized"))
        batch_op.drop_column("created_by_normalized")
        batch_op.drop_column("source_normalized")
        batch_op.drop_column("created_by")
        batch_op.drop_column("source")
