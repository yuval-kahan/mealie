import asyncio
import html
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

import sqlalchemy as sa
import sqlalchemy.exc
from bs4 import BeautifulSoup
from pydantic import UUID4

from mealie.core import exceptions
from mealie.db.models._model_utils.datetime import get_utc_now
from mealie.db.models.household.uploaded_book import UploadedBook
from mealie.db.models.recipe import RecipeModel
from mealie.lang.providers import Translator
from mealie.repos.repository_factory import AllRepositories
from mealie.schema.group.ai_providers import AIProviderOut
from mealie.schema.household.household import HouseholdInDB
from mealie.schema.openai.recipe import OpenAIBookRecipeChunkParse, OpenAIBookTranslationChunkParse, OpenAIRecipe
from mealie.schema.recipe.recipe import Recipe, create_recipe_slug
from mealie.schema.user import PrivateUser
from mealie.services._base_service import BaseService
from mealie.services.openai import OpenAIService
from mealie.services.recipe.recipe_service import OpenAIRecipeService, RecipeService
from mealie.services.scraper import cleaner

EXTRACTION_NOT_STARTED = "not_started"
EXTRACTION_PROCESSING = "processing"
EXTRACTION_RETRYING = "retrying"
EXTRACTION_COMPLETED = "completed"
EXTRACTION_PARTIAL_FAILED = "partial_failed"
EXTRACTION_FAILED = "failed"

TRANSLATION_NOT_STARTED = "not_started"
TRANSLATION_PROCESSING = "processing"
TRANSLATION_RETRYING = "retrying"
TRANSLATION_COMPLETED = "completed"
TRANSLATION_PARTIAL_FAILED = "partial_failed"
TRANSLATION_FAILED = "failed"

CHUNK_PENDING = "pending"
CHUNK_PROCESSING = "processing"
CHUNK_RETRYING = "retrying"
CHUNK_COMPLETED = "completed"
CHUNK_FAILED = "failed"

