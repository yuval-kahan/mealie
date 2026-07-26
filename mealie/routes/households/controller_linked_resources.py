from typing import Literal

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, status
from pydantic import UUID4, Field

from mealie.db.models.household.shopping_list import (
    ShoppingList,
    ShoppingListItem,
    ShoppingListItemRecipeReference,
    ShoppingListRecipeReference,
)
from mealie.db.models.household.shopping_website import (
    RecipeShoppingWebsite,
    ShoppingListShoppingWebsite,
    ShoppingWebsite,
)
from mealie.db.models.household.video import RecipeVideo, ShoppingListVideo, Video
from mealie.db.models.recipe.recipe import RecipeModel
from mealie.routes._base import controller
from mealie.routes._base.base_controllers import BaseUserController
from mealie.schema._mealie import MealieModel

router = APIRouter(prefix="/households/linked-resources", tags=["Households: Linked Resources"])
EntityType = Literal["recipe", "shopping-list", "video", "website"]


class LinkedResourceItem(MealieModel):
    id: UUID4
    name: str
    slug: str | None = None
    url: str | None = None


class LinkedResourcesOut(MealieModel):
    recipes: list[LinkedResourceItem] = Field(default_factory=list)
    shopping_lists: list[LinkedResourceItem] = Field(default_factory=list)
    videos: list[LinkedResourceItem] = Field(default_factory=list)
    websites: list[LinkedResourceItem] = Field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.recipes) + len(self.shopping_lists) + len(self.videos) + len(self.websites)


@controller(router)
class LinkedResourcesController(BaseUserController):
    def _recipe_items(self, recipe_ids: set[UUID4]) -> list[LinkedResourceItem]:
        if not recipe_ids:
            return []
        rows = self.session.execute(
            sa.select(RecipeModel.id, RecipeModel.name, RecipeModel.slug)
            .where(RecipeModel.group_id == self.group_id, RecipeModel.id.in_(recipe_ids))
            .order_by(RecipeModel.name)
        ).all()
        return [LinkedResourceItem(id=row.id, name=row.name or row.slug, slug=row.slug) for row in rows]

    def _shopping_list_items(self, list_ids: set[UUID4]) -> list[LinkedResourceItem]:
        if not list_ids:
            return []
        rows = self.session.execute(
            sa.select(ShoppingList.id, ShoppingList.name)
            .where(ShoppingList.group_id == self.group_id, ShoppingList.id.in_(list_ids))
            .order_by(ShoppingList.name)
        ).all()
        return [LinkedResourceItem(id=row.id, name=row.name or "Shopping list") for row in rows]

    def _video_items(self, video_ids: set[UUID4]) -> list[LinkedResourceItem]:
        if not video_ids:
            return []
        rows = self.session.execute(
            sa.select(Video.id, Video.title, Video.url)
            .where(Video.group_id == self.group_id, Video.id.in_(video_ids))
            .order_by(Video.title)
        ).all()
        return [LinkedResourceItem(id=row.id, name=row.title, url=row.url) for row in rows]

    def _website_items(self, website_ids: set[UUID4]) -> list[LinkedResourceItem]:
        if not website_ids:
            return []
        rows = self.session.execute(
            sa.select(ShoppingWebsite.id, ShoppingWebsite.name, ShoppingWebsite.url)
            .where(ShoppingWebsite.group_id == self.group_id, ShoppingWebsite.id.in_(website_ids))
            .order_by(ShoppingWebsite.name)
        ).all()
        return [LinkedResourceItem(id=row.id, name=row.name, url=row.url) for row in rows]

    def _ensure_entity(self, entity_type: EntityType, entity_id: UUID4) -> None:
        model = {
            "recipe": RecipeModel,
            "shopping-list": ShoppingList,
            "video": Video,
            "website": ShoppingWebsite,
        }[entity_type]
        exists = self.session.scalar(
            sa.select(sa.exists().where(model.id == entity_id, model.group_id == self.group_id))
        )
        if not exists:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Linked resource owner not found")

    @router.get("/{entity_type}/{entity_id}", response_model=LinkedResourcesOut)
    def get_links(self, entity_type: EntityType, entity_id: UUID4) -> LinkedResourcesOut:
        self._ensure_entity(entity_type, entity_id)
        recipe_ids: set[UUID4] = set()
        list_ids: set[UUID4] = set()
        video_ids: set[UUID4] = set()
        website_ids: set[UUID4] = set()

        if entity_type == "recipe":
            list_ids.update(
                self.session.scalars(
                    sa.select(ShoppingListRecipeReference.shopping_list_id).where(
                        ShoppingListRecipeReference.recipe_id == entity_id
                    )
                )
            )
            list_ids.update(
                self.session.scalars(
                    sa.select(ShoppingListItem.shopping_list_id)
                    .join(
                        ShoppingListItemRecipeReference,
                        ShoppingListItemRecipeReference.shopping_list_item_id == ShoppingListItem.id,
                    )
                    .where(ShoppingListItemRecipeReference.recipe_id == entity_id)
                )
            )
            video_ids.update(
                self.session.scalars(sa.select(RecipeVideo.video_id).where(RecipeVideo.recipe_id == entity_id))
            )
            website_ids.update(
                self.session.scalars(
                    sa.select(RecipeShoppingWebsite.shopping_website_id).where(
                        RecipeShoppingWebsite.recipe_id == entity_id
                    )
                )
            )
        elif entity_type == "shopping-list":
            recipe_ids.update(
                self.session.scalars(
                    sa.select(ShoppingListRecipeReference.recipe_id).where(
                        ShoppingListRecipeReference.shopping_list_id == entity_id,
                        ShoppingListRecipeReference.recipe_id.is_not(None),
                    )
                )
            )
            recipe_ids.update(
                self.session.scalars(
                    sa.select(ShoppingListItemRecipeReference.recipe_id)
                    .join(
                        ShoppingListItem,
                        ShoppingListItem.id == ShoppingListItemRecipeReference.shopping_list_item_id,
                    )
                    .where(
                        ShoppingListItem.shopping_list_id == entity_id,
                        ShoppingListItemRecipeReference.recipe_id.is_not(None),
                    )
                )
            )
            video_ids.update(
                self.session.scalars(
                    sa.select(ShoppingListVideo.video_id).where(ShoppingListVideo.shopping_list_id == entity_id)
                )
            )
            website_ids.update(
                self.session.scalars(
                    sa.select(ShoppingListShoppingWebsite.shopping_website_id).where(
                        ShoppingListShoppingWebsite.shopping_list_id == entity_id
                    )
                )
            )
        elif entity_type == "video":
            recipe_ids.update(
                self.session.scalars(sa.select(RecipeVideo.recipe_id).where(RecipeVideo.video_id == entity_id))
            )
            list_ids.update(
                self.session.scalars(
                    sa.select(ShoppingListVideo.shopping_list_id).where(ShoppingListVideo.video_id == entity_id)
                )
            )
        else:
            recipe_ids.update(
                self.session.scalars(
                    sa.select(RecipeShoppingWebsite.recipe_id).where(
                        RecipeShoppingWebsite.shopping_website_id == entity_id
                    )
                )
            )
            list_ids.update(
                self.session.scalars(
                    sa.select(ShoppingListShoppingWebsite.shopping_list_id).where(
                        ShoppingListShoppingWebsite.shopping_website_id == entity_id
                    )
                )
            )

        return LinkedResourcesOut(
            recipes=self._recipe_items(recipe_ids),
            shopping_lists=self._shopping_list_items({item for item in list_ids if item}),
            videos=self._video_items(video_ids),
            websites=self._website_items(website_ids),
        )
