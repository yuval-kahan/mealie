from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, orm
from sqlalchemy.orm import Mapped, mapped_column

from .._model_base import BaseMixins, FilterableColumn, SqlAlchemyBase
from .._model_utils import guid
from .._model_utils.auto_init import auto_init

if TYPE_CHECKING:
    from ..group import Group
    from ..users import User
    from .household import Household


class Notebook(SqlAlchemyBase, BaseMixins):
    __tablename__ = "notebooks"

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
    description: FilterableColumn[str | None] = mapped_column(Text, nullable=True)
    color: FilterableColumn[str] = mapped_column(String(32), nullable=False, default="#ef8a1f")
    icon: FilterableColumn[str] = mapped_column(String(64), nullable=False, default="notebook")
    is_favorite: FilterableColumn[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    is_pinned: FilterableColumn[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    position: FilterableColumn[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    settings_json: FilterableColumn[str] = mapped_column(Text, nullable=False, default="{}")

    @auto_init()
    def __init__(self, **_) -> None:
        pass


class NotebookNode(SqlAlchemyBase, BaseMixins):
    __tablename__ = "notebook_nodes"

    id: FilterableColumn[guid.GUID] = mapped_column(guid.GUID, primary_key=True, default=guid.GUID.generate)
    notebook_id: FilterableColumn[guid.GUID] = mapped_column(
        guid.GUID,
        ForeignKey("notebooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: FilterableColumn[guid.GUID | None] = mapped_column(
        guid.GUID,
        ForeignKey("notebook_nodes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    group_id: FilterableColumn[guid.GUID] = mapped_column(
        guid.GUID,
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    household_id: FilterableColumn[guid.GUID] = mapped_column(
        guid.GUID,
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: FilterableColumn[guid.GUID] = mapped_column(
        guid.GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    node_type: FilterableColumn[str] = mapped_column(String(32), nullable=False, default="page", index=True)
    title: FilterableColumn[str] = mapped_column(String(255), nullable=False)
    content_html: FilterableColumn[str] = mapped_column(Text, nullable=False, default="")
    position: FilterableColumn[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    is_collapsed: FilterableColumn[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_favorite: FilterableColumn[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    is_pinned: FilterableColumn[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    color: FilterableColumn[str | None] = mapped_column(String(32), nullable=True)
    tags_json: FilterableColumn[str] = mapped_column(Text, nullable=False, default="[]")
    categories_json: FilterableColumn[str] = mapped_column(Text, nullable=False, default="[]")
    highlight_categories_json: FilterableColumn[str] = mapped_column(Text, nullable=False, default="[]")
    settings_json: FilterableColumn[str] = mapped_column(Text, nullable=False, default="{}")
    content_version: FilterableColumn[int] = mapped_column(Integer, nullable=False, default=1)

    @auto_init()
    def __init__(self, **_) -> None:
        pass


class NotebookRevision(SqlAlchemyBase, BaseMixins):
    __tablename__ = "notebook_revisions"

    id: FilterableColumn[guid.GUID] = mapped_column(guid.GUID, primary_key=True, default=guid.GUID.generate)
    node_id: FilterableColumn[guid.GUID] = mapped_column(
        guid.GUID,
        ForeignKey("notebook_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: FilterableColumn[guid.GUID] = mapped_column(
        guid.GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: FilterableColumn[str] = mapped_column(String(255), nullable=False)
    content_html: FilterableColumn[str] = mapped_column(Text, nullable=False, default="")
    settings_json: FilterableColumn[str] = mapped_column(Text, nullable=False, default="{}")
    content_version: FilterableColumn[int] = mapped_column(Integer, nullable=False, default=1)

    @auto_init()
    def __init__(self, **_) -> None:
        pass
