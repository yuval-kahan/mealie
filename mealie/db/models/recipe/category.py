from typing import TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.orm as orm
from slugify import slugify
from sqlalchemy.orm import Mapped, mapped_column, validates

from mealie.core import root_logger

from .._model_base import BaseMixins, FilterableColumn, SqlAlchemyBase
from .._model_utils.guid import GUID

if TYPE_CHECKING:
    from ..group import Group
    from . import RecipeModel
logger = root_logger.get_logger()


group_to_categories = sa.Table(
    "group_to_categories",
    SqlAlchemyBase.metadata,
    sa.Column("group_id", GUID, sa.ForeignKey("groups.id"), index=True),
    sa.Column("category_id", GUID, sa.ForeignKey("categories.id"), index=True),
    sa.UniqueConstraint("group_id", "category_id", name="group_id_category_id_key"),
)

plan_rules_to_categories = sa.Table(
    "plan_rules_to_categories",
    SqlAlchemyBase.metadata,
    sa.Column("group_plan_rule_id", GUID, sa.ForeignKey("group_meal_plan_rules.id"), index=True),
    sa.Column("category_id", GUID, sa.ForeignKey("categories.id"), index=True),
    sa.UniqueConstraint("group_plan_rule_id", "category_id", name="group_plan_rule_id_category_id_key"),
)

recipes_to_categories = sa.Table(
    "recipes_to_categories",
    SqlAlchemyBase.metadata,
    sa.Column("recipe_id", GUID, sa.ForeignKey("recipes.id"), index=True),
    sa.Column("category_id", GUID, sa.ForeignKey("categories.id"), index=True),
    sa.UniqueConstraint("recipe_id", "category_id", name="recipe_id_category_id_key"),
)

cookbooks_to_categories = sa.Table(
    "cookbooks_to_categories",
    SqlAlchemyBase.metadata,
    sa.Column("cookbook_id", GUID, sa.ForeignKey("cookbooks.id"), index=True),
    sa.Column("category_id", GUID, sa.ForeignKey("categories.id"), index=True),
    sa.UniqueConstraint("cookbook_id", "category_id", name="cookbook_id_category_id_key"),
)


class Category(SqlAlchemyBase, BaseMixins):
    __tablename__ = "categories"
    __table_args__ = (sa.UniqueConstraint("slug", "group_id", name="category_slug_group_id_key"),)

    # ID Relationships
    group_id: FilterableColumn[GUID] = mapped_column(GUID, sa.ForeignKey("groups.id"), nullable=False, index=True)
    group: Mapped["Group"] = orm.relationship("Group", back_populates="categories", foreign_keys=[group_id])

    id: FilterableColumn[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    name: FilterableColumn[str] = mapped_column(sa.String, index=True, nullable=False)
    slug: FilterableColumn[str] = mapped_column(sa.String, index=True, nullable=False)
    is_recipe_group: FilterableColumn[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=False,
        server_default=sa.false(),
        index=True,
    )
    recipe_group_section: FilterableColumn[str] = mapped_column(
        sa.String(64),
        nullable=False,
        default="recipes",
        server_default="recipes",
        index=True,
    )
    parent_category_id: FilterableColumn[GUID | None] = mapped_column(
        GUID,
        sa.ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    recipes: Mapped[list["RecipeModel"]] = orm.relationship(
        "RecipeModel", secondary=recipes_to_categories, back_populates="recipe_category"
    )

    @validates("name")
    def validate_name(self, key, name):
        assert name != ""
        return name

    def __init__(
        self,
        name,
        group_id,
        is_recipe_group=False,
        recipe_group_section="recipes",
        parent_category_id=None,
        slug=None,
        **_,
    ) -> None:
        self.group_id = group_id
        self.name = name.strip()
        self.slug = slugify(slug or self.name)
        self.is_recipe_group = bool(is_recipe_group)
        self.recipe_group_section = (recipe_group_section or "recipes").strip()[:64]
        self.parent_category_id = parent_category_id
