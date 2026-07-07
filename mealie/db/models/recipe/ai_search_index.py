from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import mapped_column

from mealie.db.models._model_base import FilterableColumn, SqlAlchemyBase
from mealie.db.models._model_utils.datetime import NaiveDateTime
from mealie.db.models._model_utils.guid import GUID


class RecipeAISearchIndex(SqlAlchemyBase):
    __tablename__ = "recipe_ai_search_index"

    recipe_id: FilterableColumn[GUID] = mapped_column(
        GUID,
        sa.ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    group_id: FilterableColumn[GUID] = mapped_column(GUID, sa.ForeignKey("groups.id"), nullable=False, index=True)
    recipe_slug: FilterableColumn[str] = mapped_column(sa.String, nullable=False, index=True)
    recipe_name: FilterableColumn[str | None] = mapped_column(sa.String)
    recipe_updated_at: FilterableColumn[datetime | None] = mapped_column(NaiveDateTime)
    content_hash: FilterableColumn[str] = mapped_column(sa.String, nullable=False, index=True)
    catalog_json: FilterableColumn[str] = mapped_column(sa.Text, nullable=False)
    search_text: FilterableColumn[str] = mapped_column(sa.Text, nullable=False)
    search_vector: FilterableColumn[str] = mapped_column(sa.Text, nullable=False)
