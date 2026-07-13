import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import mealie.services.recipe.recipe_service as recipe_service_module
from mealie.schema.openai.recipe_search import OpenAIRecipeSearchItem, OpenAIRecipeSearchResponse
from mealie.services.recipe.recipe_service import OpenAIRecipeService


def test_ai_recipe_target_language_instruction_uses_the_locale_name_and_is_mandatory():
    instruction = OpenAIRecipeService._target_language_instruction("he_IL")

    assert "Hebrew" in instruction
    assert "he-IL" in instruction
    assert "mandatory" in instruction
    assert "every user-facing recipe value" in instruction


def test_ai_recipe_target_language_instruction_is_empty_without_a_requested_language():
    assert OpenAIRecipeService._target_language_instruction(None) == ""


@pytest.mark.asyncio
async def test_ai_collection_checks_every_recipe_in_bounded_batches(monkeypatch):
    service = object.__new__(OpenAIRecipeService)
    service.repos = MagicMock()
    service._AI_COLLECTION_BATCH_SIZE = 2
    service._search_vector = MagicMock(return_value={})
    service._score_ai_search_index = MagicMock(return_value=1.0)
    service._ensure_ai_recipe_search_index = MagicMock(
        return_value=[
            SimpleNamespace(recipe_name=f"Recipe {index}", catalog_json=json.dumps({"slug": f"recipe-{index}"}))
            for index in range(5)
        ]
    )
    responses = [
        OpenAIRecipeSearchResponse(results=[OpenAIRecipeSearchItem(slug="recipe-0", score=90)]),
        OpenAIRecipeSearchResponse(results=[OpenAIRecipeSearchItem(slug="recipe-3", score=85)]),
        OpenAIRecipeSearchResponse(results=[OpenAIRecipeSearchItem(slug="recipe-4", score=80)]),
    ]
    get_response = AsyncMock(side_effect=responses)

    class FakeOpenAIService:
        def __init__(self, _repos):
            self.provider_settings = SimpleNamespace(ai_enabled=True)
            self.get_response = get_response

        def get_prompt(self, _name):
            return "Select matching recipes."

    monkeypatch.setattr(recipe_service_module, "OpenAIService", FakeOpenAIService)

    selected = await service.select_recipe_slugs_for_ai_collection("Italian dinner")

    assert selected == ["recipe-0", "recipe-3", "recipe-4"]
    assert get_response.await_count == 3


@pytest.mark.asyncio
async def test_ai_collection_rejects_slugs_outside_the_current_batch(monkeypatch):
    service = object.__new__(OpenAIRecipeService)
    service.repos = MagicMock()
    service._AI_COLLECTION_BATCH_SIZE = 10
    service._search_vector = MagicMock(return_value={})
    service._score_ai_search_index = MagicMock(return_value=1.0)
    service._ensure_ai_recipe_search_index = MagicMock(
        return_value=[SimpleNamespace(recipe_name="Known", catalog_json=json.dumps({"slug": "known"}))]
    )

    class FakeOpenAIService:
        def __init__(self, _repos):
            self.provider_settings = SimpleNamespace(ai_enabled=True)

        def get_prompt(self, _name):
            return "Select matching recipes."

        async def get_response(self, *_args, **_kwargs):
            return OpenAIRecipeSearchResponse(
                results=[OpenAIRecipeSearchItem(slug="invented", score=100)]
            )

    monkeypatch.setattr(recipe_service_module, "OpenAIService", FakeOpenAIService)

    assert await service.select_recipe_slugs_for_ai_collection("Dinner") == []
