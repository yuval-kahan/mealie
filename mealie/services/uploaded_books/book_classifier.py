import json
from pathlib import Path

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

            prompt = (
                "Classify a cooking book for a personal searchable library using ONLY its title and original filename. "
                "Do not request, infer from, or summarize the book contents. Return concise metadata and useful search "
                "categories and tags. Be conservative: use 'unspecified' when the title does not support a difficulty, "
                "teaching level, Michelin connection, restaurant, cuisine, chef, or technique."
            )
            if response_language:
                prompt += (
                    f" Return summary, cuisines, difficulty, book type, teaching level, techniques, categories, tags, "
                    f"and other user-facing text in {response_language}. Keep proper names in their established form."
                )
            message = (
                f"Book title: {book.name}\nOriginal filename: {book.original_file_name}\n"
                f"File type: {book.extension}\n"
                f"Requested metadata language: {response_language or 'same language as the title'}\n"
                "No book pages or book text are provided. Classify cautiously from these filename fields only."
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
