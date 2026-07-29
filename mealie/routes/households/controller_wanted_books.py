import json
import re
import shutil
from urllib.parse import urlsplit, urlunsplit

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from pydantic import UUID4
from starlette.responses import FileResponse

from mealie.db.models.household.wanted_book import WantedBook
from mealie.pkgs import safehttp
from mealie.routes._base import controller
from mealie.routes._base.base_controllers import BaseUserController
from mealie.schema.household.wanted_book import (
    WantedBookAIRequest,
    WantedBookBrowserPageRequest,
    WantedBookCreate,
    WantedBookImageURLRequest,
    WantedBookOut,
    WantedBookUpdate,
)
from mealie.schema.openai.wanted_book import OpenAIWantedBook
from mealie.schema.response.responses import ErrorResponse
from mealie.services.entity_image_service import EntityImageService
from mealie.services.openai import OpenAIService

router = APIRouter(prefix="/households/wanted-books", tags=["Households: Wanted Books"])

SPACE_RE = re.compile(r"\s+")
HTML_SCRIPT_STYLE_RE = re.compile(r"<(script|style).*?</\1>", re.IGNORECASE | re.DOTALL)
HTML_TAG_RE = re.compile(r"<[^>]+>")
ISBN_RE = re.compile(r"[^0-9Xx]")
MAX_PAGE_BYTES = 2 * 1024 * 1024
MAX_PAGE_TEXT = 250000


def normalize_terms(values: list[str], *, limit: int = 60) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        item = SPACE_RE.sub(" ", str(value).strip())[:160]
        key = item.casefold()
        if item and key not in seen:
            seen.add(key)
            result.append(item)
    return result[:limit]


def normalize_isbn(value: str | None, expected_length: int) -> str | None:
    normalized = ISBN_RE.sub("", value or "").upper()
    return normalized if len(normalized) == expected_length else None


def normalize_optional_url(value: str | None) -> str | None:
    raw = (value or "").strip()
    if not raw:
        return None
    parts = urlsplit(raw)
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse.respond("A valid HTTP or HTTPS address is required"),
        )
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, ""))


