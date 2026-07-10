import asyncio
from collections import defaultdict
from collections.abc import AsyncIterable
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path as FileSystemPath
from shutil import copyfileobj, rmtree
from tempfile import mkdtemp
from uuid import UUID

import orjson
import sqlalchemy
import sqlalchemy.exc
from fastapi import (
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Path,
    Query,
    Request,
    status,
)
from fastapi.datastructures import UploadFile
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import UUID4, Field
from slugify import slugify

from mealie.core import exceptions
from mealie.core.dependencies import (
    get_temporary_zip_path,
)
from mealie.pkgs import cache
from mealie.repos.all_repositories import get_repositories
from mealie.routes._base import controller
from mealie.routes._base.routers import MealieCrudRoute, UserAPIRouter
from mealie.schema._mealie import MealieModel
from mealie.schema.cookbook.cookbook import ReadCookBook
from mealie.schema.household.group_shopping_list import (
    ShoppingListAddRecipeParamsBulk,
    ShoppingListCreate,
)
from mealie.schema.make_dependable import make_dependable
from mealie.schema.recipe import Recipe, ScrapeRecipe, ScrapeRecipeData
from mealie.schema.recipe.recipe import (
    CreateRecipe,
    CreateRecipeByUrlBulk,
    RecipeLastMade,
    RecipeSummary,
)
from mealie.schema.recipe.recipe_ai_search import RecipeAISearchRequest, RecipeAISearchResponse
from mealie.schema.recipe.recipe_asset import RecipeAsset
from mealie.schema.recipe.recipe_scraper import ScrapeRecipeTest
from mealie.schema.recipe.recipe_suggestion import RecipeSuggestionQuery, RecipeSuggestionResponse
from mealie.schema.recipe.request_helpers import (
    RecipeDuplicate,
    UpdateImageResponse,
)
from mealie.schema.response import PaginationBase, PaginationQuery
from mealie.schema.response.pagination import RecipeSearchQuery
from mealie.schema.response.responses import (
    ErrorResponse,
    SSEDataEventDone,
    SSEDataEventMessage,
    SSEDataEventStatus,
    SuccessResponse,
)
from mealie.services import urls
from mealie.services.event_bus_service.event_types import (
    EventOperation,
    EventRecipeBulkData,
    EventRecipeBulkReportData,
    EventRecipeData,
    EventTypes,
)
from mealie.services.household_services.shopping_lists import ShoppingListService
from mealie.services.item_image_service import ItemImageEnsureResult, ItemImageService
from mealie.services.recipe.recipe_data_service import (
    InvalidDomainError,
    NotAnImageError,
    RecipeDataService,
)
from mealie.services.recipe.video_asset_service import (
    VIDEO_ASSET_EXTENSIONS,
    VideoTranscodeError,
    normalize_video_asset,
)
from mealie.services.scraper.recipe_bulk_scraper import BulkImportVideo, RecipeBulkScraperService
from mealie.services.scraper.scraped_extras import ScraperContext
from mealie.services.scraper.scraper import create_from_html
from mealie.services.scraper.scraper_strategies import (
    ForceTimeoutException,
    RecipeScraperOpenAI,
    RecipeScraperPackage,
)

from ._base import BaseRecipeController, JSONBytes

ASSET_ALLOWED_EXTENSIONS = {
    "pdf",
    "jpg",
    "jpeg",
    "png",
    "gif",
    "webp",
    "bmp",
    "avif",
    "txt",
    "md",
    "csv",
    "json",
    *VIDEO_ASSET_EXTENSIONS,
}

router = UserAPIRouter(prefix="/recipes", route_class=MealieCrudRoute)


class CreateRecipeFromText(MealieModel):
    text: str = Field(..., min_length=1, max_length=200000)
    translate_language: str | None = None
    include_ai_tips: bool = True
    auto_image: bool = True
    include_item_images: bool = True


class CreateRecipeFromBrowserPage(CreateRecipeFromText):
    source_url: str | None = None
    source_title: str | None = None
    image_url: str | None = Field(None, max_length=4000)
    create_shopping_list: bool = True
    organize_shopping_list_with_ai: bool = True


class CreateRecipeAIShoppingList(MealieModel):
    include_ai_tips: bool = True
    organize_shopping_list_with_ai: bool = True
    include_item_images: bool = True


class CreateRecipeFromBrowserPageResponse(MealieModel):
    recipe_slug: str
    group_slug: str | None = None
    shopping_list_id: UUID4 | None = None
    shopping_list_name: str | None = None
    shopping_list_created: bool = False
    shopping_list_organized: bool = False
    shopping_list_error: str | None = None


class ItemImagesEnsureResponse(MealieModel):
    existing: int = 0
    created: int = 0
    failed: int = 0


class CreateRecipeFromBrowserPageStatus(MealieModel):
    ai_enabled: bool
    provider_count: int = 0
    default_provider_configured: bool = False


