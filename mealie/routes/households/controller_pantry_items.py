import re

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import UUID4
from sqlalchemy.orm import selectinload

from mealie.db.models.household.pantry_item import PantryItem, PantrySearchHistory
from mealie.db.models.recipe.ingredient import RecipeIngredientModel
from mealie.db.models.recipe.recipe import RecipeModel
from mealie.routes._base import controller
from mealie.routes._base.base_controllers import BaseUserController
from mealie.schema.household.pantry_item import (
    PantryItemCreate,
    PantryItemOut,
    PantryItemUpdate,
    PantryRecipeSuggestion,
    PantryRecipeSuggestionRequest,
    PantryRecipeSuggestionResponse,
    PantrySearchHistoryList,
    PantrySearchHistoryOut,
)
from mealie.schema.recipe.recipe import RecipeSummary
from mealie.services.recipe.recipe_service import RecipeService

router = APIRouter(prefix="/households/pantry-items", tags=["Households: Pantry Items"])

SPACE_RE = re.compile(r"\s+")
SPLIT_RE = re.compile(r"[,;\n]+")
MAX_RECIPE_CANDIDATES = 500
MAX_HISTORY_ITEMS = 200


def compact_text(value: str | None, limit: int) -> str:
    return SPACE_RE.sub(" ", (value or "").strip())[:limit]


