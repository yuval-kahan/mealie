from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint, orm
from sqlalchemy.orm import Mapped, mapped_column

from .._model_base import BaseMixins, FilterableColumn, SqlAlchemyBase
from .._model_utils import guid
from .._model_utils.auto_init import auto_init

if TYPE_CHECKING:
    from ..group import Group
    from ..users import User
    from .household import Household


class WantedBook(SqlAlchemyBase, BaseMixins):
    __tablename__ = "wanted_books"
    __table_args__ = (
        UniqueConstraint("group_id", "dedupe_key", name="wanted_books_group_dedupe_key"),
    )

    id: FilterableColumn[guid.GUID] = mapped_column(
        guid.GUID,
        primary_key=True,
        default=guid.GUID.generate,
    )
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

    title: FilterableColumn[str] = mapped_column(String(500), nullable=False)
    subtitle: FilterableColumn[str | None] = mapped_column(String(1000), nullable=True)
    authors_json: FilterableColumn[str] = mapped_column(Text, nullable=False, default="[]")
    isbn_10: FilterableColumn[str | None] = mapped_column(String(32), nullable=True, index=True)
    isbn_13: FilterableColumn[str | None] = mapped_column(String(32), nullable=True, index=True)
    publisher: FilterableColumn[str | None] = mapped_column(String(255), nullable=True)
    published_year: FilterableColumn[int | None] = mapped_column(Integer, nullable=True)
    summary: FilterableColumn[str | None] = mapped_column(Text, nullable=True)
    source_url: FilterableColumn[str | None] = mapped_column(String(2000), nullable=True)
    cover_source_url: FilterableColumn[str | None] = mapped_column(String(2000), nullable=True)
    categories_json: FilterableColumn[str] = mapped_column(Text, nullable=False, default="[]")
    tags_json: FilterableColumn[str] = mapped_column(Text, nullable=False, default="[]")
    notes: FilterableColumn[str | None] = mapped_column(Text, nullable=True)
    dedupe_key: FilterableColumn[str] = mapped_column(String(600), nullable=False, index=True)

    @auto_init()
    def __init__(self, **_) -> None:
        pass
