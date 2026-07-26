from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, orm
from sqlalchemy.orm import Mapped, mapped_column

from .._model_base import BaseMixins, FilterableColumn, SqlAlchemyBase
from .._model_utils import guid
from .._model_utils.auto_init import auto_init

if TYPE_CHECKING:
    from ..group import Group
    from ..users import User
    from .household import Household


class RecipeShoppingWebsite(SqlAlchemyBase):
    __tablename__ = "recipe_shopping_websites"

    # Pure association rows use the linked entity IDs as their composite key.
    # Suppress the columns inherited from SqlAlchemyBase so the ORM matches the
    # intentionally minimal association table created by the migration.
    id = None
    created_at = None
    update_at = None
    updated_at = None

    recipe_id: Mapped[guid.GUID] = mapped_column(
        guid.GUID,
        ForeignKey("recipes.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    shopping_website_id: Mapped[guid.GUID] = mapped_column(
        guid.GUID,
        ForeignKey("shopping_websites.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    shopping_website: Mapped["ShoppingWebsite"] = orm.relationship(
        "ShoppingWebsite",
        back_populates="recipe_links",
    )


class ShoppingListShoppingWebsite(SqlAlchemyBase):
    __tablename__ = "shopping_list_shopping_websites"

    id = None
    created_at = None
    update_at = None
    updated_at = None

    shopping_list_id: Mapped[guid.GUID] = mapped_column(
        guid.GUID,
        ForeignKey("shopping_lists.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    shopping_website_id: Mapped[guid.GUID] = mapped_column(
        guid.GUID,
        ForeignKey("shopping_websites.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    shopping_website: Mapped["ShoppingWebsite"] = orm.relationship(
        "ShoppingWebsite",
        back_populates="shopping_list_links",
    )


class ShoppingWebsite(SqlAlchemyBase, BaseMixins):
    __tablename__ = "shopping_websites"
    __table_args__ = (UniqueConstraint("group_id", "url", name="shopping_websites_group_url_key"),)

    id: FilterableColumn[guid.GUID] = mapped_column(guid.GUID, primary_key=True, default=guid.GUID.generate)
    group_id: FilterableColumn[guid.GUID] = mapped_column(
        guid.GUID, ForeignKey("groups.id"), nullable=False, index=True
    )
    group: Mapped[Optional["Group"]] = orm.relationship("Group")
    household_id: FilterableColumn[guid.GUID] = mapped_column(
        guid.GUID, ForeignKey("households.id"), nullable=False, index=True
    )
    household: Mapped[Optional["Household"]] = orm.relationship("Household")
    user_id: FilterableColumn[guid.GUID] = mapped_column(guid.GUID, ForeignKey("users.id"), nullable=False, index=True)
    user: Mapped[Optional["User"]] = orm.relationship("User")

    name: FilterableColumn[str] = mapped_column(String(255), nullable=False)
    url: FilterableColumn[str] = mapped_column(String(2000), nullable=False)
    page_food: FilterableColumn[str | None] = mapped_column(Text, nullable=True)
    offered_foods_json: FilterableColumn[str] = mapped_column(Text, nullable=False, default="[]")
    recipe_links: Mapped[list[RecipeShoppingWebsite]] = orm.relationship(
        RecipeShoppingWebsite,
        back_populates="shopping_website",
        cascade="all, delete, delete-orphan",
        lazy="selectin",
    )
    shopping_list_links: Mapped[list[ShoppingListShoppingWebsite]] = orm.relationship(
        ShoppingListShoppingWebsite,
        back_populates="shopping_website",
        cascade="all, delete, delete-orphan",
        lazy="selectin",
    )

    @auto_init()
    def __init__(self, **_) -> None:
        pass
