import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import mealie.services.uploaded_books.ai_cookbook_builder as cookbook_builder_module
import pytest
from mealie.schema.group.ai_providers import AIProviderOut
from mealie.schema.openai.general import OpenAICookbookChapter, OpenAICookbookPlan
from mealie.services.uploaded_books.ai_cookbook_builder import AICookbookBuilder
from mealie.services.uploaded_books.book_recipe_extractor import BookTextPage, UploadedBookRecipeExtractor


def test_gemini_provider_creates_one_worker_slot_per_unique_key():
    provider = AIProviderOut(
        id=uuid4(),
        name="Google Gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        api_key="\n".join(f"key-{index}" for index in range(1, 21)),
        model="gemini-3.1-flash-lite",
    )
    extractor = object.__new__(UploadedBookRecipeExtractor)

    slots = extractor._provider_slots(SimpleNamespace(default_provider=provider))

    assert len(slots) == 20
    assert [slot.label for slot in slots] == [f"Gemini key #{index}" for index in range(1, 21)]
    assert {slot.provider.api_key for slot in slots} == {f"key-{index}" for index in range(1, 21)}


def test_ai_cookbook_split_keeps_every_recipe_and_respects_volume_limits():
    builder = object.__new__(AICookbookBuilder)
    recipes = {
        f"recipe-{index}": SimpleNamespace(
            slug=f"recipe-{index}",
            recipe_ingredient=[SimpleNamespace() for _ in range(4)],
            recipe_instructions=[SimpleNamespace() for _ in range(2)],
        )
        for index in range(1, 6)
    }
    plan = OpenAICookbookPlan(
        title="Italian Dinner",
        introduction="A practical collection.",
        chapters=[
            OpenAICookbookChapter(title="Pasta", recipe_slugs=list(recipes)),
        ],
    )

    volumes = builder._split_volumes(plan, recipes, max_recipes=2, max_pages=300)

    assert [len(volume) for volume in volumes] == [2, 2, 1]
    assert [recipe.slug for volume in volumes for _, recipe in volume] == list(recipes)


def test_pdf_classification_sample_stops_reading_at_the_requested_page_limit(monkeypatch, tmp_path):
    extraction_counts = {"pages": 0}

    class FakePage:
        def __init__(self, number: int) -> None:
            self.number = number

        def extract_text(self) -> str:
            extraction_counts["pages"] += 1
            return f"Page {self.number}"

    class FakeReader:
        pages = [FakePage(index) for index in range(1, 101)]

    monkeypatch.setitem(sys.modules, "pypdf", SimpleNamespace(PdfReader=lambda _path: FakeReader()))
    extractor = object.__new__(UploadedBookRecipeExtractor)

    pages = extractor._extract_pdf_pages(tmp_path / "large.pdf", max_pages=40)

    assert len(pages) == 40
    assert extraction_counts["pages"] == 40
    assert pages[-1].number == 40


def test_extraction_chunks_include_forward_context_without_changing_primary_ranges():
    extractor = object.__new__(UploadedBookRecipeExtractor)
    pages = [BookTextPage(number=index, text=f"Page {index} text") for index in range(1, 6)]

    chunks = extractor._build_chunks(pages, pages_per_chunk=2, forward_overlap_pages=1)

    assert [(chunk.start_page, chunk.end_page) for chunk in chunks] == [(1, 2), (3, 4), (5, 5)]
    assert chunks[0].page_numbers == [1, 2]
    assert "[Page 3]" in chunks[0].text
    assert "[Page 4]" not in chunks[0].text
    assert "[Page 5]" in chunks[1].text


@pytest.mark.asyncio
async def test_ai_cookbook_planning_uses_bounded_batches(monkeypatch):
    recipes = [
        SimpleNamespace(
            slug=f"recipe-{index}",
            name=f"Recipe {index}",
            description="Description",
            recipe_category=[],
            tags=[],
        )
        for index in range(161)
    ]
    responses = [
        OpenAICookbookPlan(
            title="Large Cookbook",
            introduction="Introduction",
            chapters=[
                OpenAICookbookChapter(
                    title=f"Chapter {batch_index}",
                    recipe_slugs=[recipe.slug for recipe in recipes[start : start + 80]],
                )
            ],
        )
        for batch_index, start in enumerate(range(0, len(recipes), 80), start=1)
    ]
    get_response = AsyncMock(side_effect=responses)

    class FakeOpenAIService:
        def __init__(self, _repos) -> None:
            self.get_response = get_response

    monkeypatch.setattr(cookbook_builder_module, "OpenAIService", FakeOpenAIService)
    builder = object.__new__(AICookbookBuilder)
    builder.repos = MagicMock()
    builder.logger = MagicMock()

    plan = await builder._build_plan("Italian recipes", None, recipes)

    assert get_response.await_count == 3
    assert [slug for chapter in plan.chapters for slug in chapter.recipe_slugs] == [
        recipe.slug for recipe in recipes
    ]
