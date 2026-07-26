import json
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime
from typing import cast

import sqlalchemy as sa
from fastapi import HTTPException, status
from pydantic import UUID4

from mealie.core.exceptions import UnexpectedNone
from mealie.db.models.household.shopping_list import ShoppingList
from mealie.lang.locale_config import LOCALE_CONFIG
from mealie.repos.all_repositories import get_repositories
from mealie.repos.repository_factory import AllRepositories
from mealie.schema.group.ai_providers import AIProviderOut
from mealie.schema.household.group_shopping_list import (
    ShoppingListAddRecipeParamsBulk,
    ShoppingListCreate,
    ShoppingListItemBase,
    ShoppingListItemCreate,
    ShoppingListItemOut,
    ShoppingListItemRecipeRefCreate,
    ShoppingListItemRecipeRefOut,
    ShoppingListItemsCollectionOut,
    ShoppingListItemUpdate,
    ShoppingListItemUpdateBulk,
    ShoppingListMergeRequest,
    ShoppingListMultiPurposeLabelCreate,
    ShoppingListOut,
    ShoppingListSave,
    ShoppingListSummary,
)
from mealie.schema.labels.multi_purpose_label import MultiPurposeLabelCreate
from mealie.schema.openai.recipe import OpenAIRecipeIngredientAdjustment
from mealie.schema.openai.shopping_list import OpenAIShoppingListOrganization
from mealie.schema.recipe.recipe import Recipe
from mealie.schema.recipe.recipe_ingredient import (
    IngredientFood,
    IngredientUnit,
    RecipeIngredient,
)
from mealie.schema.response.pagination import OrderDirection, PaginationQuery
from mealie.services.group_services.labels_service import MultiPurposeLabelService
from mealie.services.openai import OpenAIService
from mealie.services.parser_services._base import DataMatcher
from mealie.services.parser_services.parser_utils import UnitConverter, merge_quantity_and_unit


