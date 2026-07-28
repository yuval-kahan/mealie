import sys
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from zipfile import ZipFile

import pytest
from fastapi import BackgroundTasks
from PIL import Image

import mealie.services.uploaded_books.ai_cookbook_builder as cookbook_builder_module
import mealie.services.uploaded_books.book_classifier as book_classifier_module
from mealie.routes.households.controller_uploaded_books import UploadedBooksController
from mealie.schema.cookbook.uploaded_book import UploadedBookRecipeDeleteRequest
from mealie.schema.group.ai_providers import AIProviderOut
from mealie.schema.openai.general import OpenAICookbookChapter, OpenAICookbookPlan
from mealie.schema.openai.recipe import (
    OpenAIBookRecipeCatalogMatch,
    OpenAIBookRecipeCatalogParse,
    OpenAIBookRecipeSearchHint,
    OpenAIBookRecipeSearchPlan,
    OpenAIRecipe,
)
from mealie.services.recipe.recipe_service import OpenAIRecipeService
from mealie.services.uploaded_books.ai_cookbook_builder import AICookbookBuilder
from mealie.services.uploaded_books.book_recipe_extractor import (
    BookTextChunk,
    BookTextPage,
    ChunkTranslationResult,
    ProviderSlot,
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


def test_recipe_catalog_reads_compact_table_of_contents_page_numbers():
    pages = [
        BookTextPage(
            number=4,
            text=(
                "CONTENTS\n"
                "Foreword vii\n"
                "The Heat of the Kitchen 13\n"
                "The Food of the Gods: Recipes for First Courses 21\n"
                "Fish dishes 57"
            ),
        )
    ]

    entries = UploadedBookRecipeExtractor._contents_catalog_entries(pages)

    assert [(entry["title"], entry["page_start"]) for entry in entries] == [
        ("Foreword", 7),
        ("The Heat of the Kitchen", 13),
        ("The Food of the Gods: Recipes for First Courses", 21),
        ("Fish dishes", 57),
    ]


def test_recipe_catalog_validates_ai_hints_against_local_full_text():
    pages = [
        BookTextPage(
            number=10,
            text="An essay about rice traditions and restaurant history.",
        ),
        BookTextPage(
            number=22,
            text=(
                "Wild Mushroom Risotto\n"
                "Ingredients\n"
                "300 g arborio rice\n"
                "Method\n"
                "Toast the rice and gradually add stock."
            ),
        ),
    ]
    plan = OpenAIBookRecipeSearchPlan(
        search_terms=["rice", "risotto", "אורז"],
        hints=[OpenAIBookRecipeSearchHint(title="Wild Mushroom Risotto")],
    )

    entries = UploadedBookRecipeExtractor._full_text_catalog_entries(pages, "אורז", plan)

    assert [(entry["title"], entry["page_start"]) for entry in entries] == [
        ("Wild Mushroom Risotto", 22),
    ]
    assert "arborio rice" in entries[0]["excerpt"]


@pytest.mark.asyncio
async def test_recipe_catalog_retries_a_failed_batch_with_another_provider(monkeypatch):
    bad_provider = SimpleNamespace(name="bad")
    good_provider = SimpleNamespace(name="good")

    class FakeOpenAIService:
        def __init__(self, _repos) -> None:
            pass

        @staticmethod
        def get_prompt(_name):
            return "prompt"

        @staticmethod
        async def get_response(_prompt, _message, *, provider, **_kwargs):
            if provider is bad_provider:
                raise ValueError("401 invalid API key")
            return OpenAIBookRecipeCatalogParse(
                matches=[
                    OpenAIBookRecipeCatalogMatch(
                        entry_index=0,
                        is_recipe=True,
                        matches_query=True,
                        display_title="ריזוטו פטריות",
                    )
                ]
            )

    monkeypatch.setattr(
        "mealie.services.uploaded_books.book_recipe_extractor.OpenAIService",
        FakeOpenAIService,
    )
    extractor = object.__new__(UploadedBookRecipeExtractor)
    extractor.repos = MagicMock()
    extractor._provider_slots = lambda _service: [
        ProviderSlot(provider=bad_provider, label="bad key"),
        ProviderSlot(provider=good_provider, label="good key"),
    ]

    matches, used_ai, warning = await extractor._classify_catalog_entries(
        SimpleNamespace(name="Test Cookbook"),
        [{"entry_index": 0, "title": "Mushroom Risotto", "page_start": 22}],
        "risotto",
        "Hebrew",
    )

    assert used_ai is True
    assert matches[0]["display_title"] == "ריזוטו פטריות"
    assert warning is not None
    assert "bad key" in warning


def test_ten_minute_tag_requires_an_explicit_source_claim():
    service = object.__new__(OpenAIRecipeService)
    inferred_recipe = OpenAIRecipe(
        name="חביתה מהירה",
        core_dish_name="חביתה",
        tags=["מתכון מהיר בעשר דקות"],
        explicit_ten_minute_claim=False,
    )
    explicit_recipe = inferred_recipe.model_copy(update={"explicit_ten_minute_claim": True})

    _, inferred_tags = service._enhanced_recipe_organizers(inferred_recipe)
    _, explicit_tags = service._enhanced_recipe_organizers(explicit_recipe)

    assert "10 דקות" not in inferred_tags
    assert "10 דקות" in explicit_tags


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


def test_partial_translation_audit_reports_gaps_without_rejecting_saved_pages():
    translator = object.__new__(UploadedBookTranslator)
    source_text = (
        "Mix 500 grams flour with 5 eggs. Knead for 10 minutes and rest for 30 minutes before rolling."
    )
    chunks = [
        BookTextChunk(
            index=0,
            start_page=1,
            end_page=2,
            page_numbers=[1, 2],
            text=f"[Page 1]\n{source_text}\n[Page 2]\n{source_text}",
        )
    ]

    audit = translator._audit_translated_pages(
        chunks,
        [(1, source_text), (255, "Unexpected page")],
        allow_partial_pages=True,
    )

    assert audit["passed"] is False
    assert audit["partial"] is True
    assert audit["missing_pages"] == [2]
    assert audit["unexpected_pages"] == [255]


def test_partial_translation_chunks_merge_valid_pages_and_ignore_unexpected_pages(tmp_path):
    translator = object.__new__(UploadedBookTranslator)
    source_text = (
        "Mix 500 grams flour with 5 eggs. Knead for 10 minutes and rest for 30 minutes before rolling."
    )
    chunk = BookTextChunk(
        index=0,
        start_page=1,
        end_page=2,
        page_numbers=[1, 2],
        text=f"[Page 1]\n{source_text}\n[Page 2]\n{source_text}",
    )
    first_result = ChunkTranslationResult(
        chunk=chunk,
        pages={1: source_text, 255: "Unexpected page"},
        provider_label="Gemini key #1",
    )

    partial_file, page_count = translator._merge_partial_translation_result(
        tmp_path,
        first_result,
        None,
    )

    assert isinstance(partial_file, str)
    assert page_count == 1
    assert [record["page"] for record in translator._read_translated_chunk_records(tmp_path, partial_file)] == [1]

    second_result = ChunkTranslationResult(
        chunk=chunk,
        pages={2: source_text},
        provider_label="Gemini key #2",
    )
    merged_file, merged_page_count = translator._merge_partial_translation_result(
        tmp_path,
        second_result,
        partial_file,
    )

    assert isinstance(merged_file, str)
    assert merged_file == partial_file
    assert merged_page_count == 2
    assert [record["page"] for record in translator._read_translated_chunk_records(tmp_path, merged_file)] == [1, 2]


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
    assert 'id="sidebarToggle"' in output
    assert 'id="progressToggle"' in output
    assert output.index('class="reader-tools"') < output.index('class="sidebar-header"')
    assert 'readStoredBoolean("translatedBookProgressCollapsed", false)' in output
    assert 'readStoredBoolean("translatedBookSidebarCollapsed", compactViewport.matches)' in output
    assert 'data-page-index="2"' in output
    assert "IntersectionObserver" in output
    assert "תוכן עניינים" in output


def test_translated_book_visual_assets_are_normalized_deduplicated_and_rendered(tmp_path):
    translator = object.__new__(UploadedBookTranslator)
    image_bytes = BytesIO()
    with Image.new("RGB", (320, 240), color=(196, 82, 36)) as image:
        image.save(image_bytes, format="PNG")

    first_asset = translator._store_visual_bytes(
        image_bytes.getvalue(),
        tmp_path,
        1,
        1,
        "image",
        "Original dish",
        {},
    )
    deduplicated_files: dict[str, str] = {}
    first_deduplicated_asset = translator._store_visual_bytes(
        image_bytes.getvalue(),
        tmp_path,
        1,
        2,
        "image",
        "Original dish",
        deduplicated_files,
    )
    second_deduplicated_asset = translator._store_visual_bytes(
        image_bytes.getvalue(),
        tmp_path,
        2,
        1,
        "image",
        "Same original dish",
        deduplicated_files,
    )

    assert first_asset is not None
    assert first_deduplicated_asset is not None
    assert second_deduplicated_asset is not None
    assert first_deduplicated_asset["file"] == second_deduplicated_asset["file"]
    assert tmp_path.joinpath(first_deduplicated_asset["file"]).is_file()

    book = SimpleNamespace(
        name="Illustrated book",
        original_file_name="Illustrated book.pdf",
        translation_page_start=None,
        translation_page_end=None,
    )
    output = translator._build_translated_book_html(
        book,
        "English",
        [
            {
                "page": 1,
                "text": "Translated page",
                "visualAssets": [first_deduplicated_asset],
            }
        ],
    )

    assert f'src="./assets/{first_deduplicated_asset["file"]}"' in output
    assert 'loading="lazy"' in output
    assert 'decoding="async"' in output
    assert "has-visuals" in output


def test_pdf_full_page_image_layers_are_rendered_as_one_composed_page(monkeypatch, tmp_path):
    full_page_image = Image.new("RGBA", (1200, 1800), color=(20, 30, 40, 180))
    fake_page = SimpleNamespace(
        mediabox=SimpleNamespace(width=400, height=600),
        images=[SimpleNamespace(image=full_page_image)],
    )
    fake_reader = SimpleNamespace(pages=[fake_page])
    monkeypatch.setitem(
        sys.modules,
        "pypdf",
        SimpleNamespace(PdfReader=lambda _path: fake_reader),
    )

    translator = object.__new__(UploadedBookTranslator)
    translator.logger = MagicMock()
    rendered_asset = {
        "file": "page-00001-rendered.webp",
        "width": 1200,
        "height": 1800,
        "kind": "page",
        "alt": "Original page 1",
    }
    translator._render_pdf_page_visual = MagicMock(return_value=rendered_asset)

    assets = translator._extract_pdf_visual_assets(
        tmp_path / "scanned.pdf",
        [1],
        {1: "OCR text from the scanned page"},
        tmp_path,
    )

    assert assets == {1: [rendered_asset]}
    translator._render_pdf_page_visual.assert_called_once()


def test_epub_visual_assets_follow_the_source_page_and_image_order(tmp_path):
    translator = object.__new__(UploadedBookTranslator)
    epub_path = tmp_path / "illustrated.epub"
    image_bytes = BytesIO()
    with Image.new("RGB", (180, 120), color=(80, 130, 170)) as image:
        image.save(image_bytes, format="PNG")
    with ZipFile(epub_path, "w") as archive:
        archive.writestr(
            "OEBPS/text/chapter.xhtml",
            (
                "<html><body><h1>Chapter</h1><p>Text</p>"
                '<img src="../images/first.png" alt="First illustration">'
                '<img src="../images/second.png" alt="Second illustration">'
                "</body></html>"
            ),
        )
        archive.writestr("OEBPS/images/first.png", image_bytes.getvalue())
        archive.writestr("OEBPS/images/second.png", image_bytes.getvalue())
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()

    assets = translator._extract_epub_visual_assets(epub_path, [1], assets_dir)

    assert [asset["alt"] for asset in assets[1]] == [
        "First illustration",
        "Second illustration",
    ]
    assert assets[1][0]["file"] == assets[1][1]["file"]


def test_partial_translated_book_html_keeps_original_pages_and_can_resume_translation():
    translator = object.__new__(UploadedBookTranslator)
    book = SimpleNamespace(
        id="31e24103-55d4-4f02-9404-24d16be7bf46",
        name="Partial book",
        original_file_name="Partial book.pdf",
        book_metadata_json="{}",
        translation_pages_per_chunk=10,
        translation_page_start=None,
        translation_page_end=None,
    )

    output = translator._build_translated_book_html(
        book,
        "Hebrew",
        [
            {"page": 1, "text": "עמוד מתורגם", "isTranslated": True},
            {"page": 2, "text": "Original page text", "isTranslated": False},
        ],
        translation_audit={
            "source_pages": 2,
            "translated_pages": 1,
            "verified_translated_pages": 1,
            "missing_pages": [2],
            "suspicious_pages": [],
        },
    )

    assert "50%" in output
    assert 'id="completeTranslationButton"' in output
    assert "/31e24103-55d4-4f02-9404-24d16be7bf46/translate" not in output
    assert 'encodeURIComponent("31e24103-55d4-4f02-9404-24d16be7bf46")' in output
    assert 'class="book-page reading-position source-language-page"' in output
    assert 'data-translated="false"' in output
    assert "טקסט מקורי — ממתין לתרגום" in output
    assert "Original page text" in output


def test_translated_book_toc_preserves_source_contents_titles_and_printed_pages():
    raw_records = [
        {
            "page": 3,
            "text": "תוכן עניינים\nהקדמה vii\nחום המטבח 13\nמנות ראשונות 21",
            "entryType": "contents",
        },
        {"page": 7, "text": "הקדמה", "title": "הקדמה", "entryType": "chapter"},
        {"page": 13, "text": "חום המטבח", "title": "חום המטבח", "entryType": "chapter"},
        {"page": 21, "text": "מנות ראשונות", "title": "מנות ראשונות", "entryType": "chapter"},
    ]
    records = [UploadedBookTranslator._translated_page_record(record, rtl=True) for record in raw_records]

    contents = UploadedBookTranslator._translated_book_toc(records, rtl=True)

    assert [(entry["title"], entry["page"], entry["displayPage"]) for entry in contents] == [
        ("הקדמה", 7, "vii"),
        ("חום המטבח", 13, "13"),
        ("מנות ראשונות", 21, "21"),
    ]


def test_translated_book_toc_uses_ai_chapter_and_recipe_metadata_without_source_contents():
    raw_records = [
        {
            "page": 4,
            "text": "ארוחות בוקר",
            "title": "ארוחות בוקר",
            "entryType": "chapter",
            "includeInContents": True,
        },
        {
            "page": 8,
            "text": "שקשוקה",
            "title": "שקשוקה",
            "entryType": "recipe",
            "parentTitle": "ארוחות בוקר",
            "includeInContents": True,
        },
        {"page": 9, "text": "המשך הוראות ללא כותרת", "entryType": "page"},
    ]
    records = [UploadedBookTranslator._translated_page_record(record, rtl=True) for record in raw_records]

    contents = UploadedBookTranslator._translated_book_toc(records, rtl=True)

    assert [(entry["title"], entry["level"], entry["kind"]) for entry in contents] == [
        ("ארוחות בוקר", 1, "chapter"),
        ("שקשוקה", 2, "recipe"),
    ]


def test_partial_translation_does_not_embed_recipes_from_outside_the_page_range(monkeypatch):
    translator = object.__new__(UploadedBookTranslator)
    translator.repos = MagicMock()
    translator.user = SimpleNamespace(group_slug="family")
    translator._recipes_extracted_from_book = lambda _book: [
        SimpleNamespace(
            extras={"uploadedBookSourcePageStart": 182},
            source="White Heat, page 182",
            recipe_ingredient=[],
            recipe_instructions=[],
            notes=[],
            name="Outside recipe",
            slug="outside-recipe",
        )
    ]
    translator._existing_book_recipe_shopping_list = lambda *_args: None
    monkeypatch.setattr(
        "mealie.services.uploaded_books.book_recipe_extractor.ShoppingListService",
        lambda _repos: SimpleNamespace(),
    )

    sections = translator._linked_recipe_sections(SimpleNamespace(), "Hebrew", set(range(1, 21)))

    assert sections == {}


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


@pytest.mark.asyncio
async def test_translated_book_classification_uses_target_language(monkeypatch, tmp_path):
    classify = AsyncMock()

    class FakeClassifier:
        def __init__(self, *_args) -> None:
            pass

        async def classify(self, *args, **kwargs) -> None:
            await classify(*args, **kwargs)

    monkeypatch.setattr(book_classifier_module, "UploadedBookClassifier", FakeClassifier)
    translator = object.__new__(UploadedBookTranslator)
    translator.repos = MagicMock()
    translator.user = MagicMock()
    translator.household = MagicMock()
    translator.translator = MagicMock()
    translated_book = SimpleNamespace(id=uuid4())

    await translator._classify_translated_book(translated_book, tmp_path, "Hebrew")

    classify.assert_awaited_once_with(
        translated_book.id,
        tmp_path,
        response_language="Hebrew",
    )


def test_manual_classification_of_translated_book_uses_translation_language(monkeypatch, tmp_path):
    controller = object.__new__(UploadedBooksController)
    book = SimpleNamespace(
        id=uuid4(),
        classification_status="not_started",
        classification_error=None,
        is_translated_book=True,
        translation_language="Hebrew",
    )
    controller._get_book_or_404 = lambda _book_id: book
    controller.session = MagicMock()
    controller._folders = SimpleNamespace(DATA_DIR=Path(tmp_path))
    controller._repos = MagicMock()
    controller.user = MagicMock()
    controller.translator = MagicMock()
    background_tasks = BackgroundTasks()

    class FakeClassifier:
        def __init__(self, *_args) -> None:
            pass

        async def classify(self, *_args) -> None:
            pass

    monkeypatch.setattr(
        "mealie.routes.households.controller_uploaded_books.UploadedBookClassifier",
        FakeClassifier,
    )
    monkeypatch.setattr(
        "mealie.routes.households.controller_uploaded_books.UploadedBookOut.model_validate",
        classmethod(lambda _cls, value: value),
    )

    result = controller.classify_book(book.id, background_tasks)

    assert result is book
    assert len(background_tasks.tasks) == 1
    assert background_tasks.tasks[0].args[-1] == "Hebrew"
