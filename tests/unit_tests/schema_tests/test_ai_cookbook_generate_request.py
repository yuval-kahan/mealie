import pytest
from mealie.schema.cookbook.uploaded_book import AICookbookGenerateRequest
from pydantic import ValidationError


def test_ai_cookbook_request_accepts_one_definition_mode():
    preset = AICookbookGenerateRequest(mode="preset", preset="Italian food")
    prompt = AICookbookGenerateRequest(mode="prompt", prompt="Weeknight dinners")

    assert preset.preset == "Italian food"
    assert prompt.prompt == "Weeknight dinners"


@pytest.mark.parametrize(
    "payload",
    [
        {"mode": "preset", "preset": "Italian", "prompt": "Dinner"},
        {"mode": "prompt", "prompt": "Dinner", "preset": "Italian"},
        {"mode": "preset", "preset": ""},
        {"mode": "prompt", "prompt": ""},
    ],
)
def test_ai_cookbook_request_rejects_missing_or_mixed_definitions(payload):
    with pytest.raises(ValidationError):
        AICookbookGenerateRequest.model_validate(payload)
