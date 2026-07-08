import asyncio
from uuid import UUID

import sqlalchemy as sa

import mealie.db.models._all_models  # noqa: F401
from mealie.core.config import get_app_dirs
from mealie.core.root_logger import get_logger
from mealie.db.db_setup import session_context
from mealie.db.models._model_utils.datetime import get_utc_now
from mealie.db.models.household.uploaded_book import UploadedBook
from mealie.lang import get_locale_provider
from mealie.repos.all_repositories import get_repositories
from mealie.services.uploaded_books.book_recipe_extractor import (
    EXTRACTION_PROCESSING,
    EXTRACTION_RETRYING,
    TRANSLATION_PROCESSING,
    TRANSLATION_RETRYING,
    UploadedBookRecipeExtractor,
    UploadedBookTranslator,
)

logger = get_logger()

ACTIVE_EXTRACTION_STATUSES = {EXTRACTION_PROCESSING, EXTRACTION_RETRYING}
ACTIVE_TRANSLATION_STATUSES = {TRANSLATION_PROCESSING, TRANSLATION_RETRYING}

_scheduled_book_ai_tasks: set[asyncio.Task] = set()


def _due_uploaded_book_ai_jobs() -> list[tuple[str, UUID]]:
    now = get_utc_now()
    jobs: list[tuple[str, UUID]] = []

    with session_context() as session:
        books = (
            session.execute(
                sa.select(UploadedBook).where(
                    (UploadedBook.extraction_status.in_(ACTIVE_EXTRACTION_STATUSES))
                    | (UploadedBook.translation_status.in_(ACTIVE_TRANSLATION_STATUSES))
                )
            )
            .scalars()
            .all()
        )

        for book in books:
            if book.extraction_status in ACTIVE_EXTRACTION_STATUSES and UploadedBookRecipeExtractor.is_resume_due(
                book.extraction_status,
                book.extraction_chunk_status,
                now,
            ):
                jobs.append(("extraction", book.id))
                continue

            if book.translation_status in ACTIVE_TRANSLATION_STATUSES and UploadedBookRecipeExtractor.is_resume_due(
                book.translation_status,
                book.translation_chunk_status,
                now,
            ):
                jobs.append(("translation", book.id))

    return jobs


async def _run_uploaded_book_ai_job(operation: str, book_id: UUID) -> None:
    try:
        with session_context() as session:
            book = session.execute(sa.select(UploadedBook).where(UploadedBook.id == book_id)).scalars().one_or_none()
            if book is None:
                return

            repos = get_repositories(session, group_id=book.group_id, household_id=book.household_id)
            private_user = repos.users.get_one(book.user_id, "id", any_case=False)
            if private_user is None:
                logger.warning(
                    "Cannot resume uploaded book %s %s job because the owner user is missing",
                    operation,
                    book_id,
                )
                return

            household = repos.households.get_one(book.household_id)
            uploaded_books_root = get_app_dirs().DATA_DIR.joinpath("uploaded-books")
            translator = get_locale_provider()

            if operation == "extraction":
                service = UploadedBookRecipeExtractor(repos, private_user, household, translator)
                await service.extract_recipes(
                    book.id,
                    uploaded_books_root,
                    book.extraction_pages_per_chunk or 10,
                    book.extraction_translate_language or "Hebrew",
                    resume=True,
                )
            else:
                service = UploadedBookTranslator(repos, private_user, household, translator)
                await service.translate_book(
                    book.id,
                    uploaded_books_root,
                    book.translation_pages_per_chunk or 10,
                    book.translation_language or "Hebrew",
                    resume=True,
                )
    except Exception as e:
        logger.error("Failed to resume uploaded book %s job for book %s", operation, book_id)
        logger.exception(e)


async def resume_uploaded_book_ai_jobs() -> None:
    for operation, book_id in _due_uploaded_book_ai_jobs():
        service_cls = UploadedBookTranslator if operation == "translation" else UploadedBookRecipeExtractor
        if await service_cls.is_job_running(operation, book_id):
            continue

        logger.info("Resuming uploaded book %s job for book %s", operation, book_id)
        task = asyncio.create_task(_run_uploaded_book_ai_job(operation, book_id))
        _scheduled_book_ai_tasks.add(task)
        task.add_done_callback(lambda done_task: _scheduled_book_ai_tasks.discard(done_task))
