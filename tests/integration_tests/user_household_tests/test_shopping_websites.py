from fastapi.testclient import TestClient

from tests.utils.fixture_schemas import TestUser

ROUTE = "/api/households/shopping-websites"


def test_shopping_website_crud_and_search(api_client: TestClient, unique_user: TestUser):
    create_payload = {
        "name": "Example Food Shop",
        "url": "https://EXAMPLE.com/food#menu",
        "pageFood": "Fresh pasta",
        "offeredFoods": ["Pasta", "Sauces", "Pasta"],
    }

    response = api_client.post(ROUTE, json=create_payload, headers=unique_user.token)
    assert response.status_code == 201
    website = response.json()
    website_id = website["id"]
    assert website["url"] == "https://example.com/food"
    assert website["offeredFoods"] == ["Pasta", "Sauces"]

    response = api_client.get(ROUTE, params={"search": "fresh pasta"}, headers=unique_user.token)
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [website_id]

    update_payload = {
        "name": "Updated Food Shop",
        "url": "https://example.com/food",
        "pageFood": "Filled pasta",
        "offeredFoods": ["Pasta", "Cheese"],
    }
    response = api_client.put(f"{ROUTE}/{website_id}", json=update_payload, headers=unique_user.token)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Food Shop"

    response = api_client.delete(f"{ROUTE}/{website_id}", headers=unique_user.token)
    assert response.status_code == 204
    response = api_client.get(f"{ROUTE}/{website_id}", headers=unique_user.token)
    assert response.status_code == 404
