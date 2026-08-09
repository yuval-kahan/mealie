from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from mealie.services.recipe.recipe_service import OpenAIRecipeService, RecipeService
from tests.utils.factories import random_string
from tests.utils.fixture_schemas import TestUser


def test_standard_recipe_merge_creates_recipe_and_shopping_list(
    api_client: TestClient,
    unique_user: TestUser,
    monkeypatch: MonkeyPatch,
) -> None:
    async def skip_image_lookup(*_args, **_kwargs) -> bool:
        return False

    monkeypatch.setattr(RecipeService, "attach_best_effort_image", skip_image_lookup)

    source_slugs: list[str] = []
    for suffix in ("A", "B"):
        response = api_client.post(
            "/api/recipes",
            json={"name": f"{random_string()} {suffix}"},
            headers=unique_user.token,
        )
        assert response.status_code == 201
        source_slugs.append(response.json())

    response = api_client.post(
        "/api/recipes/merge",
        json={
            "sourceSlugs": source_slugs,
            "keepOriginals": True,
            "useAi": False,
        },
        headers=unique_user.token,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["recipe"]["isMergedRecipe"] is True
    assert body["recipe"]["slug"] not in source_slugs
    assert body["sourceCount"] == 2
    assert body["archivedSourceCount"] == 0
    assert body["shoppingListCreated"] is True
    assert body["shoppingListId"]

    merged_response = api_client.get(
        f"/api/recipes/{body['recipe']['slug']}",
        headers=unique_user.token,
    )
    assert merged_response.status_code == 200
    assert merged_response.json()["isMergedRecipe"] is True


def test_ai_recipe_merge_can_choose_name_and_create_shopping_list(
    api_client: TestClient,
    unique_user: TestUser,
    monkeypatch: MonkeyPatch,
) -> None:
    async def skip_image_lookup(*_args, **_kwargs) -> bool:
        return False

    async def build_merged_recipe(_self, recipes, _requested_name=None):
        return recipes[0].model_copy(deep=True, update={"name": "AI merged recipe"})

    monkeypatch.setattr(RecipeService, "attach_best_effort_image", skip_image_lookup)
    monkeypatch.setattr(OpenAIRecipeService, "build_merged_recipe", build_merged_recipe)

    source_slugs: list[str] = []
    for suffix in ("A", "B"):
        response = api_client.post(
            "/api/recipes",
            json={"name": f"{random_string()} {suffix}"},
            headers=unique_user.token,
        )
        assert response.status_code == 201
        source_slugs.append(response.json())

    response = api_client.post(
        "/api/recipes/merge",
        json={
            "sourceSlugs": source_slugs,
            "keepOriginals": True,
            "useAi": True,
        },
        headers=unique_user.token,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["recipe"]["name"] == "AI merged recipe"
    assert body["recipe"]["isMergedRecipe"] is True
    assert body["shoppingListCreated"] is True
    assert body["shoppingListId"]
