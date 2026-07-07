"""add ingredient recommended variety

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-07-08 01:10:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a2b3c4d5e6f7"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def is_postgres() -> bool:
    return op.get_context().dialect.name == "postgresql"


def upgrade():
    with op.batch_alter_table("recipes_ingredients", schema=None) as batch_op:
        batch_op.add_column(sa.Column("recommended_variety", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("recommended_variety_normalized", sa.String(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_recipes_ingredients_recommended_variety_normalized"),
            ["recommended_variety_normalized"],
            unique=False,
        )

    if is_postgres():
        with op.batch_alter_table("recipes_ingredients", schema=None) as batch_op:
            batch_op.create_index(
                "ix_recipes_ingredients_recommended_variety_normalized_gin",
                ["recommended_variety_normalized"],
                unique=False,
                postgresql_using="gin",
                postgresql_ops={"recommended_variety_normalized": "gin_trgm_ops"},
            )


def downgrade():
    if is_postgres():
        with op.batch_alter_table("recipes_ingredients", schema=None) as batch_op:
            batch_op.drop_index("ix_recipes_ingredients_recommended_variety_normalized_gin")

    with op.batch_alter_table("recipes_ingredients", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_recipes_ingredients_recommended_variety_normalized"))
        batch_op.drop_column("recommended_variety_normalized")
        batch_op.drop_column("recommended_variety")