class ShoppingListService:
    DEFAULT_FOOD_FUZZY_MATCH_THRESHOLD = 80
    AI_ORGANIZED_EXTRA_KEY = "aiOrganized"
    AI_ORGANIZED_AT_EXTRA_KEY = "aiOrganizedAt"
    MERGED_LIST_EXTRA_KEY = "isMergedList"
    MERGED_SOURCE_IDS_EXTRA_KEY = "mergedFromListIds"
    MERGED_SOURCE_NAMES_EXTRA_KEY = "mergedFromListNames"
    AI_LABEL_COLORS = {
        "ירקות ופירות": "#4CAF50",
        "מוצרי חלב וביצים": "#42A5F5",
        "בשר עוף ודגים": "#EF5350",
        "מזווה ויבשים": "#8D6E63",
        "תבלינים ורטבים": "#FF9800",
        "אפייה": "#AB47BC",
        "קפואים": "#26C6DA",
        "משקאות": "#5C6BC0",
        "ניקיון וחד פעמי": "#78909C",
        "שונות": "#959595",
    }

    def validated_unique_list_name(self, name: str | None, exclude_id: UUID4 | None = None) -> str | None:
        normalized_name = (name or "").strip()
        if not normalized_name:
            return name

        query = sa.select(ShoppingList.id).where(
            ShoppingList.group_id == self.repos.group_id,
            sa.func.lower(sa.func.trim(ShoppingList.name)) == normalized_name.lower(),
        )
        if exclude_id is not None:
            query = query.where(ShoppingList.id != exclude_id)
        if self.repos.session.execute(query.limit(1)).scalar_one_or_none() is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Shopping list name already exists")

        return normalized_name

    def available_unique_list_name(self, name: str | None) -> str | None:
        """Return a unique display name without loading every shopping list."""

        base_name = " ".join((name or "").split()).strip()
        if not base_name:
            return name

        candidate = base_name
        suffix = 2
        while True:
            query = sa.select(ShoppingList.id).where(
                ShoppingList.group_id == self.repos.group_id,
                sa.func.lower(sa.func.trim(ShoppingList.name)) == candidate.casefold(),
            )
            if self.repos.session.execute(query.limit(1)).scalar_one_or_none() is None:
                return candidate
            candidate = f"{base_name} ({suffix})"
            suffix += 1

    @staticmethod
    def _target_language_instruction(target_language: str | None) -> str:
        """Build a clear output-language contract for AI-generated list metadata."""
        requested = (target_language or "").strip().replace("_", "-")
        if not requested:
            return ""

        locale = LOCALE_CONFIG.get(requested)
        language = f"{locale.name} (locale {locale.key})" if locale else requested
        return (
            "\n\nOUTPUT LANGUAGE REQUIREMENT (mandatory): Return every generated grocery "
            f"category name and every recommended shopping note in {language}. Keep existing item "
            "names unchanged; only translate AI-generated category names and notes."
        )

    @staticmethod
    def _fallback_ai_category(target_language: str | None) -> str:
        primary_language = (target_language or "").strip().replace("_", "-").split("-", 1)[0].lower()
        return {
            "he": "שונות",
            "ar": "متفرقات",
            "de": "Sonstiges",
            "es": "Otros",
            "fr": "Autres",
            "it": "Altro",
            "pt": "Outros",
            "ru": "Другое",
        }.get(primary_language, "Other")

    def __init__(self, repos: AllRepositories):
        self.repos = repos
        self.shopping_lists = repos.group_shopping_lists
        self.list_items = repos.group_shopping_list_item
        self.list_item_refs = repos.group_shopping_list_item_references
        self.list_refs = repos.group_shopping_list_recipe_refs
        self.data_matcher = DataMatcher(self.repos, food_fuzzy_match_threshold=self.DEFAULT_FOOD_FUZZY_MATCH_THRESHOLD)

    @staticmethod
    def _normalize_ai_label_name(name: str | None) -> str:
        return " ".join(str(name or "").split()).strip()

    @classmethod
    def _ai_label_key(cls, name: str | None) -> str:
        return cls._normalize_ai_label_name(name).casefold()

    @staticmethod
    def _shopping_list_item_ai_text(item: ShoppingListItemOut) -> str:
        item_parts: list[str] = []
        if item.quantity:
            item_parts.append(str(item.quantity))
        if item.unit and item.unit.name:
            item_parts.append(item.unit.name)
        if item.food and item.food.name:
            item_parts.append(item.food.name)
        if item.note:
            item_parts.append(item.note)

        return " ".join(item_parts).strip() or item.display or ""

    def _get_or_create_ai_labels(self, category_names: list[str]):
        labels_page = self.repos.group_multi_purpose_labels.page_all(PaginationQuery(page=1, per_page=-1))
        labels_by_key = {self._ai_label_key(label.name): label for label in labels_page.items}
        label_service = MultiPurposeLabelService(self.repos)

        for category_name in category_names:
            normalized_name = self._normalize_ai_label_name(category_name)
            key = self._ai_label_key(normalized_name)
            if not key or key in labels_by_key:
                continue

            label = label_service.create_one(
                MultiPurposeLabelCreate(
                    name=normalized_name,
                    color=self.AI_LABEL_COLORS.get(normalized_name, "#959595"),
                )
            )
            labels_by_key[key] = label

        return labels_by_key

    def _shopping_list_ai_payload(self, shopping_list: ShoppingListOut) -> list[dict]:
        return [
            {
                "id": str(item.id),
                "text": self._shopping_list_item_ai_text(item),
                "currentCategory": item.label.name if item.label else None,
                "checked": item.checked,
            }
            for item in shopping_list.list_items
            if self._shopping_list_item_ai_text(item)
        ]

    async def organize_with_ai(
        self,
        list_id: UUID4,
        include_ai_tips: bool = False,
        provider: AIProviderOut | None = None,
        target_language: str | None = None,
    ) -> tuple[ShoppingListOut, ShoppingListItemsCollectionOut]:
        shopping_list = self.shopping_lists.get_one(list_id)
        if shopping_list is None:
            raise UnexpectedNone("Shopping list not found")

        items_payload = self._shopping_list_ai_payload(shopping_list)
        if not items_payload:
            raise ValueError("Shopping list is empty")

        openai_service = OpenAIService(self.repos)
        if not (openai_service.provider_settings and openai_service.provider_settings.ai_enabled):
            raise ValueError("OpenAI services are not available")

        existing_categories = [
            label_setting.label.name
            for label_setting in shopping_list.label_settings
            if label_setting.label and label_setting.label.name
        ]
        prompt = openai_service.get_prompt("shopping-lists.organize-shopping-list")
        message = (
            "Organize the shopping list items into practical grocery categories.\n\n"
            f"Add AI shopping notes JSON boolean: {json.dumps(include_ai_tips)}\n\n"
            f"Existing categories JSON:\n{json.dumps(existing_categories, ensure_ascii=False)}\n\n"
            f"Shopping list items JSON:\n{json.dumps(items_payload, ensure_ascii=False)}"
            f"{self._target_language_instruction(target_language)}"
        )

        response = await openai_service.get_response(
            prompt,
            message,
            response_schema=OpenAIShoppingListOrganization,
            provider=provider,
        )
        if not response:
            raise ValueError("AI returned an empty response")

        valid_items_by_id = {str(item.id): item for item in shopping_list.list_items}
        category_by_item_id: dict[str, str] = {}
        recommended_note_by_item_id: dict[str, str] = {}
        for assignment in response.assignments:
            item_id = str(assignment.item_id)
            if item_id not in valid_items_by_id:
                continue

            category_name = self._normalize_ai_label_name(assignment.category) or self._fallback_ai_category(
                target_language
            )
            category_by_item_id[item_id] = category_name
            if include_ai_tips and assignment.recommended_note:
                recommended_note = " ".join(assignment.recommended_note.split()).strip()
                if recommended_note:
                    recommended_note_by_item_id[item_id] = recommended_note

        # Make sure every item receives a stable category even if the model omitted one.
        for item_id, item in valid_items_by_id.items():
            if item_id not in category_by_item_id:
                category_by_item_id[item_id] = item.label.name if item.label else self._fallback_ai_category(
                    target_language
                )

        labels_by_key = self._get_or_create_ai_labels(list(category_by_item_id.values()))

        update_items: list[ShoppingListItemUpdateBulk] = []
        for item_id, category_name in category_by_item_id.items():
            item = valid_items_by_id[item_id]
            label = labels_by_key.get(self._ai_label_key(category_name))
            note = recommended_note_by_item_id.get(item_id)
            if note and note not in (item.note or ""):
                item.note = " | ".join([part for part in [item.note, note] if part])

            if not label and not note:
                continue
            if label and item.label_id == label.id and not note:
                continue

            if label:
                item.label_id = label.id
            update_items.append(item.cast(ShoppingListItemUpdateBulk, id=item.id))

        updated_items = cast(
            list[ShoppingListItemOut],
            self.list_items.update_many(update_items) if update_items else [],
        )

        updated_list = cast(ShoppingListOut, self.shopping_lists.get_one(list_id))
        extras = dict(updated_list.extras or {})
        extras[self.AI_ORGANIZED_EXTRA_KEY] = "true"
        extras[self.AI_ORGANIZED_AT_EXTRA_KEY] = datetime.now(UTC).isoformat()
        updated_list.extras = extras
        updated_list = self.shopping_lists.update(updated_list.id, updated_list)

        return updated_list, ShoppingListItemsCollectionOut(
            created_items=[],
            updated_items=updated_items,
            deleted_items=[],
        )

    async def adjust_quantities_with_ai(
        self,
        list_id: UUID4,
        request: str,
        provider: AIProviderOut | None = None,
    ) -> tuple[ShoppingListOut, ShoppingListItemsCollectionOut, str]:
        shopping_list = cast(ShoppingListOut | None, self.shopping_lists.get_one(list_id))
        if shopping_list is None:
            raise UnexpectedNone("Shopping list not found")

        source_items = list(shopping_list.list_items or [])
        if not source_items:
            raise ValueError("Shopping list is empty")
        normalized_request = " ".join(request.split()).strip()
        if len(normalized_request) < 2:
            raise ValueError("Describe the quantity change")

        openai_service = OpenAIService(self.repos)
        if not (openai_service.provider_settings and openai_service.provider_settings.ai_enabled):
            raise ValueError("OpenAI services are not available")

        ingredient_candidates = [
            {
                "ingredientIndex": index,
                "title": item.label.name if item.label else None,
                "quantity": item.quantity,
                "unit": item.unit.name if item.unit else None,
                "food": item.food.name if item.food else None,
                "note": item.note or "",
                "recommendedVariety": None,
                "originalText": self._shopping_list_item_ai_text(item),
            }
            for index, item in enumerate(source_items)
        ]
        message = (
            f"User adjustment request:\n{normalized_request}\n\n"
            "The following ingredient_candidates are the complete shopping list. "
            "Return every ingredientIndex exactly once.\n\n"
            f"{json.dumps(ingredient_candidates, ensure_ascii=False)}"
        )
        response = await openai_service.get_response(
            openai_service.get_prompt("recipes.adjust-ingredients"),
            message,
            response_schema=OpenAIRecipeIngredientAdjustment,
            provider=provider,
        )
        if not response or not response.adjusted:
            raise ValueError(response.reason if response else "AI returned an empty response")

        adjusted_by_index = {item.ingredient_index: item for item in response.ingredients}
        expected_indexes = set(range(len(source_items)))
        if len(adjusted_by_index) != len(response.ingredients) or set(adjusted_by_index) != expected_indexes:
            raise ValueError("AI returned an incomplete shopping list")

        update_items: list[ShoppingListItemUpdateBulk] = []
        for index, source in enumerate(source_items):
            adjusted = adjusted_by_index[index]
            current_food = (source.food.name if source.food else "").strip().casefold()
            adjusted_food = (adjusted.food or "").strip().casefold()
            current_unit = (source.unit.name if source.unit else "").strip().casefold()
            adjusted_unit = (adjusted.unit or "").strip().casefold()
            can_keep_structure = current_food == adjusted_food and current_unit == adjusted_unit

            if can_keep_structure and adjusted.quantity is not None:
                payload = source.cast(
                    ShoppingListItemUpdateBulk,
                    id=source.id,
                    quantity=adjusted.quantity,
                    note=adjusted.note,
                )
            else:
                adjusted_text = " ".join(
                    part
                    for part in [
                        str(adjusted.quantity) if adjusted.quantity is not None else "",
                        adjusted.unit or "",
                        adjusted.food or "",
                        adjusted.note or "",
                    ]
                    if part
                ).strip()
                payload = source.cast(
                    ShoppingListItemUpdateBulk,
                    id=source.id,
                    quantity=0,
                    unit=None,
                    unit_id=None,
                    food=None,
                    food_id=None,
                    note=adjusted.original_text or adjusted_text,
                )
            update_items.append(payload)

        changed = self.bulk_update_items(update_items)
        updated_list = cast(ShoppingListOut, self.shopping_lists.get_one(list_id))
        extras = dict(updated_list.extras or {})
        extras["aiQuantityAdjustment"] = {
            "appliedAt": datetime.now(UTC).isoformat(),
            "request": normalized_request,
            "reason": response.reason,
        }
        updated_list.extras = extras
        updated_list = self.shopping_lists.update(updated_list.id, updated_list)
        return cast(ShoppingListOut, updated_list), changed, response.reason

    def can_merge(self, item1: ShoppingListItemBase, item2: ShoppingListItemBase) -> bool:
        """Check to see if this item can be merged with another item"""

        if any(
            [
                item1.checked,
                item2.checked,
                item1.food_id != item2.food_id,
            ]
        ):
            return False

        # check if units match or if they're compatable
        if item1.unit_id != item2.unit_id:
            item1_unit = item1.unit or self.data_matcher.units_by_id.get(item1.unit_id)
            item2_unit = item2.unit or self.data_matcher.units_by_id.get(item2.unit_id)
            if not (item1_unit and item1_unit.standard_unit):
                return False
            if not (item2_unit and item2_unit.standard_unit):
                return False

            uc = UnitConverter()
            if not uc.can_convert(item1_unit.standard_unit, item2_unit.standard_unit):
                return False

        # Structured foods have already matched by ID. For legacy/unparsed items,
        # require an actual text identity so two empty records are never folded
        # together merely because both have no food ID and an empty note.
        if item1.food_id:
            return True

        note1 = (item1.note or "").strip().casefold()
        note2 = (item2.note or "").strip().casefold()
        if note1 or note2:
            return note1 == note2

        display1 = (item1.display or "").strip().casefold()
        display2 = (item2.display or "").strip().casefold()
        return bool(display1 and display1 == display2)

    def merge_items(
        self,
        from_item: ShoppingListItemCreate | ShoppingListItemUpdateBulk,
        to_item: ShoppingListItemCreate | ShoppingListItemUpdateBulk | ShoppingListItemOut,
    ) -> ShoppingListItemUpdate:
        """
        Takes an item and merges it into an already-existing item, then returns a copy

        Attributes of the `to_item` take priority over the `from_item`, except extras with overlapping keys
        """

        to_item_unit = to_item.unit or self.data_matcher.units_by_id.get(to_item.unit_id)
        from_item_unit = from_item.unit or self.data_matcher.units_by_id.get(from_item.unit_id)
        if to_item_unit and to_item_unit.standard_unit and from_item_unit and from_item_unit.standard_unit:
            merged_qty, merged_unit = merge_quantity_and_unit(
                from_item.quantity or 0, from_item_unit, to_item.quantity or 0, to_item_unit
            )
            to_item.quantity = merged_qty
            to_item.unit_id = merged_unit.id
            to_item.unit = merged_unit

        else:
            # No conversion needed, just sum the quantities
            to_item.quantity += from_item.quantity

        if to_item.note != from_item.note:
            to_item.note = " | ".join([note for note in [to_item.note, from_item.note] if note])

        if from_item.note and to_item.note != from_item.note:
            notes: set[str] = set(to_item.note.split(" | ")) if to_item.note else set()
            notes.add(from_item.note)
            to_item.note = " | ".join([note for note in notes if note])

        if to_item.extras and from_item.extras:
            to_item.extras.update(from_item.extras)

        updated_refs = {ref.recipe_id: ref for ref in from_item.recipe_references}
        for to_ref in to_item.recipe_references:
            if to_ref.recipe_id not in updated_refs:
                updated_refs[to_ref.recipe_id] = to_ref
                continue

            # merge recipe scales
            base_ref = updated_refs[to_ref.recipe_id]

            # if the scale is missing we assume it's 1 for backwards compatibility
            # if the scale is 0 we leave it alone
            if base_ref.recipe_scale is None:
                base_ref.recipe_scale = 1

            if to_ref.recipe_scale is None:
                to_ref.recipe_scale = 1

            base_ref.recipe_scale += to_ref.recipe_scale

        return to_item.cast(ShoppingListItemUpdate, recipe_references=list(updated_refs.values()))

    def remove_unused_recipe_references(self, shopping_list_id: UUID4) -> None:
        shopping_list = cast(ShoppingListOut, self.shopping_lists.get_one(shopping_list_id))

        recipe_ids_to_keep: set[UUID4] = set()
        for item in shopping_list.list_items:
            recipe_ids_to_keep.update([ref.recipe_id for ref in item.recipe_references])

        list_refs_to_delete: set[UUID4] = set()
        for list_ref in shopping_list.recipe_references:
            if list_ref.recipe_id not in recipe_ids_to_keep:
                list_refs_to_delete.add(list_ref.id)

        if list_refs_to_delete:
            self.list_refs.delete_many(list_refs_to_delete)

    def find_matching_label(self, item: ShoppingListItemBase) -> UUID4 | None:
        if item.label_id:
            return item.label_id
        if item.food:
            return item.food.label_id

        food_search = self.data_matcher.find_food_match(item.display)
        return food_search.label_id if food_search else None

    @staticmethod
    def _item_merge_bucket(item: ShoppingListItemBase) -> tuple[str, str, str] | None:
        """Return a narrow merge bucket so consolidation stays close to linear."""
        if item.checked:
            return None

        if item.food_id:
            identity_type = "food"
            identity = str(item.food_id)
        else:
            note = (item.note or "").strip().casefold()
            display = (item.display or "").strip().casefold()
            if note:
                identity_type = "note"
                identity = note
            elif display:
                identity_type = "display"
                identity = display
            else:
                return None

        return str(item.shopping_list_id), identity_type, identity

    def _consolidate_create_items(
        self,
        create_items: Iterable[ShoppingListItemCreate],
    ) -> list[ShoppingListItemCreate]:
        consolidated: list[ShoppingListItemCreate] = []
        bucket_indexes: dict[tuple[str, str, str], list[int]] = {}

        for create_item in create_items:
            bucket = self._item_merge_bucket(create_item)
            if bucket is not None:
                for index in bucket_indexes.get(bucket, []):
                    filtered_item = consolidated[index]
                    if not self.can_merge(create_item, filtered_item):
                        continue

                    consolidated[index] = self.merge_items(create_item, filtered_item).cast(
                        ShoppingListItemCreate
                    )
                    break
                else:
                    bucket_indexes.setdefault(bucket, []).append(len(consolidated))
                    consolidated.append(create_item)
                continue

            consolidated.append(create_item)

        return consolidated

    def bulk_create_items(
        self, create_items: Iterable[ShoppingListItemCreate], auto_find_labels=True
    ) -> ShoppingListItemsCollectionOut:
        """
        Create a list of items, merging into existing ones where possible.
        Optionally try to find a label for each item if one isn't provided using the item's food data or display name.
        """

        create_items = self._consolidate_create_items(create_items)
        filtered_create_items: list[ShoppingListItemCreate] = []

        # check to see if we can merge into any existing items
        update_items: list[ShoppingListItemUpdateBulk] = []
        existing_items_map: dict[UUID4, dict[tuple[str, str, str], list[ShoppingListItemOut]]] = {}
        for create_item in create_items:
            if create_item.shopping_list_id not in existing_items_map:
                query = PaginationQuery(
                    per_page=-1, query_filter=f"shopping_list_id={create_item.shopping_list_id} AND checked=false"
                )
                items_data = self.list_items.page_all(query)
                existing_item_buckets: dict[tuple[str, str, str], list[ShoppingListItemOut]] = {}
                for existing_item in items_data.items:
                    bucket = self._item_merge_bucket(existing_item)
                    if bucket is not None:
                        existing_item_buckets.setdefault(bucket, []).append(existing_item)
                existing_items_map[create_item.shopping_list_id] = existing_item_buckets

            merged = False
            create_bucket = self._item_merge_bucket(create_item)
            existing_candidates = (
                existing_items_map[create_item.shopping_list_id].get(create_bucket, [])
                if create_bucket is not None
                else []
            )
            for existing_item in existing_candidates:
                if not self.can_merge(existing_item, create_item):
                    continue

                updated_existing_item = self.merge_items(create_item, existing_item).cast(
                    ShoppingListItemUpdateBulk, id=existing_item.id
                )
                update_items.append(updated_existing_item.cast(ShoppingListItemUpdateBulk, id=existing_item.id))
                merged = True
                break

            if merged or create_item.quantity < 0:
                continue

            # create the item
            if create_item.checked:
                # checked items should not have recipe references
                create_item.recipe_references = []
            if auto_find_labels:
                create_item.label_id = self.find_matching_label(create_item)

            filtered_create_items.append(create_item)

        created_items = self.list_items.create_many(filtered_create_items) if filtered_create_items else []
        updated_items = self.list_items.update_many(update_items) if update_items else []

        for list_id in {item.shopping_list_id for item in created_items + updated_items}:
            self.remove_unused_recipe_references(list_id)

        return ShoppingListItemsCollectionOut(
            created_items=created_items, updated_items=updated_items, deleted_items=[]
        )

    def bulk_update_items(self, update_items: list[ShoppingListItemUpdateBulk]) -> ShoppingListItemsCollectionOut:
        # consolidate items to be created
        consolidated_update_items: list[ShoppingListItemUpdateBulk] = []
        delete_items: set[UUID4] = set()
        seen_update_ids: set[UUID4] = set()
        for update_item in update_items:
            # if the same item appears multiple times in one request, ignore all but the first instance
            if update_item.id in seen_update_ids:
                continue

            seen_update_ids.add(update_item.id)

            merged = False
            for i, filtered_item in enumerate(consolidated_update_items):
                if not self.can_merge(update_item, filtered_item):
                    continue

                consolidated_update_items[i] = self.merge_items(update_item, filtered_item).cast(
                    ShoppingListItemUpdateBulk, id=filtered_item.id
                )
                delete_items.add(update_item.id)
                merged = True
                break

            if not merged:
                consolidated_update_items.append(update_item)

        update_items = consolidated_update_items

        # check to see if we can merge into any existing items
        filtered_update_items: list[ShoppingListItemUpdateBulk] = []
        existing_items_map: dict[UUID4, list[ShoppingListItemOut]] = {}
        for update_item in update_items:
            if update_item.shopping_list_id not in existing_items_map:
                query = PaginationQuery(
                    per_page=-1, query_filter=f"shopping_list_id={update_item.shopping_list_id} AND checked=false"
                )
                items_data = self.list_items.page_all(query)
                existing_items_map[update_item.shopping_list_id] = items_data.items

            merged = False
            for existing_item in existing_items_map[update_item.shopping_list_id]:
                if existing_item.id in delete_items or existing_item.id == update_item.id:
                    continue

                if not self.can_merge(update_item, existing_item):
                    continue

                updated_existing_item = self.merge_items(update_item, existing_item).cast(
                    ShoppingListItemUpdateBulk, id=existing_item.id
                )
                filtered_update_items.append(updated_existing_item)
                delete_items.add(update_item.id)
                merged = True
                break

            if merged:
                continue

            # update or delete the item
            if update_item.quantity < 0:
                delete_items.add(update_item.id)
                continue

            if update_item.checked:
                # checked items should not have recipe references
                update_item.recipe_references = []

            filtered_update_items.append(update_item)

        updated_items = cast(
            list[ShoppingListItemOut],
            self.list_items.update_many(filtered_update_items) if filtered_update_items else [],  # type: ignore
        )

        deleted_items = cast(
            list[ShoppingListItemOut],
            self.list_items.delete_many(delete_items) if delete_items else [],  # type: ignore
        )

        for list_id in {item.shopping_list_id for item in updated_items + deleted_items}:
            self.remove_unused_recipe_references(list_id)

        return ShoppingListItemsCollectionOut(
            created_items=[], updated_items=updated_items, deleted_items=deleted_items
        )

    def bulk_delete_items(self, delete_items: list[UUID4]) -> ShoppingListItemsCollectionOut:
        deleted_items = cast(
            list[ShoppingListItemOut],
            self.list_items.delete_many(set(delete_items)) if delete_items else [],  # type: ignore
        )

        for list_id in {item.shopping_list_id for item in deleted_items}:
            self.remove_unused_recipe_references(list_id)

        return ShoppingListItemsCollectionOut(created_items=[], updated_items=[], deleted_items=deleted_items)

    @classmethod
    def is_merged_list(cls, shopping_list: ShoppingListCreate) -> bool:
        value = (shopping_list.extras or {}).get(cls.MERGED_LIST_EXTRA_KEY)
        return value is True or str(value).lower() == "true"

    def merge_lists(
        self,
        data: ShoppingListMergeRequest,
        owner_id: UUID4,
    ) -> tuple[ShoppingListOut, ShoppingListItemsCollectionOut]:
        source_names: list[str] = []
        for source_id in data.source_list_ids:
            source = cast(
                ShoppingListSummary | None,
                self.shopping_lists.get_one(source_id, override_schema=ShoppingListSummary),
            )
            if source is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Shopping list not found")
            if self.is_merged_list(source):
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail="A merged shopping list cannot be used as a merge source",
                )
            source_names.append((source.name or "").strip() or str(source.id))

        merged_name = (data.name or "").strip() or f"Merged: {' + '.join(source_names)}"
        merged_list = self.create_one_list(
            ShoppingListCreate(
                name=merged_name,
                extras={
                    self.MERGED_LIST_EXTRA_KEY: "true",
                    self.MERGED_SOURCE_IDS_EXTRA_KEY: json.dumps(
                        [str(source_id) for source_id in data.source_list_ids]
                    ),
                    self.MERGED_SOURCE_NAMES_EXTRA_KEY: json.dumps(source_names, ensure_ascii=False),
                },
            ),
            owner_id,
        )

        def copied_items() -> Iterator[ShoppingListItemCreate]:
            for source_id in data.source_list_ids:
                source = self.shopping_lists.get_one(source_id)
                if source is None:
                    raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Shopping list not found")

                for item in source.list_items:
                    # A merged list is a fresh checklist; source checked states remain untouched.
                    yield ShoppingListItemCreate(
                        shopping_list_id=merged_list.id,
                        checked=False,
                        position=item.position,
                        quantity=item.quantity,
                        food_id=item.food_id,
                        label_id=item.label_id,
                        unit_id=item.unit_id,
                        note=item.note,
                        recommended_variety=item.recommended_variety,
                        display=item.display if not (item.food_id or item.unit_id or item.note) else "",
                        extras=dict(item.extras or {}),
                        recipe_references=[
                            ShoppingListItemRecipeRefCreate(
                                recipe_id=reference.recipe_id,
                                recipe_quantity=reference.recipe_quantity,
                                recipe_scale=reference.recipe_scale,
                                recipe_note=reference.recipe_note,
                            )
                            for reference in item.recipe_references
                        ],
                    )

        item_changes = self.bulk_create_items(copied_items(), auto_find_labels=False)
        return cast(ShoppingListOut, self.shopping_lists.get_one(merged_list.id)), item_changes

    def get_shopping_list_items_from_recipe(
        self,
        list_id: UUID4,
        recipe_id: UUID4,
        scale: float = 1,
        recipe_ingredients: list[RecipeIngredient] | None = None,
    ) -> list[ShoppingListItemCreate]:
        """Generates a list of new list items based on a recipe"""

        if recipe_ingredients is None:
            group_recipes_repo = get_repositories(
                self.repos.session, group_id=self.repos.group_id, household_id=None
            ).recipes
            recipe = group_recipes_repo.get_one(recipe_id, "id")
            if not recipe:
                raise UnexpectedNone("Recipe not found")

            recipe_ingredients = recipe.recipe_ingredient

        list_items: list[ShoppingListItemCreate] = []
        for ingredient in recipe_ingredients:
            if isinstance(ingredient.referenced_recipe, Recipe):
                # Recursively process sub-recipe ingredients
                sub_recipe = ingredient.referenced_recipe
                sub_scale = (ingredient.quantity or 1) * scale
                sub_items = self.get_shopping_list_items_from_recipe(
                    list_id,
                    sub_recipe.id,
                    sub_scale,
                    sub_recipe.recipe_ingredient,
                )
                list_items.extend(sub_items)
                continue

            if isinstance(ingredient.food, IngredientFood):
                food_id = ingredient.food.id
                label_id = ingredient.food.label_id
            else:
                food_id = None
                label_id = None

            if isinstance(ingredient.unit, IngredientUnit):
                unit_id = ingredient.unit.id

            else:
                unit_id = None

            new_item = ShoppingListItemCreate(
                shopping_list_id=list_id,
                note=ingredient.note,
                quantity=ingredient.quantity * scale if ingredient.quantity else 0,
                food_id=food_id,
                label_id=label_id,
                unit_id=unit_id,
                recipe_references=[
                    ShoppingListItemRecipeRefCreate(
                        recipe_id=recipe_id,
                        recipe_quantity=ingredient.quantity,
                        recipe_scale=scale,
                        recipe_note=ingredient.note or None,
                    )
                ],
            )

            # some recipes have the same ingredient multiple times, so we check to see if we can combine them
            merged = False
            for existing_item in list_items:
                if not self.can_merge(existing_item, new_item):
                    continue

                # since this is the same recipe, we combine the quanities, rather than the scales
                # all items will have exactly one recipe reference
                if ingredient.quantity:
                    existing_item.quantity += ingredient.quantity
                    existing_item.recipe_references[0].recipe_quantity += ingredient.quantity  # type: ignore

                # merge notes
                if new_item.note and existing_item.note != new_item.note:
                    notes: set[str] = set(existing_item.note.split(" | ")) if existing_item.note else set()
                    notes.add(new_item.note)
                    existing_item.note = " | ".join([note for note in notes if note])

                merged = True
                break

            if not merged:
                list_items.append(new_item)

        return list_items

    def add_recipe_ingredients_to_list(
        self,
        list_id: UUID4,
        recipe_items: list[ShoppingListAddRecipeParamsBulk],
    ) -> tuple[ShoppingListOut, ShoppingListItemsCollectionOut]:
        """
        Adds recipe ingredients to a list

        Returns a tuple of:
        - Updated Shopping List
        - Impacted Shopping List Items
        """

        items_to_create = [
            item
            for recipe in recipe_items
            for item in self.get_shopping_list_items_from_recipe(
                list_id, recipe.recipe_id, recipe.recipe_increment_quantity, recipe.recipe_ingredients
            )
        ]
        item_changes = self.bulk_create_items(items_to_create)
        updated_list = cast(ShoppingListOut, self.shopping_lists.get_one(list_id))

        # update list-level recipe references
        for recipe in recipe_items:
            ref_merged = False
            for ref in updated_list.recipe_references:
                if ref.recipe_id != recipe.recipe_id:
                    continue

                ref.recipe_quantity += recipe.recipe_increment_quantity
                ref_merged = True
                break

            if not ref_merged:
                updated_list.recipe_references.append(
                    ShoppingListItemRecipeRefCreate(
                        recipe_id=recipe.recipe_id, recipe_quantity=recipe.recipe_increment_quantity
                    )
                )

        updated_list = self.shopping_lists.update(updated_list.id, updated_list)
        return updated_list, item_changes

    def remove_recipe_ingredients_from_list(
        self, list_id: UUID4, recipe_id: UUID4, recipe_decrement: float = 1
    ) -> tuple[ShoppingListOut, ShoppingListItemsCollectionOut]:
        """
        Removes a recipe's ingredients from a list

        Returns a tuple of:
        - Updated Shopping List
        - Impacted Shopping List Items
        """

        shopping_list = self.shopping_lists.get_one(list_id)
        if shopping_list is None:
            raise UnexpectedNone("Shopping list not found, cannot remove recipe ingredients")

        update_items: list[ShoppingListItemUpdateBulk] = []
        delete_items: list[UUID4] = []
        for item in shopping_list.list_items:
            found = False

            refs = cast(list[ShoppingListItemRecipeRefOut], item.recipe_references)
            for ref in refs:
                if ref.recipe_id != recipe_id:
                    continue

                # if the scale is missing we assume it's 1 for backwards compatibility
                # if the scale is 0 we leave it alone
                if ref.recipe_scale is None:
                    ref.recipe_scale = 1

                # Set Quantity
                if ref.recipe_scale > recipe_decrement:
                    # remove only part of the reference
                    item.quantity -= recipe_decrement * ref.recipe_quantity

                else:
                    # remove everything that's left on the reference
                    item.quantity -= ref.recipe_scale * ref.recipe_quantity

                # Set Reference Scale
                ref.recipe_scale -= recipe_decrement
                if ref.recipe_scale <= 0:
                    item.recipe_references.remove(ref)

                found = True
                break

            if found:
                # only remove a 0 quantity item if we removed its last recipe reference
                if item.quantity < 0 or (item.quantity == 0 and not item.recipe_references):
                    delete_items.append(item.id)

                else:
                    update_items.append(item.cast(ShoppingListItemUpdateBulk))

        response_update = self.bulk_update_items(update_items)

        deleted_item_ids = [item.id for item in response_update.deleted_items]
        response_delete = self.bulk_delete_items([id for id in delete_items if id not in deleted_item_ids])

        items = ShoppingListItemsCollectionOut(
            created_items=response_update.created_items + response_delete.created_items,
            updated_items=response_update.updated_items + response_delete.updated_items,
            deleted_items=response_update.deleted_items + response_delete.deleted_items,
        )

        # Decrement the list recipe reference count
        updated_list = self.shopping_lists.get_one(shopping_list.id)
        for recipe_ref in updated_list.recipe_references:  # type: ignore
            if recipe_ref.recipe_id != recipe_id or recipe_ref.recipe_quantity is None:
                continue

            recipe_ref.recipe_quantity -= recipe_decrement

            if recipe_ref.recipe_quantity <= 0.0:
                self.list_refs.delete(recipe_ref.id)

            else:
                self.list_refs.update(recipe_ref.id, recipe_ref)

            break

        return self.shopping_lists.get_one(shopping_list.id), items  # type: ignore

    def create_one_list(self, data: ShoppingListCreate, owner_id: UUID4):
        data = data.model_copy(update={"name": self.validated_unique_list_name(data.name)})
        create_data = data.cast(ShoppingListSave, group_id=self.repos.group_id, user_id=owner_id)
        new_list = self.shopping_lists.create(create_data)  # type: ignore

        labels = self.repos.group_multi_purpose_labels.page_all(
            PaginationQuery(page=1, per_page=-1, order_by="name", order_direction=OrderDirection.asc)
        )
        label_settings = [
            ShoppingListMultiPurposeLabelCreate(shopping_list_id=new_list.id, label_id=label.id, position=i)
            for i, label in enumerate(labels.items)
        ]

        self.repos.shopping_list_multi_purpose_labels.create_many(label_settings)
        return self.shopping_lists.get_one(new_list.id)
