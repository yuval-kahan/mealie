import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import mealie.services.uploaded_books.ai_cookbook_builder as cookbook_builder_module
import pytest
from mealie.routes.households.controller_uploaded_books import UploadedBooksController
from mealie.schema.cookbook.uploaded_book import UploadedBookRecipeDeleteRequest
from mealie.schema.group.ai_providers import AIProviderOut
from mealie.schema.openai.general import OpenAICookbookChapter, OpenAICookbookPlan
from mealie.services.uploaded_books.ai_cookbook_builder import AICookbookBuilder
from mealie.services.uploaded_books.book_recipe_extractor import (
    BookTextPage,
    UploadedBookRecipeExtractor,
    UploadedBookTranslator,
    parse_book_source_page_range,
)


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


def test_translation_completeness_rejects_an_omitted_meaningful_page():
    source = "Mix 500 grams flour with 5 eggs. Knead for 10 minutes, rest for 30 minutes, then roll and cut."

    issue = UploadedBookTranslator._translation_page_issue(12, source, "")

    assert issue is not None
    assert "page 12" in issue


def test_book_recipe_source_page_range_supports_hebrew_and_english():
    assert parse_book_source_page_range("White Heat - Marco Pierre White, עמוד 182") == (182, 182)
    assert parse_book_source_page_range("White Heat, pages 12-15") == (12, 15)
    assert parse_book_source_page_range("White Heat", 21, 30) == (21, 30)


@pytest.mark.parametrize(
    ("is_translated", "extension", "expected_fragment"),
    [(True, ".html", "#page-182"), (False, ".pdf", "#page=182")],
)
def test_book_open_redirect_uses_the_correct_page_fragment(is_translated, extension, expected_fragment):
    controller = object.__new__(UploadedBooksController)
    book_id = uuid4()
    book = SimpleNamespace(id=book_id, is_translated_book=is_translated, extension=extension)
    controller._preferred_reading_book = lambda current_book, _page: current_book

    response = controller._book_open_redirect(book, 182)

    assert response.status_code == 307
    assert response.headers["location"] == f"/api/households/uploaded-books/{book_id}/file{expected_fragment}"


def test_book_recipe_bulk_delete_skips_recipe_ids_from_other_books():
    controller = object.__new__(UploadedBooksController)
    book = SimpleNamespace(extraction_recipes_created=1)
    linked_recipe = SimpleNamespace(id=uuid4(), slug="linked-recipe")
    foreign_recipe_id = uuid4()
    controller.session = MagicMock()
    controller._get_book_or_404 = lambda _book_id: book
    controller._assert_book_not_processing = lambda _book: None
    controller._book_recipe_models = lambda _book: [linked_recipe]

    response = controller.delete_extracted_book_recipes(
        uuid4(),
        UploadedBookRecipeDeleteRequest(recipe_ids=[foreign_recipe_id]),
    )

    assert response.deleted_count == 0
    assert response.remaining_count == 1
    assert response.skipped_count == 1
    assert response.deleted_recipe_ids == []


def test_translation_completeness_allows_empty_decorative_or_ocr_page():
    assert UploadedBookTranslator._translation_page_issue(2, "WHITE HEAT", "") is None


def test_translated_book_html_has_cover_contents_and_numbered_pages():
    translator = object.__new__(UploadedBookTranslator)
    book = SimpleNamespace(
        name="White Heat",
        original_file_name="White Heat.pdf",
        translation_page_start=None,
        translation_page_end=None,
    )

    output = translator._build_translated_book_html(
        book,
        "Hebrew",
        [(1, "פתיחה לספר והסבר קצר"), (2, "מתכון לדוגמה\n500 גרם קמח")],
        has_cover=True,
    )

    assert 'id="cover"' in output
    assert 'src="./cover"' in output
    assert 'id="contents"' in output
    assert 'href="#page-2"' in output
    assert 'id="page-2"' in output
    assert 'id="bookSidebar"' in output
    assert 'id="readingProgress"' in output
    assert 'data-page-index="2"' in output
    assert "IntersectionObserver" in output
    assert "תוכן עניינים" in output


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
