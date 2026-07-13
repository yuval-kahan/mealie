import asyncio
import shutil
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import UUID4
from sqlalchemy import select
from starlette.responses import FileResponse, RedirectResponse

from mealie.core.dependencies.dependencies import get_current_user
from mealie.db.models._model_utils.datetime import get_utc_now
from mealie.db.models.household.uploaded_book import UploadedBook
from mealie.db.models.recipe import RecipeModel
from mealie.db.models.recipe.api_extras import ApiExtras
from mealie.routes._base import controller
from mealie.routes._base.base_controllers import BasePublicController
from mealie.schema.cookbook.uploaded_book import (
    AICookbookGenerateRequest,
    UploadedBookExtractRequest,
    UploadedBookOut,
    UploadedBookRecipeDeleteRequest,
    UploadedBookRecipeDeleteResponse,
    UploadedBookRecipeSummary,
    UploadedBookTranslateRequest,
)
from mealie.schema.household.household import HouseholdInDB
from mealie.schema.response.pagination import PaginationQuery
from mealie.schema.user import PrivateUser
from mealie.services.household_services.shopping_lists import ShoppingListService
from mealie.services.recipe.recipe_service import RecipeService
from mealie.services.uploaded_books import (
    AICookbookBuilder,
    UploadedBookClassifier,
    UploadedBookCoverService,
    UploadedBookRecipeExtractor,
    UploadedBookTranslator,
)
from mealie.services.uploaded_books.book_recipe_extractor import (
    EXTRACTION_CANCELLED,
    TRANSLATION_CANCELLED,
    parse_book_source_page_range,
)

router = APIRouter(prefix="/households/uploaded-books", tags=["Households: Uploaded Books"])

BOOK_MEDIA_TYPES = {
    ".7z": "application/x-7z-compressed",
    ".azw": "application/vnd.amazon.ebook",
    ".azw3": "application/vnd.amazon.ebook",
    ".azw4": "application/vnd.amazon.ebook",
    ".cb7": "application/x-7z-compressed",
    ".cbr": "application/vnd.comicbook-rar",
    ".cbt": "application/x-tar",
    ".cbz": "application/vnd.comicbook+zip",
    ".djv": "image/vnd.djvu",
    ".djvu": "image/vnd.djvu",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".epub": "application/epub+zip",
    ".fb2": "application/x-fictionbook+xml",
    ".fb2.zip": "application/zip",
    ".htm": "text/html",
    ".html": "text/html",
    ".lit": "application/x-ms-reader",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".mht": "message/rfc822",
    ".mhtml": "message/rfc822",
    ".mobi": "application/x-mobipocket-ebook",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".pdb": "application/vnd.palm",
    ".pdf": "application/pdf",
    ".rar": "application/vnd.rar",
    ".rtf": "application/rtf",
    ".txt": "text/plain",
    ".zip": "application/zip",
}
INLINE_BOOK_EXTENSIONS = {".htm", ".html", ".pdf", ".txt"}
SUPPORTED_BOOK_FORMATS = ", ".join(sorted(extension.removeprefix(".").upper() for extension in BOOK_MEDIA_TYPES))


def get_book_extension(file_name: str) -> str:
    lower_file_name = file_name.lower()
    for extension in sorted(BOOK_MEDIA_TYPES, key=len, reverse=True):
        if lower_file_name.endswith(extension):
            return extension

    return Path(lower_file_name).suffix


def get_book_stem(file_name: str, extension: str) -> str:
    if extension and file_name.lower().endswith(extension):
        return file_name[: -len(extension)]

    return Path(file_name).stem