SUPPORTED_TEXT_EXTRACTION_EXTENSIONS = {
    ".docx",
    ".epub",
    ".fb2",
    ".fb2.zip",
    ".htm",
    ".html",
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


@dataclass
class ChunkWorkResult:
    chunk: BookTextChunk
    recipes: list[OpenAIRecipe]
    provider_label: str
    wait_seconds: int | None = None
    error: str | None = None
    retryable: bool = False


@dataclass
class ChunkTranslationResult:
    chunk: BookTextChunk
    pages: dict[int, str]
    provider_label: str
    wait_seconds: int | None = None
    error: str | None = None
    retryable: bool = False


class UploadedBookRecipeExtractor(BaseService):
    PSEUDO_PAGE_CHAR_LIMIT = 3500
    MAX_AI_CHARS = 90000
    MAX_CHUNK_ATTEMPTS = 6
    DEFAULT_RETRY_WAIT_SECONDS = 60
    MAX_RETRY_WAIT_SECONDS = 30 * 60

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

    def _extract_pdf_pages(self, path: Path) -> list[BookTextPage]:
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise ValueError("PDF extraction requires the pypdf package") from e

        reader = PdfReader(str(path))
        pages: list[BookTextPage] = []
        for index, page in enumerate(reader.pages, start=1):
            text = self._normalize_text(page.extract_text() or "")
            if text:
                pages.append(BookTextPage(number=index, text=text))

        return pages

    def _extract_epub_pages(self, path: Path) -> list[BookTextPage]:
        with ZipFile(path) as archive:
            html_files = sorted(
                name
                for name in archive.namelist()
                if name.lower().endswith((".html", ".htm", ".xhtml")) and not name.endswith("/")
            )
            pages: list[BookTextPage] = []
            for name in html_files:
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

    def _extract_pages(self, path: Path, extension: str) -> list[BookTextPage]:
        if extension not in SUPPORTED_TEXT_EXTRACTION_EXTENSIONS:
            raise ValueError(f"AI extraction is not supported for {extension} files yet")

        if extension == ".pdf":
            return self._extract_pdf_pages(path)
        if extension == ".epub":
            return self._extract_epub_pages(path)
        if extension == ".docx":
            return self._extract_docx_pages(path)
        if extension == ".odt":
            return self._extract_odt_pages(path)
        if extension in {".fb2", ".fb2.zip"}:
            return self._extract_fb2_pages(path)
        if extension in {".html", ".htm", ".mhtml", ".mht"}:
            return self._extract_html_pages(path)
        if extension == ".rtf":
            return self._extract_rtf_pages(path)

        return self._text_to_pseudo_pages(path.read_text(encoding="utf-8", errors="ignore"))

    def _build_chunks(self, pages: list[BookTextPage], pages_per_chunk: int) -> list[BookTextChunk]:
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

    def _chunk_message(self, book: UploadedBook, chunk: BookTextChunk, translate_language: str) -> str:
        return (
            f"Cookbook title: {book.name}\n"
            f"Original file name: {book.original_file_name}\n"
            f"Page range: {chunk.start_page}-{chunk.end_page}\n"
            f"Translate recipes to: {translate_language}\n\n"
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

    def _initial_chunk_states(self, book: UploadedBook, chunks: list[BookTextChunk]) -> dict[int, dict]:
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
            }

        return states

    @staticmethod
    def _state_int(state: dict, key: str) -> int:
        value = state.get(key)
        return value if isinstance(value, int) else 0

    def _chunk_error_summary(self, states: dict[int, dict]) -> str | None:
        errors: list[str] = []
        for state in sorted(states.values(), key=lambda item: self._state_int(item, "index")):
            status = state.get("status")
            error = state.get("error")
            if status not in {CHUNK_RETRYING, CHUNK_FAILED} or not error:
                continue

            prefix = f"pages {state.get('startPage')}-{state.get('endPage')}"
            if status == CHUNK_RETRYING and state.get("nextRetrySeconds"):
                prefix = f"{prefix} retrying in {state.get('nextRetrySeconds')}s"
            errors.append(f"{prefix}: {str(error)[:220]}")

        return "\n".join(errors)[-1000:] if errors else None

    def _save_progress(
        self,
        book: UploadedBook,
        states: dict[int, dict],
        status: str | None = None,
    ) -> None:
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
            r"(?:retry|try again|please retry)\s+in[^\d]*(\d+(?:\.\d+)?)\s*(milliseconds?|ms|seconds?|secs?|s|minutes?|mins?|m)?",
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
    def _short_error(error: Exception) -> str:
        message = str(error).replace("\n", " ").strip()
        return message[:500] if message else error.__class__.__name__

    async def _acquire_provider_slot(self, slots: list[ProviderSlot], lock: asyncio.Lock) -> ProviderSlot:
        while True:
            sleep_for = 0.25
            async with lock:
                now = time.monotonic()
                available_slots = [slot for slot in slots if not slot.busy]
                has_busy_slots = len(available_slots) != len(slots)

                if available_slots:
                    slot = min(available_slots, key=lambda item: item.available_at)
                    wait_seconds = max(slot.available_at - now, 0)
                    if wait_seconds <= 0:
                        slot.busy = True
                        return slot

                    sleep_for = 0.25 if has_busy_slots else min(wait_seconds, 30)

            await asyncio.sleep(sleep_for)

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
    ) -> ChunkWorkResult:
        try:
            response = await openai_service.get_response(
                prompt,
                self._chunk_message(book, chunk, translate_language),
                response_schema=OpenAIBookRecipeChunkParse,
                provider=slot.provider,
            )
        except Exception as e:
            retryable = self._is_retryable_error(e)
            if retryable:
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
            )

        return ChunkWorkResult(chunk=chunk, recipes=response.recipes if response else [], provider_label=slot.label)

    def _existing_recipe_for_book_chunk(self, recipe: Recipe) -> RecipeModel | None:
        source = recipe.source or ""
        query = (
            sa.select(RecipeModel)
            .where(
                RecipeModel.group_id == self.user.group_id,
                sa.func.lower(RecipeModel.name) == recipe.name.lower(),
                sa.func.lower(sa.func.coalesce(RecipeModel.source, "")) == source.lower(),
            )
            .limit(1)
        )
        return self.repos.session.execute(query).scalars().one_or_none()

    def _recipe_with_book_source(self, recipe: OpenAIRecipe, book: UploadedBook, chunk: BookTextChunk) -> OpenAIRecipe:
        source = recipe.source or f"{book.name}, pages {chunk.start_page}-{chunk.end_page}"
        created_by = recipe.created_by or book.name
        return recipe.model_copy(update={"source": source, "created_by": created_by})

    def _save_openai_recipe(self, openai_recipe: OpenAIRecipe, book: UploadedBook, chunk: BookTextChunk) -> Recipe | None:
        if not self.openai_recipe_service._has_minimum_recipe_data(openai_recipe):
            return None

        recipe = self.openai_recipe_service._convert_recipe(self._recipe_with_book_source(openai_recipe, book, chunk))
        recipe = cleaner.clean(recipe, self.translator)

        if self._existing_recipe_for_book_chunk(recipe):
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

    async def extract_recipes(
        self,
        book_id: UUID4,
        uploaded_books_root: Path,
        pages_per_chunk: int = 10,
        translate_language: str = "Hebrew",
    ) -> None:
        book: UploadedBook | None = None

        try:
            book = self._get_book(book_id)
            path = self._book_file_path(book, uploaded_books_root)
            if not path.exists():
                raise ValueError("Uploaded book file is missing")

            book.extraction_status = EXTRACTION_PROCESSING
            book.extraction_pages_per_chunk = pages_per_chunk
            book.extraction_total_chunks = 0
            book.extraction_completed_chunks = 0
            book.extraction_failed_chunks = 0
            book.extraction_retry_count = 0
            book.extraction_recipes_found = 0
            book.extraction_recipes_created = 0
            book.extraction_error = None
            book.extraction_started_at = get_utc_now()
            book.extraction_completed_at = None
            self._save_book(book)

            pages = self._extract_pages(path, book.extension)
            if not pages:
                raise ValueError("No extractable text was found in this book")

            chunks = self._build_chunks(pages, pages_per_chunk)
            if not chunks:
                raise ValueError("No chunks could be created from this book")

            chunk_states = self._initial_chunk_states(book, chunks)
            self._save_progress(book, chunk_states, EXTRACTION_PROCESSING)

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
                    try:
                        chunk = queue.get_nowait()
                    except asyncio.QueueEmpty:
                        return

                    slot = await self._acquire_provider_slot(provider_slots, provider_lock)
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

                        async with state_lock:
                            state = chunk_states[chunk.index]
                            attempts = self._state_int(state, "attempts")

                            if result.error:
                                if result.retryable and attempts < self.MAX_CHUNK_ATTEMPTS:
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
                                        }
                                    )
                                    self._save_progress(book, chunk_states)
                                    await queue.put(chunk)
                                else:
                                    state.update(
                                        {
                                            "status": CHUNK_FAILED,
                                            "error": result.error,
                                            "provider": result.provider_label,
                                            "nextRetrySeconds": None,
                                        }
                                    )
                                    self._save_progress(book, chunk_states)
                            else:
                                recipes_created = 0
                                for recipe in result.recipes:
                                    if self._save_openai_recipe(recipe, book, result.chunk):
                                        recipes_created += 1

                                state.update(
                                    {
                                        "status": CHUNK_COMPLETED,
                                        "recipesFound": len(result.recipes),
                                        "recipesCreated": recipes_created,
                                        "error": None,
                                        "provider": result.provider_label,
                                        "nextRetrySeconds": None,
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

            failed_chunks = sum(1 for state in chunk_states.values() if state.get("status") == CHUNK_FAILED)
            book.extraction_status = EXTRACTION_PARTIAL_FAILED if failed_chunks else EXTRACTION_COMPLETED
            book.extraction_completed_at = get_utc_now()
            self._save_progress(book, chunk_states, book.extraction_status)

        except Exception as e:
            self.repos.session.rollback()
            self.logger.error(f"Failed to extract recipes from uploaded book {book_id}")
            self.logger.exception(e)
            if book is not None:
                self._set_failed(book, str(e))


class UploadedBookTranslator(UploadedBookRecipeExtractor):
    TRANSLATED_CHUNKS_DIR = "translated-chunks"

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

    def _initial_translation_chunk_states(self, book: UploadedBook, chunks: list[BookTextChunk]) -> dict[int, dict]:
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
            }

        return states

    def _save_translation_progress(
        self,
        book: UploadedBook,
        states: dict[int, dict],
        status: str | None = None,
    ) -> None:
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
    ) -> str:
        file_name = self._translated_chunk_file_name(chunk)
        payload = {
            "chunk": chunk.index,
            "startPage": chunk.start_page,
            "endPage": chunk.end_page,
            "pages": [{"page": page, "text": text} for page, text in sorted(pages.items())],
        }
        work_dir.joinpath(file_name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return file_name

    def _read_translated_chunk_pages(self, work_dir: Path, file_name: str) -> list[tuple[int, str]]:
        path = work_dir.joinpath(file_name).resolve()
        if not path.is_relative_to(work_dir.resolve()):
            raise ValueError("Invalid translated chunk file path")
        payload = json.loads(path.read_text(encoding="utf-8"))
        pages = payload.get("pages") if isinstance(payload, dict) else None
        if not isinstance(pages, list):
            return []

        translated_pages: list[tuple[int, str]] = []
        for page in pages:
            if not isinstance(page, dict):
                continue
            page_number = page.get("page")
            text = page.get("text")
            if isinstance(page_number, int) and isinstance(text, str):
                translated_pages.append((page_number, text))

        return translated_pages

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
            retryable = self._is_retryable_error(e)
            if retryable:
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
            )

        pages = {page.page: page.text for page in response.pages} if response else {}
        expected_pages = set(chunk.page_numbers)
        if not expected_pages.issubset(set(pages)):
            missing = ", ".join(str(page) for page in sorted(expected_pages - set(pages))[:10])
            return ChunkTranslationResult(
                chunk=chunk,
                pages=pages,
                provider_label=slot.label,
                error=f"AI translation response is missing page(s): {missing}",
                retryable=True,
                wait_seconds=None,
            )

        return ChunkTranslationResult(chunk=chunk, pages=pages, provider_label=slot.label)

    @staticmethod
    def _is_rtl_language(target_language: str) -> bool:
        language = target_language.lower()
        rtl_markers = ("hebrew", "עברית", "arabic", "ערבית", "farsi", "persian", "urdu", "yiddish")
        return any(marker in language for marker in rtl_markers)

    def _build_translated_book_html(
        self,
        book: UploadedBook,
        target_language: str,
        translated_pages: list[tuple[int, str]],
    ) -> str:
        direction = "rtl" if self._is_rtl_language(target_language) else "ltr"
        title = html.escape(f"{book.name} - {target_language}")
        source = html.escape(book.original_file_name)
        language = html.escape(target_language)
        page_sections: list[str] = []

        for page_number, text in translated_pages:
            page_title = html.escape(f"Page {page_number}")
            page_text = html.escape(text.strip())
            page_sections.append(
                "\n".join(
                    [
                        '<section class="page">',
                        f"<h2>{page_title}</h2>",
                        f"<pre>{page_text}</pre>",
                        "</section>",
                    ]
                )
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
      font-family: Arial, Helvetica, sans-serif;
      background: #f7f2e8;
      color: #241611;
    }}
    body {{
      margin: 0;
      padding: 32px 18px;
      line-height: 1.7;
    }}
    main {{
      max-width: 920px;
      margin: 0 auto;
      background: #fffdf8;
      border: 1px solid #eadfca;
      border-radius: 8px;
      padding: clamp(18px, 4vw, 44px);
      box-shadow: 0 8px 28px rgba(64, 42, 24, 0.08);
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: clamp(28px, 5vw, 44px);
    }}
    .meta {{
      color: #7d6d5d;
      margin-bottom: 32px;
    }}
    .page {{
      break-inside: avoid;
      border-top: 1px solid #eadfca;
      padding-top: 24px;
      margin-top: 24px;
    }}
    h2 {{
      color: #8f3f1f;
      font-size: 18px;
      margin: 0 0 12px;
    }}
    pre {{
      white-space: pre-wrap;
      word-wrap: break-word;
      font-family: inherit;
      margin: 0;
    }}
  </style>
