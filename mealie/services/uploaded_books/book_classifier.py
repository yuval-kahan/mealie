import asyncio
import json
from pathlib import Path

import httpx
import sqlalchemy as sa
from pydantic import UUID4

from mealie.db.models._model_utils.datetime import get_utc_now
from mealie.db.models.household.uploaded_book import UploadedBook
from mealie.lang.providers import Translator
from mealie.repos.repository_factory import AllRepositories
from mealie.schema.household.household import HouseholdInDB
from mealie.schema.openai.general import OpenAIBookClassification
from mealie.schema.user import PrivateUser
from mealie.services._base_service import BaseService
from mealie.services.openai import OpenAIService

from .book_cover_service import UploadedBookCoverService


class UploadedBookClassifier(BaseService):
    def __init__(
        self,
        repos: AllRepositories,
        user: PrivateUser,
        household: HouseholdInDB,
        translator: Translator,
    ) -> None:
        self.repos = repos
        self.user = user
        super().__init__()

    def _get_book(self, book_id: UUID4) -> UploadedBook:
        book = self.repos.session.execute(
            sa.select(UploadedBook).where(
                UploadedBook.id == book_id,
                UploadedBook.group_id == self.user.group_id,
            )
        ).scalar_one_or_none()
        if not book:
            raise ValueError("Uploaded book was not found")
        return book

    async def _catalog_metadata(self, book: UploadedBook) -> dict:
        """Fetch a small, bounded metadata sample without sending or reading book pages."""
        title = UploadedBookCoverService._clean_title(book.name)
        limits = httpx.Limits(max_connections=2, max_keepalive_connections=1)
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, limits=limits) as client:
            open_library, google_books = await asyncio.gather(
                self._open_library_metadata(client, title),
                self._google_books_metadata(client, title),
            )
        return {
            "query_title": title,
            "open_library": open_library,
            "google_books": google_books,
        }

    async def _open_library_metadata(self, client: httpx.AsyncClient, title: str) -> list[dict]:
        try:
            response = await client.get(
                "https://openlibrary.org/search.json",
                params={
                    "title": title,
                    "limit": 3,
                    "fields": "key,title,author_name,first_publish_year,subject,language,isbn,publisher,edition_count",
                },
                headers={"User-Agent": "Mealie cookbook metadata lookup"},
            )
            response.raise_for_status()
            documents = response.json().get("docs", [])
        except Exception as exc:
            self.logger.warning("Open Library cookbook metadata lookup failed: %s", exc)
            return []

        return [
            {
                "key": document.get("key"),
                "title": document.get("title"),
                "authors": (document.get("author_name") or [])[:5],
                "first_publish_year": document.get("first_publish_year"),
                "subjects": (document.get("subject") or [])[:20],
                "languages": (document.get("language") or [])[:8],
                "publishers": (document.get("publisher") or [])[:5],
                "isbn": (document.get("isbn") or [])[:6],
                "edition_count": document.get("edition_count"),
            }
            for document in documents[:3]
        ]

    async def _google_books_metadata(self, client: httpx.AsyncClient, title: str) -> list[dict]:
        try:
            response = await client.get(
                "https://www.googleapis.com/books/v1/volumes",
                params={"q": f'intitle:"{title}"', "maxResults": 3, "printType": "books"},
                headers={"User-Agent": "Mealie cookbook metadata lookup"},
            )
            response.raise_for_status()
            items = response.json().get("items", [])
        except Exception as exc:
            self.logger.warning("Google Books cookbook metadata lookup failed: %s", exc)
            return []

        results: list[dict] = []
        for item in items[:3]:
            info = item.get("volumeInfo", {})
            results.append(
                {
                    "title": info.get("title"),
                    "subtitle": info.get("subtitle"),
                    "authors": (info.get("authors") or [])[:5],
                    "publisher": info.get("publisher"),
                    "published_date": info.get("publishedDate"),
                    "description": str(info.get("description") or "")[:1600],
                    "categories": (info.get("categories") or [])[:12],
                    "language": info.get("language"),
                    "identifiers": (info.get("industryIdentifiers") or [])[:6],
                    "info_link": info.get("infoLink"),
                }
            )
        return results

    async def classify(
        self,
        book_id: UUID4,
        uploaded_books_root: Path,
        response_language: str | None = None,
    ) -> None:
        book = self._get_book(book_id)
        book.classification_status = "processing"
        book.classification_error = None
        self.repos.session.add(book)
        self.repos.session.commit()

        try:
            openai_service = OpenAIService(self.repos)
            if not (openai_service.provider_settings and openai_service.provider_settings.ai_enabled):
                raise ValueError("No default AI provider configured")

            catalog_metadata = await self._catalog_metadata(book)
            output_language = response_language or "Hebrew"
            prompt = (
                "Classify a cooking book for a personal searchable library using its title, filename, "
                "and the bounded public-library catalog metadata supplied below. Never request or infer "
                "from book pages and never invent facts missing from reliable catalog metadata. Return "
                "concise metadata for sorting and filtering: cuisine, difficulty "
                "(beginner/intermediate/advanced/professional), book type, teaching level, chef/author, "
                "restaurant, techniques, categories and tags. Mark Michelin-related only when the "
                "supplied evidence clearly connects the author, chef, restaurant, or book to Michelin; "
                "prestige alone is not evidence. Use 'unspecified' for unknowns."
            )
            if output_language:
                prompt += (
                    f" Return summary, cuisines, difficulty, book type, teaching level, techniques, categories, tags, "
                    f"and other user-facing text in {output_language}. Keep proper names in their established form."
                )
            message = (
                f"Book title: {book.name}\nOriginal filename: {book.original_file_name}\n"
                f"File type: {book.extension}\n"
                f"Requested metadata language: {output_language}\n"
                "No book pages or book text are provided. Public catalog metadata may contain imperfect "
                "matches, so verify title/author alignment and ignore unrelated records:\n"
                f"{json.dumps(catalog_metadata, ensure_ascii=False)}"
            )
            response = await openai_service.get_response(
                prompt,
                message,
                response_schema=OpenAIBookClassification,
            )
            if not response:
                raise ValueError("AI returned an empty classification")

            existing = json.loads(book.book_metadata_json or "{}")
            if not isinstance(existing, dict):
                existing = {}
            existing["classification"] = response.model_dump()
            existing["catalog_lookup"] = catalog_metadata
            book.book_metadata_json = json.dumps(existing, ensure_ascii=False)
            book.classification_status = "completed"
            book.classification_error = None
            try:
                await UploadedBookCoverService(self.repos).ensure_cover(book, uploaded_books_root)
            except Exception:
                self.logger.exception("Failed to cache a cover for uploaded book %s", book_id)
        except Exception as exc:
            self.logger.exception("Failed to classify uploaded book %s", book_id)
            book.classification_status = "failed"
            book.classification_error = str(exc)[:1000]
        finally:
            book.classification_updated_at = get_utc_now()
            self.repos.session.add(book)
            self.repos.session.commit()
