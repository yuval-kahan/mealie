from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint, orm
from sqlalchemy.orm import Mapped, mapped_column

from .._model_base import BaseMixins, FilterableColumn, SqlAlchemyBase
from .._model_utils import guid
from .._model_utils.auto_init import auto_init

if TYPE_CHECKING:
    from ..group import Group
    from ..users import User
    from .chef import Chef
    from .household import Household
    from .uploaded_book import UploadedBook


class Restaurant(SqlAlchemyBase, BaseMixins):
    __tablename__ = "restaurants"
    __table_args__ = (UniqueConstraint("group_id", "name", name="restaurants_group_name_key"),)

    id: FilterableColumn[guid.GUID] = mapped_column(guid.GUID, primary_key=True, default=guid.GUID.generate)
    group_id: FilterableColumn[guid.GUID] = mapped_column(
        guid.GUID, ForeignKey("groups.id"), nullable=False, index=True
    )
    group: Mapped[Optional["Group"]] = orm.relationship("Group")
    household_id: FilterableColumn[guid.GUID] = mapped_column(
        guid.GUID, ForeignKey("households.id"), nullable=False, index=True
    )
    household: Mapped[Optional["Household"]] = orm.relationship("Household")
    user_id: FilterableColumn[guid.GUID] = mapped_column(
        guid.GUID, ForeignKey("users.id"), nullable=False, index=True
    )
    user: Mapped[Optional["User"]] = orm.relationship("User")

    name: FilterableColumn[str] = mapped_column(String(255), nullable=False)
    website_url: FilterableColumn[str | None] = mapped_column(String(2000), nullable=True)
    cuisine_types_json: FilterableColumn[str] = mapped_column(Text, nullable=False, default="[]")
    addresses_json: FilterableColumn[str] = mapped_column(Text, nullable=False, default="[]")
    phone: FilterableColumn[str | None] = mapped_column(String(120), nullable=True)
    price_range: FilterableColumn[str | None] = mapped_column(String(120), nullable=True)
    description: FilterableColumn[str | None] = mapped_column(Text, nullable=True)
    notes: FilterableColumn[str | None] = mapped_column(Text, nullable=True)
    michelin_info: FilterableColumn[str | None] = mapped_column(String(500), nullable=True)
    michelin_star_count: FilterableColumn[int] = mapped_column(Integer, nullable=False, default=0)
    is_michelin_listed: FilterableColumn[bool] = mapped_column(Boolean, nullable=False, default=False)
    chef_names_json: FilterableColumn[str] = mapped_column(Text, nullable=False, default="[]")
    book_titles_json: FilterableColumn[str] = mapped_column(Text, nullable=False, default="[]")
    google_rating: FilterableColumn[float | None] = mapped_column(Float, nullable=True)
    google_review_count: FilterableColumn[int | None] = mapped_column(Integer, nullable=True)
    google_maps_url: FilterableColumn[str | None] = mapped_column(String(2000), nullable=True)
    our_rating: FilterableColumn[float | None] = mapped_column(Float, nullable=True)
    recommendation_status: FilterableColumn[str] = mapped_column(
        String(32), nullable=False, default="recommended", index=True
    )
    visit_status: FilterableColumn[str] = mapped_column(String(32), nullable=False, default="not_tried", index=True)

    chefs: Mapped[list["Chef"]] = orm.relationship(
        "Chef",
        secondary="chefs_to_restaurants",
        back_populates="restaurants",
        lazy="selectin",
    )
    uploaded_books: Mapped[list["UploadedBook"]] = orm.relationship(
        "UploadedBook",
        secondary="restaurants_to_uploaded_books",
        lazy="selectin",
    )

    @auto_init()
    def __init__(self, **_) -> None:
        pass
