import json
import re
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
from .book_recipe_extractor import UploadedBookRecipeExtractor


class UploadedBookClassifier(BaseService):
    SAMPLE_MAX_CHARS = 45_000

    def __init__(
        self,
        repos: AllRepositories,
        user: PrivateUser,
        household: HouseholdInDB,
        translator: Translator,
    ) -> None:
        self.repos = repos
        self.user = user
        self.extractor = UploadedBookRecipeExtractor(repos, user, household, translator)
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

    @staticmethod
    def _book_path(book: UploadedBook, uploaded_books_root: Path) -> Path:
        root = uploaded_books_root.joinpath(str(book.group_id)).resolve()
        path = root.joinpath(str(book.id), book.file_name).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Invalid uploaded book file path")
        return path

    def _sample_text(self, book: UploadedBook, path: Path) -> str:
        try:
            pages = self.extractor._extract_pages(path, book.extension, max_pages=40)
        except Exception:
            self.logger.warning("Could not extract classification sample for %s", book.id, exc_info=True)
            return ""

        selected = pages[:8]
        contents_pattern = re.compile(r"\b(contents?|table of contents|chapters?)\b|תוכן|פרקים", re.IGNORECASE)
        selected_numbers = {page.number for page in selected}
        for page in pages[:40]:
            if page.number not in selected_numbers and contents_pattern.search(page.text):
                selected.append(page)
                selected_numbers.add(page.number)
            if len(selected) >= 12:
                break

        sample = "\n\n".join(f"[Page {page.number}]\n{page.text}" for page in selected)
        return sample[: self.SAMPLE_MAX_CHARS]

    async def classify(self, book_id: UUID4, uploaded_books_root: Path) -> None:
        book = self._get_book(book_id)
        book.classification_status = "processing"
        book.classification_error = None
        self.repos.session.add(book)
        self.repos.session.commit()

        try:
            openai_service = OpenAIService(self.repos)
            if not (openai_service.provider_settings and openai_service.provider_settings.ai_enabled):
                raise ValueError("No default AI provider configured")

            sample = self._sample_text(book, self._book_path(book, uploaded_books_root))
            prompt = (
                "Classify a cooking book for a personal searchable library. Use the title, filename, table of contents "
                "and sample pages together. Return concise metadata. Do not claim Michelin or restaurant affiliation "
                "unless the supplied text supports it. Categories and tags should be useful search labels."
            )
            message = (
                f"Book title: {book.name}\nOriginal filename: {book.original_file_name}\n"
                f"File type: {book.extension}\n\nSample:\n"
                f"{sample or '[No extractable sample; classify cautiously from title.]'}"
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
