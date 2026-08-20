from functools import cached_property

from fastapi import APIRouter, Depends, HTTPException, status
from humps.main import camelize
from pydantic import UUID4, ConfigDict, field_validator
from slugify import slugify

from mealie.repos.all_repositories import get_repositories
from mealie.routes._base import BaseCrudController, controller
from mealie.routes._base.mixins import HttpRepo
from mealie.db.models.recipe.category import Category
from mealie.schema import mapper
from mealie.schema._mealie import MealieModel
from mealie.schema.recipe import CategoryIn, RecipeCategoryResponse
from mealie.schema.recipe.recipe import RecipeCategory, RecipeCategoryPagination
from mealie.schema.recipe.recipe_category import CategoryBase, CategoryOut, CategorySave
from mealie.schema.response.pagination import PaginationQuery
from mealie.services import urls
from mealie.services.event_bus_service.event_types import EventCategoryData, EventOperation, EventTypes

router = APIRouter(prefix="/categories", tags=["Organizer: Categories"])


class CategorySummary(MealieModel):
    id: UUID4
    slug: str
    name: str
    is_recipe_group: bool = False
    recipe_group_section: str = "recipes"
    parent_category_id: UUID4 | None = None
    model_config = ConfigDict(
        alias_generator=camelize,
        populate_by_name=True,
        from_attributes=True,
    )

    @field_validator("recipe_group_section", mode="before")
    @classmethod
    def normalize_recipe_group_section(cls, value: str | None) -> str:
        return (value or "recipes").strip() or "recipes"


