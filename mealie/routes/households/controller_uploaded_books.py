import asyncio
import json
import shutil
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import UUID4
from sqlalchemy import select
from starlette.responses import FileResponse, RedirectResponse

from mealie.core.dependencies.dependencies import get_current_user
from mealie.db.models._model_utils.datetime import get_utc_now
from mealie.db.models.household.shopping_list import ShoppingList
from mealie.db.models.household.uploaded_book import UploadedBook, UploadedBookCategory, UploadedBookReadingState
from mealie.db.models.recipe import RecipeModel
from mealie.db.models.recipe.api_extras import ApiExtras, ShoppingListExtras
from mealie.routes._base import controller
from mealie.routes._base.base_controllers import BasePublicController
from mealie.schema.cookbook.uploaded_book import (
    AICookbookGenerateRequest,
    UploadedBookCategoryCreate,
    UploadedBookCategoryOut,
    UploadedBookCategoryUpdate,
    UploadedBookCoverURLRequest,
    UploadedBookDeletePreview,
    UploadedBookExtractRequest,
    UploadedBookManualTranslationPageRequest,
    UploadedBookOut,
    UploadedBookReaderAskAIRequest,
    UploadedBookReaderAskAIResponse,
    UploadedBookReadingStateOut,
    UploadedBookReadingStateUpdate,
    UploadedBookRecipeCatalogImportRequest,
    UploadedBookRecipeCatalogRequest,
    UploadedBookRecipeCatalogResponse,
    UploadedBookRecipeDeleteRequest,
    UploadedBookRecipeDeleteResponse,
    UploadedBookRecipeSummary,
    UploadedBookTranslateRequest,
    UploadedBookUpdate,
)
from mealie.schema.household.household import HouseholdInDB
from mealie.schema.openai.general import OpenAIText
from mealie.schema.user import PrivateUser
from mealie.services.household_services.shopping_lists import ShoppingListService
from mealie.services.openai import OpenAIService
from mealie.services.recipe.recipe_service import RecipeService
from mealie.services.uploaded_books import (
    AICookbookBuilder,
    UploadedBookClassifier,
    UploadedBookCoverService,
    UploadedBookRecipeExtractor,
    UploadedBookTranslator,
)
from mealie.services.uploaded_books.book_library_categories import (
    BOOK_LIBRARY_CATEGORIES,
    UNCATEGORIZED_BOOK_CATEGORY,
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

    @staticmethod
    def _book_files_are_identical(left: Path, right: Path) -> bool:
        try:
            if left.stat().st_size != right.stat().st_size:
                return False
            with left.open("rb") as left_file, right.open("rb") as right_file:
                while True:
                    left_chunk = left_file.read(1024 * 1024)
                    right_chunk = right_file.read(1024 * 1024)
                    if left_chunk != right_chunk:
                        return False
                    if not left_chunk:
                        return True
        except OSError:
            return False

    def _duplicate_uploaded_book_candidates(self, extension: str, size: int) -> list[UploadedBook]:
        return list(
            self.session.execute(
                select(UploadedBook).where(
                    UploadedBook.group_id == self.group_id,
                    UploadedBook.household_id == self.household_id,
                    UploadedBook.extension == extension,
                    sa.or_(UploadedBook.size == size, UploadedBook.size == 0),
                )
            )
            .scalars()
            .all()
        )

    def _find_duplicate_uploaded_book(
        self,
        path: Path,
        candidates: list[UploadedBook],
    ) -> UploadedBook | None:
        for candidate in candidates:
            candidate_path = self._book_file_path(candidate)
            if candidate_path.is_file() and self._book_files_are_identical(path, candidate_path):
                return candidate
        return None

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

    def _get_book(self, book_id: UUID4) -> UploadedBook | None:
        return (
            self.session.execute(
                select(UploadedBook).where(UploadedBook.id == book_id, UploadedBook.group_id == self.group_id)
            )
            .scalars()
            .one_or_none()
        )

    def _get_book_or_404(self, book_id: UUID4) -> UploadedBook:
        book = self._get_book(book_id)
        if book is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND)

        return book

    def _ensure_book_categories(self) -> list[UploadedBookCategory]:
        categories = list(
            self.session.execute(
                select(UploadedBookCategory).where(
                    UploadedBookCategory.group_id == self.group_id,
                    UploadedBookCategory.household_id == self.household_id,
                )
            ).scalars().all()
        )
        initial_seed = not categories
        existing_names = {
            category.name.strip().casefold()
            for category in categories
            if category.parent_category_id is None
        }
        changed = False
        seed_names = (
            (*BOOK_LIBRARY_CATEGORIES, UNCATEGORIZED_BOOK_CATEGORY)
            if initial_seed
            else (UNCATEGORIZED_BOOK_CATEGORY,)
        )
        for position, name in enumerate(seed_names, start=1):
            if name.casefold() in existing_names:
                continue
            category = UploadedBookCategory(
                group_id=self.group_id,
                household_id=self.household_id,
                name=name,
                position=position,
                is_system=name == UNCATEGORIZED_BOOK_CATEGORY,
                is_protected=name == UNCATEGORIZED_BOOK_CATEGORY,
                session=self.session,
            )
            self.session.add(category)
            categories.append(category)
            existing_names.add(name.casefold())
            changed = True
        if changed:
            self.session.commit()
            categories = list(
                self.session.execute(
                    select(UploadedBookCategory).where(
                        UploadedBookCategory.group_id == self.group_id,
                        UploadedBookCategory.household_id == self.household_id,
                    )
                ).scalars().all()
            )
        return categories

    def _get_book_category_or_404(self, category_id: UUID4) -> UploadedBookCategory:
        category = self.session.execute(
            select(UploadedBookCategory).where(
                UploadedBookCategory.id == category_id,
                UploadedBookCategory.group_id == self.group_id,
                UploadedBookCategory.household_id == self.household_id,
            )
        ).scalar_one_or_none()
        if category is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Book category not found")
        return category

    def _assert_unique_book_category_name(
        self,
        name: str,
        parent_category_id: UUID4 | None,
        exclude_id: UUID4 | None = None,
    ) -> None:
        normalized = name.strip().casefold()
        if any(
            category.id != exclude_id
            and category.parent_category_id == parent_category_id
            and category.name.strip().casefold() == normalized
            for category in self._ensure_book_categories()
        ):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="A book category with this name already exists")

    def _reading_state_out(self, state: UploadedBookReadingState) -> UploadedBookReadingStateOut:
        def json_value(raw: str, fallback):
            try:
                value = json.loads(raw or "")
                return value if isinstance(value, type(fallback)) else fallback
            except (TypeError, ValueError):
                return fallback

        return UploadedBookReadingStateOut(
            id=state.id,
            book_id=state.book_id,
            user_id=state.user_id,
            current_page=state.current_page,
            current_page_index=state.current_page_index,
            scroll_offset=state.scroll_offset,
            current_chapter_id=state.current_chapter_id,
            reading_percent=state.reading_percent,
            completed_chapters=json_value(state.completed_chapters_json, []),
            total_chapters=state.total_chapters,
            notes=json_value(state.notes_json, []),
            highlights=json_value(state.highlights_json, []),
            preferences=json_value(state.preferences_json, {}),
            updated_at=state.updated_at,
        )

    def _get_or_create_reading_state(self, book: UploadedBook) -> UploadedBookReadingState:
        state = self.session.execute(
            select(UploadedBookReadingState).where(
                UploadedBookReadingState.book_id == book.id,
                UploadedBookReadingState.user_id == self.user.id,
            )
        ).scalar_one_or_none()
        if state is None:
            state = UploadedBookReadingState(
                book_id=book.id,
                group_id=self.group_id,
                user_id=self.user.id,
                session=self.session,
            )
            self.session.add(state)
            self.session.commit()
            self.session.refresh(state)
        return state

    def _get_existing_reading_state(self, book: UploadedBook) -> UploadedBookReadingState | None:
        return self.session.execute(
            select(UploadedBookReadingState).where(
                UploadedBookReadingState.book_id == book.id,
                UploadedBookReadingState.user_id == self.user.id,
            )
        ).scalar_one_or_none()

    def _preferred_reading_book(self, book: UploadedBook, page: int | None = None) -> UploadedBook:
        if book.is_translated_book or not book.translated_book_id:
            return book

        translated_book = (
            self.session.execute(
                select(UploadedBook).where(
                    UploadedBook.id == book.translated_book_id,
                    UploadedBook.group_id == self.group_id,
                    UploadedBook.is_translated_book.is_(True),
                    UploadedBook.translation_status.in_(("completed", "partial_failed")),
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
        automatic_resume = page is None
        target_book = self._preferred_reading_book(book, page)
        if page is None:
            reading_state = self._get_existing_reading_state(target_book)
            if reading_state is not None:
                page = reading_state.current_page or reading_state.current_page_index or None
        target_url = f"/api/households/uploaded-books/{target_book.id}/file"
        if page is not None:
            if automatic_resume:
                target_url += "?resume=1"
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

    def _book_recipe_models_by_id(
        self,
        book_id: UUID4,
        source_prefix: str | None = None,
    ) -> list[RecipeModel]:
        linked_by_extra = RecipeModel.extras.any(
            sa.and_(
                ApiExtras.key_name == "uploadedBookSourceId",
                ApiExtras.value == str(book_id),
            )
        )
        link_filters = [linked_by_extra]
        normalized_source_prefix = (source_prefix or "").strip().lower()
        if normalized_source_prefix:
            link_filters.append(
                sa.func.lower(sa.func.coalesce(RecipeModel.source, "")).startswith(
                    normalized_source_prefix,
                    autoescape=True,
                )
            )
        return list(
            self.session.execute(
                select(RecipeModel)
                .where(
                    RecipeModel.group_id == self.group_id,
                    RecipeModel.household_id == self.household_id,
                    sa.or_(*link_filters),
                )
                .order_by(RecipeModel.name)
            )
            .scalars()
            .unique()
            .all()
        )

    def _book_recipe_models(self, book: UploadedBook) -> list[RecipeModel]:
        return self._book_recipe_models_by_id(book.id, book.name)

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

    def _book_delete_preview(self, book: UploadedBook) -> UploadedBookDeletePreview:
        recipes = self._book_recipe_models(book)
        recipe_ids = {str(recipe.id) for recipe in recipes}
        linked_list_ids = self.session.execute(
            select(ShoppingListExtras.shopping_list_id)
            .join(ShoppingList, ShoppingList.id == ShoppingListExtras.shopping_list_id)
            .where(
                ShoppingList.group_id == self.group_id,
                sa.or_(
                    sa.and_(
                        ShoppingListExtras.key_name == "aiCreatedFromUploadedBookId",
                        ShoppingListExtras.value == str(book.id),
                    ),
                    sa.and_(
                        ShoppingListExtras.key_name == "aiCreatedFromRecipeId",
                        ShoppingListExtras.value.in_(recipe_ids),
                    ),
                ),
            )
            .distinct()
        ).scalars().all()
        linked_lists = self.session.execute(
            select(ShoppingList).where(
                ShoppingList.group_id == self.group_id,
                ShoppingList.id.in_(linked_list_ids),
            )
        ).scalars().all() if linked_list_ids else []
        return UploadedBookDeletePreview(
            recipe_ids=[recipe.id for recipe in recipes],
            recipe_names=[recipe.name or recipe.slug for recipe in recipes],
            shopping_list_ids=[shopping_list.id for shopping_list in linked_lists],
            shopping_list_names=[shopping_list.name or str(shopping_list.id) for shopping_list in linked_lists],
        )

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
        self._ensure_book_categories()
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

    @router.get("/categories", response_model=list[UploadedBookCategoryOut])
    def get_book_categories(self) -> list[UploadedBookCategoryOut]:
        categories = self._ensure_book_categories()
        categories.sort(key=lambda category: (category.position, category.name.casefold()))
        return [UploadedBookCategoryOut.model_validate(category) for category in categories]

    @router.post("/categories", response_model=UploadedBookCategoryOut, status_code=status.HTTP_201_CREATED)
    def create_book_category(self, data: UploadedBookCategoryCreate) -> UploadedBookCategoryOut:
        parent = self._get_book_category_or_404(data.parent_category_id) if data.parent_category_id else None
        if parent and parent.parent_category_id is not None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Book categories support one subcategory level")
        self._assert_unique_book_category_name(data.name, data.parent_category_id)
        max_position = self.session.execute(
            select(sa.func.max(UploadedBookCategory.position)).where(
                UploadedBookCategory.group_id == self.group_id,
                UploadedBookCategory.parent_category_id == data.parent_category_id,
            )
        ).scalar_one_or_none() or 0
        category = UploadedBookCategory(
            group_id=self.group_id,
            household_id=self.household_id,
            name=data.name,
            parent_category_id=data.parent_category_id,
            position=max_position + 1,
            session=self.session,
        )
        self.session.add(category)
        self.session.commit()
        self.session.refresh(category)
        return UploadedBookCategoryOut.model_validate(category)

    @router.patch("/categories/{category_id}", response_model=UploadedBookCategoryOut)
    def update_book_category(
        self,
        category_id: UUID4,
        data: UploadedBookCategoryUpdate,
    ) -> UploadedBookCategoryOut:
        category = self._get_book_category_or_404(category_id)
        if category.is_protected and (data.name is not None or "parent_category_id" in data.model_fields_set):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="This built-in book category cannot be changed")
        next_parent_id = (
            data.parent_category_id
            if "parent_category_id" in data.model_fields_set
            else category.parent_category_id
        )
        if next_parent_id == category.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="A category cannot be its own parent")
        if next_parent_id:
            parent = self._get_book_category_or_404(next_parent_id)
            if parent.parent_category_id is not None:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Book categories support one subcategory level")
            has_children = self.session.execute(
                select(sa.func.count()).select_from(UploadedBookCategory).where(
                    UploadedBookCategory.parent_category_id == category.id
                )
            ).scalar_one()
            if has_children:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    detail="A category with subcategories cannot become a subcategory",
                )
        next_name = data.name or category.name
        self._assert_unique_book_category_name(next_name, next_parent_id, category.id)
        if data.name is not None:
            category.name = data.name
        if "parent_category_id" in data.model_fields_set:
            category.parent_category_id = data.parent_category_id
        if data.position is not None:
            category.position = data.position
        self.session.add(category)
        self.session.commit()
        self.session.refresh(category)
        return UploadedBookCategoryOut.model_validate(category)

    @router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_book_category(
        self,
        category_id: UUID4,
        replacement_category_id: UUID4 | None = Query(None),
    ) -> None:
        category = self._get_book_category_or_404(category_id)
        if category.is_protected:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="This built-in book category cannot be deleted")
        replacement = (
            self._get_book_category_or_404(replacement_category_id)
            if replacement_category_id
            else None
        )
        if replacement and replacement.id == category.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Replacement category must be different")
        if replacement is None:
            if category.parent_category_id:
                replacement = self._get_book_category_or_404(category.parent_category_id)
            else:
                replacement = next(
                    item
                    for item in self._ensure_book_categories()
                    if item.name == UNCATEGORIZED_BOOK_CATEGORY
                )
        books = self.session.execute(
            select(UploadedBook).where(
                UploadedBook.group_id == self.group_id,
                UploadedBook.category_id == category.id,
            )
        ).scalars().all()
        for book in books:
            book.category_id = replacement.id
            self.session.add(book)
        children = self.session.execute(
            select(UploadedBookCategory).where(UploadedBookCategory.parent_category_id == category.id)
        ).scalars().all()
        for child in children:
            child.parent_category_id = None
            self.session.add(child)
        self.session.delete(category)
        self.session.commit()

    @router.patch("/{book_id}", response_model=UploadedBookOut)
    def update_book(self, book_id: UUID4, data: UploadedBookUpdate) -> UploadedBookOut:
        book = self._get_book_or_404(book_id)
        root_id = book.translated_from_book_id or book.id
        variants = self.session.execute(
            select(UploadedBook).where(
                UploadedBook.group_id == self.group_id,
                sa.or_(UploadedBook.id == root_id, UploadedBook.translated_from_book_id == root_id),
            )
        ).scalars().all()
        if data.name is not None:
            for variant in variants:
                variant.name = (
                    f"{data.name} ({variant.translation_language})"
                    if variant.is_translated_book and variant.translation_language
                    else data.name
                )
                self.session.add(variant)
        if "category_id" in data.model_fields_set:
            if data.category_id is not None:
                self._get_book_category_or_404(data.category_id)
            for variant in variants:
                variant.category_id = data.category_id
                self.session.add(variant)
        self.session.commit()
        self.session.refresh(book)
        return UploadedBookOut.model_validate(book)

    @router.get("/reading-states", response_model=list[UploadedBookReadingStateOut])
    def get_reading_states(self) -> list[UploadedBookReadingStateOut]:
        states = (
            self.session.execute(
                select(UploadedBookReadingState)
                .join(UploadedBook, UploadedBook.id == UploadedBookReadingState.book_id)
                .where(
                    UploadedBook.group_id == self.group_id,
                    UploadedBookReadingState.user_id == self.user.id,
                )
            )
            .scalars()
            .all()
        )
        return [self._reading_state_out(state) for state in states]

    @router.get("/{book_id}/reading-state", response_model=UploadedBookReadingStateOut)
    def get_reading_state(self, book_id: UUID4) -> UploadedBookReadingStateOut:
        return self._reading_state_out(self._get_or_create_reading_state(self._get_book_or_404(book_id)))

    @router.put("/{book_id}/reading-state", response_model=UploadedBookReadingStateOut)
    def update_reading_state(
        self,
        book_id: UUID4,
        data: UploadedBookReadingStateUpdate,
    ) -> UploadedBookReadingStateOut:
        state = self._get_or_create_reading_state(self._get_book_or_404(book_id))
        state.current_page = data.current_page
        state.current_page_index = data.current_page_index
        state.scroll_offset = data.scroll_offset
        state.current_chapter_id = data.current_chapter_id
        state.reading_percent = data.reading_percent
        state.completed_chapters_json = json.dumps(
            list(dict.fromkeys(data.completed_chapters)), ensure_ascii=False
        )
        state.total_chapters = data.total_chapters
        state.notes_json = json.dumps(
            [note.model_dump(mode="json") for note in data.notes], ensure_ascii=False
        )
        state.highlights_json = json.dumps(
            [highlight.model_dump(mode="json") for highlight in data.highlights], ensure_ascii=False
        )
        state.preferences_json = json.dumps(data.preferences.model_dump(mode="json"), ensure_ascii=False)
        self.session.add(state)
        self.session.commit()
        self.session.refresh(state)
        return self._reading_state_out(state)

    @router.post("/{book_id}/ask-ai", response_model=UploadedBookReaderAskAIResponse)
    async def ask_ai_about_selection(
        self,
        book_id: UUID4,
        data: UploadedBookReaderAskAIRequest,
    ) -> UploadedBookReaderAskAIResponse:
        book = self._get_book_or_404(book_id)
        openai_service = OpenAIService(self.repos)
        if not (openai_service.provider_settings and openai_service.provider_settings.ai_enabled):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="AI provider is not configured")

        length_guidance = {
            "short": "Answer in one or two concise sentences (up to about 60 words).",
            "medium": "Answer clearly in two to four short paragraphs (up to about 220 words).",
            "long": "Give a detailed but focused explanation (up to about 700 words).",
        }[data.answer_length]
        prompt = (
            "You are a careful reading assistant for a cookbook. Explain only what is supported by the "
            "selected passage and reliable culinary knowledge. If the question cannot be answered from the "
            "passage, say so plainly instead of inventing details. Use natural, everyday language. "
            f"Return the answer in {data.target_language}. {length_guidance}"
        )
        message = (
            f"Book: {book.name}\n"
            f"Page: {data.page or 'unknown'}\n"
            f"Question: {data.question.strip()}\n\n"
            f"Selected passage:\n{data.selected_text.strip()}"
        )
        try:
            response = await openai_service.get_response(prompt, message, response_schema=OpenAIText)
        except Exception as exc:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="AI could not answer this selection") from exc
        answer = (response.text if response else "").strip()
        if not answer:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="AI returned an empty answer")
        return UploadedBookReaderAskAIResponse(answer=answer[:6000])

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

    @router.put("/{book_id}/ai-recipes/{recipe_slug}", response_model=UploadedBookOut)
    async def add_recipe_to_ai_cookbook(self, book_id: UUID4, recipe_slug: str) -> UploadedBookOut:
        book = self._get_book_or_404(book_id)
        try:
            RecipeService(self.repos, self.user, self.household, self.translator).get_one(recipe_slug)
            return await AICookbookBuilder(
                self.repos, self.user, self.household, self.translator
            ).set_recipe_membership(
                book,
                recipe_slug,
                True,
                self.folders.DATA_DIR.joinpath("uploaded-books"),
            )
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @router.delete("/{book_id}/ai-recipes/{recipe_slug}", response_model=UploadedBookOut)
    async def remove_recipe_from_ai_cookbook(self, book_id: UUID4, recipe_slug: str) -> UploadedBookOut:
        book = self._get_book_or_404(book_id)
        try:
            return await AICookbookBuilder(
                self.repos, self.user, self.household, self.translator
            ).set_recipe_membership(
                book,
                recipe_slug,
                False,
                self.folders.DATA_DIR.joinpath("uploaded-books"),
            )
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
            data.allow_duplicate_recipes,
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

    @router.post("/{book_id}/translate/manual-page", response_model=UploadedBookOut)
    async def save_manual_translation_page(
        self,
        book_id: UUID4,
        data: UploadedBookManualTranslationPageRequest,
    ) -> UploadedBookOut:
        book = self._get_book_or_404(book_id)
        if book.is_translated_book:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Use the original book for translation changes")
        try:
            updated_book = await UploadedBookTranslator(
                self.repos,
                self.user,
                self.household,
                self.translator,
            ).save_manual_translation_page(
                book.id,
                self.folders.DATA_DIR.joinpath("uploaded-books"),
                data.page,
                data.text,
            )
        except ValueError as error:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
        return UploadedBookOut.model_validate(updated_book)

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
            book.translation_status in {"partial_failed", "failed"}
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
        try:
            book_metadata = json.loads(book.book_metadata_json or "{}")
        except (TypeError, ValueError):
            book_metadata = {}
        if not isinstance(book_metadata, dict):
            book_metadata = {}
        book_metadata["translation_options"] = {
            "include_linked_recipes": data.include_linked_recipes,
            "extract_recipes": data.extract_recipes,
            "auto_recipe_images": data.auto_recipe_images,
            "include_item_images": data.include_item_images,
            "include_ai_tips": data.include_ai_tips,
            "create_shopping_lists": data.create_shopping_lists,
            "organize_shopping_lists_with_ai": data.organize_shopping_lists_with_ai,
        }
        book.book_metadata_json = json.dumps(book_metadata, ensure_ascii=False)

        self.session.add(book)
        self.session.commit()
        self.session.refresh(book)

        translator = UploadedBookTranslator(self.repos, self.user, self.household, self.translator)
        bg_tasks.add_task(
            translator.translate_with_optional_extraction,
            book.id,
            self.folders.DATA_DIR.joinpath("uploaded-books"),
            data.pages_per_chunk,
            data.target_language,
            resume,
            data.page_start,
            data.page_end,
            data.include_linked_recipes,
            data.extract_recipes,
            data.auto_recipe_images,
            data.include_item_images,
            data.include_ai_tips,
            data.create_shopping_lists,
            data.organize_shopping_lists_with_ai,
        )

        return UploadedBookOut.model_validate(book)

    @router.get("/{book_id}/delete-preview", response_model=UploadedBookDeletePreview)
    def delete_book_preview(self, book_id: UUID4) -> UploadedBookDeletePreview:
        return self._book_delete_preview(self._get_book_or_404(book_id))

    @router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_book(
        self,
        book_id: UUID4,
        delete_recipes: bool = Query(False),
        delete_shopping_lists: bool = Query(False),
    ) -> None:
        book = self._get_book_or_404(book_id)
        books_to_delete = self._books_to_delete(book)

        for item in books_to_delete:
            self._assert_book_not_processing(item)

        linked = self._book_delete_preview(book)
        if delete_shopping_lists and linked.shopping_list_ids:
            self.repos.group_shopping_lists.delete_many(linked.shopping_list_ids)
        if delete_recipes and linked.recipe_ids:
            recipe_slugs = list(
                self.session.execute(
                    select(RecipeModel.slug).where(
                        RecipeModel.id.in_(linked.recipe_ids),
                        RecipeModel.group_id == self.group_id,
                    )
                ).scalars()
            )
            RecipeService(self.repos, self.user, self.household, self.translator).delete_many(recipe_slugs)

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
        category_id: UUID4 | None = Form(None),
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
            shutil.rmtree(target_dir, ignore_errors=True)
            raise
        finally:
            await file.close()

        if size == 0:
            shutil.rmtree(target_dir, ignore_errors=True)
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

        duplicate_candidates = self._duplicate_uploaded_book_candidates(extension, size)
        duplicate_book = await asyncio.to_thread(
            self._find_duplicate_uploaded_book,
            target_path,
            duplicate_candidates,
        )
        if duplicate_book is not None:
            shutil.rmtree(target_dir, ignore_errors=True)
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail={
                    "code": "uploaded_book_duplicate",
                    "existingBookId": str(duplicate_book.id),
                    "existingBookName": duplicate_book.name,
                },
            )

        book_name = (name or get_book_stem(original_file_name, extension) or "Uploaded book").strip()[:255]
        if not book_name:
            book_name = "Uploaded book"

        if category_id is not None:
            self._get_book_category_or_404(category_id)
        else:
            self._ensure_book_categories()

        book = UploadedBook(
            group_id=self.group_id,
            household_id=self.household_id,
            user_id=self.user.id,
            category_id=category_id,
            name=book_name,
            file_name=stored_file_name,
            original_file_name=original_file_name or stored_file_name,
            extension=extension,
            content_type=file.content_type,
            size=size,
            classification_status="processing" if classify_with_ai else "not_started",
            session=self.session,
        )
        book.id = book_id

        try:
            self.session.add(book)
            self.session.commit()
            self.session.refresh(book)
        except Exception:
            self.session.rollback()
            shutil.rmtree(target_dir, ignore_errors=True)
            raise

        if classify_with_ai:
            classifier = UploadedBookClassifier(self.repos, self.user, self.household, self.translator)
            bg_tasks.add_task(classifier.classify, book.id, self.folders.DATA_DIR.joinpath("uploaded-books"))

        return UploadedBookOut.model_validate(book)

    @router.get("/{book_id}/recipes", response_model=list[UploadedBookRecipeSummary])
    def get_extracted_book_recipes(self, book_id: UUID4) -> list[UploadedBookRecipeSummary]:
        book = self._get_book(book_id)
        recipes = self._book_recipe_models(book) if book else self._book_recipe_models_by_id(book_id)
        return [UploadedBookRecipeSummary.model_validate(recipe) for recipe in recipes]

    @router.post("/{book_id}/recipes/delete", response_model=UploadedBookRecipeDeleteResponse)
    def delete_extracted_book_recipes(
        self,
        book_id: UUID4,
        payload: UploadedBookRecipeDeleteRequest,
    ) -> UploadedBookRecipeDeleteResponse:
        book = self._get_book(book_id)
        if book:
            self._assert_book_not_processing(book)
        requested_ids = set(payload.recipe_ids)
        book_recipes = self._book_recipe_models(book) if book else self._book_recipe_models_by_id(book_id)
        selected_recipes = [recipe for recipe in book_recipes if recipe.id in requested_ids]
        skipped_count = len(requested_ids) - len(selected_recipes)
        selected_recipe_ids = {str(recipe.id) for recipe in selected_recipes}

        shopping_service = None
        selected_shopping_list_ids = []
        if payload.delete_shopping_lists and selected_recipe_ids:
            shopping_service = ShoppingListService(self.repos)
            selected_shopping_list_ids = self.session.execute(
                select(ShoppingListExtras.shopping_list_id)
                .join(ShoppingList, ShoppingList.id == ShoppingListExtras.shopping_list_id)
                .where(
                    ShoppingList.group_id == self.group_id,
                    ShoppingListExtras.key_name == "aiCreatedFromUploadedBookId",
                    ShoppingListExtras.value == str(book_id),
                    sa.exists(
                        select(ShoppingListExtras.id).where(
                            ShoppingListExtras.shopping_list_id == ShoppingList.id,
                            ShoppingListExtras.key_name == "aiCreatedFromRecipeId",
                            ShoppingListExtras.value.in_(selected_recipe_ids),
                        )
                    ),
                )
                .distinct()
            ).scalars().all()

        if payload.delete_recipes and selected_recipes:
            recipe_service = RecipeService(self.repos, self.user, self.household, self.translator)
            recipe_service.delete_many([recipe.slug for recipe in selected_recipes])

        deleted_shopping_lists = []
        if shopping_service and selected_shopping_list_ids:
            deleted_shopping_lists = shopping_service.shopping_lists.delete_many(selected_shopping_list_ids)

        remaining_count = len(book_recipes)
        if payload.delete_recipes:
            remaining_count = max(0, len(book_recipes) - len(selected_recipes))
            if book:
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

    @router.get("/{book_id}/assets/{file_name}", response_class=FileResponse)
    def get_translated_book_asset(self, book_id: UUID4, file_name: str) -> FileResponse:
        book = self._get_book_or_404(book_id)
        if not book.is_translated_book or book.extension not in {".htm", ".html"}:
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        if Path(file_name).name != file_name or not file_name.endswith(".webp"):
            raise HTTPException(status.HTTP_404_NOT_FOUND)

        book_dir = self._book_dir_path(book).resolve()
        assets_dir = book_dir.joinpath("assets").resolve()
        path = assets_dir.joinpath(file_name).resolve()
        if not assets_dir.is_relative_to(book_dir) or not path.is_relative_to(assets_dir) or not path.is_file():
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        return FileResponse(
            path,
            media_type="image/webp",
            content_disposition_type="inline",
            headers={
                "Cache-Control": "private, max-age=86400",
                "X-Content-Type-Options": "nosniff",
            },
        )

    @router.post("/{book_id}/cover", response_model=UploadedBookOut)
    async def upload_book_cover(self, book_id: UUID4, image: UploadFile = File(...)) -> UploadedBookOut:
        book = self._get_book_or_404(book_id)
        content = await image.read(12 * 1024 * 1024 + 1)
        await image.close()
        try:
            await UploadedBookCoverService(self.repos).save_content(
                book,
                self.folders.DATA_DIR.joinpath("uploaded-books"),
                content,
            )
        except ValueError as error:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
        return UploadedBookOut.model_validate(book)

    @router.post("/{book_id}/recipe-catalog", response_model=UploadedBookRecipeCatalogResponse)
    async def discover_recipe_catalog(
        self,
        book_id: UUID4,
        data: UploadedBookRecipeCatalogRequest,
    ) -> UploadedBookRecipeCatalogResponse:
        self._get_book_or_404(book_id)
        try:
            result = await UploadedBookRecipeExtractor(
                self.repos,
                self.user,
                self.household,
                self.translator,
            ).discover_recipe_catalog(
                book_id,
                self.folders.DATA_DIR.joinpath("uploaded-books"),
                data.query,
                data.target_language,
                data.refresh,
            )
        except ValueError as error:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
        return UploadedBookRecipeCatalogResponse.model_validate(result)

    @router.post(
        "/{book_id}/recipe-catalog/import",
        response_model=UploadedBookOut,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def import_recipe_catalog_selection(
        self,
        book_id: UUID4,
        data: UploadedBookRecipeCatalogImportRequest,
        bg_tasks: BackgroundTasks,
    ) -> UploadedBookOut:
        requested_book = self._get_book_or_404(book_id)
        source_book = (
            self._get_book_or_404(requested_book.translated_from_book_id)
            if requested_book.is_translated_book and requested_book.translated_from_book_id
            else requested_book
        )
        if source_book.extraction_status in {"processing", "retrying"}:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Book extraction is already running")
        if source_book.translation_status in {"processing", "retrying"}:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Book translation is already running")

        source_book.extraction_status = "processing"
        source_book.extraction_translate_language = data.target_language
        source_book.extraction_total_chunks = len(data.candidate_ids)
        source_book.extraction_completed_chunks = 0
        source_book.extraction_failed_chunks = 0
        source_book.extraction_recipes_found = 0
        source_book.extraction_recipes_created = 0
        source_book.extraction_error = None
        source_book.extraction_started_at = get_utc_now()
        source_book.extraction_completed_at = None
        self.session.add(source_book)
        self.session.commit()
        self.session.refresh(source_book)

        extractor = UploadedBookRecipeExtractor(self.repos, self.user, self.household, self.translator)
        bg_tasks.add_task(
            extractor.extract_selected_recipes,
            requested_book.id,
            self.folders.DATA_DIR.joinpath("uploaded-books"),
            data.candidate_ids,
            data.target_language,
            data.auto_recipe_images,
            data.include_item_images,
            data.include_ai_tips,
            data.create_shopping_lists,
            data.organize_shopping_lists_with_ai,
            data.allow_duplicate_recipes,
        )
        return UploadedBookOut.model_validate(source_book)

    @router.post("/{book_id}/cover-url", response_model=UploadedBookOut)
    async def save_book_cover_url(
        self,
        book_id: UUID4,
        data: UploadedBookCoverURLRequest,
    ) -> UploadedBookOut:
        book = self._get_book_or_404(book_id)
        try:
            await UploadedBookCoverService(self.repos).save_url(
                book,
                self.folders.DATA_DIR.joinpath("uploaded-books"),
                data.url,
            )
        except ValueError as error:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
        return UploadedBookOut.model_validate(book)

    @router.post("/{book_id}/cover-auto", response_model=UploadedBookOut)
    async def refresh_book_cover(self, book_id: UUID4) -> UploadedBookOut:
        book = self._get_book_or_404(book_id)
        if not await UploadedBookCoverService(self.repos).refresh_cover(
            book,
            self.folders.DATA_DIR.joinpath("uploaded-books"),
        ):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No suitable cookbook cover was found")
        return UploadedBookOut.model_validate(book)
