from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, orm
from sqlalchemy.orm import Mapped, mapped_column

from .._model_base import BaseMixins, FilterableColumn, NaiveDateTime, SqlAlchemyBase
from .._model_utils import guid
from .._model_utils.auto_init import auto_init

if TYPE_CHECKING:
    from ..group import Group
    from ..users import User
    from .household import Household


class UploadedBook(SqlAlchemyBase, BaseMixins):
    __tablename__ = "uploaded_books"

    id: FilterableColumn[guid.GUID] = mapped_column(guid.GUID, primary_key=True, default=guid.GUID.generate)

    group_id: FilterableColumn[guid.GUID] = mapped_column(guid.GUID, ForeignKey("groups.id"), nullable=False, index=True)
    group: Mapped[Optional["Group"]] = orm.relationship("Group")
    household_id: FilterableColumn[guid.GUID] = mapped_column(
        guid.GUID, ForeignKey("households.id"), nullable=False, index=True
    )
    household: Mapped[Optional["Household"]] = orm.relationship("Household")
    user_id: FilterableColumn[guid.GUID] = mapped_column(guid.GUID, ForeignKey("users.id"), nullable=False, index=True)
    user: Mapped[Optional["User"]] = orm.relationship("User")

    name: FilterableColumn[str] = mapped_column(String, nullable=False)
    file_name: FilterableColumn[str] = mapped_column(String, nullable=False)
    original_file_name: FilterableColumn[str] = mapped_column(String, nullable=False)
    extension: FilterableColumn[str] = mapped_column(String, nullable=False)
    content_type: FilterableColumn[str | None] = mapped_column(String, nullable=True)
    size: FilterableColumn[int] = mapped_column(Integer, nullable=False, default=0)
    is_translated_book: FilterableColumn[bool] = mapped_column(Boolean, nullable=False, default=False)
    translated_from_book_id: FilterableColumn[guid.GUID | None] = mapped_column(
        guid.GUID, ForeignKey("uploaded_books.id"), nullable=True, index=True
    )
    translated_book_id: FilterableColumn[guid.GUID | None] = mapped_column(
        guid.GUID, ForeignKey("uploaded_books.id"), nullable=True
    )
    translation_language: FilterableColumn[str | None] = mapped_column(String, nullable=True)
    translation_status: FilterableColumn[str] = mapped_column(String, nullable=False, default="not_started")
    translation_pages_per_chunk: FilterableColumn[int] = mapped_column(Integer, nullable=False, default=10)
    translation_total_chunks: FilterableColumn[int] = mapped_column(Integer, nullable=False, default=0)
    translation_completed_chunks: FilterableColumn[int] = mapped_column(Integer, nullable=False, default=0)
    translation_failed_chunks: FilterableColumn[int] = mapped_column(Integer, nullable=False, default=0)
    translation_retry_count: FilterableColumn[int] = mapped_column(Integer, nullable=False, default=0)
    translation_error: FilterableColumn[str | None] = mapped_column(String, nullable=True)
    translation_chunk_status: FilterableColumn[str | None] = mapped_column(Text, nullable=True)
    translation_started_at: FilterableColumn[datetime | None] = mapped_column(NaiveDateTime, nullable=True)
    translation_completed_at: FilterableColumn[datetime | None] = mapped_column(NaiveDateTime, nullable=True)
    extraction_status: FilterableColumn[str] = mapped_column(String, nullable=False, default="not_started")
    extraction_pages_per_chunk: FilterableColumn[int] = mapped_column(Integer, nullable=False, default=10)
    extraction_translate_language: FilterableColumn[str | None] = mapped_column(String, nullable=True)
    extraction_total_chunks: FilterableColumn[int] = mapped_column(Integer, nullable=False, default=0)
    extraction_completed_chunks: FilterableColumn[int] = mapped_column(Integer, nullable=False, default=0)
    extraction_failed_chunks: FilterableColumn[int] = mapped_column(Integer, nullable=False, default=0)
    extraction_retry_count: FilterableColumn[int] = mapped_column(Integer, nullable=False, default=0)
    extraction_recipes_found: FilterableColumn[int] = mapped_column(Integer, nullable=False, default=0)
    extraction_recipes_created: FilterableColumn[int] = mapped_column(Integer, nullable=False, default=0)
    extraction_error: FilterableColumn[str | None] = mapped_column(String, nullable=True)
    extraction_chunk_status: FilterableColumn[str | None] = mapped_column(Text, nullable=True)
    extraction_started_at: FilterableColumn[datetime | None] = mapped_column(NaiveDateTime, nullable=True)
    extraction_completed_at: FilterableColumn[datetime | None] = mapped_column(NaiveDateTime, nullable=True)

    @auto_init()
    def __init__(self, **_) -> None:
        pass