@controller(router)
class PantryItemsController(BaseUserController):
    def _to_out(self, item: PantryItem) -> PantryItemOut:
        return PantryItemOut.model_validate(item)

    def _get_or_404(self, item_id: UUID4) -> PantryItem:
        item = self.session.execute(
            sa.select(PantryItem).where(PantryItem.id == item_id, PantryItem.group_id == self.group_id)
        ).scalar_one_or_none()
        if item is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        return item

    def _apply(self, item: PantryItem, data: PantryItemCreate | PantryItemUpdate) -> None:
        item.name = compact_text(data.name, 255)
        item.quantity = data.quantity
        item.unit = compact_text(data.unit, 120) or None
        item.category = compact_text(data.category, 160) or None
        item.note = compact_text(data.note, 1000) or None

    def _available_items(self, available_text: str | None) -> list[str]:
        stored = list(
            self.session.execute(
                sa.select(PantryItem.name)
                .where(PantryItem.group_id == self.group_id)
                .order_by(PantryItem.name)
            ).scalars()
        )
        supplied = [compact_text(value, 255) for value in SPLIT_RE.split(available_text or "")]
        seen: set[str] = set()
        result: list[str] = []
        for value in [*stored, *supplied]:
            key = value.casefold()
            if value and key not in seen:
                seen.add(key)
                result.append(value)
        return result[:500]

    @staticmethod
    def _ingredient_text(ingredient: RecipeIngredientModel) -> str:
        parts = [
            ingredient.original_text,
            ingredient.note,
            ingredient.recommended_variety,
            ingredient.food.name if ingredient.food else None,
        ]
        return compact_text(" ".join(part for part in parts if part), 1000)

    async def _ai_suggestions(
        self,
        available_items: list[str],
        data: PantryRecipeSuggestionRequest,
    ) -> PantryRecipeSuggestionResponse:
        available_description = ", ".join(available_items)
        extra_request = compact_text(data.available_text, 4000)
        query = (
            "Find recipes I can prepare primarily with these available foods: "
            f"{available_description}. Prefer recipes with the fewest missing ingredients."
        )
        if extra_request:
            query += f" Additional request: {extra_request}"
        if data.target_language:
            query += (
                f" Return every explanation, reason, matched item, and missing ingredient in "
                f"{compact_text(data.target_language, 80)}."
            )
        result = await RecipeService(
            self.repos,
            self.user,
            self.household,
            self.translator,
        ).search_with_ai(query, data.limit)
        return PantryRecipeSuggestionResponse(
            items=[
                PantryRecipeSuggestion(
                    recipe=item.recipe,
                    reason=item.reason,
                    score=item.score or 0,
                )
                for item in result.items
            ],
            available_items=available_items,
            recipe_count=result.recipe_count,
        )

    def _normal_suggestions(
        self,
        available_items: list[str],
        data: PantryRecipeSuggestionRequest,
    ) -> PantryRecipeSuggestionResponse:
        normalized_available = [(name, name.casefold()) for name in available_items]
        recipes = (
            self.session.execute(
                sa.select(RecipeModel)
                .where(RecipeModel.group_id == self.group_id)
                .options(
                    *RecipeSummary.loader_options(),
                    selectinload(RecipeModel.recipe_ingredient).joinedload(RecipeIngredientModel.food),
                )
                .order_by(RecipeModel.updated_at.desc())
                .limit(MAX_RECIPE_CANDIDATES)
            )
            .scalars()
            .unique()
            .all()
        )
        ranked: list[tuple[int, str, PantryRecipeSuggestion]] = []
        for recipe in recipes:
            ingredient_names = [
                text
                for ingredient in recipe.recipe_ingredient
                if (text := self._ingredient_text(ingredient))
            ]
            if not ingredient_names:
                continue
            matched: list[str] = []
            missing: list[str] = []
            for ingredient_name in ingredient_names:
                ingredient_key = ingredient_name.casefold()
                match = next(
                    (
                        available_name
                        for available_name, available_key in normalized_available
                        if available_key in ingredient_key or ingredient_key in available_key
                    ),
                    None,
                )
                if match:
                    matched.append(match)
                else:
                    missing.append(ingredient_name)
            matched = list(dict.fromkeys(matched))
            if not matched:
                continue
            score = min(100, round((len(ingredient_names) - len(missing)) / len(ingredient_names) * 100))
            suggestion = PantryRecipeSuggestion(
                recipe=RecipeSummary.model_validate(recipe),
                matched_items=matched,
                missing_ingredients=missing[:12],
                score=score,
            )
            ranked.append((score, recipe.name or "", suggestion))
        ranked.sort(key=lambda row: (-row[0], len(row[2].missing_ingredients), row[1].casefold()))
        return PantryRecipeSuggestionResponse(
            items=[row[2] for row in ranked[: data.limit]],
            available_items=available_items,
            recipe_count=len(recipes),
        )

    def _history_to_out(self, history: PantrySearchHistory) -> PantrySearchHistoryOut | None:
        try:
            response = PantryRecipeSuggestionResponse.model_validate_json(history.response_json)
        except (TypeError, ValueError):
            return None
        return PantrySearchHistoryOut(
            id=history.id,
            query=history.query,
            use_ai=history.use_ai,
            target_language=history.target_language,
            response=response,
            created_at=history.created_at,
        )

    def _save_history(
        self,
        data: PantryRecipeSuggestionRequest,
        available_items: list[str],
        response: PantryRecipeSuggestionResponse,
    ) -> None:
        label = compact_text(data.available_text, 8000) or ", ".join(available_items)
        latest = self.session.execute(
            sa.select(PantrySearchHistory)
            .where(
                PantrySearchHistory.group_id == self.group_id,
                PantrySearchHistory.user_id == self.user.id,
            )
            .order_by(PantrySearchHistory.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        serialized = response.model_dump_json(by_alias=True)
        if (
            latest
            and latest.query == label
            and latest.use_ai == data.use_ai
            and latest.target_language == data.target_language
        ):
            latest.response_json = serialized
            self.session.add(latest)
        else:
            self.session.add(
                PantrySearchHistory(
                    group_id=self.group_id,
                    household_id=self.household_id,
                    user_id=self.user.id,
                    query=label,
                    use_ai=data.use_ai,
                    target_language=compact_text(data.target_language, 80) or None,
                    response_json=serialized,
                    session=self.session,
                )
            )
        self.session.flush()

        stale_ids = list(
            self.session.execute(
                sa.select(PantrySearchHistory.id)
                .where(
                    PantrySearchHistory.group_id == self.group_id,
                    PantrySearchHistory.user_id == self.user.id,
                )
                .order_by(PantrySearchHistory.created_at.desc())
                .offset(MAX_HISTORY_ITEMS)
            ).scalars()
        )
        if stale_ids:
            self.session.execute(sa.delete(PantrySearchHistory).where(PantrySearchHistory.id.in_(stale_ids)))
        self.session.commit()

    @router.get("", response_model=list[PantryItemOut])
    def get_all(self, search: str | None = Query(None)) -> list[PantryItemOut]:
        query = compact_text(search, 255).casefold()
        statement = sa.select(PantryItem).where(PantryItem.group_id == self.group_id)
        if query:
            statement = statement.where(
                sa.or_(
                    sa.func.lower(PantryItem.name).contains(query),
                    sa.func.lower(sa.func.coalesce(PantryItem.category, "")).contains(query),
                    sa.func.lower(sa.func.coalesce(PantryItem.note, "")).contains(query),
                )
            )
        items = self.session.execute(statement.order_by(PantryItem.category, PantryItem.name)).scalars().all()
        return [self._to_out(item) for item in items]

    @router.post("", response_model=PantryItemOut, status_code=status.HTTP_201_CREATED)
    def create_one(self, data: PantryItemCreate) -> PantryItemOut:
        normalized_name = compact_text(data.name, 255)
        item = self.session.execute(
            sa.select(PantryItem).where(
                PantryItem.group_id == self.group_id,
                sa.func.lower(PantryItem.name) == normalized_name.casefold(),
            )
        ).scalar_one_or_none()
        if item is None:
            item = PantryItem(
                group_id=self.group_id,
                household_id=self.household_id,
                user_id=self.user.id,
                name=normalized_name,
                session=self.session,
            )
        self._apply(item, data)
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return self._to_out(item)

    @router.put("/{item_id}", response_model=PantryItemOut)
    def update_one(self, item_id: UUID4, data: PantryItemUpdate) -> PantryItemOut:
        item = self._get_or_404(item_id)
        self._apply(item, data)
        self.session.commit()
        self.session.refresh(item)
        return self._to_out(item)

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_one(self, item_id: UUID4) -> None:
        item = self._get_or_404(item_id)
        self.session.delete(item)
        self.session.commit()

    @router.get("/search-history", response_model=PantrySearchHistoryList)
    def get_search_history(
        self,
        search: str | None = Query(None),
        limit: int = Query(50, ge=1, le=200),
    ) -> PantrySearchHistoryList:
        statement = sa.select(PantrySearchHistory).where(
            PantrySearchHistory.group_id == self.group_id,
            PantrySearchHistory.user_id == self.user.id,
        )
        query = compact_text(search, 255)
        if query:
            statement = statement.where(PantrySearchHistory.query.ilike(f"%{query}%"))
        rows = self.session.execute(
            statement.order_by(PantrySearchHistory.created_at.desc()).limit(limit)
        ).scalars().all()
        items = [item for row in rows if (item := self._history_to_out(row)) is not None]
        total = self.session.execute(
            sa.select(sa.func.count(PantrySearchHistory.id)).where(
                PantrySearchHistory.group_id == self.group_id,
                PantrySearchHistory.user_id == self.user.id,
            )
        ).scalar_one()
        return PantrySearchHistoryList(items=items, total=total)

    @router.delete("/search-history/{history_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_search_history(self, history_id: UUID4) -> None:
        history = self.session.execute(
            sa.select(PantrySearchHistory).where(
                PantrySearchHistory.id == history_id,
                PantrySearchHistory.group_id == self.group_id,
                PantrySearchHistory.user_id == self.user.id,
            )
        ).scalar_one_or_none()
        if history is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        self.session.delete(history)
        self.session.commit()

    @router.post("/suggest-recipes", response_model=PantryRecipeSuggestionResponse)
    async def suggest_recipes(self, data: PantryRecipeSuggestionRequest) -> PantryRecipeSuggestionResponse:
        available_items = self._available_items(data.available_text)
        if not available_items:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Add at least one available food")
        if data.use_ai:
            try:
                response = await self._ai_suggestions(available_items, data)
            except HTTPException:
                raise
            except Exception as exc:
                self.logger.exception("Failed to suggest pantry recipes with AI")
                raise HTTPException(
                    status.HTTP_502_BAD_GATEWAY,
                    detail="The AI provider could not suggest recipes right now",
                ) from exc
        else:
            response = self._normal_suggestions(available_items, data)
        self._save_history(data, available_items, response)
        return response
