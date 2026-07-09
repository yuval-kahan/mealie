from unittest.mock import MagicMock

import pytest
from PIL import Image

import mealie.services.item_image_service as item_image_module
from mealie.services.item_image_service import ItemImageService


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
