import asyncio
from dataclasses import dataclass
from pathlib import Path
from shutil import copyfile, rmtree

from pydantic import UUID4
from slugify import slugify

from mealie.lang.providers import Translator
from mealie.repos.repository_factory import AllRepositories
from mealie.schema.recipe.recipe import CreateRecipeByUrlBulk, Recipe
from mealie.schema.recipe.recipe_asset import RecipeAsset
from mealie.schema.reports.reports import (
    ReportCategory,
    ReportCreate,
    ReportEntryCreate,
    ReportEntryOut,
    ReportSummaryStatus,
)
from mealie.schema.user.user import GroupInDB
from mealie.services._base_service import BaseService
from mealie.services.recipe.recipe_service import RecipeService
from mealie.services.scraper.scraper import create_from_html


@dataclass
class BulkImportVideo:
    index: int
    path: Path
    original_name: str
    extension: str


class RecipeBulkScraperService(BaseService):
    report_entries: list[ReportEntryCreate]

    def __init__(
        self, service: RecipeService, repos: AllRepositories, group: GroupInDB, translator: Translator
    ) -> None:
        self.service = service
        self.repos = repos
        self.group = group
        self.report_entries = []
        self.translator = translator

        super().__init__()

    def get_report_id(self) -> UUID4:
        import_report = ReportCreate(
            name="Bulk Import",
            category=ReportCategory.bulk_import,
            status=ReportSummaryStatus.in_progress,
            group_id=self.group.id,
        )

        self.report = self.repos.group_reports.create(import_report)
        return self.report.id

    def _add_error_entry(self, message: str, exception: str = "") -> None:
        self.report_entries.append(
            ReportEntryCreate(
                report_id=self.report.id,
                success=False,
                message=message,
                exception=exception,
            )
        )

    def _save_all_entries(self) -> None:
        is_success = True
        is_failure = True

        new_entries: list[ReportEntryOut] = []
        for entry in self.report_entries:
            if is_failure and entry.success:
                is_failure = False

            if is_success and not entry.success:
                is_success = False

            new_entries.append(self.repos.group_report_entries.create(entry))

        if is_success:
            self.report.status = ReportSummaryStatus.success

        if is_failure:
            self.report.status = ReportSummaryStatus.failure

        if not is_success and not is_failure:
            self.report.status = ReportSummaryStatus.partial

        self.report.entries = new_entries
        self.repos.group_reports.update(self.report.id, self.report)

    def _attach_video(self, recipe: Recipe, video: BulkImportVideo) -> None:
        name = Path(video.original_name).stem or f"Video {video.index + 1}"
        file_slug = slugify(name) or f"video-{video.index + 1}"
        file_name = f"{file_slug}.{video.extension}"
        dest = recipe.asset_dir / file_name

        copyfile(video.path, dest)

        if recipe.assets is None:
            recipe.assets = []

        recipe.assets.append(RecipeAsset(name=name, icon="mdi-play", file_name=file_name))
        if recipe.settings is not None:
            recipe.settings.show_assets = True

        self.service.update_one(recipe.slug, recipe)

    async def scrape(
        self,
        urls: CreateRecipeByUrlBulk,
        videos: list[BulkImportVideo] | None = None,
        video_temp_dir: Path | None = None,
    ) -> None:
        sem = asyncio.Semaphore(3)
        videos_by_index = {video.index: video for video in videos or []}

        async def _do(url: str) -> Recipe | None:
            async with sem:
                try:
                    recipe, _ = await create_from_html(url, self.repos, self.translator)
                    return recipe
                except Exception as e:
                    self.service.logger.error(f"failed to scrape url during bulk url import {url}")
                    self.service.logger.exception(e)
                    self._add_error_entry(f"failed to scrape url {url}", str(e))
                    return None

        try:
            if self.report is None:
                self.get_report_id()
            tasks = [_do(b.url) for b in urls.imports]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for idx, (b, recipe) in enumerate(zip(urls.imports, results, strict=True)):
                if not recipe or isinstance(recipe, BaseException):
                    continue

                if b.tags:
                    recipe.tags = b.tags

                if b.categories:
                    recipe.recipe_category = b.categories

                try:
                    created_recipe = self.service.create_one(recipe)
                    if video := videos_by_index.get(idx):
                        self._attach_video(created_recipe, video)
                except Exception as e:
                    self.service.logger.error(f"Failed to save recipe to database during bulk url import {b.url}")
                    self.service.logger.exception(e)
                    self._add_error_entry(f"Failed to save recipe to database during bulk url import {b.url}", str(e))
                    continue

                self.report_entries.append(
                    ReportEntryCreate(
                        report_id=self.report.id,
                        success=True,
                        message=f"Successfully imported recipe {recipe.name}",
                        exception="",
                    )
                )

            self._save_all_entries()
        finally:
            if video_temp_dir is not None:
                rmtree(video_temp_dir, ignore_errors=True)