def clean_html_text(value: str) -> str:
    value = HTML_SCRIPT_STYLE_RE.sub(" ", value)
    value = re.sub(r"</(p|div|h[1-6]|li|br|nav|section)>", "\n", value, flags=re.IGNORECASE)
    value = HTML_TAG_RE.sub(" ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return SPACE_RE.sub(" ", value).strip()[:MAX_PAGE_TEXT]


@controller(router)
class WantedBooksController(BaseUserController):
    @property
    def image_service(self) -> EntityImageService:
        return EntityImageService(self.folders.DATA_DIR)

    def _image_path(self, book: WantedBook):
        return self.image_service.image_path("wanted-books", book.group_id, book.id)

    def _statement(self):
        return sa.select(WantedBook).where(WantedBook.group_id == self.group_id)

    def _get_or_404(self, book_id: UUID4) -> WantedBook:
        book = self.session.execute(self._statement().where(WantedBook.id == book_id)).scalar_one_or_none()
        if book is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        return book

    def _to_out(self, book: WantedBook) -> WantedBookOut:
        image_path = self._image_path(book)
        try:
            image_stat = image_path.stat()
        except FileNotFoundError:
            image_stat = None
        return WantedBookOut(
            id=book.id,
            group_id=book.group_id,
            household_id=book.household_id,
            user_id=book.user_id,
            title=book.title,
            subtitle=book.subtitle,
            authors=json.loads(book.authors_json or "[]"),
            isbn_10=book.isbn_10,
            isbn_13=book.isbn_13,
            publisher=book.publisher,
            published_year=book.published_year,
            summary=book.summary,
            source_url=book.source_url,
            cover_source_url=book.cover_source_url,
            categories=json.loads(book.categories_json or "[]"),
            tags=json.loads(book.tags_json or "[]"),
            notes=book.notes,
            has_image=bool(image_stat and image_stat.st_size > 0),
            image_version=str(image_stat.st_mtime_ns) if image_stat else None,
            created_at=book.created_at,
            updated_at=book.updated_at,
        )

    @staticmethod
    def _dedupe_key(data: WantedBookCreate | WantedBookUpdate) -> str:
        isbn_13 = normalize_isbn(data.isbn_13, 13)
        if isbn_13:
            return f"isbn13:{isbn_13}"
        isbn_10 = normalize_isbn(data.isbn_10, 10)
        if isbn_10:
            return f"isbn10:{isbn_10}"
        authors = "|".join(sorted(value.casefold() for value in normalize_terms(data.authors)))
        title = SPACE_RE.sub(" ", data.title.strip()).casefold()
        return f"title:{title}|authors:{authors}"[:600]

    def _apply(self, book: WantedBook, data: WantedBookCreate | WantedBookUpdate) -> None:
        book.title = SPACE_RE.sub(" ", data.title.strip())[:500]
        book.subtitle = SPACE_RE.sub(" ", (data.subtitle or "").strip())[:1000] or None
        book.authors_json = json.dumps(normalize_terms(data.authors), ensure_ascii=False)
        book.isbn_10 = normalize_isbn(data.isbn_10, 10)
        book.isbn_13 = normalize_isbn(data.isbn_13, 13)
        book.publisher = SPACE_RE.sub(" ", (data.publisher or "").strip())[:255] or None
        book.published_year = data.published_year
        book.summary = (data.summary or "").strip() or None
        book.source_url = normalize_optional_url(data.source_url)
        book.cover_source_url = normalize_optional_url(data.cover_source_url)
        book.categories_json = json.dumps(normalize_terms(data.categories), ensure_ascii=False)
        book.tags_json = json.dumps(normalize_terms(data.tags), ensure_ascii=False)
        book.notes = (data.notes or "").strip() or None
        book.dedupe_key = self._dedupe_key(data)

    def _save(self, data: WantedBookCreate) -> WantedBook:
        dedupe_key = self._dedupe_key(data)
        book = self.session.execute(
            self._statement().where(WantedBook.dedupe_key == dedupe_key)
        ).scalar_one_or_none()
        if book is None:
            book = WantedBook(
                group_id=self.group_id,
                household_id=self.household_id,
                user_id=self.user.id,
                title=data.title.strip(),
                dedupe_key=dedupe_key,
                session=self.session,
            )
        self._apply(book, data)
        self.session.add(book)
        self.session.commit()
        self.session.refresh(book)
        return book

    async def _fetch_url_text(self, url: str) -> str:
        chunks: list[bytes] = []
        total = 0
        limits = httpx.Limits(max_connections=2, max_keepalive_connections=1)
        async with httpx.AsyncClient(
            transport=safehttp.AsyncSafeTransport(impersonate="chrome"),
            timeout=30,
            follow_redirects=True,
            limits=limits,
        ) as client:
            async with client.stream("GET", url, headers={"User-Agent": "Mealie Wanted Books/1.0"}) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    remaining = MAX_PAGE_BYTES - total
                    if remaining <= 0:
                        break
                    chunks.append(chunk[:remaining])
                    total += min(len(chunk), remaining)
        return clean_html_text(b"".join(chunks).decode("utf-8", errors="replace"))

    async def _analyze(
        self,
        data: WantedBookAIRequest,
        *,
        page_title: str | None = None,
        page_text: str | None = None,
        page_image_url: str | None = None,
    ) -> WantedBookCreate:
        openai_service = OpenAIService(self.repos)
        if not (openai_service.provider_settings and openai_service.provider_settings.ai_enabled):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("OpenAI services are not enabled"),
            )
        source_url = normalize_optional_url(data.url)
        if source_url and not page_text:
            page_text = await self._fetch_url_text(source_url)
        message = "\n\n".join(
            part
            for part in (
                f"User request:\n{data.prompt.strip()}" if (data.prompt or "").strip() else "",
                f"Source URL: {source_url}" if source_url else "",
                f"Page title: {page_title.strip()}" if (page_title or "").strip() else "",
                f"Visible page content:\n{(page_text or '')[:MAX_PAGE_TEXT]}" if page_text else "",
                "Output language for summary, categories, and tags: Hebrew.",
            )
            if part
        )
        response = await openai_service.get_response(
            openai_service.get_prompt("books.parse-wanted-book"),
            message,
            response_schema=OpenAIWantedBook,
        )
        if not response or not response.is_book or not response.title.strip():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("The supplied page or request does not identify a book"),
            )
        return WantedBookCreate(
            title=response.title,
            subtitle=response.subtitle,
            authors=normalize_terms(response.authors),
            isbn_10=response.isbn_10,
            isbn_13=response.isbn_13,
            publisher=response.publisher,
            published_year=response.published_year,
            summary=response.summary,
            source_url=response.source_url or source_url,
            cover_source_url=response.cover_image_url or page_image_url,
            categories=normalize_terms(response.categories),
            tags=normalize_terms(response.tags),
        )

    async def _save_cover_if_available(self, book: WantedBook) -> None:
        if self._image_path(book).exists() or not book.cover_source_url:
            return
        try:
            book.cover_source_url = await self.image_service.save_url(
                self._image_path(book),
                book.cover_source_url,
            )
            self.session.add(book)
            self.session.commit()
        except (ValueError, httpx.HTTPError):
            self.logger.warning("Could not save cover for wanted book %s", book.title)

    @router.get("", response_model=list[WantedBookOut])
    def get_all(self, search: str | None = Query(None)) -> list[WantedBookOut]:
        statement = self._statement()
        query = (search or "").strip()
        if query:
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            statement = statement.where(
                sa.or_(
                    WantedBook.title.ilike(pattern, escape="\\"),
                    WantedBook.subtitle.ilike(pattern, escape="\\"),
                    WantedBook.authors_json.ilike(pattern, escape="\\"),
                    WantedBook.isbn_10.ilike(pattern, escape="\\"),
                    WantedBook.isbn_13.ilike(pattern, escape="\\"),
                    WantedBook.publisher.ilike(pattern, escape="\\"),
                    WantedBook.categories_json.ilike(pattern, escape="\\"),
                    WantedBook.tags_json.ilike(pattern, escape="\\"),
                )
            )
        rows = self.session.execute(
            statement.order_by(WantedBook.created_at.desc(), WantedBook.title.asc())
        ).scalars().all()
        return [self._to_out(book) for book in rows]

    @router.post("", response_model=WantedBookOut, status_code=status.HTTP_201_CREATED)
    async def create(self, data: WantedBookCreate) -> WantedBookOut:
        book = self._save(data)
        await self._save_cover_if_available(book)
        return self._to_out(book)

    @router.post("/ai-create", response_model=WantedBookOut, status_code=status.HTTP_201_CREATED)
    async def create_with_ai(self, data: WantedBookAIRequest) -> WantedBookOut:
        book = self._save(await self._analyze(data))
        await self._save_cover_if_available(book)
        return self._to_out(book)

    @router.post("/browser-page", response_model=WantedBookOut, status_code=status.HTTP_201_CREATED)
    async def create_from_browser_page(self, data: WantedBookBrowserPageRequest) -> WantedBookOut:
        book = self._save(
            await self._analyze(
                data,
                page_title=data.page_title,
                page_text=data.page_text,
                page_image_url=data.page_image_url,
            )
        )
        await self._save_cover_if_available(book)
        return self._to_out(book)

    @router.put("/{book_id}", response_model=WantedBookOut)
    async def update(self, book_id: UUID4, data: WantedBookUpdate) -> WantedBookOut:
        book = self._get_or_404(book_id)
        self._apply(book, data)
        self.session.add(book)
        self.session.commit()
        await self._save_cover_if_available(book)
        return self._to_out(book)

    @router.get("/{book_id}/image", response_class=FileResponse)
    def get_image(self, book_id: UUID4) -> FileResponse:
        book = self._get_or_404(book_id)
        path = self._image_path(book)
        if not path.exists():
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        return FileResponse(path, media_type="image/webp", content_disposition_type="inline")

    @router.post("/{book_id}/image", response_model=WantedBookOut)
    async def upload_image(self, book_id: UUID4, image: UploadFile = File(...)) -> WantedBookOut:
        book = self._get_or_404(book_id)
        content = await image.read(12 * 1024 * 1024 + 1)
        await image.close()
        try:
            await self.image_service.save_content(self._image_path(book), content)
        except ValueError as error:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ErrorResponse.respond(str(error))) from error
        return self._to_out(book)

    @router.post("/{book_id}/image-url", response_model=WantedBookOut)
    async def save_image_url(self, book_id: UUID4, data: WantedBookImageURLRequest) -> WantedBookOut:
        book = self._get_or_404(book_id)
        try:
            book.cover_source_url = await self.image_service.save_url(self._image_path(book), data.url)
        except (ValueError, httpx.HTTPError) as error:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ErrorResponse.respond(str(error))) from error
        self.session.add(book)
        self.session.commit()
        return self._to_out(book)

    @router.post("/{book_id}/image-auto", response_model=WantedBookOut)
    async def find_image(self, book_id: UUID4) -> WantedBookOut:
        book = self._get_or_404(book_id)
        query = " ".join([book.title, *json.loads(book.authors_json or "[]"), "book cover"])
        try:
            book.cover_source_url = await self.image_service.search_and_save_public_image(self._image_path(book), query)
        except (ValueError, httpx.HTTPError) as error:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ErrorResponse.respond(str(error))) from error
        self.session.add(book)
        self.session.commit()
        return self._to_out(book)

    @router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete(self, book_id: UUID4) -> None:
        book = self._get_or_404(book_id)
        image_dir = self._image_path(book).parent
        self.session.delete(book)
        self.session.commit()
        shutil.rmtree(image_dir, ignore_errors=True)
