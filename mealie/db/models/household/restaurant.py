from typing import TYPE_CHECKING, Optional

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint, orm
from sqlalchemy.orm import Mapped, mapped_column

from .._model_base import BaseMixins, FilterableColumn, SqlAlchemyBase
from .._model_utils import guid
from .._model_utils.auto_init import auto_init

if TYPE_CHECKING:
    from ..group import Group
    from ..users import User
    from .household import Household


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
    google_rating: FilterableColumn[float | None] = mapped_column(Float, nullable=True)
    google_review_count: FilterableColumn[int | None] = mapped_column(Integer, nullable=True)
    google_maps_url: FilterableColumn[str | None] = mapped_column(String(2000), nullable=True)
    our_rating: FilterableColumn[float | None] = mapped_column(Float, nullable=True)
    recommendation_status: FilterableColumn[str] = mapped_column(
        String(32), nullable=False, default="recommended", index=True
    )
    visit_status: FilterableColumn[str] = mapped_column(String(32), nullable=False, default="not_tried", index=True)

    @auto_init()
    def __init__(self, **_) -> None:
        pass
