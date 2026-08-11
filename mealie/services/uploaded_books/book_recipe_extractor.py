import asyncio
import hashlib
import html
import json
import posixpath
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import ClassVar
from urllib.parse import quote, unquote
from uuid import uuid4
from zipfile import ZipFile

import sqlalchemy as sa
import sqlalchemy.exc
from bs4 import BeautifulSoup
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import UUID4

from mealie.core import exceptions
from mealie.db.models._model_utils.datetime import get_utc_now
from mealie.db.models.household.shopping_list import ShoppingList
from mealie.db.models.household.uploaded_book import UploadedBook
from mealie.db.models.recipe import RecipeModel
from mealie.db.models.recipe.api_extras import ApiExtras, ShoppingListExtras
from mealie.lang.providers import Translator
from mealie.repos.repository_factory import AllRepositories
from mealie.schema.group.ai_providers import AIProviderOut
from mealie.schema.household.group_shopping_list import ShoppingListAddRecipeParamsBulk, ShoppingListCreate
from mealie.schema.household.household import HouseholdInDB
from mealie.schema.openai.recipe import (
    OpenAIBookRecipeCatalogParse,
    OpenAIBookRecipeChunkParse,
    OpenAIBookRecipeSearchPlan,
    OpenAIBookTranslationChunkParse,
    OpenAIRecipe,
)
from mealie.schema.recipe.recipe import Recipe, create_recipe_slug
from mealie.schema.user import PrivateUser
from mealie.services._base_service import BaseService
from mealie.services.household_services.shopping_lists import ShoppingListService
from mealie.services.item_image_service import ItemImageService
from mealie.services.openai import OpenAIService
from mealie.services.recipe.recipe_service import OpenAIRecipeService, RecipeService
from mealie.services.uploaded_books.book_cover_service import BOOK_COVER_FILE_NAME, UploadedBookCoverService
from mealie.services.uploaded_books.book_reader_assets import (
    BOOK_READER_ID_PLACEHOLDER,
    book_reader_css,
    book_reader_labels,
    book_reader_panels,
    book_reader_script,
)

EXTRACTION_NOT_STARTED = "not_started"
EXTRACTION_PROCESSING = "processing"
EXTRACTION_RETRYING = "retrying"
EXTRACTION_COMPLETED = "completed"
EXTRACTION_PARTIAL_FAILED = "partial_failed"
EXTRACTION_FAILED = "failed"
EXTRACTION_CANCELLED = "cancelled"

TRANSLATION_NOT_STARTED = "not_started"
TRANSLATION_PROCESSING = "processing"
TRANSLATION_RETRYING = "retrying"
TRANSLATION_COMPLETED = "completed"
TRANSLATION_PARTIAL_FAILED = "partial_failed"
TRANSLATION_FAILED = "failed"
TRANSLATION_CANCELLED = "cancelled"

BOOK_SOURCE_PAGE_PATTERN = re.compile(
    r"(?:pages?|p\.?|עמוד(?:ים)?|עמ[׳'])\s*[:#]?\s*(\d{1,5})(?:\s*[-–—]\s*(\d{1,5}))?",
    flags=re.IGNORECASE,
)


def parse_book_source_page_range(
    source: str | None,
    fallback_start: int | None = None,
    fallback_end: int | None = None,
) -> tuple[int | None, int | None]:
    match = BOOK_SOURCE_PAGE_PATTERN.search(source or "")
    if not match:
        return fallback_start, fallback_end if fallback_end is not None else fallback_start

    page_start = int(match.group(1))
    page_end = int(match.group(2)) if match.group(2) else page_start
    return page_start, page_end

CHUNK_PENDING = "pending"
CHUNK_PROCESSING = "processing"
CHUNK_RETRYING = "retrying"
CHUNK_COMPLETED = "completed"
CHUNK_FAILED = "failed"

SUPPORTED_TEXT_EXTRACTION_EXTENSIONS = {
    ".docx",
    ".csv",
    ".epub",
    ".fb2",
    ".fb2.zip",
    ".htm",
    ".html",
    ".json",
    ".md",
    ".markdown",
    ".mht",
    ".mhtml",
    ".odt",
    ".pdf",
    ".rtf",
    ".txt",
}


@dataclass
class BookTextPage:
    number: int
    text: str


@dataclass
class BookTextChunk:
    index: int
    start_page: int
    end_page: int
    page_numbers: list[int]
    text: str


@dataclass
class ChunkExtractionResult:
    chunk: BookTextChunk
    recipes: list[OpenAIRecipe]
    error: str | None = None


@dataclass
class ProviderSlot:
    provider: AIProviderOut
    label: str
    available_at: float = 0.0
    busy: bool = False
    disabled: bool = False
    disabled_reason: str | None = None


@dataclass
class ChunkWorkResult:
    chunk: BookTextChunk
    recipes: list[OpenAIRecipe]
    provider_label: str
    wait_seconds: int | None = None
    error: str | None = None
    retryable: bool = False
    provider_disabled: bool = False


@dataclass
class ChunkTranslationResult:
    chunk: BookTextChunk
    pages: dict[int, str]
    provider_label: str
    page_metadata: dict[int, dict] | None = None
    wait_seconds: int | None = None
    error: str | None = None
    retryable: bool = False
    provider_disabled: bool = False