@controller(router)
class RecipeController(BaseRecipeController):
    def _item_image_service(self) -> ItemImageService:
        return ItemImageService(self.group_id, self.repos)

    @staticmethod
    def _item_image_result_response(result: ItemImageEnsureResult) -> ItemImagesEnsureResponse:
        return ItemImagesEnsureResponse(existing=result.existing, created=result.created, failed=result.failed)

    def _mark_recipe_item_images_ensured(self, recipe: Recipe, result: ItemImageEnsureResult) -> None:
        if result.failed != 0:
            return

        recipe.extras = {
            **(recipe.extras or {}),
            "itemImagesEnsured": True,
            "itemImagesEnsuredAt": datetime.now(UTC).isoformat(),
            "itemImagesResult": {
                "existing": result.existing,
                "created": result.created,
                "failed": result.failed,
            },
        }
        self.service.update_one(recipe.slug, recipe)

    async def _ensure_recipe_item_images(self, recipe: Recipe) -> ItemImageEnsureResult:
        try:
            result = await self._item_image_service().ensure_recipe_images(recipe)
            self._mark_recipe_item_images_ensured(recipe, result)
            return result
        except Exception:
            self.logger.exception("Failed to ensure recipe item images")
            return ItemImageEnsureResult(failed=1)

    async def _ensure_shopping_list_item_images(self, shopping_list) -> ItemImageEnsureResult:
        try:
            return await self._item_image_service().ensure_shopping_list_images(shopping_list)
        except Exception:
            self.logger.exception("Failed to ensure shopping list item images")
            return ItemImageEnsureResult(failed=1)

    def _raw_ai_provider_status(self) -> tuple[int, str | None, str | None, str | None]:
        settings = self.session.execute(
            sqlalchemy.text(
                """
                SELECT id, default_provider_id, image_provider_id
                FROM ai_provider_settings
                WHERE group_id = :group_id
                """
            ),
            {"group_id": self.repos.uuid_to_str(self.group_id)},
        ).mappings().one_or_none()
        if not settings:
            return 0, None, None, None

        provider_count = self.session.execute(
            sqlalchemy.text("SELECT COUNT(*) FROM ai_providers WHERE settings_id = :settings_id"),
            {"settings_id": settings["id"]},
        ).scalar_one()
        return (
            int(provider_count or 0),
            settings["default_provider_id"],
            settings["image_provider_id"],
            settings["id"],
        )

    def _ai_enabled(self) -> bool:
        provider_count, default_provider_id, _image_provider_id, settings_id = self._raw_ai_provider_status()
        if not (provider_count and default_provider_id and settings_id):
            return False

        provider_exists = self.session.execute(
            sqlalchemy.text(
                "SELECT 1 FROM ai_providers WHERE id = :provider_id AND settings_id = :settings_id LIMIT 1"
            ),
            {"provider_id": default_provider_id, "settings_id": settings_id},
        ).scalar()
        return bool(provider_exists)

    def _image_ai_enabled(self) -> bool:
        provider_count, default_provider_id, image_provider_id, settings_id = self._raw_ai_provider_status()
        provider_id = image_provider_id or default_provider_id
        if not (provider_count and provider_id and settings_id):
            return False

        provider_exists = self.session.execute(
            sqlalchemy.text(
                "SELECT 1 FROM ai_providers WHERE id = :provider_id AND settings_id = :settings_id LIMIT 1"
            ),
            {"provider_id": provider_id, "settings_id": settings_id},
        ).scalar()
        return bool(provider_exists)

    def handle_exceptions(self, ex: Exception) -> None:
        thrownType = type(ex)

        if thrownType == exceptions.PermissionDenied:
            self.logger.error("Permission Denied on recipe controller action")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ErrorResponse.respond(message="Permission Denied")
            )
        elif thrownType == exceptions.NoEntryFound:
            self.logger.error("No Entry Found on recipe controller action")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=ErrorResponse.respond(message="No Entry Found")
            )
        elif thrownType == sqlalchemy.exc.IntegrityError:
            self.logger.error("SQL Integrity Error on recipe controller action")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=ErrorResponse.respond(message="Recipe already exists")
            )
        elif thrownType == exceptions.RecursiveRecipe:
            self.logger.error("Recursive Recipe Link Error on recipe controller action")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond(message=self.t("exceptions.recursive-recipe-link")),
            )
        elif thrownType == exceptions.SlugError:
            self.logger.error("Failed to generate a valid slug from recipe name")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond(message="Unable to generate recipe slug"),
            )
        elif thrownType == exceptions.NotARecipe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond(
                    message=str(ex) or "The pasted text does not look like a recipe",
                    exception="NotARecipe",
                ),
            )
        else:
            self.logger.error("Unknown Error on recipe controller action")
            self.logger.exception(ex)
            raise HTTPException(
                status_code=500, detail=ErrorResponse.respond(message="Unknown Error", exception=ex.__class__.__name__)
            )

    # =======================================================================
    # URL Scraping Operations

    @router.post("/test-scrape-url")
    async def test_parse_recipe_url(self, data: ScrapeRecipeTest):
        # Debugger should produce the same result as the scraper sees before cleaning
        ScraperClass = RecipeScraperOpenAI if data.use_openai else RecipeScraperPackage
        try:
            if scraped_data := await ScraperClass(data.url, self.translator, self.repos).scrape_url():
                return scraped_data.schema.data
        except ForceTimeoutException as e:
            raise HTTPException(
                status_code=408, detail=ErrorResponse.respond(message="Recipe Scraping Timed Out")
            ) from e

        return "recipe_scrapers was unable to scrape this URL"

    @router.post("/create/html-or-json", status_code=201, response_model=str)
    async def create_recipe_from_html_or_json(self, req: ScrapeRecipeData) -> str:
        """Takes in raw HTML or a https://schema.org/Recipe object as a JSON string and parses it like a URL"""

        if req.data.startswith("{"):
            req.data = RecipeScraperPackage.ld_json_to_html(req.data)

        async for event in self._create_recipe_from_web(req):
            if isinstance(event.data, SSEDataEventDone):
                return event.data.slug
            if isinstance(event.data, SSEDataEventMessage) and event.event == SSEDataEventStatus.ERROR:
                raise HTTPException(status_code=400, detail=ErrorResponse.respond(message=event.data.message))

        # This should never be reachable, since we should always hit DONE or hit an exception/ERROR
        raise HTTPException(status_code=500, detail=ErrorResponse.respond(message="Unknown Error"))

    @router.post("/create/html-or-json/stream", response_class=EventSourceResponse)
    async def create_recipe_from_html_or_json_stream(self, req: ScrapeRecipeData) -> AsyncIterable[ServerSentEvent]:
        """
        Takes in raw HTML or a https://schema.org/Recipe object as a JSON string and parses it like a URL,
        streaming progress via SSE
        """

        if req.data.startswith("{"):
            req.data = RecipeScraperPackage.ld_json_to_html(req.data)

        async for event in self._create_recipe_from_web(req):
            yield event

    @router.post("/create/url", status_code=201, response_model=str)
    async def parse_recipe_url(self, req: ScrapeRecipe) -> str:
        """Takes in a URL and attempts to scrape data and load it into the database"""

        async for event in self._create_recipe_from_web(req):
            if isinstance(event.data, SSEDataEventDone):
                return event.data.slug
            if isinstance(event.data, SSEDataEventMessage) and event.event == SSEDataEventStatus.ERROR:
                raise HTTPException(status_code=400, detail=ErrorResponse.respond(message=event.data.message))

        # This should never be reachable, since we should always hit DONE or hit an exception/ERROR
        raise HTTPException(status_code=500, detail=ErrorResponse.respond(message="Unknown Error"))

    @router.post("/create/url/stream", response_class=EventSourceResponse)
    async def parse_recipe_url_stream(self, req: ScrapeRecipe) -> AsyncIterable[ServerSentEvent]:
        """
        Takes in a URL and attempts to scrape data and load it into the database,
        streaming progress via SSE
        """

        async for event in self._create_recipe_from_web(req):
            yield event

    async def _create_recipe_from_web(self, req: ScrapeRecipe | ScrapeRecipeData) -> AsyncIterable[ServerSentEvent]:
        """
        Create a recipe from the web, returning progress via SSE.
        Events will continue to be yielded until:
            - The recipe is created, emitting:
                - event=SSEDataEventStatus.DONE
                - data=SSEDataEventDone(...)
            - An exception is raised, emitting:
                - event=SSEDataEventStatus.ERROR
                - data=SSEDataEventMessage(...)
        """

        if isinstance(req, ScrapeRecipeData):
            html = req.data
            url = req.url or ""
            use_openai = False
        else:
            html = None
            url = req.url
            use_openai = req.use_openai

        queue: asyncio.Queue[ServerSentEvent | None] = asyncio.Queue()

        async def on_progress(message: str) -> None:
            await queue.put(
                ServerSentEvent(
                    data=SSEDataEventMessage(message=message),
                    event=SSEDataEventStatus.PROGRESS,
                )
            )

        async def run() -> None:
            try:
                recipe, extras = await create_from_html(
                    url,
                    self.repos,
                    self.translator,
                    html,
                    on_progress=on_progress,
                    use_openai=use_openai,
                )
                slug = self._finish_recipe_from_web(req, recipe, extras)
                await queue.put(
                    ServerSentEvent(
                        data=SSEDataEventDone(slug=slug),
                        event=SSEDataEventStatus.DONE,
                    )
                )
            except Exception as e:
                self.logger.exception("Error in streaming recipe creation")
                await queue.put(
                    ServerSentEvent(
                        data=SSEDataEventMessage(message=e.__class__.__name__),
                        event=SSEDataEventStatus.ERROR,
                    )
                )
            finally:
                await queue.put(None)

        task = asyncio.create_task(run())
        try:
            while (event := await queue.get()) is not None:
                yield event
        finally:
            if not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    def _finish_recipe_from_web(self, req: ScrapeRecipe | ScrapeRecipeData, recipe: Recipe, extras: object) -> str:
        if req.include_tags:
            ctx = ScraperContext(self.repos)
            recipe.tags = extras.use_tags(ctx)  # type: ignore

        if req.include_categories:
            ctx = ScraperContext(self.repos)
            recipe.recipe_category = extras.use_categories(ctx)  # type: ignore

        new_recipe = self.service.create_one(recipe)

        if new_recipe:
            self.publish_event(
                event_type=EventTypes.recipe_created,
                document_data=EventRecipeData(operation=EventOperation.create, recipe_slug=new_recipe.slug),
                group_id=new_recipe.group_id,
                household_id=new_recipe.household_id,
                message=self.t(
                    "notifications.generic-created-with-url",
                    name=new_recipe.name,
                    url=urls.recipe_url(self.group.slug, new_recipe.slug, self.settings.BASE_URL),
                ),
            )

        return new_recipe.slug

    @router.post("/create/url/bulk", status_code=202)
    def parse_recipe_url_bulk(self, bulk: CreateRecipeByUrlBulk, bg_tasks: BackgroundTasks):
        """Takes in a URL and attempts to scrape data and load it into the database"""
        bulk_scraper = RecipeBulkScraperService(self.service, self.repos, self.group, self.translator)
        report_id = bulk_scraper.get_report_id()
        bg_tasks.add_task(bulk_scraper.scrape, bulk)

        self.publish_event(
            event_type=EventTypes.recipe_created,
            document_data=EventRecipeBulkReportData(operation=EventOperation.create, report_id=report_id),
            group_id=self.group_id,
            household_id=self.household_id,
        )

        return {"reportId": report_id}

    def _stage_bulk_video_assets(
        self,
        video_indexes: list[int] | None,
        videos: list[UploadFile] | None,
    ) -> tuple[list[BulkImportVideo], FileSystemPath | None]:
        video_indexes = video_indexes or []
        videos = videos or []

        if not videos:
            return [], None

        if len(video_indexes) != len(videos):
            raise HTTPException(status_code=400, detail="Video indexes do not match uploaded videos")

        temp_dir = FileSystemPath(mkdtemp(prefix="mealie-bulk-video-"))
        staged_videos: list[BulkImportVideo] = []

        try:
            for position, (index, video) in enumerate(zip(video_indexes, videos, strict=True)):
                original_name = video.filename or f"video-{index + 1}"
                extension = original_name.split(".")[-1].lower()
                if extension not in VIDEO_ASSET_EXTENSIONS:
                    raise HTTPException(status_code=400, detail="Unsupported video extension")

                dest = temp_dir / f"{position}.{extension}"
                with dest.open("wb") as buffer:
                    copyfileobj(video.file, buffer)

                staged_videos.append(
                    BulkImportVideo(
                        index=index,
                        path=dest,
                        original_name=original_name,
                        extension=extension,
                    )
                )
        except Exception:
            rmtree(temp_dir, ignore_errors=True)
            raise

        return staged_videos, temp_dir

    @router.post("/create/url/bulk/assets", status_code=202)
    def parse_recipe_url_bulk_with_assets(
        self,
        bg_tasks: BackgroundTasks,
        bulk: str = Form(...),
        video_indexes: list[int] | None = Form(None),
        videos: list[UploadFile] | None = File(None),
    ):
        """Bulk URL import with optional per-row video assets."""
        bulk_payload = CreateRecipeByUrlBulk.model_validate_json(bulk)
        staged_videos, temp_dir = self._stage_bulk_video_assets(video_indexes, videos)

        bulk_scraper = RecipeBulkScraperService(self.service, self.repos, self.group, self.translator)
        report_id = bulk_scraper.get_report_id()
        bg_tasks.add_task(bulk_scraper.scrape, bulk_payload, staged_videos, temp_dir)

        self.publish_event(
            event_type=EventTypes.recipe_created,
            document_data=EventRecipeBulkReportData(operation=EventOperation.create, report_id=report_id),
            group_id=self.group_id,
            household_id=self.household_id,
        )

        return {"reportId": report_id}

    # ==================================================================================================================
    # Other Create Operations

    @router.post("/create/zip", status_code=201)
    def create_recipe_from_zip(self, archive: UploadFile = File(...)):
        """Create recipe from archive"""
        with get_temporary_zip_path() as temp_path:
            recipe = self.service.create_from_zip(archive, temp_path)
            self.publish_event(
                event_type=EventTypes.recipe_created,
                document_data=EventRecipeData(operation=EventOperation.create, recipe_slug=recipe.slug),
                group_id=recipe.group_id,
                household_id=recipe.household_id,
            )

        return recipe.slug

    @router.post("/create/image", status_code=201)
    async def create_recipe_from_image(
        self,
        images: list[UploadFile] = File(...),
        notes: str | None = Form(None, max_length=5000),
        translate_language: str | None = Query(None, alias="translateLanguage"),
        include_ai_tips: bool = Query(True, alias="includeAiTips"),
        include_item_images: bool = Query(True, alias="includeItemImages"),
    ):
        """
        Create a recipe from an image using OpenAI.
        Optionally specify a language for it to translate the recipe to.
        """

        if not self._image_ai_enabled():
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse.respond("OpenAI image services are not enabled"),
            )

        recipe = await self.service.create_from_images(images, translate_language, include_ai_tips, notes)
        if include_item_images:
            await self._ensure_recipe_item_images(recipe)
        self.publish_event(
            event_type=EventTypes.recipe_created,
            document_data=EventRecipeData(operation=EventOperation.create, recipe_slug=recipe.slug),
            group_id=recipe.group_id,
            household_id=recipe.household_id,
        )

        return recipe.slug

    @router.post("/create/text", status_code=201)
    async def create_recipe_from_text(self, data: CreateRecipeFromText):
        """Create a recipe from pasted recipe text using OpenAI."""

        if not self._ai_enabled():
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse.respond("OpenAI services are not enabled"),
            )

        recipe_text = data.text.strip()
        if not recipe_text:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse.respond("Recipe text cannot be empty"),
            )

        try:
            recipe = await self.service.create_from_text(
                recipe_text,
                translate_language=data.translate_language,
                include_ai_tips=data.include_ai_tips,
                auto_image=data.auto_image,
            )
            if data.include_item_images:
                await self._ensure_recipe_item_images(recipe)
        except exceptions.NotARecipe as e:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse.respond(
                    message=str(e) or "The pasted text does not look like a recipe",
                    exception="NotARecipe",
                ),
            ) from e

        self.publish_event(
            event_type=EventTypes.recipe_created,
            document_data=EventRecipeData(operation=EventOperation.create, recipe_slug=recipe.slug),
            group_id=recipe.group_id,
            household_id=recipe.household_id,
        )

        return recipe.slug

    @router.get("/create/browser-page/status", response_model=CreateRecipeFromBrowserPageStatus)
    def create_recipe_from_browser_page_status(self):
        """Return whether browser-extension recipe creation can use AI for the current group."""

        provider_count, default_provider_id, _image_provider_id, settings_id = self._raw_ai_provider_status()
        return CreateRecipeFromBrowserPageStatus(
            ai_enabled=self._ai_enabled(),
            provider_count=provider_count,
            default_provider_configured=bool(default_provider_id and settings_id),
        )

    @router.post("/create/browser-page", response_model=CreateRecipeFromBrowserPageResponse, status_code=201)
    async def create_recipe_from_browser_page(self, data: CreateRecipeFromBrowserPage):
        """Create a recipe from page content extracted by the browser extension."""

        if not self._ai_enabled():
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse.respond("OpenAI services are not enabled"),
            )

        recipe_text = self._browser_page_recipe_text(data)
        if not recipe_text:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse.respond("Recipe text cannot be empty"),
            )

        try:
            recipe = await self.service.create_from_text(
                recipe_text,
                data.translate_language,
                data.include_ai_tips,
                auto_image=not data.image_url,
            )
            if data.include_item_images:
                await self._ensure_recipe_item_images(recipe)
        except exceptions.NotARecipe as e:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse.respond(
                    message=str(e) or "The extracted page content does not look like a recipe",
                    exception="NotARecipe",
                ),
            ) from e

        self.publish_event(
            event_type=EventTypes.recipe_created,
            document_data=EventRecipeData(operation=EventOperation.create, recipe_slug=recipe.slug),
            group_id=recipe.group_id,
            household_id=recipe.household_id,
        )

        if data.image_url:
            await self.service.attach_best_effort_image(recipe, image_url=data.image_url, search_query=recipe.name)

        response = CreateRecipeFromBrowserPageResponse(
            recipe_slug=recipe.slug,
            group_slug=getattr(self.group, "slug", None),
        )
        if data.create_shopping_list:
            response = await self._create_browser_recipe_shopping_list(recipe, data, response)

        return response

    def _browser_page_recipe_text(self, data: CreateRecipeFromBrowserPage) -> str:
        recipe_text = data.text.strip()
        source_parts = []
        if data.source_title:
            source_parts.append(f"Source title: {data.source_title.strip()}")
        if data.source_url:
            source_parts.append(f"Source URL: {data.source_url.strip()}")

        if not source_parts:
            return recipe_text

        return "\n".join(source_parts + ["", recipe_text]).strip()

    def _browser_shopping_list_name(self, recipe: Recipe, shopping_service: ShoppingListService) -> str:
        base_name = (recipe.name or recipe.slug or "Shopping List").strip()
        existing_lists = shopping_service.shopping_lists.page_all(PaginationQuery(page=1, per_page=-1))
        existing_names = {
            (shopping_list.name or "").strip().casefold()
            for shopping_list in existing_lists.items
            if (shopping_list.name or "").strip()
        }

        name = base_name
        suffix = 2
        while name.casefold() in existing_names:
            name = f"{base_name} ({suffix})"
            suffix += 1

        return name

    def _find_recipe_named_shopping_list(self, recipe: Recipe, shopping_service: ShoppingListService):
        recipe_name = (recipe.name or "").strip().casefold()
        if not recipe_name:
            return None

        existing_lists = shopping_service.shopping_lists.page_all(PaginationQuery(page=1, per_page=-1))
        for shopping_list in existing_lists.items:
            if (shopping_list.name or "").strip().casefold() == recipe_name:
                return shopping_list

        return None

    async def _create_browser_recipe_shopping_list(
        self,
        recipe: Recipe,
        data: CreateRecipeFromBrowserPage,
        response: CreateRecipeFromBrowserPageResponse,
    ) -> CreateRecipeFromBrowserPageResponse:
        return await self._create_recipe_shopping_list(
            recipe,
            response,
            include_ai_tips=data.include_ai_tips,
            organize_shopping_list_with_ai=data.organize_shopping_list_with_ai,
            include_item_images=data.include_item_images,
            extras={
                "aiCreatedFromBrowserExtension": True,
                "sourceUrl": data.source_url,
            },
        )

    async def _create_recipe_shopping_list(
        self,
        recipe: Recipe,
        response: CreateRecipeFromBrowserPageResponse,
        include_ai_tips: bool,
        organize_shopping_list_with_ai: bool,
        include_item_images: bool = True,
        extras: dict[str, object | None] | None = None,
    ) -> CreateRecipeFromBrowserPageResponse:
        shopping_service = ShoppingListService(self.repos)

        try:
            shopping_list = shopping_service.create_one_list(
                ShoppingListCreate(
                    name=self._browser_shopping_list_name(recipe, shopping_service),
                    extras={
                        **(extras or {}),
                        "aiCreatedFromRecipeSlug": recipe.slug,
                        "aiCreatedFromRecipeId": str(recipe.id),
                    },
                ),
                self.user.id,
            )

            if not shopping_list:
                raise ValueError("Shopping list was not created")

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

            response.shopping_list_id = shopping_list.id
            response.shopping_list_name = shopping_list.name
            response.shopping_list_created = True

            if organize_shopping_list_with_ai:
                try:
                    shopping_list, _items = await shopping_service.organize_with_ai(
                        shopping_list.id,
                        include_ai_tips=include_ai_tips,
                    )
                    response.shopping_list_id = shopping_list.id
                    response.shopping_list_name = shopping_list.name
                    response.shopping_list_organized = True
                except Exception as e:
                    self.logger.exception("Failed to organize browser-extension shopping list with AI")
                    response.shopping_list_error = str(e) or "AI shopping list organization failed"

            if include_item_images:
                await self._ensure_shopping_list_item_images(shopping_list)
        except Exception as e:
            self.logger.exception("Failed to create browser-extension shopping list")
            response.shopping_list_error = str(e) or "Shopping list creation failed"

        return response

    @router.post("/{slug}/shopping-list-ai", response_model=CreateRecipeFromBrowserPageResponse, status_code=201)
    async def create_ai_shopping_list_for_recipe(
        self,
        slug: str,
        data: CreateRecipeAIShoppingList,
    ) -> CreateRecipeFromBrowserPageResponse:
        """Create a new shopping list from a recipe and optionally organize it with AI."""

        if not self._ai_enabled():
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse.respond("OpenAI services are not enabled"),
            )

        try:
            recipe = self.service.get_one(slug)
        except Exception as e:
            self.handle_exceptions(e)
            raise

        response = CreateRecipeFromBrowserPageResponse(
            recipe_slug=recipe.slug,
            group_slug=getattr(self.group, "slug", None),
        )
        return await self._create_recipe_shopping_list(
            recipe,
            response,
            include_ai_tips=data.include_ai_tips,
            organize_shopping_list_with_ai=data.organize_shopping_list_with_ai,
            include_item_images=data.include_item_images,
            extras={"aiCreatedFromRecipeAction": True},
        )

    @router.post(
        "/{slug}/shopping-list/open-or-create",
        response_model=CreateRecipeFromBrowserPageResponse,
        status_code=201,
    )
    async def open_or_create_shopping_list_for_recipe(self, slug: str) -> CreateRecipeFromBrowserPageResponse:
        """Return an existing recipe-named shopping list, or create one and organize it with AI when available."""

        try:
            recipe = self.service.get_one(slug)
        except Exception as e:
            self.handle_exceptions(e)
            raise

        shopping_service = ShoppingListService(self.repos)
        existing_list = self._find_recipe_named_shopping_list(recipe, shopping_service)
        if existing_list:
            return CreateRecipeFromBrowserPageResponse(
                recipe_slug=recipe.slug,
                group_slug=getattr(self.group, "slug", None),
                shopping_list_id=existing_list.id,
                shopping_list_name=existing_list.name,
                shopping_list_created=False,
                shopping_list_organized=bool((existing_list.extras or {}).get("aiOrganized")),
            )

        response = CreateRecipeFromBrowserPageResponse(
            recipe_slug=recipe.slug,
            group_slug=getattr(self.group, "slug", None),
        )
        return await self._create_recipe_shopping_list(
            recipe,
            response,
            include_ai_tips=True,
            organize_shopping_list_with_ai=self._ai_enabled(),
            include_item_images=True,
            extras={"createdFromOpenOrCreateRecipeShoppingList": True},
        )

    @router.post("/{slug}/item-images/ensure", response_model=ItemImagesEnsureResponse)
    async def ensure_recipe_item_images(self, slug: str) -> ItemImagesEnsureResponse:
        """Find and cache ingredient/tool images for a recipe."""

        try:
            recipe = self.service.get_one(slug)
        except Exception as e:
            self.handle_exceptions(e)
            raise

        result = await self._ensure_recipe_item_images(recipe)
        return self._item_image_result_response(result)

    @router.post("/ai-search", response_model=RecipeAISearchResponse)
    async def search_recipes_with_ai(self, data: RecipeAISearchRequest) -> RecipeAISearchResponse:
        """Search existing recipes using the configured AI provider."""

        if not self._ai_enabled():
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse.respond("OpenAI services are not enabled"),
            )

        try:
            return await self.service.search_with_ai(data.query, data.limit)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse.respond(str(e)),
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse.respond("AI recipe search failed"),
            ) from e

    # ==================================================================================================================
    # CRUD Operations

    @router.get("", response_model=PaginationBase[RecipeSummary])
    def get_all(
        self,
        request: Request,
        q: PaginationQuery = Depends(make_dependable(PaginationQuery)),
        search_query: RecipeSearchQuery = Depends(make_dependable(RecipeSearchQuery)),
        categories: list[UUID4 | str] | None = Query(None),
        tags: list[UUID4 | str] | None = Query(None),
        tools: list[UUID4 | str] | None = Query(None),
        foods: list[UUID4 | str] | None = Query(None),
        households: list[UUID4 | str] | None = Query(None),
    ):
        cookbook_data: ReadCookBook | None = None
        if search_query.cookbook:
            if isinstance(search_query.cookbook, UUID):
                cb_match_attr = "id"
            else:
                try:
                    UUID(search_query.cookbook)
                    cb_match_attr = "id"
                except ValueError:
                    cb_match_attr = "slug"
            cookbook_data = self.group_cookbooks.get_one(search_query.cookbook, cb_match_attr)

            if cookbook_data is None:
                raise HTTPException(status_code=404, detail="cookbook not found")

        # We use "group_recipes" here so we can return all recipes regardless of household. The query filter can
        # include a household_id to filter by household.
        # We use "by_user" so we can sort favorites and other user-specific data correctly.
        pagination_response = self.group_recipes.by_user(self.user.id).page_all(
            pagination=q,
            cookbook=cookbook_data,
            categories=categories,
            tags=tags,
            tools=tools,
            foods=foods,
            households=households,
            require_all_categories=search_query.require_all_categories,
            require_all_tags=search_query.require_all_tags,
            require_all_tools=search_query.require_all_tools,
            require_all_foods=search_query.require_all_foods,
            search=search_query.search,
        )

        # merge default pagination with the request's query params
        query_params = q.model_dump() | {**request.query_params}
        pagination_response.set_pagination_guides(
            router.url_path_for("get_all"),
            {k: v for k, v in query_params.items() if v is not None},
        )

        json_compatible_response = orjson.dumps(pagination_response.model_dump(by_alias=True))

        # Response is returned directly, to avoid validation and improve performance
        return JSONBytes(content=json_compatible_response)

    @router.get("/suggestions", response_model=RecipeSuggestionResponse)
    def suggest_recipes(
        self,
        q: RecipeSuggestionQuery = Depends(make_dependable(RecipeSuggestionQuery)),
        foods: list[UUID4] | None = Query(None),
        tools: list[UUID4] | None = Query(None),
    ) -> RecipeSuggestionResponse:
        group_recipes_by_user = get_repositories(
            self.session, group_id=self.group_id, household_id=None
        ).recipes.by_user(self.user.id)

        recipes = group_recipes_by_user.find_suggested_recipes(q, foods, tools)
        response = RecipeSuggestionResponse(items=recipes)
        json_compatible_response = orjson.dumps(response.model_dump(by_alias=True))

        # Response is returned directly, to avoid validation and improve performance
        return JSONBytes(content=json_compatible_response)

    @router.get("/{slug}", response_model=Recipe)
    def get_one(self, slug: str = Path(..., description="A recipe's slug or id")):
        """Takes in a recipe's slug or id and returns all data for a recipe"""
        try:
            recipe = self.service.get_one(slug)
        except Exception as e:
            self.handle_exceptions(e)
            return None

        return recipe

    @router.post("", status_code=201, response_model=str)
    def create_one(self, data: CreateRecipe) -> str | None:
        """Takes in a JSON string and loads data into the database as a new entry"""
        try:
            new_recipe = self.service.create_one(data)
        except Exception as e:
            self.handle_exceptions(e)
            return None

        if new_recipe:
            self.publish_event(
                event_type=EventTypes.recipe_created,
                document_data=EventRecipeData(operation=EventOperation.create, recipe_slug=new_recipe.slug),
                group_id=new_recipe.group_id,
                household_id=new_recipe.household_id,
                message=self.t(
                    "notifications.generic-created-with-url",
                    name=new_recipe.name,
                    url=urls.recipe_url(self.group.slug, new_recipe.slug, self.settings.BASE_URL),
                ),
            )

        return new_recipe.slug

    @router.post("/{slug}/duplicate", status_code=201, response_model=Recipe)
    def duplicate_one(self, slug: str, req: RecipeDuplicate) -> Recipe:
        """Duplicates a recipe with a new custom name if given"""
        try:
            new_recipe = self.service.duplicate_one(slug, req)
        except Exception as e:
            self.handle_exceptions(e)

        if new_recipe:
            self.publish_event(
                event_type=EventTypes.recipe_created,
                document_data=EventRecipeData(operation=EventOperation.create, recipe_slug=new_recipe.slug),
                group_id=new_recipe.group_id,
                household_id=new_recipe.household_id,
                message=self.t(
                    "notifications.generic-duplicated",
                    name=new_recipe.name,
                ),
            )

        return new_recipe

    @router.put("/{slug}")
    def update_one(self, slug: str, data: Recipe):
        """Updates a recipe by existing slug and data."""
        try:
            recipe = self.service.update_one(slug, data)
        except Exception as e:
            self.handle_exceptions(e)

        if recipe:
            self.publish_event(
                event_type=EventTypes.recipe_updated,
                document_data=EventRecipeData(operation=EventOperation.update, recipe_slug=recipe.slug),
                group_id=recipe.group_id,
                household_id=recipe.household_id,
                message=self.t(
                    "notifications.generic-updated-with-url",
                    name=recipe.name,
                    url=urls.recipe_url(self.group.slug, recipe.slug, self.settings.BASE_URL),
                ),
            )

        return recipe

    @router.put("")
    def update_many(self, data: list[Recipe]):
        updated_by_group_and_household: defaultdict[UUID4, defaultdict[UUID4, list[Recipe]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for recipe in data:
            r = self.service.update_one(recipe.id, recipe)  # type: ignore
            updated_by_group_and_household[r.group_id][r.household_id].append(r)

        all_updated: list[Recipe] = []
        if updated_by_group_and_household:
            for group_id, household_dict in updated_by_group_and_household.items():
                for household_id, updated_recipes in household_dict.items():
                    all_updated.extend(updated_recipes)
                    self.publish_event(
                        event_type=EventTypes.recipe_updated,
                        document_data=EventRecipeBulkData(
                            operation=EventOperation.update, recipe_slugs=[r.slug for r in updated_recipes]
                        ),
                        group_id=group_id,
                        household_id=household_id,
                    )

        return all_updated

    @router.patch("/{slug}")
    def patch_one(self, slug: str, data: Recipe):
        """Updates a recipe by existing slug and data."""
        try:
            recipe = self.service.patch_one(slug, data)
        except Exception as e:
            self.handle_exceptions(e)

        if recipe:
            self.publish_event(
                event_type=EventTypes.recipe_updated,
                document_data=EventRecipeData(operation=EventOperation.update, recipe_slug=recipe.slug),
                group_id=recipe.group_id,
                household_id=recipe.household_id,
                message=self.t(
                    "notifications.generic-updated-with-url",
                    name=recipe.name,
                    url=urls.recipe_url(self.group.slug, recipe.slug, self.settings.BASE_URL),
                ),
            )

        return recipe

    @router.patch("")
    def patch_many(self, data: list[Recipe]):
        updated_by_group_and_household: defaultdict[UUID4, defaultdict[UUID4, list[Recipe]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for recipe in data:
            r = self.service.patch_one(recipe.id, recipe)  # type: ignore
            updated_by_group_and_household[r.group_id][r.household_id].append(r)

        all_updated: list[Recipe] = []
        if updated_by_group_and_household:
            for group_id, household_dict in updated_by_group_and_household.items():
                for household_id, updated_recipes in household_dict.items():
                    all_updated.extend(updated_recipes)
                    self.publish_event(
                        event_type=EventTypes.recipe_updated,
                        document_data=EventRecipeBulkData(
                            operation=EventOperation.update, recipe_slugs=[r.slug for r in updated_recipes]
                        ),
                        group_id=group_id,
                        household_id=household_id,
                    )

        return all_updated

    @router.patch("/{slug}/last-made")
    def update_last_made(self, slug: str, data: RecipeLastMade):
        """Update a recipe's last made timestamp"""

        try:
            recipe = self.service.update_last_made(slug, data.timestamp)
        except Exception as e:
            self.handle_exceptions(e)

        if recipe:
            self.publish_event(
                event_type=EventTypes.recipe_updated,
                document_data=EventRecipeData(operation=EventOperation.update, recipe_slug=recipe.slug),
                group_id=recipe.group_id,
                household_id=recipe.household_id,
                message=self.t(
                    "notifications.generic-updated-with-url",
                    name=recipe.name,
                    url=urls.recipe_url(self.group.slug, recipe.slug, self.settings.BASE_URL),
                ),
            )

        return recipe

    @router.delete("/{slug}")
    def delete_one(self, slug: str):
        """Deletes a recipe by slug"""
        try:
            recipe = self.service.delete_one(slug)
        except Exception as e:
            self.handle_exceptions(e)

        if recipe:
            self.publish_event(
                event_type=EventTypes.recipe_deleted,
                document_data=EventRecipeData(operation=EventOperation.delete, recipe_slug=recipe.slug),
                group_id=recipe.group_id,
                household_id=recipe.household_id,
                message=self.t("notifications.generic-deleted", name=recipe.name),
            )

        return recipe

    # ==================================================================================================================
    # Image and Assets

    @router.post("/{slug}/image", tags=["Recipe: Images and Assets"])
    async def scrape_image_url(self, slug: str, url: ScrapeRecipe):
        recipe = self.mixins.get_one(slug)
        data_service = RecipeDataService(recipe.id)

        try:
            image_scraped = await data_service.scrape_image(url.url)
        except NotAnImageError as e:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse.respond("Url is not an image"),
            ) from e
        except InvalidDomainError as e:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse.respond("Url is not from an allowed domain"),
            ) from e

        if not image_scraped:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse.respond("Unable to download image"),
            )

        recipe.image = cache.cache_key.new_key()
        self.service.update_one(recipe.slug, recipe)

    @router.post("/{slug}/image/ai", response_model=UpdateImageResponse, tags=["Recipe: Images and Assets"])
    async def create_ai_recipe_image(self, slug: str):
        recipe = self.mixins.get_one(slug)
        category_names = [category.name for category in recipe.recipe_category or [] if category.name]
        tag_names = [tag.name for tag in recipe.tags or [] if tag.name]
        ingredient_names = [
            ingredient.display or ingredient.note or (ingredient.food.name if ingredient.food else "")
            for ingredient in (recipe.recipe_ingredient or [])[:8]
        ]
        ingredient_names = [name.strip() for name in ingredient_names if name and name.strip()]
        recipe_name = recipe.name or recipe.slug
        search_queries = [
            recipe_name,
            " ".join([recipe_name, *category_names[:2], *tag_names[:2]]),
            " ".join([recipe_name, *ingredient_names[:3]]),
            " ".join([recipe_name, recipe.created_by or ""]),
        ]

        try:
            image_attached = await self.service.attach_best_effort_image(
                recipe,
                search_queries=search_queries,
                source_url=recipe.source,
            )
        except Exception as e:
            self.handle_exceptions(e)
            return None

        if not image_attached or not recipe.image:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse.respond("Could not find a usable image for this recipe"),
            )

        return UpdateImageResponse(image=recipe.image)

    @router.put("/{slug}/image", response_model=UpdateImageResponse, tags=["Recipe: Images and Assets"])
    def update_recipe_image(self, slug: str, image: bytes = File(...), extension: str = Form(...)):
        try:
            new_version = self.service.update_recipe_image(slug, image, extension)
            return UpdateImageResponse(image=new_version)
        except Exception as e:
            self.handle_exceptions(e)
            return None

    @router.delete("/{slug}/image", tags=["Recipe: Images and Assets"])
    def delete_recipe_image(self, slug: str):
        try:
            self.service.delete_recipe_image(slug)
            return SuccessResponse.respond(message=self.t("recipe.recipe-image-deleted"))
        except Exception as e:
            self.handle_exceptions(e)
            return None

    @router.post("/{slug}/assets", response_model=RecipeAsset, tags=["Recipe: Images and Assets"])
    async def upload_recipe_asset(
        self,
        slug: str,
        name: str = Form(...),
        icon: str = Form(...),
        extension: str = Form(...),
        file: UploadFile = File(...),
    ):
        """Upload a file to store as a recipe asset"""
        if "." in extension:
            extension = extension.split(".")[-1]

        extension = extension.lower()
        if extension not in ASSET_ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Unsupported file extension")

        file_slug = slugify(name)
        if not extension or not file_slug:
            raise HTTPException(status_code=400, detail="Missing required fields")

        file_name = f"{file_slug}.{extension}"

        recipe = self.service.get_one(slug)

        dest = recipe.asset_dir / file_name

        # Ensure path is relative to the recipe's asset directory
        if dest.absolute().parent != recipe.asset_dir:
            raise HTTPException(
                status_code=400,
                detail=f"File name {file_name} or extension {extension} not valid",
            )

        def copy_upload() -> None:
            with dest.open("wb") as buffer:
                copyfileobj(file.file, buffer)

        try:
            await asyncio.to_thread(copy_upload)
        except Exception:
            dest.unlink(missing_ok=True)
            raise
        finally:
            await file.close()

        if not dest.is_file():
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR)

        if extension in VIDEO_ASSET_EXTENSIONS:
            try:
                dest = await normalize_video_asset(dest)
            except VideoTranscodeError as exc:
                dest.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Video conversion failed: {exc}",
                ) from exc
            extension = "mp4"
            file_name = dest.name

        asset_in = RecipeAsset(name=name, icon=icon, file_name=file_name)

        if recipe.assets is not None:
            recipe.assets.append(asset_in)

        if extension in VIDEO_ASSET_EXTENSIONS and recipe.settings is not None:
            recipe.settings.show_assets = True

        self.service.update_one(slug, recipe)

        return asset_in
