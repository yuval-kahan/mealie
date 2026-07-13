from types import SimpleNamespace
from unittest.mock import MagicMock

import mealie.routes.recipe.recipe_crud_routes as recipe_crud_module
import pytest
from fastapi import HTTPException
from mealie.schema.openai.recipe import (
    OpenAIRecipeIngredientAdjustment,
    OpenAIRecipeIngredientAdjustmentItem,
    OpenAIRecipeIngredientScale,
)
from mealie.schema.recipe.recipe_ingredient import RecipeIngredient


def ingredient(quantity: float, name: str, unit: str):
    return SimpleNamespace(
        quantity=quantity,
        title=None,
        food=SimpleNamespace(name=name),
        display="",
        note="",
        unit=SimpleNamespace(name=unit),
    )


def controller_with_recipe(recipe):
    controller = object.__new__(recipe_crud_module.RecipeController)
    controller.__dict__["service"] = SimpleNamespace(get_one=lambda _slug: recipe)
    controller._repos = MagicMock()
    controller._ai_enabled = lambda: True
    return controller


@pytest.mark.asyncio
async def test_ai_ingredient_quantity_scales_everything_from_validated_ratio(monkeypatch):
    response = OpenAIRecipeIngredientScale(
        matched=True,
        ingredient_index=0,
        target_quantity_in_recipe_unit=250,
        interpreted_ingredient="קמח",
    )

    class FakeOpenAIService:
        def __init__(self, _repos) -> None:
            pass

        @staticmethod
        def get_prompt(_name: str) -> str:
            return "prompt"

        async def get_response(self, *_args, **_kwargs):
            return response

    monkeypatch.setattr(recipe_crud_module, "OpenAIService", FakeOpenAIService)
    controller = controller_with_recipe(
        SimpleNamespace(recipe_ingredient=[ingredient(500, "קמח", "גרם"), ingredient(5, "ביצים", "")])
    )

    result = await controller.scale_recipe_from_ingredient_text(
        "bread",
        recipe_crud_module.RecipeIngredientScaleFromTextRequest(text="יש לי 250 גרם קמח"),
    )

    assert result.ingredient_index == 0
    assert result.original_quantity == 500
    assert result.target_quantity == 250
    assert result.scale == 0.5
    assert result.ingredient_name == "קמח"


@pytest.mark.asyncio
async def test_ai_ingredient_quantity_rejects_ambiguous_request(monkeypatch):
    response = OpenAIRecipeIngredientScale(
        matched=False,
        reason="No quantity was supplied",
    )

    class FakeOpenAIService:
        def __init__(self, _repos) -> None:
            pass

        @staticmethod
        def get_prompt(_name: str) -> str:
            return "prompt"

        async def get_response(self, *_args, **_kwargs):
            return response

    monkeypatch.setattr(recipe_crud_module, "OpenAIService", FakeOpenAIService)
    controller = controller_with_recipe(SimpleNamespace(recipe_ingredient=[ingredient(500, "flour", "g")]))

    with pytest.raises(HTTPException) as exc_info:
        await controller.scale_recipe_from_ingredient_text(
            "bread",
            recipe_crud_module.RecipeIngredientScaleFromTextRequest(text="change the flour"),
        )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_ai_ingredient_adjustment_rebuilds_the_complete_ordered_list(monkeypatch):
    response = OpenAIRecipeIngredientAdjustment(
        adjusted=True,
        reason="Scaled to half the flour.",
        ingredients=[
            OpenAIRecipeIngredientAdjustmentItem(
                ingredient_index=0,
                quantity=250,
                unit="g",
                food="flour",
                original_text="250 g flour",
            ),
            OpenAIRecipeIngredientAdjustmentItem(
                ingredient_index=1,
                quantity=2.5,
                food="eggs",
                original_text="2.5 eggs",
            ),
        ],
    )

    class FakeOpenAIService:
        def __init__(self, _repos) -> None:
            pass

        @staticmethod
        def get_prompt(_name: str) -> str:
            return "prompt"

        async def get_response(self, *_args, **_kwargs):
            return response

    monkeypatch.setattr(recipe_crud_module, "OpenAIService", FakeOpenAIService)
    original_ingredients = [
        RecipeIngredient(quantity=500, unit="g", food="flour", original_text="500 g flour"),
        RecipeIngredient(quantity=5, food="eggs", original_text="5 eggs"),
    ]
    controller = controller_with_recipe(SimpleNamespace(recipe_ingredient=original_ingredients))

    result = await controller.adjust_recipe_ingredients_with_ai(
        "bread",
        recipe_crud_module.RecipeIngredientsAdjustWithAIRequest(text="I have only 250 g flour"),
    )

    assert result.adjustment_note == "Scaled to half the flour."
    assert [ingredient.quantity for ingredient in result.ingredients] == [250, 2.5]
    assert [ingredient.food.name for ingredient in result.ingredients] == ["flour", "eggs"]
    assert [ingredient.reference_id for ingredient in result.ingredients] == [
        ingredient.reference_id for ingredient in original_ingredients
    ]


@pytest.mark.asyncio
async def test_ai_ingredient_adjustment_rejects_a_partial_replacement(monkeypatch):
    response = OpenAIRecipeIngredientAdjustment(
        adjusted=True,
        ingredients=[
            OpenAIRecipeIngredientAdjustmentItem(
                ingredient_index=0,
                quantity=250,
                unit="g",
                food="flour",
            ),
        ],
    )

    class FakeOpenAIService:
        def __init__(self, _repos) -> None:
            pass

        @staticmethod
        def get_prompt(_name: str) -> str:
            return "prompt"

        async def get_response(self, *_args, **_kwargs):
            return response

    monkeypatch.setattr(recipe_crud_module, "OpenAIService", FakeOpenAIService)
    controller = controller_with_recipe(
        SimpleNamespace(
            recipe_ingredient=[
                RecipeIngredient(quantity=500, unit="g", food="flour"),
                RecipeIngredient(quantity=5, food="eggs"),
            ]
        )
    )

    with pytest.raises(HTTPException) as exc_info:
        await controller.adjust_recipe_ingredients_with_ai(
            "bread",
            recipe_crud_module.RecipeIngredientsAdjustWithAIRequest(text="I have 250 g flour"),
        )

    assert exc_info.value.status_code == 400