</head>
<body>
  <main>
    <h1>{title}</h1>
    <div class="meta">Translated to {language} from {source}</div>
    {"".join(page_sections)}
  </main>
</body>
</html>
"""

    def _create_translated_book(
        self,
        book: UploadedBook,
        uploaded_books_root: Path,
        target_language: str,
        html_content: str,
    ) -> UploadedBook:
        translated_book_id = uuid4()
        file_name = f"{translated_book_id}.html"
        root = uploaded_books_root.joinpath(str(book.group_id)).resolve()
        target_dir = root.joinpath(str(translated_book_id)).resolve()
        if not target_dir.is_relative_to(root):
            raise ValueError("Invalid translated book target path")
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir.joinpath(file_name).resolve()
        if not target_path.is_relative_to(target_dir):
            raise ValueError("Invalid translated book file path")
        target_path.write_text(html_content, encoding="utf-8")

        translated_book = UploadedBook(
            group_id=book.group_id,
            household_id=book.household_id,
            user_id=book.user_id,
            name=f"{book.name} ({target_language})",
            file_name=file_name,
            original_file_name=f"{book.name} - {target_language}.html",
            extension=".html",
            content_type="text/html; charset=utf-8",
            size=target_path.stat().st_size,
            is_translated_book=True,
            translated_from_book_id=book.id,
            translation_language=target_language,
            translation_status=TRANSLATION_COMPLETED,
            translation_completed_at=get_utc_now(),
            session=self.repos.session,
        )
        translated_book.id = translated_book_id
        self.repos.session.add(translated_book)
        self.repos.session.commit()
        self.repos.session.refresh(translated_book)
        return translated_book

    async def translate_book(
        self,
        book_id: UUID4,
        uploaded_books_root: Path,
        pages_per_chunk: int = 10,
        target_language: str = "Hebrew",
    ) -> None:
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
            book.translation_total_chunks = 0
            book.translation_completed_chunks = 0
            book.translation_failed_chunks = 0
            book.translation_retry_count = 0
            book.translation_error = None
            book.translation_chunk_status = None
            book.translation_started_at = get_utc_now()
            book.translation_completed_at = None
            self._save_book(book)

            pages = self._extract_pages(path, book.extension)
            if not pages:
                raise ValueError("No extractable text was found in this book")

            chunks = self._build_chunks(pages, pages_per_chunk)
            if not chunks:
                raise ValueError("No chunks could be created from this book")

            work_dir = self._reset_translated_chunks_dir(uploaded_books_root, book, target_language)
            chunk_states = self._initial_translation_chunk_states(book, chunks)
            self._save_translation_progress(book, chunk_states, TRANSLATION_PROCESSING)

            openai_service = OpenAIService(self.repos)
            if not (openai_service.provider_settings and openai_service.provider_settings.ai_enabled):
                raise ValueError("AI provider is not configured")

            provider_slots = self._provider_slots(openai_service)
            prompt = openai_service.get_prompt("recipes.translate-book-chunk")

            queue: asyncio.Queue[BookTextChunk] = asyncio.Queue()
            for chunk in chunks:
                await queue.put(chunk)

            provider_lock = asyncio.Lock()
            state_lock = asyncio.Lock()

            async def worker() -> None:
                while True:
                    try:
                        chunk = queue.get_nowait()
                    except asyncio.QueueEmpty:
                        return

                    slot = await self._acquire_provider_slot(provider_slots, provider_lock)
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

                        async with state_lock:
                            state = chunk_states[chunk.index]
                            attempts = self._state_int(state, "attempts")

                            if result.error:
                                if result.retryable and attempts < self.MAX_CHUNK_ATTEMPTS:
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
                                        }
                                    )
                                    self._save_translation_progress(book, chunk_states)
                                    await queue.put(chunk)
                                else:
                                    state.update(
                                        {
                                            "status": CHUNK_FAILED,
                                            "error": result.error,
                                            "provider": result.provider_label,
                                            "nextRetrySeconds": None,
                                        }
                                    )
                                    self._save_translation_progress(book, chunk_states)
                            else:
                                translated_chunk_file = self._write_translated_chunk(work_dir, result.chunk, result.pages)
                                state.update(
                                    {
                                        "status": CHUNK_COMPLETED,
                                        "pagesTranslated": len(result.pages),
                                        "translatedChunkFile": translated_chunk_file,
                                        "error": None,
                                        "provider": result.provider_label,
                                        "nextRetrySeconds": None,
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

            failed_chunks = sum(1 for state in chunk_states.values() if state.get("status") == CHUNK_FAILED)
            if failed_chunks:
                book.translation_status = TRANSLATION_PARTIAL_FAILED
                book.translation_completed_at = get_utc_now()
                self._save_translation_progress(book, chunk_states, TRANSLATION_PARTIAL_FAILED)
                return

            translated_pages: list[tuple[int, str]] = []
            for state in sorted(chunk_states.values(), key=lambda item: self._state_int(item, "index")):
                file_name = state.get("translatedChunkFile")
                if isinstance(file_name, str):
                    translated_pages.extend(self._read_translated_chunk_pages(work_dir, file_name))

            translated_pages = sorted(dict(translated_pages).items())
            html_content = self._build_translated_book_html(book, target_language, translated_pages)
            translated_book = self._create_translated_book(book, uploaded_books_root, target_language, html_content)

            book.translated_book_id = translated_book.id
            book.translation_status = TRANSLATION_COMPLETED
            book.translation_completed_at = get_utc_now()
            self._save_translation_progress(book, chunk_states, TRANSLATION_COMPLETED)

        except Exception as e:
            self.repos.session.rollback()
            self.logger.error(f"Failed to translate uploaded book {book_id}")
            self.logger.exception(e)
            if book is not None:
                self._set_translation_failed(book, str(e))