@controller(router)
class RecipeCategoryController(BaseCrudController):
    # =========================================================================
    # CRUD Operations
    @cached_property
    def repo(self):
        return self.repos.categories

    @cached_property
    def mixins(self):
        return HttpRepo[CategorySave, CategoryOut, CategorySave](self.repo, self.logger)

    @router.get("", response_model=RecipeCategoryPagination)
    def get_all(self, q: PaginationQuery = Depends(PaginationQuery), search: str | None = None):
        """Returns a list of available categories in the database"""
        response = self.repo.page_all(
            pagination=q,
            override=RecipeCategory,
            search=search,
        )

        response.set_pagination_guides(router.url_path_for("get_all"), q.model_dump())
        return response

    @router.post("", response_model=CategoryOut, status_code=201)
    def create_one(self, category: CategoryIn):
        """Creates a Category in the database"""
        self.checks.can_organize()

        category_name = category.name.strip()
        existing_categories = self.repos.categories.get_all()
        requested_section = category.recipe_group_section or "recipes"
        for existing_category in existing_categories:
            same_name = existing_category.name.strip().casefold() == category_name.casefold()
            same_scope = (
                bool(existing_category.is_recipe_group) == bool(category.is_recipe_group)
                and (existing_category.recipe_group_section or "recipes") == requested_section
                and existing_category.parent_category_id == category.parent_category_id
            )
            if same_name and same_scope:
                return CategoryOut.model_validate(existing_category)

        save_data = mapper.cast(category, CategorySave, group_id=self.group_id)
        save_data.name = category_name
        used_slugs = {existing_category.slug for existing_category in existing_categories}
        base_slug = slugify(category_name) or "category"
        unique_slug = base_slug
        suffix = 2
        while unique_slug in used_slugs:
            unique_slug = f"{base_slug}-{suffix}"
            suffix += 1
        save_data.slug = unique_slug
        new_category = self.mixins.create_one(save_data)
        if new_category:
            self.publish_event(
                event_type=EventTypes.category_created,
                document_data=EventCategoryData(operation=EventOperation.create, category_id=new_category.id),
                group_id=new_category.group_id,
                household_id=None,
                message=self.t(
                    "notifications.generic-created-with-url",
                    name=new_category.name,
                    url=urls.category_url(new_category.slug, self.settings.BASE_URL),
                ),
            )

        return new_category

    @router.get("/empty", response_model=list[CategoryBase])
    def get_all_empty(self):
        """Returns a list of categories that do not contain any recipes"""
        return self.repos.categories.get_empty()

    @router.get("/recipe-groups", response_model=list[CategorySummary])
    def get_recipe_groups(self):
        """Returns every custom recipe-library category, without pagination."""
        categories = (
            self.repos.session.query(Category)
            .filter(
                Category.group_id == self.group_id,
                Category.is_recipe_group.is_(True),
            )
            .order_by(Category.recipe_group_section.asc(), Category.name.asc())
            .all()
        )
        return [CategorySummary.model_validate(category) for category in categories]

    @router.get("/{item_id}", response_model=CategorySummary)
    def get_one(self, item_id: UUID4):
        """Returns a list of recipes associated with the provided category."""
        category_obj = self.mixins.get_one(item_id)
        category_obj = CategorySummary.model_validate(category_obj)
        return category_obj

    @router.put("/{item_id}", response_model=CategorySummary)
    def update_one(self, item_id: UUID4, update_data: CategoryIn):
        """Updates an existing Tag in the database"""
        self.checks.can_organize()
        current = self.mixins.get_one(item_id)
        category_name = update_data.name.strip()
        if not category_name:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Category name cannot be empty")

        update_data.name = category_name
        if "is_recipe_group" not in update_data.model_fields_set:
            update_data.is_recipe_group = bool(current.is_recipe_group)
        if "recipe_group_section" not in update_data.model_fields_set:
            update_data.recipe_group_section = current.recipe_group_section or "recipes"
        if "parent_category_id" not in update_data.model_fields_set:
            update_data.parent_category_id = current.parent_category_id

        # Category slugs are unique per group. A rename must go through the
        # same collision-safe slug allocation as category creation, otherwise
        # renaming one category to an existing slug fails with a generic 400.
        existing_categories = self.repos.categories.get_all()
        used_slugs = {
            existing_category.slug
            for existing_category in existing_categories
            if existing_category.id != current.id and existing_category.slug
        }
        base_slug = slugify(category_name) or "category"
        unique_slug = base_slug
        suffix = 2
        while unique_slug in used_slugs:
            unique_slug = f"{base_slug}-{suffix}"
            suffix += 1

        save_data = mapper.cast(update_data, CategorySave, group_id=self.group_id)
        save_data.slug = unique_slug
        category = self.mixins.update_one(save_data, item_id)

        if category:
            self.publish_event(
                event_type=EventTypes.category_updated,
                document_data=EventCategoryData(operation=EventOperation.update, category_id=category.id),
                group_id=category.group_id,
                household_id=None,
                message=self.t(
                    "notifications.generic-updated-with-url",
                    name=category.name,
                    url=urls.category_url(category.slug, self.settings.BASE_URL),
                ),
            )

        return category

    @router.delete("/{item_id}")
    def delete_one(self, item_id: UUID4):
        """
        Removes a recipe category from the database. Deleting a
        category does not impact a recipe. The category will be removed
        from any recipes that contain it
        """
        self.checks.can_organize()
        category = self.mixins.get_one(item_id)
        children = self.repos.session.query(Category).filter(
            Category.group_id == self.group_id,
            Category.parent_category_id == item_id,
        ).all()
        for child in children:
            child.parent_category_id = category.parent_category_id
            self.repos.session.add(child)
        if children:
            self.repos.session.flush()
        if category := self.mixins.delete_one(item_id):
            self.publish_event(
                event_type=EventTypes.category_deleted,
                document_data=EventCategoryData(operation=EventOperation.delete, category_id=category.id),
                group_id=category.group_id,
                household_id=None,
                message=self.t("notifications.generic-deleted", name=category.name),
            )

    # =========================================================================
    # Read All Operations

    @router.get("/slug/{category_slug}")
    def get_one_by_slug(self, category_slug: str):
        """Returns a category object with the associated recieps relating to the category"""
        category: RecipeCategory = self.mixins.get_one(category_slug, "slug")

        group_recipes = get_repositories(self.repos.session, group_id=self.group_id, household_id=None).recipes
        recipe_data = group_recipes.page_all(
            PaginationQuery(per_page=-1, query_filter=f'recipe_category.id IN ["{category.id}"]')
        )

        return RecipeCategoryResponse.model_construct(
            id=category.id,
            slug=category.slug,
            name=category.name,
            group_id=category.group_id,
            is_recipe_group=category.is_recipe_group,
            recipe_group_section=category.recipe_group_section or "recipes",
            parent_category_id=category.parent_category_id,
            recipes=recipe_data.items,
        )
