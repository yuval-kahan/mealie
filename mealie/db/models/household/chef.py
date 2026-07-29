from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table, Text, UniqueConstraint, orm
from sqlalchemy.orm import Mapped, mapped_column

from .._model_base import BaseMixins, FilterableColumn, SqlAlchemyBase
from .._model_utils import guid
from .._model_utils.auto_init import auto_init

if TYPE_CHECKING:
    from ..group import Group
    from ..users import User
    from .household import Household
    from .restaurant import Restaurant
    from .uploaded_book import UploadedBook


chefs_to_restaurants = Table(
    "chefs_to_restaurants",
    SqlAlchemyBase.metadata,
    Column("chef_id", guid.GUID, ForeignKey("chefs.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "restaurant_id",
        guid.GUID,
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

chefs_to_uploaded_books = Table(
    "chefs_to_uploaded_books",
    SqlAlchemyBase.metadata,
    Column("chef_id", guid.GUID, ForeignKey("chefs.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "uploaded_book_id",
        guid.GUID,
        ForeignKey("uploaded_books.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

restaurants_to_uploaded_books = Table(
    "restaurants_to_uploaded_books",
    SqlAlchemyBase.metadata,
    Column(
        "restaurant_id",
        guid.GUID,
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "uploaded_book_id",
        guid.GUID,
        ForeignKey("uploaded_books.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Chef(SqlAlchemyBase, BaseMixins):
    __tablename__ = "chefs"
    __table_args__ = (UniqueConstraint("group_id", "name", name="chefs_group_name_key"),)

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

    name: FilterableColumn[str] = mapped_column(String(255), nullable=False)
    aliases_json: FilterableColumn[str] = mapped_column(Text, nullable=False, default="[]")
    rank: FilterableColumn[str] = mapped_column(String(32), nullable=False, default="good", index=True)
    country: FilterableColumn[str | None] = mapped_column(String(120), nullable=True)
    cuisines_json: FilterableColumn[str] = mapped_column(Text, nullable=False, default="[]")
    specialties_json: FilterableColumn[str] = mapped_column(Text, nullable=False, default="[]")
    biography: FilterableColumn[str | None] = mapped_column(Text, nullable=True)
    career_summary: FilterableColumn[str | None] = mapped_column(Text, nullable=True)
    awards_json: FilterableColumn[str] = mapped_column(Text, nullable=False, default="[]")
    notable_restaurants_json: FilterableColumn[str] = mapped_column(Text, nullable=False, default="[]")
    book_titles_json: FilterableColumn[str] = mapped_column(Text, nullable=False, default="[]")
    website_url: FilterableColumn[str | None] = mapped_column(String(2000), nullable=True)
    wikipedia_url: FilterableColumn[str | None] = mapped_column(String(2000), nullable=True)
    instagram_url: FilterableColumn[str | None] = mapped_column(String(2000), nullable=True)
    has_michelin_restaurant: FilterableColumn[bool] = mapped_column(Boolean, nullable=False, default=False)
    michelin_star_count: FilterableColumn[int] = mapped_column(Integer, nullable=False, default=0)
    michelin_summary: FilterableColumn[str | None] = mapped_column(Text, nullable=True)
    notes: FilterableColumn[str | None] = mapped_column(Text, nullable=True)

    restaurants: Mapped[list["Restaurant"]] = orm.relationship(
        "Restaurant",
        secondary=chefs_to_restaurants,
        back_populates="chefs",
        lazy="selectin",
    )
    uploaded_books: Mapped[list["UploadedBook"]] = orm.relationship(
        "UploadedBook",
        secondary=chefs_to_uploaded_books,
        lazy="selectin",
    )

    @auto_init()
    def __init__(self, **_) -> None:
        pass
