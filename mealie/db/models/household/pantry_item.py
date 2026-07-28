from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Float, ForeignKey, String, Text, UniqueConstraint, orm
from sqlalchemy.orm import Mapped, mapped_column

from .._model_base import BaseMixins, FilterableColumn, SqlAlchemyBase
from .._model_utils import guid
from .._model_utils.auto_init import auto_init

if TYPE_CHECKING:
    from ..group import Group
    from ..users import User
    from .household import Household


class PantryItem(SqlAlchemyBase, BaseMixins):
    __tablename__ = "pantry_items"
    __table_args__ = (UniqueConstraint("group_id", "name", name="pantry_items_group_name_key"),)

    id: FilterableColumn[guid.GUID] = mapped_column(guid.GUID, primary_key=True, default=guid.GUID.generate)
    group_id: FilterableColumn[guid.GUID] = mapped_column(
        guid.GUID,
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    group: Mapped[Optional["Group"]] = orm.relationship("Group")
    household_id: FilterableColumn[guid.GUID] = mapped_column(
        guid.GUID,
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    household: Mapped[Optional["Household"]] = orm.relationship("Household")
    user_id: FilterableColumn[guid.GUID] = mapped_column(
        guid.GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user: Mapped[Optional["User"]] = orm.relationship("User")

    name: FilterableColumn[str] = mapped_column(String(255), nullable=False)
    quantity: FilterableColumn[float | None] = mapped_column(Float, nullable=True)
    unit: FilterableColumn[str | None] = mapped_column(String(120), nullable=True)
    category: FilterableColumn[str | None] = mapped_column(String(160), nullable=True, index=True)
    note: FilterableColumn[str | None] = mapped_column(String(1000), nullable=True)

    @auto_init()
    def __init__(self, **_) -> None:
        pass


class PantrySearchHistory(SqlAlchemyBase, BaseMixins):
    __tablename__ = "pantry_search_history"

    id: FilterableColumn[guid.GUID] = mapped_column(guid.GUID, primary_key=True, default=guid.GUID.generate)
    group_id: FilterableColumn[guid.GUID] = mapped_column(
        guid.GUID,
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    group: Mapped[Optional["Group"]] = orm.relationship("Group")
    household_id: FilterableColumn[guid.GUID] = mapped_column(
        guid.GUID,
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    household: Mapped[Optional["Household"]] = orm.relationship("Household")
    user_id: FilterableColumn[guid.GUID] = mapped_column(
        guid.GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user: Mapped[Optional["User"]] = orm.relationship("User")

    query: FilterableColumn[str] = mapped_column(Text, nullable=False)
    use_ai: FilterableColumn[bool] = mapped_column(Boolean, nullable=False, default=False)
    target_language: FilterableColumn[str | None] = mapped_column(String(80), nullable=True)
    response_json: FilterableColumn[str] = mapped_column(Text, nullable=False)

    @auto_init()
    def __init__(self, **_) -> None:
        pass
