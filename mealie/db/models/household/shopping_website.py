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

    @auto_init()
    def __init__(self, **_) -> None:
        pass
