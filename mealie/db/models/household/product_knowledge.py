from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String, Text, orm
from sqlalchemy.orm import Mapped, mapped_column

from .._model_base import BaseMixins, FilterableColumn, SqlAlchemyBase
from .._model_utils import guid
from .._model_utils.auto_init import auto_init

if TYPE_CHECKING:
    from ..group import Group
    from ..users import User
    from .household import Household


class ProductKnowledge(SqlAlchemyBase, BaseMixins):
    __tablename__ = "product_knowledge"

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

    title: FilterableColumn[str] = mapped_column(String(255), nullable=False)
    summary: FilterableColumn[str | None] = mapped_column(Text, nullable=True)
    content: FilterableColumn[str] = mapped_column(Text, nullable=False)
    source: FilterableColumn[str | None] = mapped_column(String(2000), nullable=True)
    image_source_url: FilterableColumn[str | None] = mapped_column(String(2000), nullable=True)
    categories_json: FilterableColumn[str] = mapped_column(Text, nullable=False, default="[]")
    tags_json: FilterableColumn[str] = mapped_column(Text, nullable=False, default="[]")
    quality_rating: FilterableColumn[int | None] = mapped_column(Integer, nullable=True)

    @auto_init()
    def __init__(self, **_) -> None:
        pass