class UploadedBookRecipeExtractor(BaseService):
    PSEUDO_PAGE_CHAR_LIMIT = 3500
    MAX_AI_CHARS = 90000
    MAX_CHUNK_ATTEMPTS = 6
    DEFAULT_RETRY_WAIT_SECONDS = 60
    MAX_RETRY_WAIT_SECONDS = 30 * 60
    RECIPE_CATALOG_MAX_ENTRIES = 2000
    RECIPE_CATALOG_AI_BATCH_SIZE = 100
    RECIPE_CATALOG_FULL_TEXT_LIMIT = 300
    _running_jobs: ClassVar[set[tuple[str, str]]] = set()
    _running_jobs_lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    def __init__(
        self,
        repos: AllRepositories,
        user: PrivateUser,
        household: HouseholdInDB,
        translator: Translator,
    ) -> None:
        self.repos = repos
        self.user = user
        self.household = household
        self.translator = translator
        self.recipe_service = RecipeService(repos, user, household, translator)
        self.openai_recipe_service = OpenAIRecipeService(repos, user, household, translator)
        super().__init__()

    @classmethod
    async def is_job_running(cls, operation: str, book_id: UUID4 | str) -> bool:
        async with cls._running_jobs_lock:
            return (operation, str(book_id)) in cls._running_jobs

    @classmethod
    async def _claim_job(cls, operation: str, book_id: UUID4 | str) -> bool:
        key = (operation, str(book_id))
        async with cls._running_jobs_lock:
            if key in cls._running_jobs:
                return False

            cls._running_jobs.add(key)
            return True

    @classmethod
    async def _release_job(cls, operation: str, book_id: UUID4 | str) -> None:
        async with cls._running_jobs_lock:
            cls._running_jobs.discard((operation, str(book_id)))

    def _get_book(self, book_id: UUID4) -> UploadedBook:
        book = (
            self.repos.session.execute(
                sa.select(UploadedBook).where(UploadedBook.id == book_id, UploadedBook.group_id == self.user.group_id)
            )
            .scalars()
            .one_or_none()
        )
        if book is None:
            raise ValueError("Uploaded book was not found")

        return book

    def _save_book(self, book: UploadedBook) -> None:
        self.repos.session.add(book)
        self.repos.session.commit()

    @staticmethod
    def _book_metadata(book: UploadedBook) -> dict:
        try:
            value = json.loads(book.book_metadata_json or "{}")
        except (TypeError, ValueError):
            return {}
        return value if isinstance(value, dict) else {}

    def _update_book_metadata(self, book: UploadedBook, **updates) -> None:
        metadata = self._book_metadata(book)
        metadata.update(updates)
        book.book_metadata_json = json.dumps(metadata, ensure_ascii=False)
        self._save_book(book)

    def _current_status(self, book: UploadedBook, column) -> str | None:
        with self.repos.session.no_autoflush:
            return self.repos.session.execute(
                sa.select(column).where(UploadedBook.id == book.id, UploadedBook.group_id == self.user.group_id)
            ).scalar_one_or_none()

    def _is_extraction_cancelled(self, book: UploadedBook) -> bool:
        return self._current_status(book, UploadedBook.extraction_status) == EXTRACTION_CANCELLED

    def _is_translation_cancelled(self, book: UploadedBook) -> bool:
        return self._current_status(book, UploadedBook.translation_status) == TRANSLATION_CANCELLED

    def _set_extraction_cancelled(self, book: UploadedBook) -> None:
        book.extraction_status = EXTRACTION_CANCELLED
        book.extraction_error = "Cancelled by user"
        book.extraction_completed_at = get_utc_now()
        self._save_book(book)

    def _set_translation_cancelled(self, book: UploadedBook) -> None:
        book.translation_status = TRANSLATION_CANCELLED
        book.translation_error = "Cancelled by user"
        book.translation_completed_at = get_utc_now()
        self._save_book(book)

    def _set_failed(self, book: UploadedBook, error: str) -> None:
        book.extraction_status = EXTRACTION_FAILED
        book.extraction_error = error[:1000]
        book.extraction_completed_at = get_utc_now()
        self._save_book(book)

    def _book_file_path(self, book: UploadedBook, uploaded_books_root: Path) -> Path:
        root = uploaded_books_root.joinpath(str(book.group_id)).resolve()
        path = root.joinpath(str(book.id), book.file_name).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Invalid uploaded book file path")
        return path

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _text_to_pseudo_pages(self, text: str) -> list[BookTextPage]:
        text = self._normalize_text(text)
        if not text:
            return []

        pages: list[BookTextPage] = []
        for start in range(0, len(text), self.PSEUDO_PAGE_CHAR_LIMIT):
            pages.append(BookTextPage(number=len(pages) + 1, text=text[start : start + self.PSEUDO_PAGE_CHAR_LIMIT]))

        return pages

    def _extract_pdf_pages(self, path: Path, max_pages: int | None = None) -> list[BookTextPage]:
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise ValueError("PDF extraction requires the pypdf package") from e

        reader = PdfReader(str(path))
        pages: list[BookTextPage] = []
        for index, page in enumerate(reader.pages, start=1):
            if max_pages is not None and index > max_pages:
                break
            text = self._normalize_text(page.extract_text() or "")
            if text:
                pages.append(BookTextPage(number=index, text=text))

        return pages

    def _extract_epub_pages(self, path: Path, max_pages: int | None = None) -> list[BookTextPage]:
        with ZipFile(path) as archive:
            html_files = sorted(
                name
                for name in archive.namelist()
                if name.lower().endswith((".html", ".htm", ".xhtml")) and not name.endswith("/")
            )
            pages: list[BookTextPage] = []
            for name in html_files:
                if max_pages is not None and len(pages) >= max_pages:
                    break
                html = archive.read(name).decode("utf-8", errors="ignore")
                text = self._normalize_text(BeautifulSoup(html, "lxml").get_text("\n"))
                if text:
                    pages.append(BookTextPage(number=len(pages) + 1, text=text))

        return pages

    def _extract_docx_pages(self, path: Path) -> list[BookTextPage]:
        with ZipFile(path) as archive:
            xml = archive.read("word/document.xml").decode("utf-8", errors="ignore")
        text = BeautifulSoup(xml, "xml").get_text("\n")
        return self._text_to_pseudo_pages(text)

    def _extract_odt_pages(self, path: Path) -> list[BookTextPage]:
        with ZipFile(path) as archive:
            xml = archive.read("content.xml").decode("utf-8", errors="ignore")
        text = BeautifulSoup(xml, "xml").get_text("\n")
        return self._text_to_pseudo_pages(text)

    def _extract_fb2_pages(self, path: Path) -> list[BookTextPage]:
        if path.suffix.lower() == ".zip":
            with ZipFile(path) as archive:
                fb2_name = next((name for name in archive.namelist() if name.lower().endswith(".fb2")), None)
                if not fb2_name:
                    raise ValueError("FB2 ZIP archive does not contain an .fb2 file")
                xml = archive.read(fb2_name).decode("utf-8", errors="ignore")
        else:
            xml = path.read_text(encoding="utf-8", errors="ignore")

        text = BeautifulSoup(xml, "xml").get_text("\n")
        return self._text_to_pseudo_pages(text)

    def _extract_html_pages(self, path: Path) -> list[BookTextPage]:
        html = path.read_text(encoding="utf-8", errors="ignore")
        text = BeautifulSoup(html, "lxml").get_text("\n")
        return self._text_to_pseudo_pages(text)

    def _extract_rtf_pages(self, path: Path) -> list[BookTextPage]:
        raw = path.read_text(encoding="utf-8", errors="ignore")
        text = re.sub(r"\\'[0-9a-fA-F]{2}", " ", raw)
        text = re.sub(r"\\[a-zA-Z]+\d* ?", " ", text)
        text = text.replace("{", " ").replace("}", " ")
        return self._text_to_pseudo_pages(text)

    def _extract_pages(
        self,
        path: Path,
        extension: str,
        max_pages: int | None = None,
    ) -> list[BookTextPage]:
        if extension not in SUPPORTED_TEXT_EXTRACTION_EXTENSIONS:
            raise ValueError(f"AI extraction is not supported for {extension} files yet")

        if extension == ".pdf":
            return self._extract_pdf_pages(path, max_pages=max_pages)
        if extension == ".epub":
            return self._extract_epub_pages(path, max_pages=max_pages)
        if extension == ".docx":
            pages = self._extract_docx_pages(path)
            return pages[:max_pages] if max_pages is not None else pages
        if extension == ".odt":
            pages = self._extract_odt_pages(path)
            return pages[:max_pages] if max_pages is not None else pages
        if extension in {".fb2", ".fb2.zip"}:
            pages = self._extract_fb2_pages(path)
            return pages[:max_pages] if max_pages is not None else pages
        if extension in {".html", ".htm", ".mhtml", ".mht"}:
            pages = self._extract_html_pages(path)
            return pages[:max_pages] if max_pages is not None else pages
        if extension == ".rtf":
            pages = self._extract_rtf_pages(path)
            return pages[:max_pages] if max_pages is not None else pages

        if max_pages is not None:
            with path.open("r", encoding="utf-8", errors="ignore") as source:
                text = source.read(self.PSEUDO_PAGE_CHAR_LIMIT * max_pages)
            return self._text_to_pseudo_pages(text)[:max_pages]

        return self._text_to_pseudo_pages(path.read_text(encoding="utf-8", errors="ignore"))

    @staticmethod
    def _catalog_text_key(value: str | None) -> str:
        return re.sub(r"[^\w\u0590-\u05ff]+", " ", value or "", flags=re.UNICODE).casefold().strip()

    @staticmethod
    def _roman_page_number(value: str) -> int | None:
        text = value.strip().upper()
        if not text or not re.fullmatch(r"[IVXLCDM]+", text):
            return None
        values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
        result = 0
        previous = 0
        for character in reversed(text):
            current = values[character]
            result += -current if current < previous else current
            previous = max(previous, current)
        return result or None

    @classmethod
    def _contents_catalog_entries(cls, pages: list[BookTextPage]) -> list[dict]:
        marker_pattern = re.compile(
            r"\b(?:table\s+of\s+contents|contents|index\s+of\s+recipes)\b|תוכן\s+עניינים",
            flags=re.IGNORECASE,
        )
        line_pattern = re.compile(
            r"^\s*(?P<title>.+?)\s*(?:[.·•…_\-]{2,}\s*)"
            r"(?P<page>\d{1,4}|[ivxlcdm]{1,10})\s*$",
            flags=re.IGNORECASE,
        )
        loose_pattern = re.compile(
            r"^\s*(?P<title>[^\d][^|]{2,110}?)\s{2,}(?P<page>\d{1,4}|[ivxlcdm]{1,10})\s*$",
            flags=re.IGNORECASE,
        )
        compact_pattern = re.compile(
            r"^\s*(?P<title>[^\d][^|]{2,110}?)\s+(?P<page>\d{1,4}|[ivxlcdm]{1,10})\s*$",
            flags=re.IGNORECASE,
        )
        entries: list[dict] = []
        in_contents = False
        quiet_pages = 0
        for page in pages[:100]:
            page_has_marker = bool(marker_pattern.search(page.text))
            if page_has_marker:
                in_contents = True
            if not in_contents:
                continue

            page_matches = 0
            for raw_line in page.text.splitlines():
                line = " ".join(raw_line.split()).strip(" .·•…_-")
                if not line or marker_pattern.fullmatch(line):
                    continue
                match = (
                    line_pattern.match(raw_line.strip())
                    or loose_pattern.match(raw_line.rstrip())
                    or compact_pattern.match(raw_line.rstrip())
                )
                if not match:
                    continue
                title = " ".join(match.group("title").split()).strip(" .·•…_-")
                if len(title) < 2 or len(title) > 140:
                    continue
                page_value = match.group("page")
                printed_page = int(page_value) if page_value.isdigit() else cls._roman_page_number(page_value)
                if printed_page is None or printed_page < 1:
                    continue
                entries.append(
                    {
                        "entry_index": len(entries),
                        "title": title,
                        "chapter": None,
                        "page_start": printed_page,
                        "source_page": page.number,
                    }
                )
                page_matches += 1

            quiet_pages = quiet_pages + 1 if page_matches == 0 else 0
            if entries and quiet_pages >= 2:
                break

        deduplicated: list[dict] = []
        seen: set[tuple[str, int]] = set()
        for entry in entries:
            key = (cls._catalog_text_key(entry["title"]), entry["page_start"])
            if not key[0] or key in seen:
                continue
            seen.add(key)
            entry["entry_index"] = len(deduplicated)
            deduplicated.append(entry)
        return deduplicated[: cls.RECIPE_CATALOG_MAX_ENTRIES]

    @classmethod
    def _heading_catalog_entries(cls, pages: list[BookTextPage]) -> list[dict]:
        generic_lines = {
            "ingredients",
            "ingredient",
            "instructions",
            "directions",
            "method",
            "notes",
            "מרכיבים",
            "אופן ההכנה",
            "הוראות",
            "הערות",
        }
        entries: list[dict] = []
        last_title_key = ""
        for page in pages:
            title = ""
            for raw_line in page.text.splitlines()[:30]:
                candidate = " ".join(raw_line.split()).strip(" .·•…_-")
                words = candidate.split()
                if not 2 <= len(candidate) <= 140 or len(words) > 18:
                    continue
                normalized = cls._catalog_text_key(candidate)
                if normalized in generic_lines or re.match(r"^(?:page|עמוד)\s+\d+$", normalized):
                    continue
                if candidate.endswith((".", "!", "?", ":")) and len(words) > 8:
                    continue
                if re.match(r"^[\d\s/.,%°+-]+$", candidate):
                    continue
                title = candidate
                break
            title_key = cls._catalog_text_key(title)
            if not title_key or title_key == last_title_key:
                continue
            last_title_key = title_key
            entries.append(
                {
                    "entry_index": len(entries),
                    "title": title,
                    "chapter": None,
                    "page_start": page.number,
                    "source_page": page.number,
                }
            )
            if len(entries) >= cls.RECIPE_CATALOG_MAX_ENTRIES:
                break
        return entries

    @classmethod
    def _full_text_catalog_entries(
        cls,
        pages: list[BookTextPage],
        query: str,
        plan: OpenAIBookRecipeSearchPlan | None,
    ) -> list[dict]:
        values = [query]
        if plan:
            values.extend(plan.search_terms)
            values.extend(hint.title for hint in plan.hints)

        terms: list[str] = []
        seen_terms: set[str] = set()
        for value in values:
            normalized = cls._catalog_text_key(value)
            if len(normalized) < 2 or normalized in seen_terms:
                continue
            seen_terms.add(normalized)
            terms.append(normalized)
        terms = terms[:60]
        if not terms:
            return []

        recipe_marker = re.compile(
            r"\b(?:ingredients?|directions?|instructions?|method|serves?|yield|recipe)\b"
            r"|(?:מרכיבים|אופן\s+הכנה|הוראות|מנות|מתכון)",
            flags=re.IGNORECASE,
        )
        hint_titles = [
            (hint.title.strip(), cls._catalog_text_key(hint.title))
            for hint in (plan.hints if plan else [])
            if hint.title.strip()
        ]
        scored_pages: list[tuple[int, BookTextPage, list[str], str | None]] = []
        for page in pages:
            page_key = cls._catalog_text_key(page.text)
            if not page_key:
                continue
            matched_terms = [term for term in terms if term in page_key]
            if not matched_terms:
                continue
            matched_hint = next((title for title, key in hint_titles if key and key in page_key), None)
            exact_query = cls._catalog_text_key(query) in page_key if query.strip() else False
            has_recipe_marker = bool(recipe_marker.search(page.text))
            score = (18 if matched_hint else 0) + (10 if exact_query else 0)
            score += min(sum(page_key.count(term) for term in matched_terms), 12)
            score += 5 if has_recipe_marker else 0
            if not (matched_hint or exact_query or has_recipe_marker or len(matched_terms) >= 2):
                continue
            scored_pages.append((score, page, matched_terms, matched_hint))

        selected = sorted(
            scored_pages,
            key=lambda item: (-item[0], item[1].number),
        )[: cls.RECIPE_CATALOG_FULL_TEXT_LIMIT]
        selected.sort(key=lambda item: item[1].number)

        entries: list[dict] = []
        seen_pages: set[int] = set()
        for _score, page, matched_terms, matched_hint in selected:
            if page.number in seen_pages:
                continue
            seen_pages.add(page.number)
            lines = [" ".join(line.split()).strip() for line in page.text.splitlines()]
            lines = [line for line in lines if line]
            title = matched_hint or ""
            if not title:
                for line in lines[:50]:
                    line_key = cls._catalog_text_key(line)
                    if (
                        2 <= len(line) <= 140
                        and len(line.split()) <= 18
                        and any(term in line_key for term in matched_terms)
                    ):
                        title = line.strip(" .·•…_-")
                        break
            if not title:
                heading_entries = cls._heading_catalog_entries([page])
                title = heading_entries[0]["title"] if heading_entries else query.strip()
            if not title:
                continue

            relevant_index = next(
                (
                    index
                    for index, line in enumerate(lines)
                    if any(term in cls._catalog_text_key(line) for term in matched_terms)
                ),
                0,
            )
            excerpt_start = max(0, relevant_index - 5)
            excerpt = "\n".join(lines[excerpt_start : relevant_index + 16])[:2200]
            entries.append(
                {
                    "entry_index": 0,
                    "title": title,
                    "chapter": None,
                    "page_start": page.number,
                    "page_end": min(page.number + 3, pages[-1].number),
                    "source_page": page.number,
                    "entry_source": "full_text",
                    "excerpt": excerpt,
                }
            )
        return entries

    async def _recipe_search_plan(
        self,
        book: UploadedBook,
        query: str,
        target_language: str,
    ) -> tuple[OpenAIBookRecipeSearchPlan | None, str | None]:
        if not query.strip():
            return None, None
        openai_service = OpenAIService(self.repos)
        try:
            slots = self._provider_slots(openai_service)
        except Exception as error:
            return None, self._short_error(error)

        prompt = openai_service.get_prompt("recipes.locate-book-recipes")
        errors: list[str] = []
        message = (
            f"Cookbook title and edition: {book.name}\n"
            f"Target display language: {target_language}\n"
            f"Recipe search request: {query.strip()}"
        )
        for slot in slots:
            try:
                response = await openai_service.get_response(
                    prompt,
                    message,
                    response_schema=OpenAIBookRecipeSearchPlan,
                    provider=slot.provider,
                )
                if response:
                    return response, None
            except Exception as error:
                errors.append(self._short_error(error))
        return None, "; ".join(dict.fromkeys(errors))[:1000] or None

    @staticmethod
    def _catalog_candidate_id(book_id: UUID4 | str, entry: dict) -> str:
        payload = (
            f"{book_id}|{entry.get('entry_index')}|{entry.get('title')}|"
            f"{entry.get('page_start')}|{entry.get('source_page')}"
        )
        return hashlib.sha256(payload.encode("utf-8", errors="ignore")).hexdigest()[:24]

    def _catalog_source_book(self, book: UploadedBook) -> UploadedBook:
        if not book.is_translated_book or not book.translated_from_book_id:
            return book
        return self._get_book(book.translated_from_book_id)

    def _catalog_entries_for_book(
        self,
        book: UploadedBook,
        uploaded_books_root: Path,
        refresh: bool,
        pages: list[BookTextPage] | None = None,
    ) -> tuple[list[dict], str]:
        metadata = self._book_metadata(book)
        cached_entries = metadata.get("recipe_catalog_entries")
        cached_source = metadata.get("recipe_catalog_source")
        if (
            not refresh
            and isinstance(cached_entries, list)
            and cached_entries
            and cached_source in {"contents", "headings"}
        ):
            return [entry for entry in cached_entries if isinstance(entry, dict)], str(cached_source)

        path = self._book_file_path(book, uploaded_books_root)
        first_pages = pages[:100] if pages is not None else self._extract_pages(path, book.extension, max_pages=100)
        entries = self._contents_catalog_entries(first_pages)
        source = "contents"
        if not entries:
            heading_pages = (
                pages[: self.RECIPE_CATALOG_MAX_ENTRIES]
                if pages is not None
                else self._extract_pages(path, book.extension, max_pages=self.RECIPE_CATALOG_MAX_ENTRIES)
            )
            entries = self._heading_catalog_entries(heading_pages)
            source = "headings"
        if not entries:
            raise ValueError("No usable table of contents or local headings were found in this book")

        for index, entry in enumerate(entries):
            entry["entry_index"] = index
            next_start = entries[index + 1]["page_start"] if index + 1 < len(entries) else entry["page_start"] + 12
            entry["page_end"] = max(entry["page_start"], min(next_start - 1, entry["page_start"] + 12))

        metadata["recipe_catalog_entries"] = entries
        metadata["recipe_catalog_source"] = source
        metadata["recipe_catalog_indexed_at"] = datetime.now(UTC).isoformat()
        book.book_metadata_json = json.dumps(metadata, ensure_ascii=False)
        self._save_book(book)
        return entries, source

    async def _classify_catalog_entries(
        self,
        book: UploadedBook,
        entries: list[dict],
        query: str,
        target_language: str,
    ) -> tuple[dict[int, dict], bool, str | None]:
        openai_service = OpenAIService(self.repos)
        slots = self._provider_slots(openai_service)
        prompt = openai_service.get_prompt("recipes.discover-book-recipes")
        batch_size = 30 if any(entry.get("excerpt") for entry in entries) else self.RECIPE_CATALOG_AI_BATCH_SIZE
        batches = [
            entries[index : index + batch_size]
            for index in range(0, len(entries), batch_size)
        ]
        matches: dict[int, dict] = {}
        errors: list[str] = []
        result_lock = asyncio.Lock()
        slot_lock = asyncio.Lock()
        disabled_slots: set[int] = set()
        concurrency = asyncio.Semaphore(max(1, min(len(slots), len(batches))))

        async def classify_batch(batch_index: int, batch: list[dict]) -> None:
            for offset in range(len(slots)):
                slot_index = (batch_index + offset) % len(slots)
                async with slot_lock:
                    if slot_index in disabled_slots:
                        continue
                slot = slots[slot_index]
                try:
                    message = (
                        f"Cookbook title: {book.name}\n"
                        f"Target display language: {target_language}\n"
                        f"Search request: {query.strip() or '[all recipes]'}\n\n"
                        "Compact entries JSON:\n"
                        f"{json.dumps(batch, ensure_ascii=False)}"
                    )
                    async with concurrency:
                        response = await openai_service.get_response(
                            prompt,
                            message,
                            response_schema=OpenAIBookRecipeCatalogParse,
                            provider=slot.provider,
                        )
                    if response is None:
                        raise ValueError(f"{slot.label} returned no recipe catalog response")
                    async with result_lock:
                        for match in response.matches:
                            matches[match.entry_index] = match.model_dump(mode="json")
                    return
                except Exception as error:
                    async with result_lock:
                        errors.append(f"{slot.label}: {self._short_error(error)}")
                    if self._is_provider_disabled_error(error):
                        async with slot_lock:
                            disabled_slots.add(slot_index)

        await asyncio.gather(
            *(classify_batch(batch_index, batch) for batch_index, batch in enumerate(batches))
        )
        warning = "; ".join(dict.fromkeys(errors))[:1000] or None
        return matches, bool(matches), warning

    async def discover_recipe_catalog(
        self,
        book_id: UUID4,
        uploaded_books_root: Path,
        query: str = "",
        target_language: str = "Hebrew",
        refresh: bool = False,
    ) -> dict:
        requested_book = self._get_book(book_id)
        book = self._catalog_source_book(requested_book)
        normalized_query = self._catalog_text_key(query)
        plan: OpenAIBookRecipeSearchPlan | None = None
        plan_warning: str | None = None
        pages: list[BookTextPage] | None = None
        if normalized_query:
            plan, plan_warning = await self._recipe_search_plan(book, query, target_language)
            path = self._book_file_path(book, uploaded_books_root)
            pages = self._extract_pages(path, book.extension)
            if not pages:
                raise ValueError("No extractable text was found in this book")

        try:
            base_entries, base_source = self._catalog_entries_for_book(
                book,
                uploaded_books_root,
                refresh,
                pages,
            )
        except ValueError:
            if not normalized_query:
                raise
            base_entries, base_source = [], "headings"

        full_text_entries = (
            self._full_text_catalog_entries(pages or [], query, plan)
            if normalized_query
            else []
        )
        source = base_source
        if full_text_entries:
            source = "hybrid" if base_entries else "full_text"

        entries: list[dict] = []
        seen_entries: set[tuple[str, int]] = set()
        query_key = self._catalog_text_key(query)
        for entry in [*full_text_entries, *base_entries]:
            title_key = self._catalog_text_key(entry.get("title"))
            page_start = int(entry.get("page_start") or 1)
            dedupe_page = page_start if entry.get("entry_source") == "full_text" and title_key == query_key else 0
            key = (title_key, dedupe_page)
            if not title_key or key in seen_entries:
                continue
            seen_entries.add(key)
            copied = dict(entry)
            copied["entry_index"] = len(entries)
            entries.append(copied)
        if not entries:
            raise ValueError("No matching text, table of contents, or local headings were found in this book")

        matches, used_ai, warning = await self._classify_catalog_entries(
            book,
            entries,
            query,
            target_language,
        )
        warning_parts = [value for value in (plan_warning, warning) if value]
        warning = "; ".join(dict.fromkeys(warning_parts))[:1000] or None
        metadata = self._book_metadata(book)
        prior_candidates = {
            candidate.get("id"): candidate
            for candidate in metadata.get("recipe_catalog_candidates", [])
            if isinstance(candidate, dict) and candidate.get("id")
        }
        raw_imported_recipes = metadata.get("recipe_catalog_imported", {})
        if not isinstance(raw_imported_recipes, dict):
            raw_imported_recipes = {}
        imported_recipes = {
            str(candidate_id): str(recipe_slug)
            for candidate_id, recipe_slug in raw_imported_recipes.items()
            if candidate_id and recipe_slug
        }
        candidates: list[dict] = []
        seen_candidates: set[tuple[str, int]] = set()
        for entry in entries:
            match = matches.get(int(entry["entry_index"]))
            if match:
                include = bool(match.get("is_recipe")) and bool(match.get("matches_query"))
            else:
                title_key = self._catalog_text_key(entry.get("title"))
                include = (
                    not normalized_query
                    or normalized_query in title_key
                    or entry.get("entry_source") == "full_text"
                )
            if not include:
                continue
            candidate_id = self._catalog_candidate_id(book.id, entry)
            previous = prior_candidates.get(candidate_id, {})
            display_title = (match or {}).get("display_title") or entry["title"]
            candidate_key = (
                self._catalog_text_key(display_title),
                int(entry["page_start"]),
            )
            if candidate_key in seen_candidates:
                continue
            seen_candidates.add(candidate_key)
            candidates.append(
                {
                    "id": candidate_id,
                    "title": display_title,
                    "source_title": entry["title"],
                    "chapter": (match or {}).get("chapter") or entry.get("chapter"),
                    "page_start": int(entry["page_start"]),
                    "page_end": int(entry.get("page_end") or entry["page_start"]),
                    "reason": (match or {}).get("reason")
                    or ("Verified local full-text match" if entry.get("entry_source") == "full_text" else None),
                    "imported_recipe_slug": imported_recipes.get(candidate_id)
                    or previous.get("imported_recipe_slug"),
                }
            )

        metadata["recipe_catalog_candidates"] = candidates
        metadata["recipe_catalog_last_query"] = query
        metadata["recipe_catalog_generated_at"] = datetime.now(UTC).isoformat()
        book.book_metadata_json = json.dumps(metadata, ensure_ascii=False)
        self._save_book(book)
        return {
            "book_id": requested_book.id,
            "query": query,
            "source": source,
            "candidates": candidates,
            "generated_at": metadata["recipe_catalog_generated_at"],
            "used_ai": used_ai,
            "warning": warning,
        }

    @staticmethod
    def _filter_pages_by_range(
        pages: list[BookTextPage],
        page_start: int | None = None,
        page_end: int | None = None,
    ) -> list[BookTextPage]:
        if page_start is not None and page_end is not None and page_end < page_start:
            raise ValueError("End page must be greater than or equal to start page")

        return [
            page
            for page in pages
            if (page_start is None or page.number >= page_start) and (page_end is None or page.number <= page_end)
        ]

    def _build_chunks(
        self,
        pages: list[BookTextPage],
        pages_per_chunk: int,
        forward_overlap_pages: int = 0,
    ) -> list[BookTextChunk]:
        chunks: list[BookTextChunk] = []
        current_pages: list[BookTextPage] = []
        current_chars = 0

        def flush() -> None:
            nonlocal current_pages, current_chars
            if not current_pages:
                return

            text = "\n\n".join(f"[Page {page.number}]\n{page.text}" for page in current_pages)
            chunks.append(
                BookTextChunk(
                    index=len(chunks),
                    start_page=current_pages[0].number,
                    end_page=current_pages[-1].number,
                    page_numbers=[page.number for page in current_pages],
                    text=text,
                )
            )
            current_pages = []
            current_chars = 0

        for page in pages:
            page_len = len(page.text)
            should_flush_by_pages = len(current_pages) >= pages_per_chunk
            should_flush_by_chars = current_pages and current_chars + page_len > self.MAX_AI_CHARS
            if should_flush_by_pages or should_flush_by_chars:
                flush()

            current_pages.append(page)
            current_chars += page_len

        flush()

        if forward_overlap_pages > 0:
            page_positions = {page.number: index for index, page in enumerate(pages)}
            for chunk in chunks:
                last_position = page_positions[chunk.page_numbers[-1]]
                overlap = pages[last_position + 1 : last_position + 1 + forward_overlap_pages]
                chunk_chars = len(chunk.text)
                for page in overlap:
                    page_text = f"\n\n[Page {page.number}]\n{page.text}"
                    if chunk_chars + len(page_text) > self.MAX_AI_CHARS:
                        break
                    chunk.text += page_text
                    chunk_chars += len(page_text)

        return chunks

    def _provider_slots(self, openai_service: OpenAIService) -> list[ProviderSlot]:
        provider = openai_service.default_provider
        if provider is None:
            raise ValueError("No default AI provider configured")

        if not OpenAIService._is_gemini_provider_data(provider):
            return [ProviderSlot(provider=provider, label=provider.name or provider.model or "AI provider")]

        keys = OpenAIService._split_api_keys(provider.api_key)
        if not keys:
            return [ProviderSlot(provider=provider, label="Gemini key #1")]

        return [
            ProviderSlot(provider=provider.model_copy(update={"api_key": key}), label=f"Gemini key #{index}")
            for index, key in enumerate(keys, start=1)
        ]

    def _chunk_message(
        self,
        book: UploadedBook,
        chunk: BookTextChunk,
        translate_language: str,
        target_recipe_title: str | None = None,
    ) -> str:
        target_instruction = (
            "\n"
            f"Requested recipe title: {target_recipe_title}\n"
            "Return only this requested recipe. Ignore complete neighboring recipes unless they are explicitly "
            "part of the requested preparation.\n"
            if target_recipe_title
            else ""
        )
        return (
            f"Cookbook title: {book.name}\n"
            f"Original file name: {book.original_file_name}\n"
            f"Primary page range: {chunk.start_page}-{chunk.end_page}\n"
            f"Translate recipes to: {translate_language}\n"
            f"{target_instruction}\n"
            "The text may include up to two following pages as overlap context. "
            "Return a recipe only when its title or ingredient list begins inside the primary page range. "
            "Use overlap pages only to complete a recipe that began in the primary range.\n\n"
            "Cookbook chunk text:\n"
            f"{chunk.text}"
        )

    @staticmethod
    def _chunk_range_key(chunk: BookTextChunk) -> str:
        return f"{chunk.start_page}-{chunk.end_page}"

    def _load_chunk_states(self, book: UploadedBook) -> dict[str, dict]:
        if not book.extraction_chunk_status:
            return {}

        try:
            payload = json.loads(book.extraction_chunk_status)
        except (TypeError, ValueError):
            return {}

        if not isinstance(payload, list):
            return {}

        states: dict[str, dict] = {}
        for item in payload:
            if not isinstance(item, dict):
                continue
            range_key = item.get("range")
            if isinstance(range_key, str):
                states[range_key] = item

        return states

    def _initial_chunk_states(
        self, book: UploadedBook, chunks: list[BookTextChunk], preserve_incomplete_attempts: bool = False
    ) -> dict[int, dict]:
        existing_states = self._load_chunk_states(book)
        states: dict[int, dict] = {}

        for chunk in chunks:
            range_key = self._chunk_range_key(chunk)
            previous = existing_states.get(range_key)
            if previous and previous.get("status") == CHUNK_COMPLETED:
                states[chunk.index] = {
                    **previous,
                    "index": chunk.index,
                    "range": range_key,
                    "startPage": chunk.start_page,
                    "endPage": chunk.end_page,
                    "status": CHUNK_COMPLETED,
                }
                continue

            if previous and preserve_incomplete_attempts:
                states[chunk.index] = {
                    **previous,
                    "index": chunk.index,
                    "range": range_key,
                    "startPage": chunk.start_page,
                    "endPage": chunk.end_page,
                    "status": CHUNK_PENDING,
                    "nextRetrySeconds": None,
                    "nextRetryAt": None,
                }
                continue

            states[chunk.index] = {
                "index": chunk.index,
                "range": range_key,
                "startPage": chunk.start_page,
                "endPage": chunk.end_page,
                "status": CHUNK_PENDING,
                "attempts": 0,
                "recipesFound": 0,
                "recipesCreated": 0,
                "error": None,
                "provider": None,
                "nextRetrySeconds": None,
                "nextRetryAt": None,
            }

        return states

    @staticmethod
    def _state_int(state: dict, key: str) -> int:
        value = state.get(key)
        return value if isinstance(value, int) else 0

    @staticmethod
    def _retry_at(wait_seconds: int) -> str:
        return (get_utc_now() + timedelta(seconds=wait_seconds)).isoformat()

    @staticmethod
    def _parse_retry_at(value: object) -> datetime | None:
        if not isinstance(value, str) or not value:
            return None

        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)

        return parsed.astimezone(UTC)

    @classmethod
    def is_resume_due(cls, status: str, chunk_status: str | None, now: datetime | None = None) -> bool:
        if status == CHUNK_PROCESSING:
            return True
        if status != CHUNK_RETRYING:
            return False

        now = now or get_utc_now()
        try:
            states = json.loads(chunk_status or "[]")
        except (TypeError, ValueError):
            return True

        if not isinstance(states, list):
            return True

        has_retrying_state = False
        for state in states:
            if not isinstance(state, dict):
                continue

            state_status = state.get("status")
            if state_status in {CHUNK_PENDING, CHUNK_PROCESSING}:
                return True

            if state_status != CHUNK_RETRYING:
                continue

            has_retrying_state = True
            retry_at = cls._parse_retry_at(state.get("nextRetryAt"))
            if retry_at is None or retry_at <= now:
                return True

        return not has_retrying_state

    def _chunk_error_summary(self, states: dict[int, dict]) -> str | None:
        errors: list[str] = []
        for state in sorted(states.values(), key=lambda item: self._state_int(item, "index")):
            status = state.get("status")
            error = state.get("error")
            if status not in {CHUNK_RETRYING, CHUNK_FAILED} or not error:
                continue

            prefix = f"pages {state.get('startPage')}-{state.get('endPage')}"
            if status == CHUNK_RETRYING and state.get("nextRetrySeconds"):
                retry_at = state.get("nextRetryAt")
                if retry_at:
                    prefix = f"{prefix} retrying at {retry_at}"
                else:
                    prefix = f"{prefix} retrying in {state.get('nextRetrySeconds')}s"
            errors.append(f"{prefix}: {str(error)[:220]}")

        return "\n".join(errors)[-1000:] if errors else None

    def _save_progress(
        self,
        book: UploadedBook,
        states: dict[int, dict],
        status: str | None = None,
    ) -> None:
        if status != EXTRACTION_CANCELLED and self._is_extraction_cancelled(book):
            self._set_extraction_cancelled(book)
            return

        state_values = list(states.values())
        book.extraction_total_chunks = len(state_values)
        book.extraction_completed_chunks = sum(1 for state in state_values if state.get("status") == CHUNK_COMPLETED)
        book.extraction_failed_chunks = sum(1 for state in state_values if state.get("status") == CHUNK_FAILED)
        book.extraction_retry_count = sum(max(self._state_int(state, "attempts") - 1, 0) for state in state_values)
        book.extraction_recipes_found = sum(self._state_int(state, "recipesFound") for state in state_values)
        book.extraction_recipes_created = sum(self._state_int(state, "recipesCreated") for state in state_values)
        book.extraction_chunk_status = json.dumps(
            sorted(state_values, key=lambda item: self._state_int(item, "index")),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        book.extraction_error = self._chunk_error_summary(states)

        if status:
            book.extraction_status = status
        elif any(state.get("status") == CHUNK_RETRYING for state in state_values):
            book.extraction_status = EXTRACTION_RETRYING
        else:
            book.extraction_status = EXTRACTION_PROCESSING

        self._save_book(book)

    def _retry_wait_seconds(self, error: Exception) -> int | None:
        message = str(error)
        patterns = [
            r"retry(?:\s|-)?after[^\d]*(\d+(?:\.\d+)?)\s*(milliseconds?|ms|seconds?|secs?|s|minutes?|mins?|m)?",
            (
                r"(?:retry|try again|please retry)\s+in[^\d]*(\d+(?:\.\d+)?)\s*"
                r"(milliseconds?|ms|seconds?|secs?|s|minutes?|mins?|m)?"
            ),
        ]

        for pattern in patterns:
            match = re.search(pattern, message, flags=re.IGNORECASE)
            if not match:
                continue

            value = float(match.group(1))
            unit = (match.group(2) or "seconds").lower()
            if unit in {"millisecond", "milliseconds", "ms"}:
                value = value / 1000
            elif unit in {"minute", "minutes", "min", "mins", "m"}:
                value = value * 60

            return max(1, min(int(value) + 1, self.MAX_RETRY_WAIT_SECONDS))

        return None

    @staticmethod
    def _is_retryable_error(error: Exception) -> bool:
        if isinstance(error, exceptions.RateLimitError):
            return True

        message = str(error).lower()
        retryable_markers = (
            "429",
            "rate limit",
            "ratelimit",
            "retry-after",
            "resource_exhausted",
            "quota",
            "too many requests",
            "temporarily unavailable",
            "timeout",
            "timed out",
            "500",
            "502",
            "503",
            "504",
        )
        return any(marker in message for marker in retryable_markers)

    @staticmethod
    def _is_provider_disabled_error(error: Exception) -> bool:
        message = str(error).lower()
        if any(marker in message for marker in ("quota", "rate limit", "resource_exhausted", "retry-after")):
            return False

        disabled_markers = (
            "401",
            "403",
            "api key not valid",
            "api_key_invalid",
            "invalid api key",
            "invalid_api_key",
            "incorrect api key",
            "authentication",
            "unauthorized",
            "not authorized",
            "permission_denied",
            "permission denied",
            "denied access",
        )
        return any(marker in message for marker in disabled_markers)

    @staticmethod
    def _short_error(error: Exception) -> str:
        message = str(error).replace("\n", " ").strip()
        return message[:500] if message else error.__class__.__name__

    async def _acquire_provider_slot(self, slots: list[ProviderSlot], lock: asyncio.Lock) -> ProviderSlot:
        while True:
            sleep_for = 0.25
            async with lock:
                now = time.monotonic()
                enabled_slots = [slot for slot in slots if not slot.disabled]
                if not enabled_slots:
                    raise RuntimeError("No usable AI provider keys remain")

                available_slots = [slot for slot in enabled_slots if not slot.busy]
                has_busy_slots = len(available_slots) != len(enabled_slots)

                if available_slots:
                    slot = min(available_slots, key=lambda item: item.available_at)
                    wait_seconds = max(slot.available_at - now, 0)
                    if wait_seconds <= 0:
                        slot.busy = True
                        return slot

                    sleep_for = 0.25 if has_busy_slots else min(wait_seconds, 30)

            await asyncio.sleep(sleep_for)

    async def _disable_provider_slot(self, slot: ProviderSlot, lock: asyncio.Lock, reason: str | None = None) -> None:
        async with lock:
            slot.disabled = True
            slot.disabled_reason = reason
            slot.available_at = 0

    async def _has_usable_provider_slot(self, slots: list[ProviderSlot], lock: asyncio.Lock) -> bool:
        async with lock:
            return any(not slot.disabled for slot in slots)

    async def _release_provider_slot(
        self,
        slot: ProviderSlot,
        lock: asyncio.Lock,
        wait_seconds: int | None = None,
    ) -> None:
        async with lock:
            if wait_seconds:
                slot.available_at = max(slot.available_at, time.monotonic() + wait_seconds)
            slot.busy = False

    async def _extract_chunk_once(
        self,
        openai_service: OpenAIService,
        prompt: str,
        slot: ProviderSlot,
        book: UploadedBook,
        chunk: BookTextChunk,
        translate_language: str,
        target_recipe_title: str | None = None,
    ) -> ChunkWorkResult:
        try:
            response = await openai_service.get_response(
                prompt,
                self._chunk_message(book, chunk, translate_language, target_recipe_title),
                response_schema=OpenAIBookRecipeChunkParse,
                provider=slot.provider,
            )
        except Exception as e:
            provider_disabled = self._is_provider_disabled_error(e)
            retryable = False if provider_disabled else self._is_retryable_error(e)
            if provider_disabled:
                self.logger.warning(
                    f"Disabling AI provider slot {slot.label} after extraction error "
                    f"for book chunk {chunk.index + 1}: {e}"
                )
            elif retryable:
                self.logger.warning(
                    f"Retryable AI extraction error for book chunk {chunk.index + 1} using {slot.label}: {e}"
                )
            else:
                self.logger.error(f"Failed to extract recipes from book chunk {chunk.index + 1}")
                self.logger.exception(e)

            return ChunkWorkResult(
                chunk=chunk,
                recipes=[],
                provider_label=slot.label,
                wait_seconds=self._retry_wait_seconds(e),
                error=self._short_error(e),
                retryable=retryable,
                provider_disabled=provider_disabled,
            )

        return ChunkWorkResult(chunk=chunk, recipes=response.recipes if response else [], provider_label=slot.label)

    def _existing_recipe_for_book_chunk(self, recipe: Recipe, book: UploadedBook) -> RecipeModel | None:
        source = recipe.source or ""
        linked_to_book = RecipeModel.extras.any(
            sa.and_(
                ApiExtras.key_name == "uploadedBookSourceId",
                ApiExtras.value == str(book.id),
            )
        )
        query = (
            sa.select(RecipeModel)
            .where(
                RecipeModel.group_id == self.user.group_id,
                sa.func.lower(RecipeModel.name) == recipe.name.lower(),
                sa.or_(
                    linked_to_book,
                    sa.func.lower(sa.func.coalesce(RecipeModel.source, "")) == source.lower(),
                    sa.func.lower(sa.func.coalesce(RecipeModel.source, "")).startswith(
                        book.name.lower(), autoescape=True
                    ),
                ),
            )
            .limit(1)
        )
        return self.repos.session.execute(query).scalars().one_or_none()

    def _recipe_with_book_source(self, recipe: OpenAIRecipe, book: UploadedBook, chunk: BookTextChunk) -> OpenAIRecipe:
        explicit_start, explicit_end = parse_book_source_page_range(recipe.source)
        if explicit_start is not None and not chunk.start_page <= explicit_start <= chunk.end_page:
            explicit_start = None
            explicit_end = None
        page_start = explicit_start or chunk.start_page
        page_end = explicit_end or page_start
        page_label = (
            str(page_start)
            if page_start == page_end
            else f"{page_start}-{page_end}"
        )
        source = f"{book.name}, pages {page_label}"
        created_by = recipe.created_by or book.name
        categories = recipe.categories or ["מתכונים מספרי בישול"]
        tags = recipe.tags or [book.name]
        return recipe.model_copy(
            update={
                "source": source,
                "created_by": created_by,
                "categories": categories,
                "tags": tags,
            }
        )

    def _save_openai_recipe(
        self,
        openai_recipe: OpenAIRecipe,
        book: UploadedBook,
        chunk: BookTextChunk,
        allow_duplicate_recipes: bool = False,
    ) -> Recipe | None:
        if not self.openai_recipe_service._has_minimum_recipe_data(openai_recipe):
            return None

        recipe = self.openai_recipe_service._convert_recipe(self._recipe_with_book_source(openai_recipe, book, chunk))
        recipe = self.recipe_service.apply_ai_recipe_attribution(recipe)
        recipe = self.recipe_service._apply_primary_library_membership(recipe, "book")
        page_start, page_end = parse_book_source_page_range(recipe.source, chunk.start_page, chunk.end_page)
        recipe.extras = {
            **(recipe.extras or {}),
            "uploadedBookSourceId": str(book.id),
            "uploadedBookSourcePageStart": page_start,
            "uploadedBookSourcePageEnd": page_end,
        }

        if not allow_duplicate_recipes and self._existing_recipe_for_book_chunk(recipe, book):
            return None

        try:
            return self.recipe_service.create_one(recipe)
        except sqlalchemy.exc.IntegrityError:
            self.repos.session.rollback()
            recipe.name = f"{recipe.name} ({book.name} {chunk.start_page}-{chunk.end_page})"
            recipe.slug = create_recipe_slug(recipe.name)
            return self.recipe_service.create_one(recipe)
        except Exception as e:
            self.repos.session.rollback()
            self.logger.error(f"Failed to save extracted recipe '{recipe.name}' from uploaded book '{book.name}'")
            self.logger.exception(e)
            return None

    def _recipes_extracted_from_book(self, book: UploadedBook) -> list[Recipe]:
        linked_to_book = RecipeModel.extras.any(
            sa.and_(
                ApiExtras.key_name == "uploadedBookSourceId",
                ApiExtras.value == str(book.id),
            )
        )
        slugs = self.repos.session.execute(
            sa.select(RecipeModel.slug).where(
                RecipeModel.group_id == self.user.group_id,
                RecipeModel.household_id == self.user.household_id,
                sa.or_(
                    linked_to_book,
                    sa.func.lower(sa.func.coalesce(RecipeModel.source, "")).startswith(
                        book.name.lower(), autoescape=True
                    ),
                ),
            )
        ).scalars().unique()
        recipes: list[Recipe] = []
        for slug in slugs:
            try:
                recipes.append(self.recipe_service.get_one(slug))
            except Exception:
                self.logger.exception("Failed to load extracted recipe '%s' for enrichment", slug)
        return recipes

    @staticmethod
    def _shopping_list_extras(shopping_list) -> dict:
        extras = getattr(shopping_list, "extras", None)
        return extras if isinstance(extras, dict) else {}

    def _existing_book_recipe_shopping_list(
        self,
        shopping_service: ShoppingListService,
        book: UploadedBook,
        recipe: Recipe,
    ):
        matching_list_id = self.repos.session.execute(
            sa.select(ShoppingListExtras.shopping_list_id)
            .join(ShoppingList, ShoppingList.id == ShoppingListExtras.shopping_list_id)
            .where(
                ShoppingList.group_id == self.user.group_id,
                ShoppingListExtras.key_name == "aiCreatedFromUploadedBookId",
                ShoppingListExtras.value == str(book.id),
                sa.exists(
                    sa.select(ShoppingListExtras.id).where(
                        ShoppingListExtras.shopping_list_id == ShoppingList.id,
                        ShoppingListExtras.key_name == "aiCreatedFromRecipeId",
                        ShoppingListExtras.value == str(recipe.id),
                    )
                ),
            )
            .limit(1)
        ).scalar_one_or_none()
        return shopping_service.shopping_lists.get_one(matching_list_id) if matching_list_id else None

    def _unique_shopping_list_name(self, shopping_service: ShoppingListService, base_name: str) -> str:
        return shopping_service.available_unique_list_name(base_name.strip() or "רשימת קניות")

    async def _ensure_book_recipe_shopping_list(
        self,
        book: UploadedBook,
        recipe: Recipe,
        organize_with_ai: bool,
        include_ai_tips: bool,
        include_item_images: bool,
        provider_slots: list[ProviderSlot] | None = None,
        provider_cursor: list[int] | None = None,
        target_language: str | None = None,
    ) -> bool:
        shopping_service = ShoppingListService(self.repos)
        existing = self._existing_book_recipe_shopping_list(shopping_service, book, recipe)
        if existing:
            shopping_list = existing
            if organize_with_ai and shopping_list.list_items and str(
                self._shopping_list_extras(shopping_list).get(ShoppingListService.AI_ORGANIZED_EXTRA_KEY, "")
            ).lower() != "true":
                shopping_list = await self._organize_shopping_list_with_slots(
                    shopping_service,
                    shopping_list.id,
                    include_ai_tips,
                    provider_slots,
                    provider_cursor,
                    target_language,
                )
            if include_item_images:
                await ItemImageService(self.user.group_id, self.repos).ensure_shopping_list_images(shopping_list)
            return True

        shopping_list = shopping_service.create_one_list(
            ShoppingListCreate(
                name=self._unique_shopping_list_name(shopping_service, recipe.name or recipe.slug),
                extras={
                    "aiCreatedFromUploadedBook": True,
                    "aiCreatedFromUploadedBookId": str(book.id),
                    "aiCreatedFromRecipeId": str(recipe.id),
                    "aiCreatedFromRecipeSlug": recipe.slug,
                },
            ),
            self.user.id,
        )
        if not shopping_list:
            return False

        shopping_list, _items = shopping_service.add_recipe_ingredients_to_list(
            shopping_list.id,
            [
                ShoppingListAddRecipeParamsBulk(
                    recipe_id=recipe.id,
                    recipe_increment_quantity=1,
                    recipe_ingredients=recipe.recipe_ingredient or None,
                )
            ],
        )
        if organize_with_ai:
            shopping_list = await self._organize_shopping_list_with_slots(
                shopping_service,
                shopping_list.id,
                include_ai_tips,
                provider_slots,
                provider_cursor,
                target_language,
            )
        if include_item_images:
            await ItemImageService(self.user.group_id, self.repos).ensure_shopping_list_images(shopping_list)
        return True

    async def _organize_shopping_list_with_slots(
        self,
        shopping_service: ShoppingListService,
        shopping_list_id: UUID4,
        include_ai_tips: bool,
        provider_slots: list[ProviderSlot] | None,
        provider_cursor: list[int] | None,
        target_language: str | None = None,
    ):
        if not provider_slots or provider_cursor is None:
            shopping_list, _items = await shopping_service.organize_with_ai(
                shopping_list_id,
                include_ai_tips=include_ai_tips,
                target_language=target_language,
            )
            return shopping_list

        last_error: Exception | None = None
        for _attempt in range(max(len(provider_slots) * 2, 1)):
            enabled_slots = [slot for slot in provider_slots if not slot.disabled]
            if not enabled_slots:
                break
            slot = enabled_slots[provider_cursor[0] % len(enabled_slots)]
            provider_cursor[0] += 1
            try:
                shopping_list, _items = await shopping_service.organize_with_ai(
                    shopping_list_id,
                    include_ai_tips=include_ai_tips,
                    provider=slot.provider,
                    target_language=target_language,
                )
                return shopping_list
            except Exception as error:
                last_error = error
                if self._is_provider_disabled_error(error):
                    slot.disabled = True
                    slot.disabled_reason = self._short_error(error)
                    continue
                if self._is_retryable_error(error):
                    continue
                raise

        if last_error:
            raise last_error
        raise RuntimeError("No usable AI provider keys remain for shopping-list organization")

    async def enrich_book_recipes(
        self,
        book: UploadedBook,
        *,
        recipes: list[Recipe] | None = None,
        auto_recipe_images: bool = True,
        include_item_images: bool = True,
        include_ai_tips: bool = True,
        create_shopping_lists: bool = True,
        organize_shopping_lists_with_ai: bool = True,
        allow_duplicate_recipes: bool = False,
    ) -> dict:
        recipes = recipes if recipes is not None else self._recipes_extracted_from_book(book)
        stats = {
            "recipes": len(recipes),
            "recipe_images_created": 0,
            "recipe_images_failed": 0,
            "item_images_created": 0,
            "item_images_existing": 0,
            "item_images_failed": 0,
            "shopping_lists_created_or_existing": 0,
            "shopping_lists_failed": 0,
        }
        item_image_service = ItemImageService(self.user.group_id, self.repos) if include_item_images else None
        provider_slots: list[ProviderSlot] | None = None
        provider_cursor: list[int] | None = None
        if create_shopping_lists and organize_shopping_lists_with_ai:
            openai_service = OpenAIService(self.repos)
            provider_slots = self._provider_slots(openai_service)
            provider_cursor = [0]

        if item_image_service:
            try:
                result = await item_image_service.ensure_recipes_images(recipes)
                stats["item_images_created"] += result.created
                stats["item_images_existing"] += result.existing
                stats["item_images_failed"] += result.failed
                if result.failed == 0:
                    for recipe in recipes:
                        recipe.extras = {
                            **(recipe.extras or {}),
                            "itemImagesEnsured": True,
                            "itemImagesEnsuredAt": datetime.now(UTC).isoformat(),
                        }
                        self.recipe_service.update_one(recipe.slug, recipe)
            except Exception:
                stats["item_images_failed"] += 1
                self.logger.exception("Failed to add item images to recipes extracted from '%s'", book.name)

        for recipe in recipes:
            if auto_recipe_images and not recipe.image:
                try:
                    image_created = await self.recipe_service.attach_best_effort_image(
                        recipe,
                        search_queries=[
                            recipe.name,
                            f"{book.name} {recipe.name}",
                            f"{recipe.name} plated dish",
                        ],
                    )
                    stats["recipe_images_created" if image_created else "recipe_images_failed"] += 1
                except Exception:
                    stats["recipe_images_failed"] += 1
                    self.logger.exception("Failed to add an image to extracted recipe '%s'", recipe.name)

            if create_shopping_lists:
                try:
                    if await self._ensure_book_recipe_shopping_list(
                        book,
                        recipe,
                        organize_shopping_lists_with_ai,
                        include_ai_tips,
                        include_item_images,
                        provider_slots,
                        provider_cursor,
                        getattr(book, "extraction_translate_language", None),
                    ):
                        stats["shopping_lists_created_or_existing"] += 1
                    else:
                        stats["shopping_lists_failed"] += 1
                except Exception:
                    self.repos.session.rollback()
                    stats["shopping_lists_failed"] += 1
                    self.logger.exception("Failed to create a shopping list for extracted recipe '%s'", recipe.name)

        self._update_book_metadata(
            book,
            extraction_enrichment={
                **stats,
                "completed_at": datetime.now(UTC).isoformat(),
            },
        )
        return stats

    def _candidate_chunk(
        self,
        pages: list[BookTextPage],
        candidate: dict,
        index: int,
    ) -> BookTextChunk:
        requested_start = int(candidate.get("page_start") or 1)
        requested_end = int(candidate.get("page_end") or requested_start)
        title_key = self._catalog_text_key(candidate.get("source_title") or candidate.get("title"))
        title_tokens = [token for token in title_key.split() if len(token) > 2]
        located_start: int | None = None
        if title_tokens:
            for page in pages:
                page_key = self._catalog_text_key(page.text[:5000])
                if title_key and title_key in page_key:
                    located_start = page.number
                    break
                matched_tokens = sum(token in page_key for token in title_tokens)
                if len(title_tokens) >= 2 and matched_tokens >= min(3, len(title_tokens)):
                    located_start = page.number
                    break

        start_page = located_start or requested_start
        requested_span = max(0, min(requested_end - requested_start, 12))
        end_page = start_page + requested_span
        selected_pages = [page for page in pages if start_page <= page.number <= end_page]
        if not selected_pages:
            selected_pages = sorted(pages, key=lambda page: abs(page.number - start_page))[:1]
        if not selected_pages:
            raise ValueError(f"No source page was found for '{candidate.get('title')}'")

        selected_pages.sort(key=lambda page: page.number)
        text = "\n\n".join(f"[Page {page.number}]\n{page.text}" for page in selected_pages)
        return BookTextChunk(
            index=index,
            start_page=selected_pages[0].number,
            end_page=selected_pages[-1].number,
            page_numbers=[page.number for page in selected_pages],
            text=text[: self.MAX_AI_CHARS],
        )

    async def extract_selected_recipes(
        self,
        book_id: UUID4,
        uploaded_books_root: Path,
        candidate_ids: list[str],
        target_language: str = "Hebrew",
        auto_recipe_images: bool = True,
        include_item_images: bool = True,
        include_ai_tips: bool = True,
        create_shopping_lists: bool = True,
        organize_shopping_lists_with_ai: bool = True,
        allow_duplicate_recipes: bool = False,
    ) -> None:
        if not await self._claim_job("selective_extraction", book_id):
            self.logger.info("Selective extraction job %s is already running", book_id)
            return

        requested_book: UploadedBook | None = None
        try:
            requested_book = self._get_book(book_id)
            book = self._catalog_source_book(requested_book)
            metadata = self._book_metadata(book)
            catalog = [
                candidate
                for candidate in metadata.get("recipe_catalog_candidates", [])
                if isinstance(candidate, dict)
            ]
            selected_ids = set(candidate_ids)
            selected = [candidate for candidate in catalog if candidate.get("id") in selected_ids]
            if len(selected) != len(selected_ids):
                raise ValueError("One or more selected cookbook recipes are no longer in the current candidate list")

            path = self._book_file_path(book, uploaded_books_root)
            pages = self._extract_pages(path, book.extension)
            if not pages:
                raise ValueError("No extractable text was found in this book")

            openai_service = OpenAIService(self.repos)
            if not (openai_service.provider_settings and openai_service.provider_settings.ai_enabled):
                raise ValueError("AI provider is not configured")
            slots = self._provider_slots(openai_service)
            prompt = openai_service.get_prompt("recipes.extract-book-recipes")
            queue: asyncio.Queue[tuple[int, dict]] = asyncio.Queue()
            for index, candidate in enumerate(selected):
                queue.put_nowait((index, candidate))

            results: list[tuple[dict, ChunkWorkResult]] = []
            result_lock = asyncio.Lock()

            async def worker(slot: ProviderSlot) -> None:
                while True:
                    try:
                        chunk_index, candidate = queue.get_nowait()
                    except asyncio.QueueEmpty:
                        return
                    try:
                        chunk = self._candidate_chunk(pages, candidate, chunk_index)
                        result = await self._extract_chunk_once(
                            openai_service,
                            prompt,
                            slot,
                            book,
                            chunk,
                            target_language,
                            str(candidate.get("source_title") or candidate.get("title") or ""),
                        )
                        async with result_lock:
                            results.append((candidate, result))
                    finally:
                        queue.task_done()

            book.extraction_status = EXTRACTION_PROCESSING
            book.extraction_translate_language = target_language
            book.extraction_total_chunks = len(selected)
            book.extraction_completed_chunks = 0
            book.extraction_failed_chunks = 0
            book.extraction_recipes_found = 0
            book.extraction_recipes_created = 0
            book.extraction_error = None
            book.extraction_started_at = get_utc_now()
            book.extraction_completed_at = None
            self._save_book(book)

            worker_count = min(len(slots), len(selected))
            await asyncio.gather(*(worker(slot) for slot in slots[:worker_count]))
            pages.clear()
            created_recipes: list[Recipe] = []
            candidate_updates: dict[str, str] = {}
            errors: list[str] = []
            for candidate, result in results:
                if result.error:
                    errors.append(f"{candidate.get('title')}: {result.error}")
                    continue
                book.extraction_recipes_found += len(result.recipes)
                if not result.recipes:
                    errors.append(f"{candidate.get('title')}: no complete recipe was returned")
                    continue

                saved = self._save_openai_recipe(
                    result.recipes[0],
                    book,
                    result.chunk,
                    allow_duplicate_recipes=allow_duplicate_recipes,
                )
                if saved:
                    created_recipes.append(saved)
                    candidate_updates[str(candidate["id"])] = saved.slug
                    book.extraction_recipes_created += 1

            book.extraction_completed_chunks = len(results) - len(errors)
            book.extraction_failed_chunks = len(errors)
            book.extraction_status = EXTRACTION_COMPLETED if not errors else EXTRACTION_PARTIAL_FAILED
            book.extraction_error = "; ".join(errors)[:1000] or None
            book.extraction_completed_at = get_utc_now()

            refreshed_metadata = self._book_metadata(book)
            raw_imported_recipes = refreshed_metadata.get("recipe_catalog_imported", {})
            if not isinstance(raw_imported_recipes, dict):
                raw_imported_recipes = {}
            imported_recipes = {
                str(candidate_id): str(recipe_slug)
                for candidate_id, recipe_slug in raw_imported_recipes.items()
                if candidate_id and recipe_slug
            }
            imported_recipes.update(candidate_updates)
            for candidate in refreshed_metadata.get("recipe_catalog_candidates", []):
                if not isinstance(candidate, dict):
                    continue
                imported_slug = candidate_updates.get(str(candidate.get("id")))
                if imported_slug:
                    candidate["imported_recipe_slug"] = imported_slug
            refreshed_metadata["recipe_catalog_imported"] = imported_recipes
            refreshed_metadata["recipe_catalog_last_import_at"] = datetime.now(UTC).isoformat()
            refreshed_metadata["recipe_catalog_last_imported_ids"] = list(candidate_updates)
            book.book_metadata_json = json.dumps(refreshed_metadata, ensure_ascii=False)
            self._save_book(book)

            if created_recipes:
                await self.enrich_book_recipes(
                    book,
                    recipes=created_recipes,
                    auto_recipe_images=auto_recipe_images,
                    include_item_images=include_item_images,
                    include_ai_tips=include_ai_tips,
                    create_shopping_lists=create_shopping_lists,
                    organize_shopping_lists_with_ai=organize_shopping_lists_with_ai,
                    allow_duplicate_recipes=allow_duplicate_recipes,
                )
        except Exception as error:
            self.repos.session.rollback()
            if requested_book is not None:
                source_book = self._catalog_source_book(requested_book)
                self._set_failed(source_book, str(error))
            self.logger.exception("Selective cookbook recipe extraction failed for %s", book_id)
        finally:
            await self._release_job("selective_extraction", book_id)

    async def extract_recipes(  # noqa: C901
        self,
        book_id: UUID4,
        uploaded_books_root: Path,
        pages_per_chunk: int = 10,
        translate_language: str = "Hebrew",
        resume: bool = False,
        page_start: int | None = None,
        page_end: int | None = None,
        auto_recipe_images: bool = True,
        include_item_images: bool = True,
        include_ai_tips: bool = True,
        create_shopping_lists: bool = True,
        organize_shopping_lists_with_ai: bool = True,
        allow_duplicate_recipes: bool = False,
    ) -> None:
        if not await self._claim_job("extraction", book_id):
            self.logger.info(f"Uploaded book extraction job {book_id} is already running")
            return

        book: UploadedBook | None = None

        try:
            book = self._get_book(book_id)
            path = self._book_file_path(book, uploaded_books_root)
            if not path.exists():
                raise ValueError("Uploaded book file is missing")

            book.extraction_status = EXTRACTION_PROCESSING
            book.extraction_pages_per_chunk = pages_per_chunk
            book.extraction_translate_language = translate_language
            book.extraction_page_start = page_start
            book.extraction_page_end = page_end
            if not resume:
                book.extraction_total_chunks = 0
                book.extraction_completed_chunks = 0
                book.extraction_failed_chunks = 0
                book.extraction_retry_count = 0
                book.extraction_recipes_found = 0
                book.extraction_recipes_created = 0
                book.extraction_chunk_status = None
            book.extraction_error = None
            book.extraction_started_at = book.extraction_started_at if resume else get_utc_now()
            book.extraction_started_at = book.extraction_started_at or get_utc_now()
            book.extraction_completed_at = None
            self._save_book(book)
            self._update_book_metadata(
                book,
                extraction_options={
                    "auto_recipe_images": auto_recipe_images,
                    "include_item_images": include_item_images,
                    "include_ai_tips": include_ai_tips,
                    "create_shopping_lists": create_shopping_lists,
                    "organize_shopping_lists_with_ai": organize_shopping_lists_with_ai,
                    "allow_duplicate_recipes": allow_duplicate_recipes,
                },
            )

            pages = self._extract_pages(path, book.extension)
            if not pages:
                raise ValueError("No extractable text was found in this book")

            pages = self._filter_pages_by_range(pages, page_start, page_end)
            if not pages:
                raise ValueError("No extractable text was found in the selected page range")

            chunks = self._build_chunks(pages, pages_per_chunk, forward_overlap_pages=2)
            if not chunks:
                raise ValueError("No chunks could be created from this book")
            del pages

            chunk_states = self._initial_chunk_states(book, chunks, preserve_incomplete_attempts=resume)
            self._save_progress(book, chunk_states, EXTRACTION_PROCESSING)
            if self._is_extraction_cancelled(book):
                self._set_extraction_cancelled(book)
                return

            openai_service = OpenAIService(self.repos)
            if not (openai_service.provider_settings and openai_service.provider_settings.ai_enabled):
                raise ValueError("AI provider is not configured")

            provider_slots = self._provider_slots(openai_service)
            prompt = openai_service.get_prompt("recipes.extract-book-recipes")

            queue: asyncio.Queue[BookTextChunk] = asyncio.Queue()
            for chunk in chunks:
                if chunk_states[chunk.index].get("status") == CHUNK_COMPLETED:
                    continue
                await queue.put(chunk)

            provider_lock = asyncio.Lock()
            state_lock = asyncio.Lock()

            async def worker() -> None:
                while True:
                    if self._is_extraction_cancelled(book):
                        return

                    try:
                        chunk = queue.get_nowait()
                    except asyncio.QueueEmpty:
                        return

                    try:
                        if self._is_extraction_cancelled(book):
                            queue.task_done()
                            return

                        slot = await self._acquire_provider_slot(provider_slots, provider_lock)
                    except RuntimeError as e:
                        async with state_lock:
                            state = chunk_states[chunk.index]
                            state.update(
                                {
                                    "status": CHUNK_FAILED,
                                    "error": str(e),
                                    "provider": None,
                                    "nextRetrySeconds": None,
                                    "nextRetryAt": None,
                                }
                            )
                            self._save_progress(book, chunk_states)
                        queue.task_done()
                        continue

                    wait_seconds: int | None = None

                    try:
                        async with state_lock:
                            state = chunk_states[chunk.index]
                            attempts = self._state_int(state, "attempts") + 1
                            state.update(
                                {
                                    "status": CHUNK_PROCESSING,
                                    "attempts": attempts,
                                    "provider": slot.label,
                                    "nextRetrySeconds": None,
                                    "nextRetryAt": None,
                                }
                            )
                            self._save_progress(book, chunk_states)

                        result = await self._extract_chunk_once(
                            openai_service,
                            prompt,
                            slot,
                            book,
                            chunk,
                            translate_language,
                        )

                        if self._is_extraction_cancelled(book):
                            return

                        has_usable_provider = True
                        if result.error and result.provider_disabled:
                            await self._disable_provider_slot(slot, provider_lock, result.error)
                            has_usable_provider = await self._has_usable_provider_slot(provider_slots, provider_lock)

                        async with state_lock:
                            state = chunk_states[chunk.index]
                            attempts = self._state_int(state, "attempts")

                            if result.error:
                                if result.provider_disabled and has_usable_provider:
                                    state["attempts"] = max(attempts - 1, 0)
                                    state.update(
                                        {
                                            "status": CHUNK_RETRYING,
                                            "error": f"{result.provider_label} disabled: {result.error}",
                                            "provider": result.provider_label,
                                            "nextRetrySeconds": None,
                                            "nextRetryAt": None,
                                        }
                                    )
                                    self._save_progress(book, chunk_states)
                                    await queue.put(chunk)
                                elif result.retryable and attempts < self.MAX_CHUNK_ATTEMPTS:
                                    backoff_seconds = min(
                                        self.DEFAULT_RETRY_WAIT_SECONDS * (2 ** max(attempts - 1, 0)),
                                        self.MAX_RETRY_WAIT_SECONDS,
                                    )
                                    wait_seconds = result.wait_seconds or backoff_seconds
                                    state.update(
                                        {
                                            "status": CHUNK_RETRYING,
                                            "error": result.error,
                                            "provider": result.provider_label,
                                            "nextRetrySeconds": wait_seconds,
                                            "nextRetryAt": self._retry_at(wait_seconds),
                                        }
                                    )
                                    self._save_progress(book, chunk_states)
                                    await queue.put(chunk)
                                else:
                                    state.update(
                                        {
                                            "status": CHUNK_FAILED,
                                            "error": (
                                                f"No usable AI provider keys remain after {result.provider_label}: "
                                                f"{result.error}"
                                                if result.provider_disabled
                                                else result.error
                                            ),
                                            "provider": result.provider_label,
                                            "nextRetrySeconds": None,
                                            "nextRetryAt": None,
                                        }
                                    )
                                    self._save_progress(book, chunk_states)
                            else:
                                recipes_created = 0
                                for recipe in result.recipes:
                                    if self._save_openai_recipe(
                                        recipe,
                                        book,
                                        result.chunk,
                                        allow_duplicate_recipes=allow_duplicate_recipes,
                                    ):
                                        recipes_created += 1

                                state.update(
                                    {
                                        "status": CHUNK_COMPLETED,
                                        "recipesFound": len(result.recipes),
                                        "recipesCreated": recipes_created,
                                        "error": None,
                                        "provider": result.provider_label,
                                        "nextRetrySeconds": None,
                                        "nextRetryAt": None,
                                        "completedAt": get_utc_now().isoformat(),
                                    }
                                )
                                self._save_progress(book, chunk_states)
                    finally:
                        await self._release_provider_slot(slot, provider_lock, wait_seconds)
                        queue.task_done()

            worker_count = min(len(provider_slots), queue.qsize())
            if worker_count:
                await asyncio.gather(*(worker() for _ in range(worker_count)))

            if self._is_extraction_cancelled(book):
                self._set_extraction_cancelled(book)
                return

            failed_chunks = sum(1 for state in chunk_states.values() if state.get("status") == CHUNK_FAILED)
            await self.enrich_book_recipes(
                book,
                auto_recipe_images=auto_recipe_images,
                include_item_images=include_item_images,
                include_ai_tips=include_ai_tips,
                create_shopping_lists=create_shopping_lists,
                organize_shopping_lists_with_ai=organize_shopping_lists_with_ai,
            )
            book.extraction_status = EXTRACTION_PARTIAL_FAILED if failed_chunks else EXTRACTION_COMPLETED
            book.extraction_completed_at = get_utc_now()
            self._save_progress(book, chunk_states, book.extraction_status)

        except Exception as e:
            self.repos.session.rollback()
            self.logger.error(f"Failed to extract recipes from uploaded book {book_id}")
            self.logger.exception(e)
            if book is not None:
                if self._is_extraction_cancelled(book):
                    self._set_extraction_cancelled(book)
                else:
                    self._set_failed(book, str(e))
        finally:
            await self._release_job("extraction", book_id)


class UploadedBookTranslator(UploadedBookRecipeExtractor):
    TRANSLATED_CHUNKS_DIR = "translated-chunks"
    VISUAL_ASSET_CACHE_VERSION = 1
    VISUAL_ASSET_CACHE_DIR = "visual-assets-v1"
    VISUAL_ASSET_MANIFEST = "manifest.json"
    MAX_VISUAL_ASSETS_PER_PAGE = 24
    MAX_VISUAL_SOURCE_BYTES = 32 * 1024 * 1024
    MAX_VISUAL_SOURCE_PIXELS = 80_000_000
    MAX_VISUAL_DIMENSION = 2400
    MIN_VISUAL_DIMENSION = 64

    @classmethod
    def _store_visual_image(
        cls,
        image: Image.Image,
        target_dir: Path,
        page_number: int,
        order: int,
        kind: str,
        alt: str,
        deduplicated_files: dict[str, str],
    ) -> dict | None:
        width, height = image.size
        if width <= 0 or height <= 0 or width * height > cls.MAX_VISUAL_SOURCE_PIXELS:
            return None
        if kind != "page" and min(width, height) < cls.MIN_VISUAL_DIMENSION:
            return None

        transposed = ImageOps.exif_transpose(image)
        try:
            working = transposed.copy()
        finally:
            if transposed is not image:
                transposed.close()

        try:
            working.thumbnail(
                (cls.MAX_VISUAL_DIMENSION, cls.MAX_VISUAL_DIMENSION),
                Image.Resampling.LANCZOS,
            )
            has_alpha = "A" in working.getbands() or "transparency" in working.info
            converted = working.convert("RGBA" if has_alpha else "RGB")
            working.close()
            working = converted
            output_width, output_height = working.size
            with BytesIO() as output:
                working.save(output, format="WEBP", quality=88, method=4)
                content = output.getvalue()
        finally:
            working.close()

        content_hash = hashlib.sha256(content).hexdigest()
        file_name = deduplicated_files.get(content_hash)
        if file_name is None:
            file_name = f"page-{page_number:05d}-{order:02d}-{content_hash[:12]}.webp"
            target_path = target_dir.joinpath(file_name).resolve()
            if not target_path.is_relative_to(target_dir.resolve()):
                raise ValueError("Invalid translated book visual asset path")
            with NamedTemporaryFile(delete=False, dir=target_dir, suffix=".tmp") as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(content)
            try:
                temporary_path.replace(target_path)
            finally:
                temporary_path.unlink(missing_ok=True)
            deduplicated_files[content_hash] = file_name

        return {
            "file": file_name,
            "width": output_width,
            "height": output_height,
            "kind": "page" if kind == "page" else "image",
            "alt": re.sub(r"\s+", " ", alt or "").strip()[:240],
        }

    @classmethod
    def _store_visual_bytes(
        cls,
        content: bytes,
        target_dir: Path,
        page_number: int,
        order: int,
        kind: str,
        alt: str,
        deduplicated_files: dict[str, str],
    ) -> dict | None:
        if not content or len(content) > cls.MAX_VISUAL_SOURCE_BYTES:
            return None
        try:
            with Image.open(BytesIO(content)) as image:
                return cls._store_visual_image(
                    image,
                    target_dir,
                    page_number,
                    order,
                    kind,
                    alt,
                    deduplicated_files,
                )
        except (Image.DecompressionBombError, OSError, UnidentifiedImageError, ValueError):
            return None

    def _render_pdf_page_visual(
        self,
        source_path: Path,
        target_dir: Path,
        page_number: int,
        deduplicated_files: dict[str, str],
    ) -> dict | None:
        renderer = shutil.which("pdftoppm")
        if renderer is None:
            return None

        with TemporaryDirectory(dir=target_dir) as temporary_dir:
            output_prefix = Path(temporary_dir).joinpath("source-page")
            result = subprocess.run(
                [
                    renderer,
                    "-f",
                    str(page_number),
                    "-l",
                    str(page_number),
                    "-singlefile",
                    "-jpeg",
                    "-jpegopt",
                    "quality=88",
                    "-scale-to",
                    str(self.MAX_VISUAL_DIMENSION),
                    str(source_path),
                    str(output_prefix),
                ],
                check=False,
                capture_output=True,
                timeout=120,
            )
            rendered_path = output_prefix.with_suffix(".jpg")
            if result.returncode != 0 or not rendered_path.exists():
                return None
            try:
                with Image.open(rendered_path) as image:
                    return self._store_visual_image(
                        image,
                        target_dir,
                        page_number,
                        1,
                        "page",
                        f"Original page {page_number}",
                        deduplicated_files,
                    )
            except (Image.DecompressionBombError, OSError, UnidentifiedImageError, ValueError):
                return None

    def _extract_pdf_visual_assets(
        self,
        source_path: Path,
        page_numbers: list[int],
        source_text_by_page: dict[int, str],
        target_dir: Path,
    ) -> dict[int, list[dict]]:
        try:
            from pypdf import PdfReader
        except ImportError:
            return {}

        reader = PdfReader(str(source_path))
        assets_by_page: dict[int, list[dict]] = {}
        deduplicated_files: dict[str, str] = {}
        fallback_logged = False
        for page_number in page_numbers:
            if page_number < 1 or page_number > len(reader.pages):
                continue
            page_assets: list[dict] = []
            extraction_failed = False
            full_page_visual = False
            try:
                page = reader.pages[page_number - 1]
                page_width = float(page.mediabox.width)
                page_height = float(page.mediabox.height)
                page_aspect_ratio = page_width / page_height if page_height else 0
                for order, image_file in enumerate(page.images, start=1):
                    if order > self.MAX_VISUAL_ASSETS_PER_PAGE:
                        break
                    extracted_image = image_file.image
                    try:
                        image_width, image_height = extracted_image.size
                        image_aspect_ratio = image_width / image_height if image_height else 0
                        if (
                            max(image_width, image_height) >= 1000
                            and page_aspect_ratio
                            and abs(image_aspect_ratio - page_aspect_ratio) <= 0.03
                        ):
                            # Full-page scans often expose their color image and masks as
                            # separate PDF images. Render the composed page once instead.
                            full_page_visual = True
                            break
                        asset = self._store_visual_image(
                            extracted_image,
                            target_dir,
                            page_number,
                            order,
                            "image",
                            f"Original visual from page {page_number}",
                            deduplicated_files,
                        )
                    finally:
                        extracted_image.close()
                    if asset:
                        page_assets.append(asset)
            except Exception:
                extraction_failed = True
                if not fallback_logged:
                    self.logger.debug(
                        f"Falling back to rendered source pages for PDF {source_path.name}",
                        exc_info=True,
                    )
                    fallback_logged = True

            source_text = source_text_by_page.get(page_number, "").strip()
            if full_page_visual or extraction_failed or (not page_assets and len(source_text) < 80):
                rendered_asset = self._render_pdf_page_visual(
                    source_path,
                    target_dir,
                    page_number,
                    deduplicated_files,
                )
                if rendered_asset:
                    page_assets = [rendered_asset]
            elif len(page_assets) == 1 and len(source_text) < 500:
                page_assets[0]["kind"] = "page"

            if page_assets:
                assets_by_page[page_number] = page_assets

        return assets_by_page

    def _extract_epub_visual_assets(
        self,
        source_path: Path,
        page_numbers: list[int],
        target_dir: Path,
    ) -> dict[int, list[dict]]:
        requested_pages = set(page_numbers)
        assets_by_page: dict[int, list[dict]] = {}
        deduplicated_files: dict[str, str] = {}
        with ZipFile(source_path) as archive:
            archive_names = set(archive.namelist())
            html_files = sorted(
                name
                for name in archive_names
                if name.lower().endswith((".html", ".htm", ".xhtml")) and not name.endswith("/")
            )
            page_number = 0
            for html_name in html_files:
                document = archive.read(html_name).decode("utf-8", errors="ignore")
                soup = BeautifulSoup(document, "lxml")
                if not self._normalize_text(soup.get_text("\n")):
                    continue
                page_number += 1
                if page_number not in requested_pages:
                    continue

                page_assets: list[dict] = []
                for order, image_tag in enumerate(soup.find_all("img"), start=1):
                    if order > self.MAX_VISUAL_ASSETS_PER_PAGE:
                        break
                    source = str(image_tag.get("src") or "").strip()
                    if not source or source.startswith(("data:", "http://", "https://")):
                        continue
                    source = unquote(source.split("#", 1)[0].split("?", 1)[0])
                    archive_path = posixpath.normpath(
                        posixpath.join(posixpath.dirname(html_name), source)
                    )
                    if (
                        archive_path.startswith("../")
                        or archive_path.startswith("/")
                        or archive_path not in archive_names
                    ):
                        continue
                    archive_info = archive.getinfo(archive_path)
                    if archive_info.file_size > self.MAX_VISUAL_SOURCE_BYTES:
                        continue
                    asset = self._store_visual_bytes(
                        archive.read(archive_path),
                        target_dir,
                        page_number,
                        order,
                        "image",
                        str(image_tag.get("alt") or f"Original visual from page {page_number}"),
                        deduplicated_files,
                    )
                    if asset:
                        page_assets.append(asset)
                if page_assets:
                    assets_by_page[page_number] = page_assets

        return assets_by_page

    @staticmethod
    def _visual_asset_file_names(assets_by_page: dict[int, list[dict]]) -> set[str]:
        return {
            str(asset.get("file"))
            for assets in assets_by_page.values()
            for asset in assets
            if isinstance(asset, dict) and isinstance(asset.get("file"), str)
        }

    def _load_visual_asset_cache(
        self,
        cache_dir: Path,
        fingerprint: dict,
    ) -> dict[int, list[dict]] | None:
        manifest_path = cache_dir.joinpath(self.VISUAL_ASSET_MANIFEST)
        if not manifest_path.exists():
            return None
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError):
            return None
        if not isinstance(payload, dict) or payload.get("fingerprint") != fingerprint:
            return None
        raw_assets = payload.get("assets")
        if not isinstance(raw_assets, dict):
            return None

        assets_by_page: dict[int, list[dict]] = {}
        for raw_page, raw_page_assets in raw_assets.items():
            if not str(raw_page).isdigit() or not isinstance(raw_page_assets, list):
                return None
            page_assets: list[dict] = []
            for asset in raw_page_assets:
                if not isinstance(asset, dict):
                    return None
                file_name = asset.get("file")
                if (
                    not isinstance(file_name, str)
                    or Path(file_name).name != file_name
                    or not file_name.endswith(".webp")
                    or not cache_dir.joinpath(file_name).is_file()
                ):
                    return None
                page_assets.append(asset)
            if page_assets:
                assets_by_page[int(raw_page)] = page_assets
        return assets_by_page

    def _visual_assets_for_translation(
        self,
        source_path: Path,
        extension: str,
        page_numbers: set[int],
        source_text_by_page: dict[int, str],
        work_dir: Path,
    ) -> tuple[dict[int, list[dict]], Path | None]:
        if extension not in {".pdf", ".epub"}:
            return {}, None

        ordered_pages = sorted(page_numbers)
        source_stat = source_path.stat()
        fingerprint = {
            "version": self.VISUAL_ASSET_CACHE_VERSION,
            "sourceSize": source_stat.st_size,
            "sourceMtimeNs": source_stat.st_mtime_ns,
            "extension": extension,
            "pages": ordered_pages,
        }
        cache_dir = work_dir.joinpath(self.VISUAL_ASSET_CACHE_DIR).resolve()
        if not cache_dir.is_relative_to(work_dir.resolve()):
            raise ValueError("Invalid translated book visual cache path")
        cached_assets = self._load_visual_asset_cache(cache_dir, fingerprint)
        if cached_assets is not None:
            return cached_assets, cache_dir

        staging_dir = work_dir.joinpath(f".{self.VISUAL_ASSET_CACHE_DIR}-{uuid4().hex}.tmp").resolve()
        if not staging_dir.is_relative_to(work_dir.resolve()):
            raise ValueError("Invalid translated book visual staging path")
        staging_dir.mkdir(parents=True, exist_ok=False)
        try:
            if extension == ".pdf":
                assets_by_page = self._extract_pdf_visual_assets(
                    source_path,
                    ordered_pages,
                    source_text_by_page,
                    staging_dir,
                )
            else:
                assets_by_page = self._extract_epub_visual_assets(
                    source_path,
                    ordered_pages,
                    staging_dir,
                )

            used_files = self._visual_asset_file_names(assets_by_page)
            for asset_path in staging_dir.glob("*.webp"):
                if asset_path.name not in used_files:
                    asset_path.unlink(missing_ok=True)
            staging_dir.joinpath(self.VISUAL_ASSET_MANIFEST).write_text(
                json.dumps(
                    {
                        "fingerprint": fingerprint,
                        "assets": {str(page): assets for page, assets in assets_by_page.items()},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            backup_dir = work_dir.joinpath(f".{self.VISUAL_ASSET_CACHE_DIR}-{uuid4().hex}.old").resolve()
            if cache_dir.exists():
                cache_dir.replace(backup_dir)
            try:
                staging_dir.replace(cache_dir)
            except Exception:
                if backup_dir.exists() and not cache_dir.exists():
                    backup_dir.replace(cache_dir)
                raise
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            return assets_by_page, cache_dir
        finally:
            if staging_dir.exists():
                shutil.rmtree(staging_dir)

    def _set_translation_failed(self, book: UploadedBook, error: str) -> None:
        book.translation_status = TRANSLATION_FAILED
        book.translation_error = error[:1000]
        book.translation_completed_at = get_utc_now()
        self._save_book(book)

    def _load_translation_chunk_states(self, book: UploadedBook) -> dict[str, dict]:
        if not book.translation_chunk_status:
            return {}

        try:
            payload = json.loads(book.translation_chunk_status)
        except (TypeError, ValueError):
            return {}

        if not isinstance(payload, list):
            return {}

        states: dict[str, dict] = {}
        for item in payload:
            if not isinstance(item, dict):
                continue
            range_key = item.get("range")
            if isinstance(range_key, str):
                states[range_key] = item

        return states

    def _initial_translation_chunk_states(
        self, book: UploadedBook, chunks: list[BookTextChunk], preserve_incomplete_attempts: bool = False
    ) -> dict[int, dict]:
        existing_states = self._load_translation_chunk_states(book)
        states: dict[int, dict] = {}

        for chunk in chunks:
            range_key = self._chunk_range_key(chunk)
            previous = existing_states.get(range_key)
            if previous and previous.get("status") == CHUNK_COMPLETED and previous.get("translatedChunkFile"):
                states[chunk.index] = {
                    **previous,
                    "index": chunk.index,
                    "range": range_key,
                    "startPage": chunk.start_page,
                    "endPage": chunk.end_page,
                    "status": CHUNK_COMPLETED,
                }
                continue

            if previous and preserve_incomplete_attempts:
                states[chunk.index] = {
                    **previous,
                    "index": chunk.index,
                    "range": range_key,
                    "startPage": chunk.start_page,
                    "endPage": chunk.end_page,
                    "status": CHUNK_PENDING,
                    "previousAttempts": self._state_int(previous, "attempts"),
                    "attempts": 0,
                    "translatedChunkFile": previous.get("translatedChunkFile"),
                    "nextRetrySeconds": None,
                    "nextRetryAt": None,
                }
                continue

            states[chunk.index] = {
                "index": chunk.index,
                "range": range_key,
                "startPage": chunk.start_page,
                "endPage": chunk.end_page,
                "status": CHUNK_PENDING,
                "attempts": 0,
                "pagesTranslated": 0,
                "translatedChunkFile": None,
                "error": None,
                "provider": None,
                "nextRetrySeconds": None,
                "nextRetryAt": None,
            }

        return states

    def _save_translation_progress(
        self,
        book: UploadedBook,
        states: dict[int, dict],
        status: str | None = None,
    ) -> None:
        if status != TRANSLATION_CANCELLED and self._is_translation_cancelled(book):
            self._set_translation_cancelled(book)
            return

        state_values = list(states.values())
        book.translation_total_chunks = len(state_values)
        book.translation_completed_chunks = sum(1 for state in state_values if state.get("status") == CHUNK_COMPLETED)
        book.translation_failed_chunks = sum(1 for state in state_values if state.get("status") == CHUNK_FAILED)
        book.translation_retry_count = sum(max(self._state_int(state, "attempts") - 1, 0) for state in state_values)
        book.translation_chunk_status = json.dumps(
            sorted(state_values, key=lambda item: self._state_int(item, "index")),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        book.translation_error = self._chunk_error_summary(states)

        if status:
            book.translation_status = status
        elif any(state.get("status") == CHUNK_RETRYING for state in state_values):
            book.translation_status = TRANSLATION_RETRYING
        else:
            book.translation_status = TRANSLATION_PROCESSING

        self._save_book(book)

    @staticmethod
    def _safe_language_key(target_language: str) -> str:
        language = target_language.strip().lower()
        language = re.sub(r"[^a-z0-9\u0590-\u05ff]+", "-", language)
        return language.strip("-") or "translated"

    def _translated_chunks_dir(self, uploaded_books_root: Path, book: UploadedBook, target_language: str) -> Path:
        root = uploaded_books_root.joinpath(str(book.group_id)).resolve()
        work_dir = root.joinpath(str(book.id), self.TRANSLATED_CHUNKS_DIR, self._safe_language_key(target_language))
        work_dir = work_dir.resolve()
        if not work_dir.is_relative_to(root):
            raise ValueError("Invalid translated chunks path")
        work_dir.mkdir(parents=True, exist_ok=True)
        return work_dir

    def _reset_translated_chunks_dir(self, uploaded_books_root: Path, book: UploadedBook, target_language: str) -> Path:
        work_dir = self._translated_chunks_dir(uploaded_books_root, book, target_language)
        for path in work_dir.glob("chunk-*.json"):
            path.unlink(missing_ok=True)
        return work_dir

    @staticmethod
    def _translated_chunk_file_name(chunk: BookTextChunk) -> str:
        return f"chunk-{chunk.index + 1:05d}.json"

    def _write_translated_chunk(
        self,
        work_dir: Path,
        chunk: BookTextChunk,
        pages: dict[int, str],
        page_metadata: dict[int, dict] | None = None,
    ) -> str:
        file_name = self._translated_chunk_file_name(chunk)
        page_metadata = page_metadata or {}
        expected_pages = set(chunk.page_numbers)
        payload = {
            "chunk": chunk.index,
            "startPage": chunk.start_page,
            "endPage": chunk.end_page,
            "pages": [
                {
                    "page": page,
                    "text": text,
                    **page_metadata.get(page, {}),
                }
                for page, text in sorted(pages.items())
                if page in expected_pages
            ],
        }
        work_dir.joinpath(file_name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return file_name

    def _read_translated_chunk_records(self, work_dir: Path, file_name: str) -> list[dict]:
        path = work_dir.joinpath(file_name).resolve()
        if not path.is_relative_to(work_dir.resolve()):
            raise ValueError("Invalid translated chunk file path")
        payload = json.loads(path.read_text(encoding="utf-8"))
        pages = payload.get("pages") if isinstance(payload, dict) else None
        if not isinstance(pages, list):
            return []

        translated_pages: list[dict] = []
        for page in pages:
            if not isinstance(page, dict):
                continue
            page_number = page.get("page")
            text = page.get("text")
            if isinstance(page_number, int) and isinstance(text, str):
                translated_pages.append(
                    {
                        "page": page_number,
                        "text": text,
                        "title": page.get("title") if isinstance(page.get("title"), str) else None,
                        "entryType": page.get("entryType") if isinstance(page.get("entryType"), str) else "page",
                        "parentTitle": page.get("parentTitle") if isinstance(page.get("parentTitle"), str) else None,
                        "includeInContents": bool(page.get("includeInContents", False)),
                    }
                )

        return translated_pages

    def _read_translated_chunk_pages(self, work_dir: Path, file_name: str) -> list[tuple[int, str]]:
        return [(record["page"], record["text"]) for record in self._read_translated_chunk_records(work_dir, file_name)]

    def _merge_partial_translation_result(
        self,
        work_dir: Path,
        result: ChunkTranslationResult,
        previous_file: str | None,
    ) -> tuple[str | None, int]:
        expected_pages = set(result.chunk.page_numbers)
        source_pages = self._source_pages_from_chunk(result.chunk)
        merged_pages: dict[int, str] = {}
        merged_metadata: dict[int, dict] = {}

        if previous_file:
            try:
                previous_records = self._read_translated_chunk_records(work_dir, previous_file)
            except (OSError, TypeError, ValueError):
                previous_records = []
            for record in previous_records:
                page_number = record["page"]
                if page_number not in expected_pages:
                    continue
                if self._translation_page_issue(
                    page_number,
                    source_pages.get(page_number, ""),
                    record["text"],
                ):
                    continue
                merged_pages[page_number] = record["text"]
                merged_metadata[page_number] = {
                    "title": record.get("title"),
                    "entryType": record.get("entryType", "page"),
                    "parentTitle": record.get("parentTitle"),
                    "includeInContents": bool(record.get("includeInContents", False)),
                }

        result_metadata = result.page_metadata or {}
        for page_number, translated_text in result.pages.items():
            if page_number not in expected_pages:
                continue
            if self._translation_page_issue(
                page_number,
                source_pages.get(page_number, ""),
                translated_text,
            ):
                continue
            merged_pages[page_number] = translated_text
            merged_metadata[page_number] = result_metadata.get(page_number, {})

        if not merged_pages:
            return None, 0

        file_name = self._write_translated_chunk(
            work_dir,
            result.chunk,
            merged_pages,
            merged_metadata,
        )
        return file_name, len(merged_pages)

    def _translation_message(self, book: UploadedBook, chunk: BookTextChunk, target_language: str) -> str:
        return (
            f"Cookbook title: {book.name}\n"
            f"Original file name: {book.original_file_name}\n"
            f"Page range: {chunk.start_page}-{chunk.end_page}\n"
            f"Target language: {target_language}\n\n"
            "Translate the following cookbook pages:\n"
            f"{chunk.text}"
        )

    async def _translate_chunk_once(
        self,
        openai_service: OpenAIService,
        prompt: str,
        slot: ProviderSlot,
        book: UploadedBook,
        chunk: BookTextChunk,
        target_language: str,
    ) -> ChunkTranslationResult:
        try:
            response = await openai_service.get_response(
                prompt,
                self._translation_message(book, chunk, target_language),
                response_schema=OpenAIBookTranslationChunkParse,
                provider=slot.provider,
            )
        except Exception as e:
            provider_disabled = self._is_provider_disabled_error(e)
            retryable = False if provider_disabled else self._is_retryable_error(e)
            if provider_disabled:
                self.logger.warning(
                    f"Disabling AI provider slot {slot.label} after translation error "
                    f"for book chunk {chunk.index + 1}: {e}"
                )
            elif retryable:
                self.logger.warning(
                    f"Retryable AI translation error for book chunk {chunk.index + 1} using {slot.label}: {e}"
                )
            else:
                self.logger.error(f"Failed to translate book chunk {chunk.index + 1}")
                self.logger.exception(e)

            return ChunkTranslationResult(
                chunk=chunk,
                pages={},
                provider_label=slot.label,
                wait_seconds=self._retry_wait_seconds(e),
                error=self._short_error(e),
                retryable=retryable,
                provider_disabled=provider_disabled,
            )

        expected_pages = set(chunk.page_numbers)
        pages = {
            page.page: page.text
            for page in (response.pages if response else [])
            if page.page in expected_pages
        }
        page_metadata = {
            page.page: {
                "title": page.title.strip() if page.title else None,
                "entryType": page.entry_type.strip().lower() or "page",
                "parentTitle": page.parent_title.strip() if page.parent_title else None,
                "includeInContents": page.include_in_contents,
            }
            for page in (response.pages if response else [])
            if page.page in expected_pages
        }
        if not expected_pages.issubset(set(pages)):
            missing = ", ".join(str(page) for page in sorted(expected_pages - set(pages))[:10])
            return ChunkTranslationResult(
                chunk=chunk,
                pages=pages,
                provider_label=slot.label,
                page_metadata=page_metadata,
                error=f"AI translation response is missing page(s): {missing}",
                retryable=True,
                wait_seconds=None,
            )

        source_pages = self._source_pages_from_chunk(chunk)
        suspicious_pages = [
            (page_number, issue)
            for page_number in chunk.page_numbers
            if (
                issue := self._translation_page_issue(
                    page_number,
                    source_pages.get(page_number, ""),
                    pages.get(page_number, ""),
                )
            )
        ]
        if suspicious_pages:
            try:
                for page_number, _issue in suspicious_pages:
                    repaired_page = await self._repair_translation_page(
                        openai_service,
                        prompt,
                        slot,
                        book,
                        page_number,
                        source_pages.get(page_number, ""),
                        target_language,
                    )
                    if repaired_page is not None:
                        pages[page_number] = repaired_page
            except Exception as e:
                provider_disabled = self._is_provider_disabled_error(e)
                return ChunkTranslationResult(
                    chunk=chunk,
                    pages=pages,
                    provider_label=slot.label,
                    page_metadata=page_metadata,
                    wait_seconds=self._retry_wait_seconds(e),
                    error=self._short_error(e),
                    retryable=not provider_disabled,
                    provider_disabled=provider_disabled,
                )

            remaining_issues = [
                issue
                for page_number, _issue in suspicious_pages
                if (
                    issue := self._translation_page_issue(
                        page_number,
                        source_pages.get(page_number, ""),
                        pages.get(page_number, ""),
                    )
                )
            ]
            if remaining_issues:
                return ChunkTranslationResult(
                    chunk=chunk,
                    pages=pages,
                    provider_label=slot.label,
                    page_metadata=page_metadata,
                    error="AI translation completeness check failed: " + "; ".join(remaining_issues[:6]),
                    retryable=True,
                    wait_seconds=None,
                )

        return ChunkTranslationResult(
            chunk=chunk,
            pages=pages,
            provider_label=slot.label,
            page_metadata=page_metadata,
        )

    async def _repair_translation_page(
        self,
        openai_service: OpenAIService,
        prompt: str,
        slot: ProviderSlot,
        book: UploadedBook,
        page_number: int,
        source_text: str,
        target_language: str,
    ) -> str | None:
        repair_prompt = (
            prompt
            + "\n\nThis is a completeness repair for one page that was shortened or omitted previously. "
            "Translate the entire page line by line. Preserve every paragraph, caption, credit, list item and number. "
            "Do not summarize even if the page is legal text, an index, a caption page, or fragmented OCR."
        )
        message = (
            f"Cookbook title: {book.name}\n"
            f"Original file name: {book.original_file_name}\n"
            f"Page range: {page_number}-{page_number}\n"
            f"Target language: {target_language}\n\n"
            f"Translate this single cookbook page completely:\n[Page {page_number}]\n{source_text}"
        )
        response = await openai_service.get_response(
            repair_prompt,
            message,
            response_schema=OpenAIBookTranslationChunkParse,
            provider=slot.provider,
        )
        if not response:
            return None
        return next((page.text for page in response.pages if page.page == page_number), None)

    @staticmethod
    def _source_pages_from_chunk(chunk: BookTextChunk) -> dict[int, str]:
        matches = list(re.finditer(r"(?m)^\[Page (\d+)\]\n", chunk.text))
        pages: dict[int, str] = {}
        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(chunk.text)
            page_number = int(match.group(1))
            if page_number in chunk.page_numbers:
                pages[page_number] = chunk.text[start:end].strip()
        return pages

    @staticmethod
    def _translation_text_metrics(text: str) -> tuple[str, int, list[str]]:
        normalized = re.sub(r"\s+", " ", text or "").strip()
        words = re.findall(r"[^\W\d_]{2,}", normalized, flags=re.UNICODE)
        numbers = [
            re.sub(r"[.,]", "", number)
            for number in re.findall(r"(?<!\w)\d+(?:[.,]\d+)?", normalized)
        ]
        return normalized, len(words), numbers

    @classmethod
    def _translation_page_issue(cls, page_number: int, source: str, translated: str) -> str | None:
        source_text, source_word_count, source_numbers = cls._translation_text_metrics(source)
        translated_text, translated_word_count, translated_numbers = cls._translation_text_metrics(translated)
        source_blocks = [block for block in re.split(r"\n\s*\n", source or "") if block.strip()]
        translated_blocks = [block for block in re.split(r"\n\s*\n", translated or "") if block.strip()]
        source_list_items = sum(
            1 for line in (source or "").splitlines() if re.match(r"^\s*(?:[-*•]|\d+[.)])\s+", line)
        )
        translated_list_items = sum(
            1 for line in (translated or "").splitlines() if re.match(r"^\s*(?:[-*•]|\d+[.)])\s+", line)
        )

        # Empty scans, decorative pages, and OCR fragments are allowed to stay empty.
        if source_word_count < 8 or len(source_text) < 45:
            return None
        if translated_word_count < 4 or len(translated_text) < 20:
            return f"page {page_number} is empty or nearly empty"

        length_ratio = len(translated_text) / max(len(source_text), 1)
        word_ratio = translated_word_count / max(source_word_count, 1)
        if length_ratio < 0.32 and word_ratio < 0.38:
            return f"page {page_number} is suspiciously short ({length_ratio:.0%} of source text)"
        if len(source_blocks) >= 4 and len(translated_blocks) / len(source_blocks) < 0.35:
            return f"page {page_number} lost paragraph structure"
        if source_list_items >= 4 and translated_list_items / source_list_items < 0.5:
            return f"page {page_number} lost list or instruction items"

        unique_source_numbers = set(source_numbers)
        if len(unique_source_numbers) >= 4:
            translated_number_set = set(translated_numbers)
            retained = len(unique_source_numbers & translated_number_set) / len(unique_source_numbers)
            if retained < 0.55:
                return f"page {page_number} lost too many numbers or quantities ({retained:.0%} retained)"

        return None

    def _audit_translated_pages(
        self,
        chunks: list[BookTextChunk],
        translated_pages: list[tuple[int, str]],
        *,
        allow_partial_pages: bool = False,
    ) -> dict:
        source_pages: dict[int, str] = {}
        expected_pages: set[int] = set()
        for chunk in chunks:
            expected_pages.update(chunk.page_numbers)
            source_pages.update(self._source_pages_from_chunk(chunk))

        translated_page_map = dict(translated_pages)
        missing_pages = sorted(expected_pages - set(translated_page_map))
        unexpected_pages = sorted(set(translated_page_map) - expected_pages)
        suspicious_pages: list[str] = []
        suspicious_page_numbers: list[int] = []
        for page_number in sorted(expected_pages):
            if page_number not in translated_page_map and allow_partial_pages:
                continue
            issue = self._translation_page_issue(
                page_number,
                source_pages.get(page_number, ""),
                translated_page_map.get(page_number, ""),
            )
            if issue:
                suspicious_pages.append(issue)
                suspicious_page_numbers.append(page_number)
        verified_translated_pages = max(
            0,
            len(expected_pages & set(translated_page_map)) - len(suspicious_page_numbers),
        )
        audit = {
            "version": 1,
            "source_pages": len(expected_pages),
            "translated_pages": len(translated_page_map),
            "verified_translated_pages": verified_translated_pages,
            "missing_pages": missing_pages,
            "unexpected_pages": unexpected_pages,
            "suspicious_pages": suspicious_pages,
            "suspicious_page_numbers": suspicious_page_numbers,
            "partial": bool(missing_pages or unexpected_pages or suspicious_pages),
            "passed": not missing_pages and not unexpected_pages and not suspicious_pages,
        }
        if not audit["passed"] and not allow_partial_pages:
            details = []
            if missing_pages:
                details.append(f"missing pages: {', '.join(map(str, missing_pages[:12]))}")
            if unexpected_pages:
                details.append(f"unexpected pages: {', '.join(map(str, unexpected_pages[:12]))}")
            if suspicious_pages:
                details.append("; ".join(suspicious_pages[:8]))
            raise ValueError("Translated book completeness audit failed: " + " | ".join(details))
        return audit

    @staticmethod
    def _is_rtl_language(target_language: str) -> bool:
        language = target_language.lower()
        rtl_markers = ("hebrew", "עברית", "arabic", "ערבית", "farsi", "persian", "urdu", "yiddish")
        return any(marker in language for marker in rtl_markers)

    @staticmethod
    def _translated_page_heading(text: str, page_number: int, rtl: bool) -> str:
        ignored = {
            "white heat",
            "basics",
            "contents",
            "table of contents",
            "תוכן עניינים",
            "יסודות",
        }
        for raw_line in (text or "").splitlines()[:14]:
            line = re.sub(r"\s+", " ", raw_line).strip(" -–—|:.;")
            if not line or line.casefold() in ignored or len(line) > 105:
                continue
            if len(re.findall(r"[^\W\d_]{2,}", line, flags=re.UNICODE)) < 2:
                continue
            return line
        return f"עמוד {page_number}" if rtl else f"Page {page_number}"

    @staticmethod
    def _translated_page_record(value: dict | tuple[int, str], rtl: bool) -> dict:
        if isinstance(value, dict):
            page_number = int(value.get("page", 0))
            text = str(value.get("text") or "")
            title = str(value.get("title") or "").strip()
            entry_type = str(value.get("entryType") or "page").strip().lower()
            parent_title = str(value.get("parentTitle") or "").strip()
            include_in_contents = bool(value.get("includeInContents", False))
            is_translated = bool(value.get("isTranslated", True))
            visual_assets = value.get("visualAssets") if isinstance(value.get("visualAssets"), list) else []
        else:
            page_number, text = value
            title = ""
            entry_type = "page"
            parent_title = ""
            include_in_contents = False
            is_translated = True
            visual_assets = []

        fallback = UploadedBookTranslator._translated_page_heading(text, page_number, rtl)
        generic_titles = {
            f"page {page_number}".casefold(),
            f"עמוד {page_number}".casefold(),
            "page",
            "עמוד",
        }
        if title.casefold() in generic_titles:
            title = ""
        return {
            "page": page_number,
            "text": text,
            "title": title or fallback,
            "explicitTitle": title,
            "entryType": entry_type,
            "parentTitle": parent_title,
            "includeInContents": include_in_contents,
            "isTranslated": is_translated,
            "visualAssets": visual_assets,
        }

    @staticmethod
    def _roman_page_number(value: str) -> int | None:
        token = value.strip().upper()
        if not token or not re.fullmatch(r"[IVXLCDM]+", token):
            return None
        values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
        result = 0
        previous = 0
        for character in reversed(token):
            current = values[character]
            result += -current if current < previous else current
            previous = max(previous, current)
        return result if result > 0 else None

    @staticmethod
    def _toc_title_key(value: str) -> str:
        return re.sub(r"[^\w\u0590-\u05ff]+", " ", value, flags=re.UNICODE).strip().casefold()

    @classmethod
    def _translated_book_toc(cls, records: list[dict], rtl: bool) -> list[dict]:  # noqa: C901
        """Build a compact, hierarchical TOC from the source TOC or AI page metadata."""

        if not records:
            return []

        records_by_page = {record["page"]: record for record in records}
        page_index = {record["page"]: index + 1 for index, record in enumerate(records)}
        known_titles = {
            cls._toc_title_key(record.get("explicitTitle") or record.get("title") or ""): record["page"]
            for record in records
            if cls._toc_title_key(record.get("explicitTitle") or record.get("title") or "")
        }

        parsed_source_entries: list[dict] = []
        for record in records:
            text = record.get("text") or ""
            first_lines = " ".join(text.splitlines()[:5]).casefold()
            is_contents_page = record.get("entryType") == "contents" or any(
                marker in first_lines for marker in ("table of contents", "contents", "תוכן עניינים")
            )
            if not is_contents_page:
                continue

            for raw_line in text.splitlines():
                stripped = raw_line.rstrip()
                match = re.match(r"^(\s*)(.+?)\s+(?:\.{2,}\s*)?([0-9]{1,4}|[ivxlcdm]{1,8})$", stripped, re.I)
                if not match:
                    continue
                indent, raw_title, raw_page = match.groups()
                toc_title = re.sub(r"\s+", " ", raw_title).strip(" .-–—|:")
                if len(toc_title) < 2 or toc_title.casefold() in {
                    "contents",
                    "table of contents",
                    "תוכן עניינים",
                }:
                    continue
                printed_page = int(raw_page) if raw_page.isdigit() else cls._roman_page_number(raw_page)
                title_key = cls._toc_title_key(toc_title)
                target_page = known_titles.get(title_key)
                if target_page is None:
                    target_page = next(
                        (
                            page
                            for title, page in known_titles.items()
                            if title_key and (title_key in title or title in title_key)
                        ),
                        None,
                    )
                if target_page is None and printed_page in records_by_page:
                    target_page = printed_page
                if target_page is None:
                    continue
                parsed_source_entries.append(
                    {
                        "title": toc_title,
                        "page": target_page,
                        "displayPage": raw_page,
                        "index": page_index[target_page],
                        "level": 2 if len(indent.expandtabs(4)) >= 2 else 1,
                        "kind": "section",
                    }
                )

        entries = parsed_source_entries if len(parsed_source_entries) >= 2 else []
        if not entries:
            current_parent = ""
            seen_parents: set[str] = set()
            for record in records:
                entry_type = record.get("entryType") or "page"
                title = (record.get("explicitTitle") or "").strip()
                parent_title = (record.get("parentTitle") or "").strip()
                should_include = record.get("includeInContents") or entry_type in {"chapter", "section", "recipe"}
                if not title or not should_include:
                    continue
                if parent_title and parent_title != current_parent:
                    parent_key = cls._toc_title_key(parent_title)
                    if parent_key not in seen_parents:
                        entries.append(
                            {
                                "title": parent_title,
                                "page": record["page"],
                                "displayPage": record["page"],
                                "index": page_index[record["page"]],
                                "level": 1,
                                "kind": "chapter",
                            }
                        )
                        seen_parents.add(parent_key)
                    current_parent = parent_title
                entries.append(
                    {
                        "title": title,
                        "page": record["page"],
                        "displayPage": record["page"],
                        "index": page_index[record["page"]],
                        "level": 1 if entry_type == "chapter" and not parent_title else 2,
                        "kind": entry_type,
                    }
                )
                if entry_type == "chapter":
                    chapter_key = cls._toc_title_key(title)
                    if chapter_key:
                        seen_parents.add(chapter_key)
                    current_parent = title

        if not entries:
            # Legacy translated chunks have no metadata. Keep only meaningful headings,
            # rather than flooding the contents panel with generic "Page N" entries.
            seen_headings: set[str] = set()
            for record in records:
                title = str(record.get("explicitTitle") or "").strip()
                if not title:
                    first_line = next(
                        (
                            re.sub(r"\s+", " ", line).strip(" -–—|")
                            for line in str(record.get("text") or "").splitlines()
                            if line.strip()
                        ),
                        "",
                    )
                    word_count = len(re.findall(r"[^\W\d_]{2,}", first_line, flags=re.UNICODE))
                    sentence_like = bool(re.search(r"[.!?。！？]\s*$", first_line))
                    if 2 <= word_count <= 10 and 3 <= len(first_line) <= 80 and not sentence_like:
                        title = first_line
                key = cls._toc_title_key(title)
                if not key or key in seen_headings or key in {"page", "עמוד"}:
                    continue
                if re.fullmatch(r"(?:page|עמוד)\s*\d+", title, re.I):
                    continue
                seen_headings.add(key)
                entries.append(
                    {
                        "title": title,
                        "page": record["page"],
                        "displayPage": record["page"],
                        "index": page_index[record["page"]],
                        "level": 1,
                        "kind": "section",
                    }
                )

        unique_entries: list[dict] = []
        seen: set[tuple[str, int]] = set()
        for entry in entries:
            key = (cls._toc_title_key(entry["title"]), int(entry["page"]))
            if not key[0] or key in seen:
                continue
            seen.add(key)
            unique_entries.append(entry)
        return unique_entries

    @staticmethod
    def _recipe_ingredient_text(ingredient) -> str:
        if getattr(ingredient, "display", ""):
            return str(ingredient.display).strip()
        pieces = []
        quantity = getattr(ingredient, "quantity", None)
        if quantity:
            pieces.append(str(quantity))
        unit = getattr(ingredient, "unit", None)
        if unit and getattr(unit, "name", None):
            pieces.append(str(unit.name))
        food = getattr(ingredient, "food", None)
        if food and getattr(food, "name", None):
            pieces.append(str(food.name))
        note = str(getattr(ingredient, "note", "") or "").strip()
        if note:
            pieces.append(note)
        return " ".join(pieces).strip()

    def _linked_recipe_sections(
        self,
        book: UploadedBook,
        target_language: str,
        available_pages: set[int],
    ) -> dict[int, list[str]]:
        if not available_pages:
            return {}

        first_available_page = min(available_pages)
        last_available_page = max(available_pages)
        rtl = self._is_rtl_language(target_language)
        labels = {
            "from_site": "מהאתר שלך" if rtl else "From your site",
            "ingredients": "מרכיבים" if rtl else "Ingredients",
            "method": "אופן ההכנה" if rtl else "Method",
            "notes": "הערות" if rtl else "Notes",
            "shopping_list": "רשימת קניות" if rtl else "Shopping list",
            "open_recipe": "פתח מתכון באתר" if rtl else "Open recipe in Mealie",
            "open_list": "פתח רשימת קניות באתר" if rtl else "Open shopping list in Mealie",
        }
        shopping_service = ShoppingListService(self.repos)
        result: dict[int, list[str]] = {}

        for recipe in self._recipes_extracted_from_book(book):
            extras = recipe.extras if isinstance(recipe.extras, dict) else {}
            source_page = extras.get("uploadedBookSourcePageStart")
            try:
                page_number = int(source_page)
            except (TypeError, ValueError):
                page_number, _ = parse_book_source_page_range(recipe.source)
            if not page_number:
                continue
            if page_number < first_available_page or page_number > last_available_page:
                continue
            target_page = page_number if page_number in available_pages else min(
                available_pages,
                key=lambda candidate: abs(candidate - page_number),
            )

            ingredients = [
                value
                for ingredient in (recipe.recipe_ingredient or [])
                if (value := self._recipe_ingredient_text(ingredient))
            ]
            instructions = [
                str(step.text or step.summary or "").strip()
                for step in (recipe.recipe_instructions or [])
                if str(step.text or step.summary or "").strip()
            ]
            notes = [
                " — ".join(value for value in (str(note.title or "").strip(), str(note.text or "").strip()) if value)
                for note in (recipe.notes or [])
                if str(note.title or note.text or "").strip()
            ]
            shopping_list = self._existing_book_recipe_shopping_list(shopping_service, book, recipe)
            shopping_items = [
                value
                for item in (shopping_list.list_items if shopping_list else [])
                if (value := self._recipe_ingredient_text(item))
            ]

            recipe_link = f"/g/{quote(self.user.group_slug)}/r/{quote(recipe.slug)}"
            shopping_link = f"/shopping-lists/{shopping_list.id}" if shopping_list else ""
            parts = [
                '<section class="linked-recipe">',
                f'<div class="linked-recipe__eyebrow">{html.escape(labels["from_site"])}</div>',
                f"<h3>{html.escape(recipe.name or recipe.slug)}</h3>",
            ]
            if ingredients:
                parts.extend(
                    [
                        f"<h4>{html.escape(labels['ingredients'])}</h4>",
                        "<ul>" + "".join(f"<li>{html.escape(value)}</li>" for value in ingredients) + "</ul>",
                    ]
                )
            if instructions:
                parts.extend(
                    [
                        f"<h4>{html.escape(labels['method'])}</h4>",
                        "<ol>" + "".join(f"<li>{html.escape(value)}</li>" for value in instructions) + "</ol>",
                    ]
                )
            if notes:
                parts.extend(
                    [
                        f"<h4>{html.escape(labels['notes'])}</h4>",
                        "<ul>" + "".join(f"<li>{html.escape(value)}</li>" for value in notes) + "</ul>",
                    ]
                )
            if shopping_items:
                parts.extend(
                    [
                        f"<h4>{html.escape(labels['shopping_list'])}</h4>",
                        "<ul>" + "".join(f"<li>{html.escape(value)}</li>" for value in shopping_items) + "</ul>",
                    ]
                )
            parts.append('<div class="linked-recipe__actions">')
            parts.append(
                f'<a href="{recipe_link}" target="_top">{html.escape(labels["open_recipe"])}</a>'
            )
            if shopping_link:
                parts.append(
                    f'<a href="{shopping_link}" target="_top">{html.escape(labels["open_list"])}</a>'
                )
            parts.extend(["</div>", "</section>"])
            result.setdefault(target_page, []).append("".join(parts))
        return result

    def _build_translated_book_html(
        self,
        book: UploadedBook,
        target_language: str,
        translated_pages: list[dict] | list[tuple[int, str]],
        has_cover: bool = False,
        linked_recipe_sections: dict[int, list[str]] | None = None,
        translation_audit: dict | None = None,
    ) -> str:
        rtl = self._is_rtl_language(target_language)
        direction = "rtl" if rtl else "ltr"
        title = html.escape(f"{book.name} - {target_language}")
        source = html.escape(book.original_file_name)
        language = html.escape(target_language)
        if book.translation_page_start and book.translation_page_end:
            page_range = f"Pages {book.translation_page_start}-{book.translation_page_end}"
        elif book.translation_page_start:
            page_range = f"From page {book.translation_page_start}"
        elif book.translation_page_end:
            page_range = f"Through page {book.translation_page_end}"
        else:
            page_range = "Whole book"
        page_range = html.escape(page_range)
        labels = {
            "contents": "תוכן עניינים" if rtl else "Table of contents",
            "cover": "שער" if rtl else "Cover",
            "page": "עמוד" if rtl else "Page",
            "of": "מתוך" if rtl else "of",
            "previous": "הקודם" if rtl else "Previous",
            "next": "הבא" if rtl else "Next",
            "translated": "תורגם אל" if rtl else "Translated to",
            "from": "מתוך" if rtl else "from",
            "pages": "עמודים" if rtl else "pages",
            "reading_progress": "התקדמות בקריאה" if rtl else "Reading progress",
            "open_contents": "פתח תוכן עניינים" if rtl else "Open table of contents",
            "close_contents": "מזער תוכן עניינים" if rtl else "Collapse table of contents",
            "open_progress": "פתח התקדמות" if rtl else "Open reading progress",
            "close_progress": "מזער התקדמות" if rtl else "Collapse reading progress",
            "chapter_progress": "פרקים שנקראו" if rtl else "Chapters read",
            "chapter_complete": "סמן פרק כנקרא" if rtl else "Mark chapter as read",
            "translation_progress": "התקדמות התרגום" if rtl else "Translation progress",
            "translated_pages": "עמודים מתורגמים" if rtl else "pages translated",
            "finish_translation": "השלם תרגום" if rtl else "Finish translation",
            "translation_starting": "מפעיל השלמת תרגום..." if rtl else "Starting translation...",
            "translation_started": "השלמת התרגום התחילה. ניתן לרענן או לפתוח שוב את הספר מאוחר יותר." if rtl
            else "Translation resumed. Refresh or reopen the book later to see the completed pages.",
            "translation_failed": "לא ניתן להפעיל את השלמת התרגום." if rtl
            else "Translation could not be resumed.",
            "source_page": "טקסט מקורי — ממתין לתרגום" if rtl else "Original text — translation pending",
            "original_visual": "תמונה מהספר המקורי" if rtl else "Visual from the original book",
            "original_page_image": "צילום העמוד המקורי" if rtl else "Original page image",
        }
        records = [self._translated_page_record(value, rtl) for value in translated_pages]
        records.sort(key=lambda record: record["page"])
        translation_audit = translation_audit or {}
        total_translation_pages = max(
            int(translation_audit.get("source_pages") or len(records)),
            len(records),
            1,
        )
        translated_page_count_value = translation_audit.get("verified_translated_pages")
        if translated_page_count_value is None:
            translated_page_count_value = (
                int(translation_audit.get("translated_pages") or 0)
                - len(translation_audit.get("suspicious_pages") or [])
            )
        translated_page_count = min(
            total_translation_pages,
            max(
                0,
                int(
                    translated_page_count_value
                    if translation_audit
                    else sum(1 for record in records if record.get("isTranslated", True))
                ),
            ),
        )
        translation_percent = round((translated_page_count / total_translation_pages) * 100)
        try:
            source_metadata = json.loads(book.book_metadata_json or "{}")
        except (AttributeError, TypeError, ValueError):
            source_metadata = {}
        if not isinstance(source_metadata, dict):
            source_metadata = {}
        translation_options = source_metadata.get("translation_options")
        if not isinstance(translation_options, dict):
            translation_options = {}
        source_book_id = str(getattr(book, "id", "") or "")
        resume_payload = {
            "pagesPerChunk": max(1, min(100, int(getattr(book, "translation_pages_per_chunk", 10) or 10))),
            "targetLanguage": target_language,
            "pageStart": getattr(book, "translation_page_start", None),
            "pageEnd": getattr(book, "translation_page_end", None),
            "includeLinkedRecipes": translation_options.get("include_linked_recipes", True),
            "extractRecipes": translation_options.get("extract_recipes", False),
            "autoRecipeImages": translation_options.get("auto_recipe_images", True),
            "includeItemImages": translation_options.get("include_item_images", True),
            "includeAiTips": translation_options.get("include_ai_tips", True),
            "createShoppingLists": translation_options.get("create_shopping_lists", True),
            "organizeShoppingListsWithAi": translation_options.get("organize_shopping_lists_with_ai", True),
        }
        resume_payload_json = json.dumps(resume_payload, ensure_ascii=False).replace("</", "<\\/")
        linked_recipe_sections = linked_recipe_sections or {}
        toc_entries = self._translated_book_toc(records, rtl)
        chapter_order = 0
        current_chapter_id = ""
        for entry in toc_entries:
            if int(entry.get("level", 1)) == 1:
                chapter_order += 1
                title_key = re.sub(r"[^\w-]+", "-", self._toc_title_key(entry["title"]), flags=re.UNICODE)
                title_key = title_key.strip("-")[:48] or "chapter"
                current_chapter_id = f"chapter-{chapter_order}-{title_key}"
            entry["chapterId"] = current_chapter_id
            entry["chapterOrder"] = chapter_order

        chapter_by_page_index: dict[int, str] = {}
        top_level_entries = [entry for entry in toc_entries if int(entry.get("level", 1)) == 1]
        active_chapter_id = ""
        top_level_cursor = 0
        for record_index in range(1, len(records) + 1):
            while (
                top_level_cursor < len(top_level_entries)
                and int(top_level_entries[top_level_cursor]["index"]) <= record_index
            ):
                active_chapter_id = str(top_level_entries[top_level_cursor].get("chapterId") or "")
                top_level_cursor += 1
            chapter_by_page_index[record_index] = active_chapter_id

        page_sections: list[str] = []
        toc_items: list[str] = []
        for entry in toc_entries:
            chapter_id = html.escape(str(entry.get("chapterId") or ""), quote=True)
            chapter_order_value = int(entry.get("chapterOrder") or 0)
            checkbox = ""
            if int(entry.get("level", 1)) == 1 and chapter_id:
                checkbox = (
                    f'<input class="chapter-checkbox" type="checkbox" data-chapter-id="{chapter_id}" '
                    f'data-chapter-order="{chapter_order_value}" title="{html.escape(labels["chapter_complete"])}" '
                    f'aria-label="{html.escape(labels["chapter_complete"])}: {html.escape(entry["title"])}">'
                )
            toc_items.append(
                f'<li class="toc-level-{entry["level"]} toc-kind-{html.escape(entry["kind"])}" '
                f'data-chapter-id="{chapter_id}"><div class="toc-row">{checkbox}'
                f'<a href="#page-{entry["page"]}" data-page-target="{entry["index"]}">'
                f'<span>{html.escape(entry["title"])}</span>'
                f'<strong>{html.escape(str(entry.get("displayPage", entry["page"])))}</strong>'
                "</a></div></li>"
            )

        for index, record in enumerate(records):
            page_number = record["page"]
            text = record["text"]
            page_heading = record["title"]
            page_title = html.escape(f"{labels['page']} {page_number}")
            page_text = html.escape(text.strip())
            is_translated = bool(record.get("isTranslated", True))
            page_status = (
                ""
                if is_translated
                else f'<span class="source-page-badge">{html.escape(labels["source_page"])}</span>'
            )
            page_class = "book-page reading-position" + ("" if is_translated else " source-language-page")
            previous_link = (
                f'<a href="#page-{records[index - 1]["page"]}">‹ {labels["previous"]}</a>'
                if index > 0
                else "<span></span>"
            )
            next_link = (
                f'<a href="#page-{records[index + 1]["page"]}">{labels["next"]} ›</a>'
                if index + 1 < len(records)
                else "<span></span>"
            )
            linked_markup = "".join(linked_recipe_sections.get(page_number, []))
            page_chapter_id = html.escape(chapter_by_page_index.get(index + 1, ""), quote=True)
            visual_items: list[str] = []
            for asset in record.get("visualAssets") or []:
                if not isinstance(asset, dict):
                    continue
                file_name = str(asset.get("file") or "")
                if not re.fullmatch(r"[A-Za-z0-9._-]+\.webp", file_name):
                    continue
                kind = "page" if asset.get("kind") == "page" else "image"
                alt = str(asset.get("alt") or labels["original_visual"])
                try:
                    width = max(1, min(self.MAX_VISUAL_DIMENSION, int(asset.get("width") or 1)))
                    height = max(1, min(self.MAX_VISUAL_DIMENSION, int(asset.get("height") or 1)))
                except (TypeError, ValueError):
                    width, height = 1, 1
                caption = (
                    f"<figcaption>{html.escape(labels['original_page_image'])}</figcaption>"
                    if kind == "page"
                    else ""
                )
                escaped_file_name = html.escape(file_name, quote=True)
                visual_items.append(
                    f'<figure class="page-visual page-visual--{kind}">'
                    f'<a href="./assets/{escaped_file_name}" target="_blank" rel="noopener">'
                    f'<img src="./assets/{escaped_file_name}" alt="{html.escape(alt, quote=True)}" '
                    f'width="{width}" height="{height}" loading="lazy" decoding="async">'
                    f"</a>{caption}</figure>"
                )
            visual_markup = (
                '<div class="page-visuals">' + "".join(visual_items) + "</div>"
                if visual_items
                else ""
            )
            if visual_items:
                page_class += " has-visuals"
            page_sections.append(
                "\n".join(
                    [
                        f'<article class="{page_class}" id="page-{page_number}" '
                        f'data-page-index="{index + 1}" data-page-number="{page_number}" '
                        f'data-page-label="{page_title}" data-chapter-id="{page_chapter_id}" '
                        f'data-translated="{str(is_translated).lower()}">',
                        '<header class="page-header">',
                        f"<span>{html.escape(page_heading)}{page_status}</span>",
                        f"<strong>{page_title}</strong>",
                        "</header>",
                        visual_markup,
                        f'<pre dir="{"inherit" if is_translated else "auto"}">{page_text}</pre>',
                        linked_markup,
                        '<footer class="page-footer">',
                        previous_link,
                        '<a href="#contents">' + labels["contents"] + "</a>",
                        next_link,
                        "</footer>",
                        f'<div class="printed-page-number">{page_number}</div>',
                        "</article>",
                    ]
                )
            )

        cover_markup = (
            '<img class="cover-image" src="./cover" alt="" loading="eager">'
            if has_cover
            else '<div class="cover-fallback" aria-hidden="true">☰</div>'
        )
        finish_translation_markup = ""
        if translation_percent < 100 and source_book_id:
            finish_translation_markup = (
                f'<button class="finish-translation" id="completeTranslationButton" type="button">'
                f'{html.escape(labels["finish_translation"])}</button>'
            )
        translation_summary_markup = (
            '<div class="translation-summary" aria-label="'
            + html.escape(labels["translation_progress"])
            + '">'
            + '<span class="translation-summary__label">'
            + html.escape(labels["translation_progress"])
            + "</span>"
            + f'<strong>{translation_percent}%</strong>'
            + '<span class="translation-summary__count">'
            + f"{translated_page_count}/{total_translation_pages} "
            + html.escape(labels["translated_pages"])
            + "</span>"
            + '<span class="translation-summary__track" aria-hidden="true">'
            + f'<span style="width:{translation_percent}%"></span></span>'
            + finish_translation_markup
            + '<span class="translation-summary__status" id="translationResumeStatus" role="status"></span>'
            + "</div>"
        )

        return f"""<!doctype html>
<html lang="auto" dir="{direction}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Georgia, "Times New Roman", Arial, sans-serif;
      background: #ece8df;
      color: #211914;
      scroll-behavior: smooth;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 0 18px 56px;
      line-height: 1.75;
      transition: padding-left 180ms ease;
    }}
    .book-shell {{
      max-width: 980px;
      margin: 0 auto;
    }}
    .book-toolbar {{
      align-items: center;
      background: rgba(255, 253, 248, 0.96);
      border-bottom: 1px solid #d9cebc;
      display: flex;
      flex-wrap: wrap;
      gap: 18px;
      inset-inline: 0;
      justify-content: center;
      padding: 10px 16px;
      position: sticky;
      top: 0;
      z-index: 10;
    }}
    .book-toolbar a, .page-footer a {{ color: #8f3f1f; font-weight: 700; text-decoration: none; }}
    .translation-summary {{
      align-items: center;
      display: flex;
      flex-wrap: wrap;
      font-family: Arial, Helvetica, sans-serif;
      font-size: 13px;
      gap: 7px;
      justify-content: center;
    }}
    .translation-summary__label {{ font-weight: 700; }}
    .translation-summary__count {{ color: #6f6257; }}
    .translation-summary__track {{
      background: #eadfd2;
      border-radius: 4px;
      display: inline-block;
      height: 7px;
      overflow: hidden;
      width: 84px;
    }}
    .translation-summary__track > span {{
      background: #e8881f;
      display: block;
      height: 100%;
    }}
    .finish-translation {{
      background: #e8881f;
      border: 0;
      border-radius: 4px;
      color: #fff;
      cursor: pointer;
      font: inherit;
      font-weight: 700;
      min-height: 32px;
      padding: 6px 10px;
    }}
    .finish-translation:hover, .finish-translation:focus-visible {{
      background: #b95f12;
      outline: 2px solid #6e370c;
      outline-offset: 2px;
    }}
    .finish-translation:disabled {{ cursor: wait; opacity: 0.65; }}
    .translation-summary__status {{
      flex-basis: 100%;
      min-height: 0;
      text-align: center;
    }}
    .translation-summary__status:empty {{ display: none; }}
    .book-sidebar {{
      background: rgba(255, 253, 248, 0.98);
      border: 1px solid #d9cebc;
      border-radius: 6px;
      box-shadow: 0 8px 26px rgba(61, 45, 29, 0.16);
      direction: {direction};
      display: flex;
      flex-direction: column;
      left: 12px;
      overflow: hidden;
      position: fixed;
      top: 64px;
      bottom: 104px;
      transition: width 180ms ease;
      width: 320px;
      z-index: 30;
    }}
    .book-sidebar.is-collapsed {{ width: 48px; }}
    .book-sidebar.is-collapsed .reader-tools {{ display: none; }}
    .sidebar-header {{
      align-items: center;
      border-bottom: 1px solid #dfd4c4;
      display: flex;
      flex: 0 0 auto;
      gap: 10px;
      min-height: 48px;
      padding: 6px;
    }}
    .sidebar-title {{
      flex: 1;
      font-family: Arial, Helvetica, sans-serif;
      font-size: 16px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .sidebar-toggle, .progress-toggle {{
      align-items: center;
      background: transparent;
      border: 0;
      border-radius: 4px;
      color: #8f3f1f;
      cursor: pointer;
      display: inline-flex;
      flex: 0 0 34px;
      font-size: 24px;
      height: 34px;
      justify-content: center;
      padding: 0;
      width: 34px;
    }}
    .sidebar-toggle:hover, .sidebar-toggle:focus-visible,
    .progress-toggle:hover, .progress-toggle:focus-visible {{
      background: #f1e5d6;
      outline: 2px solid #b95f35;
      outline-offset: 1px;
    }}
    .sidebar-scroll {{
      flex: 1;
      min-height: 0;
      overflow-y: auto;
      overscroll-behavior: contain;
      padding: 8px 10px 14px;
      scrollbar-gutter: stable;
    }}
    .book-sidebar.is-collapsed .sidebar-title,
    .book-sidebar.is-collapsed .sidebar-scroll {{ display: none; }}
    .sidebar-toc {{ list-style: none; margin: 0; padding: 0; }}
    .sidebar-toc li {{ border-bottom: 1px solid #eee4d5; }}
    .sidebar-toc a {{
      align-items: baseline;
      color: #2f261f;
      display: flex;
      font-family: Arial, Helvetica, sans-serif;
      font-size: 13px;
      gap: 10px;
      justify-content: space-between;
      padding: 8px 6px;
      text-decoration: none;
    }}
    .sidebar-toc a span {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .sidebar-toc .toc-level-2 a {{ font-size: 12px; padding-inline-start: 22px; }}
    .sidebar-toc .toc-kind-recipe a::before {{ color: #a94f29; content: "•"; flex: 0 0 auto; }}
    .sidebar-toc a:hover, .sidebar-toc a:focus-visible {{ background: #f6eee3; }}
    .sidebar-toc a.is-active {{
      background: #f1dfcd;
      border-inline-start: 3px solid #a94f29;
      color: #7f3418;
      font-weight: 700;
    }}
    .reading-progress {{
      background: rgba(255, 253, 248, 0.98);
      border: 1px solid #d9cebc;
      border-radius: 6px;
      bottom: 12px;
      box-shadow: 0 8px 26px rgba(61, 45, 29, 0.16);
      direction: {direction};
      left: 12px;
      padding: 8px 10px 10px;
      position: fixed;
      transition: width 180ms ease;
      width: 320px;
      z-index: 31;
    }}
    .reading-progress.is-collapsed {{ padding: 6px; width: 90px; }}
    .progress-header {{ align-items: center; display: flex; gap: 8px; min-height: 34px; }}
    .progress-title {{
      flex: 1;
      font-family: Arial, Helvetica, sans-serif;
      font-size: 14px;
      font-weight: 700;
    }}
    .progress-percent {{
      color: #8f3f1f;
      font-family: Arial, Helvetica, sans-serif;
      font-size: 16px;
      font-weight: 700;
      white-space: nowrap;
    }}
    .progress-details {{ font-family: Arial, Helvetica, sans-serif; font-size: 13px; margin-top: 5px; }}
    .reading-progress.is-collapsed .progress-title,
    .reading-progress.is-collapsed .progress-details {{ display: none; }}
    .progress-track {{
      background: #e8dfd3;
      border-radius: 3px;
      height: 6px;
      margin-top: 7px;
      overflow: hidden;
    }}
    .progress-fill {{ background: #a94f29; height: 100%; transition: width 180ms ease; width: 0; }}
    @media (min-width: 1180px) {{
      body.sidebar-expanded {{ padding-left: 350px; }}
    }}
    .cover-page, .contents-page, .book-page {{
      background: #fffdf8;
      border: 1px solid #d9cebc;
      border-radius: 6px;
      box-shadow: 0 8px 26px rgba(61, 45, 29, 0.12);
      margin: 28px auto;
      min-height: min(1120px, calc(100vh - 92px));
      overflow: hidden;
      padding: clamp(26px, 6vw, 72px);
      position: relative;
      scroll-margin-top: 64px;
    }}
    .cover-page {{
      align-items: center;
      display: grid;
      gap: 34px;
      grid-template-columns: minmax(230px, 0.8fr) minmax(280px, 1.2fr);
    }}
    .cover-image {{
      aspect-ratio: 3 / 4;
      border: 1px solid #cfc2af;
      box-shadow: 0 12px 28px rgba(45, 31, 18, 0.2);
      max-height: 720px;
      object-fit: cover;
      width: 100%;
    }}
    .cover-fallback {{
      align-items: center;
      aspect-ratio: 3 / 4;
      background: #ede3d4;
      color: #8f3f1f;
      display: flex;
      font-size: 72px;
      justify-content: center;
    }}
    h1 {{
      font-size: clamp(34px, 6vw, 64px);
      line-height: 1.15;
      margin: 0 0 22px;
    }}
    .meta {{
      color: #7d6d5d;
      font-family: Arial, Helvetica, sans-serif;
    }}
    .contents-page h2 {{ font-size: 36px; margin: 0 0 28px; }}
    .toc {{ columns: 2; column-gap: 48px; list-style: none; margin: 0; padding: 0; }}
    .toc li {{ break-inside: avoid; border-bottom: 1px dotted #cbbca7; margin-bottom: 9px; padding-bottom: 7px; }}
    .toc a {{ color: inherit; display: flex; gap: 12px; justify-content: space-between; text-decoration: none; }}
    .toc span {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .toc .toc-level-1 {{ font-size: 17px; font-weight: 700; margin-top: 14px; }}
    .toc .toc-level-2 {{ font-size: 14px; margin-inline-start: 24px; }}
    .page-header {{
      align-items: baseline;
      border-bottom: 1px solid #dfd4c4;
      color: #79563e;
      display: flex;
      font-family: Arial, Helvetica, sans-serif;
      gap: 16px;
      justify-content: space-between;
      margin-bottom: 28px;
      padding-bottom: 12px;
    }}
    .source-language-page {{
      border-color: #d89242;
      box-shadow: 0 8px 26px rgba(154, 77, 39, 0.18);
    }}
    .source-page-badge {{
      background: #fff1dc;
      border: 1px solid #e2a35d;
      border-radius: 4px;
      color: #8b430e;
      display: inline-block;
      font-size: 12px;
      font-weight: 700;
      margin-inline-start: 10px;
      padding: 2px 7px;
    }}
    .page-visuals {{
      display: grid;
      gap: 24px;
      margin: 0 0 30px;
    }}
    .page-visual {{
      margin: 0;
      text-align: center;
    }}
    .page-visual a {{
      display: block;
      line-height: 0;
    }}
    .page-visual img {{
      background: #f5f1e9;
      border: 1px solid #d9cebc;
      box-shadow: 0 8px 22px rgba(61, 45, 29, 0.14);
      height: auto;
      margin: 0 auto;
      max-height: 820px;
      max-width: 100%;
      object-fit: contain;
      width: auto;
    }}
    .page-visual--page img {{ width: 100%; }}
    .page-visual figcaption {{
      color: #75685b;
      font-family: Arial, Helvetica, sans-serif;
      font-size: 12px;
      line-height: 1.4;
      margin-top: 8px;
    }}
    pre {{
      white-space: pre-wrap;
      word-wrap: break-word;
      font-family: inherit;
      margin: 0;
      min-height: 760px;
    }}
    .book-page.has-visuals pre {{ min-height: 320px; }}
    .linked-recipe {{
      background: #fbf4e9;
      border: 1px solid #d9c5aa;
      border-radius: 6px;
      margin: 38px 0 18px;
      padding: 24px;
    }}
    .linked-recipe__eyebrow {{
      color: #9a4d27;
      font-family: Arial, Helvetica, sans-serif;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }}
    .linked-recipe h3 {{ font-size: 26px; line-height: 1.25; margin: 6px 0 20px; }}
    .linked-recipe h4 {{ color: #75452d; font-size: 18px; margin: 22px 0 8px; }}
    .linked-recipe li {{ margin-bottom: 6px; }}
    .linked-recipe__actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 24px; }}
    .linked-recipe__actions a {{
      background: #8f3f1f;
      border-radius: 4px;
      color: #fff;
      font-family: Arial, Helvetica, sans-serif;
      font-weight: 700;
      padding: 8px 12px;
      text-decoration: none;
    }}
    .page-footer {{
      border-top: 1px solid #dfd4c4;
      display: grid;
      font-family: Arial, Helvetica, sans-serif;
      grid-template-columns: 1fr 1fr 1fr;
      margin-top: 36px;
      padding-top: 14px;
      text-align: center;
    }}
    .page-footer > :first-child {{ text-align: start; }}
    .page-footer > :last-child {{ text-align: end; }}
    .printed-page-number {{ bottom: 20px; color: #7d6d5d; inset-inline: 0; position: absolute; text-align: center; }}
    @media (max-width: 720px) {{
      body {{ padding-inline: 8px; }}
      .book-sidebar {{ bottom: 96px; left: 8px; max-width: calc(100vw - 16px); top: 58px; }}
      .book-sidebar:not(.is-collapsed) {{ width: min(320px, calc(100vw - 16px)); }}
      .reading-progress {{ bottom: 8px; left: 8px; max-width: calc(100vw - 16px); }}
      .cover-page {{ grid-template-columns: 1fr; }}
      .cover-image, .cover-fallback {{ margin: 0 auto; max-width: 360px; }}
      .toc {{ columns: 1; }}
      .cover-page, .contents-page, .book-page {{ min-height: auto; padding: 24px 20px 58px; }}
      pre {{ min-height: 0; }}
    }}
    @media print {{
      @page {{ margin: 16mm; size: A4; }}
      body {{ background: #fff; padding: 0; }}
      .book-toolbar, .book-sidebar, .reading-progress {{ display: none; }}
      .cover-page, .contents-page, .book-page {{
        border: 0;
        box-shadow: none;
        break-after: page;
        margin: 0;
        min-height: 0;
        padding: 0;
      }}
      .page-footer {{ display: none; }}
    }}
    {book_reader_css(direction)}
  </style>
</head>
<body>
  <nav class="book-toolbar" aria-label="{labels['contents']}">
    <a href="#cover">{labels['cover']}</a>
    <a href="#contents">{labels['contents']}</a>
    <span>{len(records)} {labels['pages']}</span>
    {translation_summary_markup}
  </nav>
  <aside class="book-sidebar" id="bookSidebar" aria-label="{labels['contents']}">
    {book_reader_panels(book_reader_labels(rtl))}
    <div class="sidebar-header">
      <button class="sidebar-toggle" id="sidebarToggle" type="button"
        aria-expanded="true" title="{labels['close_contents']}">‹</button>
      <strong class="sidebar-title">{labels['contents']}</strong>
    </div>
    <nav class="sidebar-scroll" id="sidebarScroll" aria-label="{labels['contents']}">
      <ol class="sidebar-toc">{"".join(toc_items)}</ol>
    </nav>
  </aside>
  <section class="reading-progress" id="readingProgress" aria-label="{labels['reading_progress']}">
    <div class="progress-header">
      <strong class="progress-title">{labels['reading_progress']}</strong>
      <span class="progress-percent" id="progressPercent">0%</span>
      <button class="progress-toggle" id="progressToggle" type="button"
        aria-expanded="true" title="{labels['close_progress']}">−</button>
    </div>
    <div class="progress-details">
      <div id="progressPage">{labels['cover']}</div>
      <div class="progress-track" aria-hidden="true"><div class="progress-fill" id="progressFill"></div></div>
      <div class="progress-chapters">
        <div class="progress-chapters__row"><span>{labels['chapter_progress']}</span>
          <span><span id="chapterProgressDetails">0 / {chapter_order}</span> ·
            <strong id="chapterProgressPercent">0%</strong></span></div>
        <div class="progress-track" aria-hidden="true">
          <div class="progress-fill progress-chapters__fill" id="chapterProgressFill"></div>
        </div>
      </div>
    </div>
  </section>
  <main class="book-shell">
    <section class="cover-page reading-position" id="cover" data-page-index="0"
      data-page-number="0" data-page-label="{labels['cover']}">
      {cover_markup}
      <div>
        <h1>{title}</h1>
        <div class="meta">{labels['translated']} {language}<br>{labels['from']} {source}<br>{page_range}</div>
      </div>
    </section>
    <section class="contents-page reading-position" id="contents" data-page-index="0"
      data-page-number="0" data-page-label="{labels['contents']}">
      <h2>{labels['contents']}</h2>
      <ol class="toc">{"".join(toc_items)}</ol>
    </section>
    {"".join(page_sections)}
  </main>
  {book_reader_script(book_reader_labels(rtl))}
  <script>
    (() => {{
      const completeTranslationButton = document.getElementById("completeTranslationButton");
      const translationResumeStatus = document.getElementById("translationResumeStatus");
      if (completeTranslationButton) {{
        completeTranslationButton.addEventListener("click", async () => {{
          if (completeTranslationButton.disabled) return;
          completeTranslationButton.disabled = true;
          if (translationResumeStatus) {{
            translationResumeStatus.textContent = {json.dumps(labels["translation_starting"], ensure_ascii=False)};
          }}
          try {{
            const response = await fetch(
              `/api/households/uploaded-books/${{encodeURIComponent({json.dumps(source_book_id)})}}/translate`,
              {{
                method: "POST",
                credentials: "same-origin",
                headers: {{ "Content-Type": "application/json" }},
                body: JSON.stringify({resume_payload_json}),
              }},
            );
            if (!response.ok) throw new Error(`Translation request failed (${{response.status}})`);
            if (translationResumeStatus) {{
              translationResumeStatus.textContent = {json.dumps(labels["translation_started"], ensure_ascii=False)};
            }}
          }} catch (_error) {{
            completeTranslationButton.disabled = false;
            if (translationResumeStatus) {{
              translationResumeStatus.textContent = {json.dumps(labels["translation_failed"], ensure_ascii=False)};
            }}
          }}
        }});
      }}

      const sidebar = document.getElementById("bookSidebar");
      const sidebarToggle = document.getElementById("sidebarToggle");
      const sidebarScroll = document.getElementById("sidebarScroll");
      const progress = document.getElementById("readingProgress");
      const progressToggle = document.getElementById("progressToggle");
      const progressPercent = document.getElementById("progressPercent");
      const progressPage = document.getElementById("progressPage");
      const progressFill = document.getElementById("progressFill");
      const positions = [...document.querySelectorAll(".reading-position")];
      const pageLinks = [...document.querySelectorAll(".sidebar-toc a[data-page-target]")];
      const totalPages = {len(records)};
      const pageWord = {json.dumps(labels['page'], ensure_ascii=False)};
      const ofWord = {json.dumps(labels['of'], ensure_ascii=False)};
      const coverLabel = {json.dumps(labels['cover'], ensure_ascii=False)};
      const compactViewport = window.matchMedia("(max-width: 1179px)");

      const readStoredBoolean = (key, fallback) => {{
        try {{
          const value = localStorage.getItem(key);
          return value === null ? fallback : value === "true";
        }} catch (_error) {{
          return fallback;
        }}
      }};
      const storeBoolean = (key, value) => {{
        try {{ localStorage.setItem(key, String(value)); }} catch (_error) {{ /* storage is optional */ }}
      }};

      let sidebarCollapsed = readStoredBoolean("translatedBookSidebarCollapsed", compactViewport.matches);
      let progressCollapsed = readStoredBoolean("translatedBookProgressCollapsed", false);

      const applySidebarState = () => {{
        sidebar.classList.toggle("is-collapsed", sidebarCollapsed);
        document.body.classList.toggle("sidebar-expanded", !sidebarCollapsed);
        sidebarToggle.textContent = sidebarCollapsed ? "›" : "‹";
        sidebarToggle.setAttribute("aria-expanded", String(!sidebarCollapsed));
        sidebarToggle.title = sidebarCollapsed
          ? {json.dumps(labels['open_contents'], ensure_ascii=False)}
          : {json.dumps(labels['close_contents'], ensure_ascii=False)};
      }};
      const applyProgressState = () => {{
        progress.classList.toggle("is-collapsed", progressCollapsed);
        progressToggle.textContent = progressCollapsed ? "+" : "−";
        progressToggle.setAttribute("aria-expanded", String(!progressCollapsed));
        progressToggle.title = progressCollapsed
          ? {json.dumps(labels['open_progress'], ensure_ascii=False)}
          : {json.dumps(labels['close_progress'], ensure_ascii=False)};
      }};

      sidebarToggle.addEventListener("click", () => {{
        sidebarCollapsed = !sidebarCollapsed;
        storeBoolean("translatedBookSidebarCollapsed", sidebarCollapsed);
        applySidebarState();
      }});
      progressToggle.addEventListener("click", () => {{
        progressCollapsed = !progressCollapsed;
        storeBoolean("translatedBookProgressCollapsed", progressCollapsed);
        applyProgressState();
      }});

      const updateReadingPosition = (position) => {{
        const pageIndex = Number(position.dataset.pageIndex || 0);
        const pageNumber = position.dataset.pageNumber || "0";
        const pageLabel = position.dataset.pageLabel || coverLabel;
        const percent = pageIndex > 0 && totalPages > 0
          ? Math.min(100, Math.max(1, Math.round((pageIndex / totalPages) * 100)))
          : 0;
        progressPercent.textContent = `${{percent}}%`;
        progressFill.style.width = `${{percent}}%`;
        progressPage.textContent = pageIndex > 0
          ? `${{pageWord}} ${{pageNumber}} · ${{pageIndex}} ${{ofWord}} ${{totalPages}}`
          : pageLabel;

        pageLinks.forEach((link) => {{
          link.classList.toggle("is-active", Number(link.dataset.pageTarget) === pageIndex);
        }});
        const activeLink = pageLinks.find((link) => Number(link.dataset.pageTarget) === pageIndex);
        if (activeLink && !sidebarCollapsed) {{
          const top = activeLink.offsetTop;
          const bottom = top + activeLink.offsetHeight;
          if (top < sidebarScroll.scrollTop) sidebarScroll.scrollTo({{ top, behavior: "smooth" }});
          else if (bottom > sidebarScroll.scrollTop + sidebarScroll.clientHeight) {{
            sidebarScroll.scrollTo({{ top: bottom - sidebarScroll.clientHeight, behavior: "smooth" }});
          }}
        }}
        window.dispatchEvent(new CustomEvent("mealie:book-position", {{ detail: {{
          pageIndex,
          pageNumber: Number(pageNumber || 0),
          chapterId: position.dataset.chapterId || null,
          percent,
        }} }}));
      }};

      const observer = new IntersectionObserver((entries) => {{
        const visible = entries.filter((entry) => entry.isIntersecting);
        if (!visible.length) return;
        visible.sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        updateReadingPosition(visible[0].target);
      }}, {{ rootMargin: "-20% 0px -55% 0px", threshold: [0, 0.01, 0.25] }});
      positions.forEach((position) => observer.observe(position));
      window.addEventListener("pagehide", () => observer.disconnect(), {{ once: true }});

      pageLinks.forEach((link) => {{
        link.addEventListener("click", (event) => {{
          const targetSelector = link.getAttribute("href");
          const target = targetSelector ? document.querySelector(targetSelector) : null;
          if (target) {{
            event.preventDefault();
            const top = target.getBoundingClientRect().top + window.scrollY - 64;
            window.scrollTo({{ top: Math.max(0, top), behavior: "instant" }});
            history.pushState(null, "", targetSelector);
            updateReadingPosition(target);
          }}
          if (compactViewport.matches) {{
            sidebarCollapsed = true;
            storeBoolean("translatedBookSidebarCollapsed", true);
            applySidebarState();
          }}
        }});
      }});

      applySidebarState();
      applyProgressState();
      const initialPosition = document.querySelector(location.hash + ".reading-position") || positions[0];
      if (initialPosition) updateReadingPosition(initialPosition);
    }})();
  </script>
</body>
</html>
"""

    def _replace_translated_visual_assets(
        self,
        target_dir: Path,
        visual_assets_dir: Path | None,
        visual_assets_by_page: dict[int, list[dict]] | None,
    ) -> None:
        if visual_assets_dir is None or visual_assets_by_page is None:
            return

        target_dir = target_dir.resolve()
        source_dir = visual_assets_dir.resolve()
        assets_dir = target_dir.joinpath("assets").resolve()
        if not assets_dir.is_relative_to(target_dir):
            raise ValueError("Invalid translated book assets target path")

        staging_dir = target_dir.joinpath(f".assets-{uuid4().hex}.tmp").resolve()
        backup_dir = target_dir.joinpath(f".assets-{uuid4().hex}.old").resolve()
        if not staging_dir.is_relative_to(target_dir) or not backup_dir.is_relative_to(target_dir):
            raise ValueError("Invalid translated book assets staging path")

        staging_dir.mkdir(parents=True, exist_ok=False)
        try:
            for file_name in sorted(self._visual_asset_file_names(visual_assets_by_page)):
                if Path(file_name).name != file_name or not file_name.endswith(".webp"):
                    continue
                source_path = source_dir.joinpath(file_name).resolve()
                if not source_path.is_relative_to(source_dir) or not source_path.is_file():
                    raise ValueError(f"Translated book visual asset is missing: {file_name}")
                shutil.copy2(source_path, staging_dir.joinpath(file_name))

            if assets_dir.exists():
                assets_dir.replace(backup_dir)
            try:
                staging_dir.replace(assets_dir)
            except Exception:
                if backup_dir.exists() and not assets_dir.exists():
                    backup_dir.replace(assets_dir)
                raise
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
        finally:
            if staging_dir.exists():
                shutil.rmtree(staging_dir)

    def _create_translated_book(
        self,
        book: UploadedBook,
        uploaded_books_root: Path,
        target_language: str,
        html_content: str,
        translation_audit: dict,
        include_linked_recipes: bool = True,
        translation_status: str = TRANSLATION_COMPLETED,
        visual_assets_dir: Path | None = None,
        visual_assets_by_page: dict[int, list[dict]] | None = None,
    ) -> UploadedBook:
        translated_book = None
        if book.translated_book_id:
            translated_book = self.repos.session.execute(
                sa.select(UploadedBook).where(
                    UploadedBook.id == book.translated_book_id,
                    UploadedBook.group_id == book.group_id,
                    UploadedBook.is_translated_book.is_(True),
                )
            ).scalar_one_or_none()

        translated_book_id = translated_book.id if translated_book else uuid4()
        file_name = translated_book.file_name if translated_book else f"{translated_book_id}.html"
        root = uploaded_books_root.joinpath(str(book.group_id)).resolve()
        target_dir = root.joinpath(str(translated_book_id)).resolve()
        if not target_dir.is_relative_to(root):
            raise ValueError("Invalid translated book target path")
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir.joinpath(file_name).resolve()
        if not target_path.is_relative_to(target_dir):
            raise ValueError("Invalid translated book file path")
        temporary_path = target_dir.joinpath(f".{file_name}.tmp").resolve()
        try:
            temporary_path.write_text(
                html_content.replace(BOOK_READER_ID_PLACEHOLDER, str(translated_book_id)),
                encoding="utf-8",
            )
            self._replace_translated_visual_assets(
                target_dir,
                visual_assets_dir,
                visual_assets_by_page,
            )
            temporary_path.replace(target_path)
        finally:
            temporary_path.unlink(missing_ok=True)

        source_cover = UploadedBookCoverService.cover_path(uploaded_books_root, book)
        if source_cover.exists():
            shutil.copy2(source_cover, target_dir.joinpath(BOOK_COVER_FILE_NAME))

        try:
            source_metadata = json.loads(book.book_metadata_json or "{}")
        except (TypeError, ValueError):
            source_metadata = {}
        if not isinstance(source_metadata, dict):
            source_metadata = {}
        translated_metadata = {
            **source_metadata,
            "translated_from_book_id": str(book.id),
            "translation_language": target_language,
            "translation_audit": translation_audit,
            "translation_include_linked_recipes": include_linked_recipes,
            "visual_asset_count": sum(
                len(assets)
                for assets in (visual_assets_by_page or {}).values()
            ),
            "visual_asset_pages": sorted((visual_assets_by_page or {}).keys()),
        }
        if source_cover.exists():
            translated_metadata["cover_file_name"] = BOOK_COVER_FILE_NAME

        values = {
            "group_id": book.group_id,
            "household_id": book.household_id,
            "user_id": book.user_id,
            "category_id": book.category_id,
            "name": f"{book.name} ({target_language})",
            "file_name": file_name,
            "original_file_name": f"{book.name} - {target_language}.html",
            "extension": ".html",
            "content_type": "text/html; charset=utf-8",
            "size": target_path.stat().st_size,
            "book_metadata_json": json.dumps(translated_metadata, ensure_ascii=False),
            "is_translated_book": True,
            "translated_from_book_id": book.id,
            "translation_language": target_language,
            "translation_status": translation_status,
            "translation_page_start": book.translation_page_start,
            "translation_page_end": book.translation_page_end,
            "translation_completed_at": get_utc_now(),
        }
        if translated_book:
            for key, value in values.items():
                setattr(translated_book, key, value)
        else:
            translated_book = UploadedBook(**values, session=self.repos.session)
            translated_book.id = translated_book_id
        assert translated_book is not None
        self.repos.session.add(translated_book)
        self.repos.session.commit()
        self.repos.session.refresh(translated_book)
        return translated_book

    async def translate_with_optional_extraction(
        self,
        book_id: UUID4,
        uploaded_books_root: Path,
        pages_per_chunk: int = 10,
        target_language: str = "Hebrew",
        resume: bool = False,
        page_start: int | None = None,
        page_end: int | None = None,
        include_linked_recipes: bool = True,
        extract_recipes: bool = False,
        auto_recipe_images: bool = True,
        include_item_images: bool = True,
        include_ai_tips: bool = True,
        create_shopping_lists: bool = True,
        organize_shopping_lists_with_ai: bool = True,
    ) -> None:
        if extract_recipes and not resume:
            extractor = UploadedBookRecipeExtractor(self.repos, self.user, self.household, self.translator)
            await extractor.extract_recipes(
                book_id,
                uploaded_books_root,
                pages_per_chunk,
                target_language,
                resume=False,
                page_start=page_start,
                page_end=page_end,
                auto_recipe_images=auto_recipe_images,
                include_item_images=include_item_images,
                include_ai_tips=include_ai_tips,
                create_shopping_lists=create_shopping_lists,
                organize_shopping_lists_with_ai=organize_shopping_lists_with_ai,
                allow_duplicate_recipes=False,
            )
        await self.translate_book(
            book_id,
            uploaded_books_root,
            pages_per_chunk,
            target_language,
            resume,
            page_start,
            page_end,
            include_linked_recipes,
        )

    async def _classify_translated_book(
        self,
        translated_book: UploadedBook,
        uploaded_books_root: Path,
        target_language: str,
    ) -> None:
        # Imported here to avoid a module cycle: the classifier uses this extractor for sampling.
        from .book_classifier import UploadedBookClassifier

        classifier = UploadedBookClassifier(self.repos, self.user, self.household, self.translator)
        await classifier.classify(
            translated_book.id,
            uploaded_books_root,
            response_language=target_language,
        )

    async def _assemble_translated_book(
        self,
        book: UploadedBook,
        uploaded_books_root: Path,
        target_language: str,
        chunks: list[BookTextChunk],
        chunk_states: dict[int, dict],
        work_dir: Path,
        include_linked_recipes: bool,
        classify: bool = True,
    ) -> UploadedBook | None:
        translated_records: list[dict] = []
        for state in sorted(chunk_states.values(), key=lambda item: self._state_int(item, "index")):
            file_name = state.get("translatedChunkFile")
            if isinstance(file_name, str):
                try:
                    translated_records.extend(self._read_translated_chunk_records(work_dir, file_name))
                except (OSError, TypeError, ValueError):
                    self.logger.warning(
                        f"Ignoring unreadable partial translation file {file_name} for uploaded book {book.id}",
                        exc_info=True,
                    )
        if not translated_records:
            return None

        expected_pages = {
            page_number
            for chunk in chunks
            for page_number in chunk.page_numbers
        }
        ignored_unexpected_pages = sorted(
            {
                record["page"]
                for record in translated_records
                if record["page"] not in expected_pages
            }
        )
        translated_records = [
            record
            for record in translated_records
            if record["page"] in expected_pages
        ]
        if not translated_records:
            return None

        translated_record_map = {record["page"]: record for record in translated_records}
        translated_pages = [(page, record["text"]) for page, record in translated_record_map.items()]
        translation_audit = self._audit_translated_pages(
            chunks,
            translated_pages,
            allow_partial_pages=True,
        )
        if ignored_unexpected_pages:
            translation_audit["ignored_unexpected_pages"] = ignored_unexpected_pages

        unverified_pages = {
            int(page)
            for page in (
                list(translation_audit.get("missing_pages") or [])
                + list(translation_audit.get("suspicious_page_numbers") or [])
            )
        }
        source_text_by_page: dict[int, str] = {}
        for chunk in chunks:
            chunk_source_pages = self._source_pages_from_chunk(chunk)
            source_text_by_page.update(chunk_source_pages)
        for page_number in sorted(expected_pages):
            translated_record = translated_record_map.get(page_number)
            if translated_record is not None and page_number not in unverified_pages:
                translated_record["isTranslated"] = True
                continue
            translated_record_map[page_number] = {
                "page": page_number,
                "text": source_text_by_page.get(page_number, ""),
                "title": None,
                "entryType": "page",
                "parentTitle": None,
                "includeInContents": False,
                "isTranslated": False,
            }

        translated_records = [translated_record_map[page] for page in sorted(translated_record_map)]
        available_pages = set(expected_pages)
        del translated_pages, translated_record_map, unverified_pages

        visual_assets_by_page: dict[int, list[dict]] = {}
        visual_assets_dir: Path | None = None
        try:
            source_path = self._book_file_path(book, uploaded_books_root)
            visual_assets_by_page, visual_assets_dir = await asyncio.to_thread(
                self._visual_assets_for_translation,
                source_path,
                book.extension,
                expected_pages,
                source_text_by_page,
                work_dir,
            )
        except Exception:
            self.logger.warning(
                f"Translated book {book.id} will be saved without some original visual assets",
                exc_info=True,
            )
        for record in translated_records:
            record["visualAssets"] = visual_assets_by_page.get(int(record["page"]), [])
        translation_audit["visual_asset_pages"] = sorted(visual_assets_by_page)
        translation_audit["visual_asset_count"] = sum(
            len(assets) for assets in visual_assets_by_page.values()
        )
        del source_text_by_page

        cover_service = UploadedBookCoverService(self.repos)
        has_cover = await cover_service.ensure_cover(book, uploaded_books_root)
        linked_recipe_sections = (
            self._linked_recipe_sections(book, target_language, available_pages)
            if include_linked_recipes
            else {}
        )
        html_content = self._build_translated_book_html(
            book,
            target_language,
            translated_records,
            has_cover=has_cover,
            linked_recipe_sections=linked_recipe_sections,
            translation_audit=translation_audit,
        )
        translated_book = self._create_translated_book(
            book,
            uploaded_books_root,
            target_language,
            html_content,
            translation_audit,
            include_linked_recipes,
            (
                TRANSLATION_COMPLETED
                if translation_audit["passed"]
                else TRANSLATION_PARTIAL_FAILED
            ),
            visual_assets_dir,
            visual_assets_by_page,
        )
        del html_content, linked_recipe_sections, translated_records, visual_assets_by_page
        if classify:
            try:
                await self._classify_translated_book(
                    translated_book,
                    uploaded_books_root,
                    target_language,
                )
            except Exception:
                self.logger.warning(
                    f"Translated book {translated_book.id} was saved, but AI classification failed",
                    exc_info=True,
                )
        book.translated_book_id = translated_book.id
        return translated_book

    async def save_manual_translation_page(
        self,
        book_id: UUID4,
        uploaded_books_root: Path,
        page_number: int,
        translated_text: str,
    ) -> UploadedBook:
        book = self._get_book(book_id)
        if book.translation_status in {TRANSLATION_PROCESSING, TRANSLATION_RETRYING}:
            raise ValueError("The book is currently being translated")
        target_language = (book.translation_language or "Hebrew").strip()
        path = self._book_file_path(book, uploaded_books_root)
        pages = self._extract_pages(path, book.extension)
        pages = self._filter_pages_by_range(
            pages,
            book.translation_page_start,
            book.translation_page_end,
        )
        chunks = self._build_chunks(pages, book.translation_pages_per_chunk or 10)
        target_chunk = next((chunk for chunk in chunks if page_number in chunk.page_numbers), None)
        if target_chunk is None:
            raise ValueError("The selected page is outside the translated range or contains no text")

        work_dir = self._translated_chunks_dir(uploaded_books_root, book, target_language)
        existing_states = self._load_translation_chunk_states(book)
        chunk_states = self._initial_translation_chunk_states(
            book,
            chunks,
            preserve_incomplete_attempts=True,
        )
        state = chunk_states[target_chunk.index]
        previous = existing_states.get(self._chunk_range_key(target_chunk), {})
        records: list[dict] = []
        previous_file = previous.get("translatedChunkFile")
        if isinstance(previous_file, str):
            records = self._read_translated_chunk_records(work_dir, previous_file)
        records_by_page = {record["page"]: record for record in records}
        records_by_page[page_number] = {
            "page": page_number,
            "text": translated_text.strip(),
            "title": self._translated_page_heading(
                translated_text,
                page_number,
                self._is_rtl_language(target_language),
            ),
            "entryType": "page",
            "parentTitle": None,
        }
        page_text = {page: record["text"] for page, record in records_by_page.items()}
        page_metadata = {
            page: {
                "title": record.get("title"),
                "entryType": record.get("entryType", "page"),
                "parentTitle": record.get("parentTitle"),
            }
            for page, record in records_by_page.items()
        }
        translated_chunk_file = self._write_translated_chunk(
            work_dir,
            target_chunk,
            page_text,
            page_metadata,
        )
        expected_pages = set(target_chunk.page_numbers)
        missing_pages = sorted(expected_pages - set(records_by_page))
        state.update(
            {
                "status": CHUNK_COMPLETED if not missing_pages else CHUNK_FAILED,
                "translatedChunkFile": translated_chunk_file,
                "pagesTranslated": len(expected_pages - set(missing_pages)),
                "error": None if not missing_pages else f"Manual translation is still missing pages {missing_pages}",
                "provider": "manual",
                "nextRetrySeconds": None,
                "nextRetryAt": None,
                "completedAt": get_utc_now().isoformat() if not missing_pages else None,
            }
        )
        failed_chunks = sum(1 for item in chunk_states.values() if item.get("status") != CHUNK_COMPLETED)
        final_status = TRANSLATION_PARTIAL_FAILED if failed_chunks else TRANSLATION_COMPLETED
        include_linked_recipes = True
        try:
            metadata = json.loads(book.book_metadata_json or "{}")
            options = metadata.get("translation_options", {}) if isinstance(metadata, dict) else {}
            include_linked_recipes = bool(options.get("include_linked_recipes", True))
        except (TypeError, ValueError):
            pass
        translated_book = await self._assemble_translated_book(
            book,
            uploaded_books_root,
            target_language,
            chunks,
            chunk_states,
            work_dir,
            include_linked_recipes,
            classify=False,
        )
        if translated_book is not None:
            if translated_book.translation_status == TRANSLATION_PARTIAL_FAILED:
                final_status = TRANSLATION_PARTIAL_FAILED
            translated_book.translation_status = final_status
            translated_book.translation_completed_at = get_utc_now()
            self.repos.session.add(translated_book)
        book.translation_completed_at = get_utc_now()
        self._save_translation_progress(book, chunk_states, final_status)
        return book

    async def translate_book(  # noqa: C901
        self,
        book_id: UUID4,
        uploaded_books_root: Path,
        pages_per_chunk: int = 10,
        target_language: str = "Hebrew",
        resume: bool = False,
        page_start: int | None = None,
        page_end: int | None = None,
        include_linked_recipes: bool = True,
    ) -> None:
        if not await self._claim_job("translation", book_id):
            self.logger.info(f"Uploaded book translation job {book_id} is already running")
            return

        book: UploadedBook | None = None

        try:
            target_language = target_language.strip() or "Hebrew"
            book = self._get_book(book_id)
            path = self._book_file_path(book, uploaded_books_root)
            if not path.exists():
                raise ValueError("Uploaded book file is missing")

            book.translation_status = TRANSLATION_PROCESSING
            book.translation_language = target_language
            book.translation_pages_per_chunk = pages_per_chunk
            book.translation_page_start = page_start
            book.translation_page_end = page_end
            if not resume:
                book.translation_total_chunks = 0
                book.translation_completed_chunks = 0
                book.translation_failed_chunks = 0
                book.translation_retry_count = 0
                book.translation_chunk_status = None
            book.translation_error = None
            book.translation_started_at = book.translation_started_at if resume else get_utc_now()
            book.translation_started_at = book.translation_started_at or get_utc_now()
            book.translation_completed_at = None
            self._save_book(book)

            pages = self._extract_pages(path, book.extension)
            if not pages:
                raise ValueError("No extractable text was found in this book")

            pages = self._filter_pages_by_range(pages, page_start, page_end)
            if not pages:
                raise ValueError("No extractable text was found in the selected page range")

            chunks = self._build_chunks(pages, pages_per_chunk)
            if not chunks:
                raise ValueError("No chunks could be created from this book")
            del pages

            work_dir = (
                self._translated_chunks_dir(uploaded_books_root, book, target_language)
                if resume
                else self._reset_translated_chunks_dir(uploaded_books_root, book, target_language)
            )
            chunk_states = self._initial_translation_chunk_states(
                book, chunks, preserve_incomplete_attempts=resume
            )
            self._save_translation_progress(book, chunk_states, TRANSLATION_PROCESSING)
            if (
                resume
                and not book.translated_book_id
                and any(state.get("translatedChunkFile") for state in chunk_states.values())
            ):
                partial_snapshot = await self._assemble_translated_book(
                    book,
                    uploaded_books_root,
                    target_language,
                    chunks,
                    chunk_states,
                    work_dir,
                    include_linked_recipes,
                    classify=False,
                )
                if partial_snapshot is not None:
                    partial_snapshot.translation_status = TRANSLATION_PARTIAL_FAILED
                    self.repos.session.add(partial_snapshot)
                    self._save_translation_progress(book, chunk_states, TRANSLATION_PROCESSING)
            if self._is_translation_cancelled(book):
                self._set_translation_cancelled(book)
                return

            openai_service = OpenAIService(self.repos)
            if not (openai_service.provider_settings and openai_service.provider_settings.ai_enabled):
                raise ValueError("AI provider is not configured")

            provider_slots = self._provider_slots(openai_service)
            prompt = openai_service.get_prompt("recipes.translate-book-chunk")

            queue: asyncio.Queue[BookTextChunk] = asyncio.Queue()
            for chunk in chunks:
                if chunk_states[chunk.index].get("status") == CHUNK_COMPLETED:
                    continue
                await queue.put(chunk)

            provider_lock = asyncio.Lock()
            state_lock = asyncio.Lock()

            async def worker() -> None:
                while True:
                    if self._is_translation_cancelled(book):
                        return

                    try:
                        chunk = queue.get_nowait()
                    except asyncio.QueueEmpty:
                        return

                    try:
                        if self._is_translation_cancelled(book):
                            queue.task_done()
                            return

                        slot = await self._acquire_provider_slot(provider_slots, provider_lock)
                    except RuntimeError as e:
                        async with state_lock:
                            state = chunk_states[chunk.index]
                            state.update(
                                {
                                    "status": CHUNK_FAILED,
                                    "error": str(e),
                                    "provider": None,
                                    "nextRetrySeconds": None,
                                    "nextRetryAt": None,
                                }
                            )
                            self._save_translation_progress(book, chunk_states)
                        queue.task_done()
                        continue

                    wait_seconds: int | None = None

                    try:
                        async with state_lock:
                            state = chunk_states[chunk.index]
                            attempts = self._state_int(state, "attempts") + 1
                            state.update(
                                {
                                    "status": CHUNK_PROCESSING,
                                    "attempts": attempts,
                                    "provider": slot.label,
                                    "nextRetrySeconds": None,
                                    "nextRetryAt": None,
                                }
                            )
                            self._save_translation_progress(book, chunk_states)

                        result = await self._translate_chunk_once(
                            openai_service,
                            prompt,
                            slot,
                            book,
                            chunk,
                            target_language,
                        )

                        if self._is_translation_cancelled(book):
                            return

                        has_usable_provider = True
                        if result.error and result.provider_disabled:
                            await self._disable_provider_slot(slot, provider_lock, result.error)
                            has_usable_provider = await self._has_usable_provider_slot(provider_slots, provider_lock)

                        async with state_lock:
                            state = chunk_states[chunk.index]
                            attempts = self._state_int(state, "attempts")

                            if result.error and result.pages:
                                partial_file, partial_page_count = self._merge_partial_translation_result(
                                    work_dir,
                                    result,
                                    (
                                        state.get("translatedChunkFile")
                                        if isinstance(state.get("translatedChunkFile"), str)
                                        else None
                                    ),
                                )
                                if partial_file:
                                    state["translatedChunkFile"] = partial_file
                                    state["pagesTranslated"] = partial_page_count

                            if result.error:
                                if result.provider_disabled and has_usable_provider:
                                    state["attempts"] = max(attempts - 1, 0)
                                    state.update(
                                        {
                                            "status": CHUNK_RETRYING,
                                            "error": f"{result.provider_label} disabled: {result.error}",
                                            "provider": result.provider_label,
                                            "nextRetrySeconds": None,
                                            "nextRetryAt": None,
                                        }
                                    )
                                    self._save_translation_progress(book, chunk_states)
                                    await queue.put(chunk)
                                elif result.retryable and attempts < self.MAX_CHUNK_ATTEMPTS:
                                    backoff_seconds = min(
                                        self.DEFAULT_RETRY_WAIT_SECONDS * (2 ** max(attempts - 1, 0)),
                                        self.MAX_RETRY_WAIT_SECONDS,
                                    )
                                    wait_seconds = result.wait_seconds or backoff_seconds
                                    state.update(
                                        {
                                            "status": CHUNK_RETRYING,
                                            "error": result.error,
                                            "provider": result.provider_label,
                                            "nextRetrySeconds": wait_seconds,
                                            "nextRetryAt": self._retry_at(wait_seconds),
                                        }
                                    )
                                    self._save_translation_progress(book, chunk_states)
                                    await queue.put(chunk)
                                else:
                                    state.update(
                                        {
                                            "status": CHUNK_FAILED,
                                            "error": (
                                                f"No usable AI provider keys remain after {result.provider_label}: "
                                                f"{result.error}"
                                                if result.provider_disabled
                                                else result.error
                                            ),
                                            "provider": result.provider_label,
                                            "nextRetrySeconds": None,
                                            "nextRetryAt": None,
                                        }
                                    )
                                    self._save_translation_progress(book, chunk_states)
                            else:
                                translated_chunk_file = self._write_translated_chunk(
                                    work_dir,
                                    result.chunk,
                                    result.pages,
                                    result.page_metadata,
                                )
                                state.update(
                                    {
                                        "status": CHUNK_COMPLETED,
                                        "pagesTranslated": len(result.pages),
                                        "translatedChunkFile": translated_chunk_file,
                                        "error": None,
                                        "provider": result.provider_label,
                                        "nextRetrySeconds": None,
                                        "nextRetryAt": None,
                                        "completedAt": get_utc_now().isoformat(),
                                    }
                                )
                                self._save_translation_progress(book, chunk_states)
                    finally:
                        await self._release_provider_slot(slot, provider_lock, wait_seconds)
                        queue.task_done()

            worker_count = min(len(provider_slots), queue.qsize())
            if worker_count:
                await asyncio.gather(*(worker() for _ in range(worker_count)))

            if self._is_translation_cancelled(book):
                self._set_translation_cancelled(book)
                return

            failed_chunks = sum(1 for state in chunk_states.values() if state.get("status") == CHUNK_FAILED)
            translated_book = await self._assemble_translated_book(
                book,
                uploaded_books_root,
                target_language,
                chunks,
                chunk_states,
                work_dir,
                include_linked_recipes,
            )
            final_status = TRANSLATION_PARTIAL_FAILED if failed_chunks else TRANSLATION_COMPLETED
            if translated_book is not None and translated_book.translation_status == TRANSLATION_PARTIAL_FAILED:
                final_status = TRANSLATION_PARTIAL_FAILED
            if translated_book is None and failed_chunks:
                book.translation_status = final_status
                book.translation_completed_at = get_utc_now()
                self._save_translation_progress(book, chunk_states, final_status)
                return
            if translated_book is None:
                raise ValueError("No translated pages were produced")

            translated_book.translation_status = final_status
            translated_book.translation_completed_at = get_utc_now()
            self.repos.session.add(translated_book)
            book.translation_status = final_status
            book.translation_completed_at = get_utc_now()
            self._save_translation_progress(book, chunk_states, final_status)

        except Exception as e:
            self.repos.session.rollback()
            self.logger.error(f"Failed to translate uploaded book {book_id}")
            self.logger.exception(e)
            if book is not None:
                if self._is_translation_cancelled(book):
                    self._set_translation_cancelled(book)
                else:
                    self._set_translation_failed(book, str(e))
        finally:
            await self._release_job("translation", book_id)