@controller(router)
class UploadedBooksController(BasePublicController):
    user: PrivateUser = Depends(get_current_user)

    @property
    def group_id(self) -> UUID4:
        return self.user.group_id

    @property
    def household_id(self) -> UUID4:
        return self.user.household_id

    @property
    def household(self) -> HouseholdInDB:
        return self.repos.households.get_one(self.household_id)

    def _books_root(self) -> Path:
        root = self.folders.DATA_DIR.joinpath("uploaded-books", str(self.group_id))
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _book_file_path(self, book: UploadedBook | UploadedBookOut) -> Path:
        root = self._books_root().resolve()
        path = root.joinpath(str(book.id), book.file_name).resolve()

        if not path.is_relative_to(root):
            raise HTTPException(status.HTTP_400_BAD_REQUEST)

        return path

    def _book_dir_path(self, book: UploadedBook | UploadedBookOut) -> Path:
        root = self._books_root().resolve()
        path = root.joinpath(str(book.id)).resolve()

        if not path.is_relative_to(root) or path == root:
            raise HTTPException(status.HTTP_400_BAD_REQUEST)

        return path

    def _assert_book_not_processing(self, book: UploadedBook) -> None:
        if book.extraction_status in {"processing", "retrying"}:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Book extraction is already running")
        if book.translation_status in {"processing", "retrying"}:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Book translation is already running")

    @staticmethod
    def _assert_valid_page_range(page_start: int | None, page_end: int | None) -> None:
        if page_start is not None and page_end is not None and page_end < page_start:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="End page must be greater than or equal to start page",
            )

    def _cancel_active_extraction(self, book: UploadedBook) -> UploadedBook:
        if book.extraction_status not in {"processing", "retrying"}:
            return book

        book.extraction_status = EXTRACTION_CANCELLED
        book.extraction_error = "Cancelled by user"
        book.extraction_completed_at = get_utc_now()
        self.session.add(book)
        self.session.commit()
        self.session.refresh(book)
        return book

    def _cancel_active_translation(self, book: UploadedBook) -> UploadedBook:
        if book.translation_status not in {"processing", "retrying"}:
            return book

        book.translation_status = TRANSLATION_CANCELLED
        book.translation_error = "Cancelled by user"
        book.translation_completed_at = get_utc_now()
        self.session.add(book)
        self.session.commit()
        self.session.refresh(book)
        return book

    def _get_book_or_404(self, book_id: UUID4) -> UploadedBook:
        book = (
            self.session.execute(
                select(UploadedBook).where(UploadedBook.id == book_id, UploadedBook.group_id == self.group_id)
            )
            .scalars()
            .one_or_none()
        )
        if book is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND)

        return book

    def _preferred_reading_book(self, book: UploadedBook, page: int | None = None) -> UploadedBook:
        if book.is_translated_book or not book.translated_book_id:
            return book

        translated_book = (
            self.session.execute(
                select(UploadedBook).where(
                    UploadedBook.id == book.translated_book_id,
                    UploadedBook.group_id == self.group_id,
                    UploadedBook.is_translated_book.is_(True),
                    UploadedBook.translation_status == "completed",
                )
            )
            .scalars()
            .one_or_none()
        )
        if translated_book is None or not self._book_file_path(translated_book).exists():
            return book

        if page is not None:
            if translated_book.translation_page_start and page < translated_book.translation_page_start:
                return book
            if translated_book.translation_page_end and page > translated_book.translation_page_end:
                return book

        return translated_book

    def _book_open_redirect(self, book: UploadedBook, page: int | None = None) -> RedirectResponse:
        target_book = self._preferred_reading_book(book, page)
        target_url = f"/api/households/uploaded-books/{target_book.id}/file"
        if page is not None:
            if target_book.is_translated_book and target_book.extension in {".htm", ".html"}:
                target_url += f"#page-{page}"
            elif target_book.extension == ".pdf":
                target_url += f"#page={page}"
        return RedirectResponse(target_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    def _book_from_recipe_source(self, source: str) -> UploadedBook | None:
        normalized_source = source.strip().casefold()
        if not normalized_source:
            return None

        books = (
            self.session.execute(
                select(UploadedBook).where(
                    UploadedBook.group_id == self.group_id,
                    UploadedBook.is_translated_book.is_(False),
                )
            )
            .scalars()
            .all()
        )
        ranked_books: list[tuple[int, UploadedBook]] = []
        for book in books:
            possible_names = {
                (book.name or "").strip().casefold(),
                get_book_stem(book.original_file_name or "", book.extension or "").strip().casefold(),
            }
            score = 0
            for name in possible_names:
                if not name:
                    continue
                if normalized_source.startswith(name):
                    score = max(score, 10_000 + len(name))
                elif name in normalized_source:
                    score = max(score, len(name))
            if score:
                ranked_books.append((score, book))

        return max(ranked_books, key=lambda item: item[0])[1] if ranked_books else None

    def _book_recipe_models(self, book: UploadedBook) -> list[RecipeModel]:
        source_prefix = (book.name or "").strip().lower()
        linked_by_extra = RecipeModel.extras.any(
            sa.and_(
                ApiExtras.key_name == "uploadedBookSourceId",
                ApiExtras.value == str(book.id),
            )
        )
        linked_by_source = sa.func.lower(sa.func.coalesce(RecipeModel.source, "")).startswith(
            source_prefix,
            autoescape=True,
        )
        return list(
            self.session.execute(
                select(RecipeModel)
                .where(
                    RecipeModel.group_id == self.group_id,
                    RecipeModel.household_id == self.household_id,
                    sa.or_(linked_by_extra, linked_by_source),
                )
                .order_by(RecipeModel.name)
            )
            .scalars()
            .unique()
            .all()
        )

    def _books_to_delete(self, book: UploadedBook) -> list[UploadedBook]:
        books_by_id = {book.id: book}

        if not book.is_translated_book:
            translated_books = (
                self.session.execute(
                    select(UploadedBook).where(
                        UploadedBook.group_id == self.group_id,
                        (
                            (UploadedBook.translated_from_book_id == book.id)
                            | (UploadedBook.id == book.translated_book_id)
                        ),
                    )
                )
                .scalars()
                .all()
            )
            books_by_id.update({translated_book.id: translated_book for translated_book in translated_books})

        return list(books_by_id.values())

    def _reset_translation_links(self, deleted_book_ids: set[UUID4]) -> None:
        linked_books = (
            self.session.execute(
                select(UploadedBook).where(
                    UploadedBook.group_id == self.group_id,
                    UploadedBook.id.not_in(deleted_book_ids),
                    (
                        UploadedBook.translated_book_id.in_(deleted_book_ids)
                        | UploadedBook.translated_from_book_id.in_(deleted_book_ids)
                    ),
                )
            )
            .scalars()
            .all()
        )

        for linked_book in linked_books:
            if linked_book.translated_book_id in deleted_book_ids:
                linked_book.translated_book_id = None
                linked_book.translation_status = "not_started"
                linked_book.translation_total_chunks = 0
                linked_book.translation_completed_chunks = 0
                linked_book.translation_failed_chunks = 0
                linked_book.translation_retry_count = 0
                linked_book.translation_error = None
                linked_book.translation_chunk_status = None
                linked_book.translation_started_at = None
                linked_book.translation_completed_at = None
            if linked_book.translated_from_book_id in deleted_book_ids:
                linked_book.translated_from_book_id = None

            self.session.add(linked_book)

    @router.get("", response_model=list[UploadedBookOut])
    def get_all(self) -> list[UploadedBookOut]:
        books = (
            self.session.execute(
                select(UploadedBook)
                .where(UploadedBook.group_id == self.group_id)
                .order_by(UploadedBook.created_at.desc(), UploadedBook.name.asc())
            )
            .scalars()
            .all()
        )

        return [UploadedBookOut.model_validate(book) for book in books]

    @router.post("/generate", response_model=list[UploadedBookOut], status_code=status.HTTP_201_CREATED)
    async def generate_ai_cookbook(self, data: AICookbookGenerateRequest) -> list[UploadedBookOut]:
        builder = AICookbookBuilder(self.repos, self.user, self.household, self.translator)
        try:
            return await builder.generate(data, self.folders.DATA_DIR.joinpath("uploaded-books"))
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @router.post("/{book_id}/refresh-ai", response_model=list[UploadedBookOut])
    async def refresh_ai_cookbook(self, book_id: UUID4) -> list[UploadedBookOut]:
        book = self._get_book_or_404(book_id)
        builder = AICookbookBuilder(self.repos, self.user, self.household, self.translator)
        try:
            return await builder.refresh(book, self.folders.DATA_DIR.joinpath("uploaded-books"))
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @router.post("/{book_id}/classify", response_model=UploadedBookOut, status_code=status.HTTP_202_ACCEPTED)
    def classify_book(self, book_id: UUID4, bg_tasks: BackgroundTasks) -> UploadedBookOut:
        book = self._get_book_or_404(book_id)
        if book.classification_status == "processing":
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Book classification is already running")
        book.classification_status = "processing"
        book.classification_error = None
        self.session.add(book)
        self.session.commit()
        self.session.refresh(book)

        classifier = UploadedBookClassifier(self.repos, self.user, self.household, self.translator)
        response_language = book.translation_language if book.is_translated_book else None
        bg_tasks.add_task(
            classifier.classify,
            book.id,
            self.folders.DATA_DIR.joinpath("uploaded-books"),
            response_language,
        )
        return UploadedBookOut.model_validate(book)

    @router.post("/{book_id}/extract-recipes", response_model=UploadedBookOut, status_code=status.HTTP_202_ACCEPTED)
    def extract_recipes(
        self,
        book_id: UUID4,
        data: UploadedBookExtractRequest,
        bg_tasks: BackgroundTasks,
    ) -> UploadedBookOut:
        book = self._get_book_or_404(book_id)
        if book.extraction_status in {"processing", "retrying"}:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Book extraction is already running")
        if book.translation_status in {"processing", "retrying"}:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Book translation is already running")
        self._assert_valid_page_range(data.page_start, data.page_end)

        resume = (
            book.extraction_status == "partial_failed"
            and book.extraction_pages_per_chunk == data.pages_per_chunk
            and (book.extraction_translate_language or data.translate_language) == data.translate_language
            and book.extraction_page_start == data.page_start
            and book.extraction_page_end == data.page_end
            and bool(book.extraction_chunk_status)
        )

        book.extraction_status = "processing"
        book.extraction_pages_per_chunk = data.pages_per_chunk
        book.extraction_translate_language = data.translate_language
        book.extraction_page_start = data.page_start
        book.extraction_page_end = data.page_end
        if not resume:
            book.extraction_total_chunks = 0
            book.extraction_completed_chunks = 0
            book.extraction_failed_chunks = 0
            book.extraction_retry_count = 0
            book.extraction_recipes_found = 0
            book.extraction_recipes_created = 0
            book.extraction_chunk_status = None
        book.extraction_error = None
        book.extraction_started_at = book.extraction_started_at if resume else None
        book.extraction_completed_at = None

        self.session.add(book)
        self.session.commit()
        self.session.refresh(book)

        extractor = UploadedBookRecipeExtractor(self.repos, self.user, self.household, self.translator)
        bg_tasks.add_task(
            extractor.extract_recipes,
            book.id,
            self.folders.DATA_DIR.joinpath("uploaded-books"),
            data.pages_per_chunk,
            data.translate_language,
            resume,
            data.page_start,
            data.page_end,
            data.auto_recipe_images,
            data.include_item_images,
            data.include_ai_tips,
            data.create_shopping_lists,
            data.organize_shopping_lists_with_ai,
        )

        return UploadedBookOut.model_validate(book)

    @router.post("/{book_id}/extract-recipes/cancel", response_model=UploadedBookOut)
    def cancel_extract_recipes(self, book_id: UUID4) -> UploadedBookOut:
        book = self._get_book_or_404(book_id)
        return UploadedBookOut.model_validate(self._cancel_active_extraction(book))

    @router.post("/{book_id}/translate/cancel", response_model=UploadedBookOut)
    def cancel_translate_book(self, book_id: UUID4) -> UploadedBookOut:
        book = self._get_book_or_404(book_id)
        return UploadedBookOut.model_validate(self._cancel_active_translation(book))

    @router.post("/{book_id}/translate", response_model=UploadedBookOut, status_code=status.HTTP_202_ACCEPTED)
    def translate_book(
        self,
        book_id: UUID4,
        data: UploadedBookTranslateRequest,
        bg_tasks: BackgroundTasks,
    ) -> UploadedBookOut:
        book = self._get_book_or_404(book_id)
        if book.is_translated_book:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Translated books cannot be translated again")
        self._assert_book_not_processing(book)
        self._assert_valid_page_range(data.page_start, data.page_end)

        resume = (
            book.translation_status == "partial_failed"
            and book.translation_pages_per_chunk == data.pages_per_chunk
            and (book.translation_language or data.target_language) == data.target_language
            and book.translation_page_start == data.page_start
            and book.translation_page_end == data.page_end
            and bool(book.translation_chunk_status)
        )

        book.translation_status = "processing"
        book.translation_language = data.target_language
        book.translation_pages_per_chunk = data.pages_per_chunk
        book.translation_page_start = data.page_start
        book.translation_page_end = data.page_end
        if not resume:
            book.translation_total_chunks = 0
            book.translation_completed_chunks = 0
            book.translation_failed_chunks = 0
            book.translation_retry_count = 0
            book.translation_chunk_status = None
        book.translation_error = None
        book.translation_started_at = book.translation_started_at if resume else None
        book.translation_completed_at = None

        self.session.add(book)
        self.session.commit()
        self.session.refresh(book)

        translator = UploadedBookTranslator(self.repos, self.user, self.household, self.translator)
        bg_tasks.add_task(
            translator.translate_book,
            book.id,
            self.folders.DATA_DIR.joinpath("uploaded-books"),
            data.pages_per_chunk,
            data.target_language,
            resume,
            data.page_start,
            data.page_end,
        )

        return UploadedBookOut.model_validate(book)

    @router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_book(self, book_id: UUID4) -> None:
        book = self._get_book_or_404(book_id)
        books_to_delete = self._books_to_delete(book)

        for item in books_to_delete:
            self._assert_book_not_processing(item)

        deleted_book_ids = {item.id for item in books_to_delete}
        book_dirs = [self._book_dir_path(item) for item in books_to_delete]

        self._reset_translation_links(deleted_book_ids)
        for item in books_to_delete:
            item.translated_from_book_id = None
            item.translated_book_id = None
            self.session.add(item)
        self.session.flush()

        for item in books_to_delete:
            self.session.delete(item)

        self.session.commit()

        for book_dir in book_dirs:
            shutil.rmtree(book_dir, ignore_errors=True)

    @router.post("", response_model=UploadedBookOut, status_code=status.HTTP_201_CREATED)
    async def upload_book(
        self,
        bg_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        name: str | None = Form(None),
        classify_with_ai: bool = Form(True),
    ) -> UploadedBookOut:
        original_file_name = file.filename or ""
        extension = get_book_extension(original_file_name)
        if extension not in BOOK_MEDIA_TYPES:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported book format. Supported formats: {SUPPORTED_BOOK_FORMATS}",
            )

        book_id = uuid4()
        stored_file_name = f"{book_id}{extension}"
        target_dir = self._books_root().joinpath(str(book_id))
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir.joinpath(stored_file_name).resolve()

        if not target_path.is_relative_to(self._books_root().resolve()):
            raise HTTPException(status.HTTP_400_BAD_REQUEST)

        def copy_upload() -> int:
            copied_size = 0
            with target_path.open("wb") as buffer:
                while chunk := file.file.read(1024 * 1024):
                    copied_size += len(chunk)
                    buffer.write(chunk)
            return copied_size

        try:
            size = await asyncio.to_thread(copy_upload)
        except Exception:
            target_path.unlink(missing_ok=True)
            raise
        finally:
            await file.close()

        if size == 0:
            target_path.unlink(missing_ok=True)
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

        book_name = (name or get_book_stem(original_file_name, extension) or "Uploaded book").strip()[:255]
        if not book_name:
            book_name = "Uploaded book"

        book = UploadedBook(
            group_id=self.group_id,
            household_id=self.household_id,
            user_id=self.user.id,
            name=book_name,
            file_name=stored_file_name,
            original_file_name=original_file_name or stored_file_name,
            extension=extension,
            content_type=file.content_type,
            size=size,
            session=self.session,
        )
        book.id = book_id

        try:
            self.session.add(book)
            self.session.commit()
            self.session.refresh(book)
        except Exception:
            self.session.rollback()
            target_path.unlink(missing_ok=True)
            raise

        if classify_with_ai:
            classifier = UploadedBookClassifier(self.repos, self.user, self.household, self.translator)
            bg_tasks.add_task(classifier.classify, book.id, self.folders.DATA_DIR.joinpath("uploaded-books"))

        return UploadedBookOut.model_validate(book)

    @router.get("/{book_id}/recipes", response_model=list[UploadedBookRecipeSummary])
    def get_extracted_book_recipes(self, book_id: UUID4) -> list[UploadedBookRecipeSummary]:
        book = self._get_book_or_404(book_id)
        return [UploadedBookRecipeSummary.model_validate(recipe) for recipe in self._book_recipe_models(book)]

    @router.post("/{book_id}/recipes/delete", response_model=UploadedBookRecipeDeleteResponse)
    def delete_extracted_book_recipes(
        self,
        book_id: UUID4,
        payload: UploadedBookRecipeDeleteRequest,
    ) -> UploadedBookRecipeDeleteResponse:
        book = self._get_book_or_404(book_id)
        self._assert_book_not_processing(book)
        requested_ids = set(payload.recipe_ids)
        book_recipes = self._book_recipe_models(book)
        selected_recipes = [recipe for recipe in book_recipes if recipe.id in requested_ids]
        skipped_count = len(requested_ids) - len(selected_recipes)
        selected_recipe_ids = {str(recipe.id) for recipe in selected_recipes}

        shopping_service = None
        selected_shopping_list_ids = []
        if payload.delete_shopping_lists and selected_recipe_ids:
            shopping_service = ShoppingListService(self.repos)
            shopping_lists = shopping_service.shopping_lists.page_all(PaginationQuery(page=1, per_page=-1))
            selected_shopping_list_ids = [
                shopping_list.id
                for shopping_list in shopping_lists.items
                if str((shopping_list.extras or {}).get("aiCreatedFromUploadedBookId") or "") == str(book.id)
                and str((shopping_list.extras or {}).get("aiCreatedFromRecipeId") or "") in selected_recipe_ids
            ]

        if payload.delete_recipes and selected_recipes:
            recipe_service = RecipeService(self.repos, self.user, self.household, self.translator)
            recipe_service.delete_many([recipe.slug for recipe in selected_recipes])

        deleted_shopping_lists = []
        if shopping_service and selected_shopping_list_ids:
            deleted_shopping_lists = shopping_service.shopping_lists.delete_many(selected_shopping_list_ids)

        remaining_count = len(book_recipes)
        if payload.delete_recipes:
            remaining_count = max(0, len(book_recipes) - len(selected_recipes))
            book.extraction_recipes_created = remaining_count
            self.session.add(book)
            self.session.commit()

        return UploadedBookRecipeDeleteResponse(
            deleted_count=len(selected_recipes) if payload.delete_recipes else 0,
            deleted_shopping_list_count=len(deleted_shopping_lists),
            remaining_count=remaining_count,
            skipped_count=skipped_count,
            deleted_recipe_ids=[recipe.id for recipe in selected_recipes] if payload.delete_recipes else [],
            deleted_shopping_list_ids=[shopping_list.id for shopping_list in deleted_shopping_lists],
        )

    @router.get("/source/open", response_class=RedirectResponse)
    def open_book_from_recipe_source(
        self,
        source: str,
        page: int | None = None,
    ) -> RedirectResponse:
        if page is not None and page < 1:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Page must be greater than zero")

        book = self._book_from_recipe_source(source)
        if book is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Uploaded cookbook was not found")

        parsed_page, _ = parse_book_source_page_range(source)
        return self._book_open_redirect(book, page or parsed_page)

    @router.get("/{book_id}/open", response_class=RedirectResponse)
    def open_book_at_page(self, book_id: UUID4, page: int | None = None) -> RedirectResponse:
        if page is not None and page < 1:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Page must be greater than zero")
        return self._book_open_redirect(self._get_book_or_404(book_id), page)

    @router.get("/{book_id}/file", response_class=FileResponse)
    def get_book_file(self, book_id: UUID4) -> FileResponse:
        book = self._get_book_or_404(book_id)
        path = self._book_file_path(book)

        if not path.exists():
            raise HTTPException(status.HTTP_404_NOT_FOUND)

        return FileResponse(
            path,
            media_type=BOOK_MEDIA_TYPES.get(book.extension, book.content_type or "application/octet-stream"),
            filename=book.original_file_name,
            content_disposition_type="inline"
            if book.extension in INLINE_BOOK_EXTENSIONS or (book.is_translated_book and book.extension == ".html")
            else "attachment",
            headers={"X-Content-Type-Options": "nosniff"},
        )

    @router.get("/{book_id}/cover", response_class=FileResponse)
    def get_book_cover(self, book_id: UUID4) -> FileResponse:
        book = self._get_book_or_404(book_id)
        path = UploadedBookCoverService.cover_path(self.folders.DATA_DIR.joinpath("uploaded-books"), book)
        if not path.exists():
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        return FileResponse(
            path,
            media_type="image/webp",
            content_disposition_type="inline",
            headers={"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff"},
        )
