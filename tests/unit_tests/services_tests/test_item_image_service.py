from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from PIL import Image

import mealie.services.item_image_service as item_image_module
from mealie.schema.openai.general import OpenAIImageSearchQueries, OpenAIImageSearchQuery
from mealie.services.item_image_service import ItemImageRequest, ItemImageService


def _service_with_mock_minifier() -> ItemImageService:
    service = object.__new__(ItemImageService)
    service.minifier = MagicMock()
    return service


def test_validate_and_minify_accepts_bounded_image(tmp_path):
    image_path = tmp_path / "ingredient.png"
    Image.new("RGB", (32, 24), color="red").save(image_path)
    service = _service_with_mock_minifier()

    service._validate_and_minify(image_path)

    service.minifier.minify.assert_called_once_with(image_path)


def test_validate_and_minify_rejects_excessive_pixels(tmp_path, monkeypatch):
    image_path = tmp_path / "ingredient.png"
    Image.new("RGB", (3, 2), color="green").save(image_path)
    service = _service_with_mock_minifier()
    monkeypatch.setattr(item_image_module, "ITEM_IMAGE_MAX_PIXELS", 5)

    with pytest.raises(ValueError, match="pixel limit"):
        service._validate_and_minify(image_path)

    service.minifier.minify.assert_not_called()


def test_search_queries_remove_quantities_and_generalize_ai_phrase():
    service = object.__new__(ItemImageService)

    queries = service._search_queries(
        ItemImageRequest("tool", "3 מחבתות", "כלי בישול"),
        "set of three nonstick frying pans",
    )

    assert queries[0] == "nonstick frying pans"
    assert "מחבתות kitchen tool equipment photo" in queries
    assert all(not query.startswith("3 מחבתות") for query in queries)


@pytest.mark.asyncio
async def test_build_ai_search_queries_uses_structured_response(monkeypatch):
    service = object.__new__(ItemImageService)
    service.repos = MagicMock()
    service.logger = MagicMock()
    response = OpenAIImageSearchQueries(
        queries=[
            OpenAIImageSearchQuery(key="food:500 גרם קמח", query="white wheat flour ingredient"),
            OpenAIImageSearchQuery(key="unexpected", query="ignore me"),
        ]
    )
    get_response = AsyncMock(return_value=response)

    class FakeOpenAIService:
        def __init__(self, _repos):
            self.provider_settings = SimpleNamespace(ai_enabled=True)
            self.get_response = get_response

    monkeypatch.setattr(item_image_module, "OpenAIService", FakeOpenAIService)

    result = await service._build_ai_search_queries([ItemImageRequest("food", "500 גרם קמח")])

    assert result == {"food:500 גרם קמח": "white wheat flour ingredient"}
    get_response.assert_awaited_once()


@pytest.mark.asyncio
async def test_build_ai_search_queries_falls_back_when_ai_is_unavailable(monkeypatch):
    service = object.__new__(ItemImageService)
    service.repos = MagicMock()
    service.logger = MagicMock()

    class FakeOpenAIService:
        def __init__(self, _repos):
            self.provider_settings = SimpleNamespace(ai_enabled=True)

        async def get_response(self, *_args, **_kwargs):
            raise RuntimeError("provider unavailable")

    monkeypatch.setattr(item_image_module, "OpenAIService", FakeOpenAIService)

    result = await service._build_ai_search_queries([ItemImageRequest("food", "עגבניה")])

    assert result == {}
    service.logger.exception.assert_called_once()
