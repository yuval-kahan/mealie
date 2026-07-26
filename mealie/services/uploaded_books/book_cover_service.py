import asyncio
import json
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import quote, urlsplit

import httpx
from PIL import Image, ImageOps

from mealie.db.models.household.uploaded_book import UploadedBook
from mealie.pkgs import safehttp
from mealie.repos.repository_factory import AllRepositories
from mealie.services._base_service import BaseService

BOOK_COVER_FILE_NAME = "cover.webp"
BOOK_COVER_MAX_BYTES = 12 * 1024 * 1024
BOOK_COVER_MAX_PIXELS = 30_000_000
BOOK_COVER_SEARCH_LIMIT = 10


class UploadedBookCoverService(BaseService):
    """Find and cache a stable local cover for uploaded and translated books."""

    def __init__(self, repos: AllRepositories):
        self.repos = repos
        super().__init__()

    @staticmethod
    def cover_path(uploaded_books_root: Path, book: UploadedBook) -> Path:
        root = uploaded_books_root.joinpath(str(book.group_id)).resolve()
        book_dir = root.joinpath(str(book.id)).resolve()
        if not book_dir.is_relative_to(root):
            raise ValueError("Invalid uploaded book cover path")
        return book_dir.joinpath(BOOK_COVER_FILE_NAME)

    @staticmethod
    def _metadata(book: UploadedBook) -> dict:
        try:
            value = json.loads(book.book_metadata_json or "{}")
        except (TypeError, ValueError):
            return {}
        return value if isinstance(value, dict) else {}

    def _save_metadata(self, book: UploadedBook, source: str, source_url: str | None = None) -> None:
        metadata = self._metadata(book)
        metadata["cover_file_name"] = BOOK_COVER_FILE_NAME
        metadata["cover_source"] = source
        if source_url:
            metadata["cover_source_url"] = source_url
        else:
            metadata.pop("cover_source_url", None)
        book.book_metadata_json = json.dumps(metadata, ensure_ascii=False)
        self.repos.session.add(book)
        self.repos.session.commit()
        self.repos.session.refresh(book)

    async def save_content(
        self,
        book: UploadedBook,
        uploaded_books_root: Path,
        content: bytes,
        source: str = "upload",
    ) -> bool:
        if not content or len(content) > BOOK_COVER_MAX_BYTES:
            raise ValueError("Cookbook cover is empty or exceeds the size limit")
        target = self.cover_path(uploaded_books_root, book)
        target.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(self._write_cover, content, target)
        self._save_metadata(book, source)
        return True

    async def save_url(self, book: UploadedBook, uploaded_books_root: Path, url: str) -> bool:
        normalized_url = url.strip()
        parts = urlsplit(normalized_url)
        if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
            raise ValueError("A valid HTTP or HTTPS cover address is required")
        target = self.cover_path(uploaded_books_root, book)
        target.parent.mkdir(parents=True, exist_ok=True)
        limits = httpx.Limits(max_connections=2, max_keepalive_connections=1)
        async with httpx.AsyncClient(
            transport=safehttp.AsyncSafeTransport(impersonate="chrome"),
            timeout=20.0,
            follow_redirects=True,
            limits=limits,
        ) as client:
            if not await self._download_cover(client, normalized_url, target):
                raise ValueError("The cookbook cover could not be downloaded")
        self._save_metadata(book, "url", normalized_url)
        return True

    async def refresh_cover(self, book: UploadedBook, uploaded_books_root: Path) -> bool:
        target = self.cover_path(uploaded_books_root, book)
        backup = target.with_suffix(".previous.webp")
        backup.unlink(missing_ok=True)
        if target.exists():
            target.replace(backup)
        try:
            if await self.ensure_cover(book, uploaded_books_root):
                backup.unlink(missing_ok=True)
                return True
            if backup.exists():
                backup.replace(target)
            return False
        except Exception:
            if backup.exists():
                backup.replace(target)
            raise

    async def ensure_cover(self, book: UploadedBook, uploaded_books_root: Path) -> bool:
        target = self.cover_path(uploaded_books_root, book)
        if target.exists() and target.stat().st_size > 0:
            return True

        target.parent.mkdir(parents=True, exist_ok=True)
        metadata = self._metadata(book)
        candidates = await self._cover_candidates(book, metadata)
        if not candidates:
            return False

        limits = httpx.Limits(max_connections=4, max_keepalive_connections=2)
        async with httpx.AsyncClient(
            transport=safehttp.AsyncSafeTransport(impersonate="chrome"),
            timeout=12.0,
            follow_redirects=True,
            limits=limits,
        ) as client:
            for url, source in candidates[:BOOK_COVER_SEARCH_LIMIT]:
                if await self._download_cover(client, url, target):
                    self._save_metadata(book, source, url)
                    return True

        return False

    async def _cover_candidates(self, book: UploadedBook, metadata: dict) -> list[tuple[str, str]]:
        classification = metadata.get("classification") if isinstance(metadata.get("classification"), dict) else {}
        author = str(classification.get("author_or_chef") or "").strip()
        restaurant = str(classification.get("restaurant") or "").strip()
        title = self._clean_title(book.name)
        if not author and " - " in title:
            possible_title, possible_author = title.rsplit(" - ", 1)
            if possible_title.strip() and possible_author.strip():
                title = possible_title.strip()
                author = possible_author.strip()

        candidates: list[tuple[str, str]] = []
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            candidates.extend(await self._open_library_candidates(client, title, author))
            if candidates:
                return candidates

            candidates.extend(await self._google_books_candidates(client, title, author))
            if candidates:
                return candidates

            queries = [
                " ".join(value for value in (title, author, "cookbook cover") if value),
                " ".join(value for value in (author, restaurant, "chef restaurant food") if value),
                " ".join(value for value in (title, restaurant, "cooking food") if value),
            ]
            for query in queries:
                if query.strip():
                    candidates.extend(await self._openverse_candidates(client, query))
                if len(candidates) >= BOOK_COVER_SEARCH_LIMIT:
                    break

        deduped: list[tuple[str, str]] = []
        seen: set[str] = set()
        for url, source in candidates:
            if url in seen:
                continue
            seen.add(url)
            deduped.append((url, source))
        return deduped

    @staticmethod
    def _clean_title(name: str) -> str:
        title = name.strip()
        for suffix in (" (Hebrew)", " - Hebrew", " (עברית)", " - עברית"):
            if title.casefold().endswith(suffix.casefold()):
                title = title[: -len(suffix)].strip()
        return title

    async def _open_library_candidates(
        self,
        client: httpx.AsyncClient,
        title: str,
        author: str,
    ) -> list[tuple[str, str]]:
        try:
            response = await client.get(
                "https://openlibrary.org/search.json",
                params={
                    "title": title,
                    "author": author or None,
                    "limit": 5,
                    "fields": "title,author_name,cover_i",
                },
                headers={"User-Agent": "Mealie cookbook cover lookup"},
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            self.logger.exception("Failed to search Open Library for a cookbook cover")
            return []

        return [
            (f"https://covers.openlibrary.org/b/id/{document['cover_i']}-L.jpg", "openlibrary")
            for document in payload.get("docs", [])
            if document.get("cover_i")
        ]

    async def _google_books_candidates(
        self,
        client: httpx.AsyncClient,
        title: str,
        author: str,
    ) -> list[tuple[str, str]]:
        query = f'intitle:"{title}"'
        if author:
            query += f' inauthor:"{author}"'
        try:
            response = await client.get(
                "https://www.googleapis.com/books/v1/volumes",
                params={"q": query, "maxResults": 5, "printType": "books"},
                headers={"User-Agent": "Mealie cookbook cover lookup"},
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            self.logger.exception("Failed to search Google Books for a cookbook cover")
            return []

        candidates: list[tuple[str, str]] = []
        for item in payload.get("items", []):
            links = item.get("volumeInfo", {}).get("imageLinks", {})
            url = links.get("extraLarge") or links.get("large") or links.get("medium") or links.get("thumbnail")
            if url:
                candidates.append((str(url).replace("http://", "https://"), "google-books"))
        return candidates

    async def _openverse_candidates(self, client: httpx.AsyncClient, query: str) -> list[tuple[str, str]]:
        try:
            response = await client.get(
                "https://api.openverse.org/v1/images/",
                params={"q": query, "page_size": 6, "mature": "false"},
                headers={"User-Agent": "Mealie cookbook cover lookup"},
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            self.logger.exception("Failed to search Openverse for a related cookbook image")
            return []

        candidates: list[tuple[str, str]] = []
        for result in payload.get("results", []):
            url = result.get("thumbnail") or result.get("url")
            if isinstance(url, str) and url.lower().startswith(("http://", "https://")):
                candidates.append((url, f"openverse:{quote(query[:80])}"))
        return candidates

    async def _download_cover(self, client: httpx.AsyncClient, url: str, target: Path) -> bool:
        try:
            chunks: list[bytes] = []
            total = 0
            async with client.stream("GET", url, headers={"User-Agent": "Mealie cookbook cover cache"}) as response:
                if response.status_code != 200:
                    return False
                if "image" not in response.headers.get("content-type", "").lower():
                    return False
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > BOOK_COVER_MAX_BYTES:
                        return False
                    chunks.append(chunk)
            await asyncio.to_thread(self._write_cover, b"".join(chunks), target)
            return target.exists() and target.stat().st_size > 0
        except Exception:
            self.logger.exception("Failed to cache cookbook cover from %s", url)
            return False

    @staticmethod
    def _write_cover(content: bytes, target: Path) -> None:
        with Image.open(BytesIO(content)) as image:
            if image.width * image.height > BOOK_COVER_MAX_PIXELS:
                raise ValueError("Cookbook cover exceeds the pixel limit")
            image = ImageOps.exif_transpose(image).convert("RGB")
            image.thumbnail((1600, 2200), Image.Resampling.LANCZOS)
            with NamedTemporaryFile(delete=False, dir=target.parent, suffix=".webp") as temp_file:
                temp_path = Path(temp_file.name)
            try:
                image.save(temp_path, "WEBP", quality=88, method=6)
                temp_path.replace(target)
            finally:
                temp_path.unlink(missing_ok=True)
