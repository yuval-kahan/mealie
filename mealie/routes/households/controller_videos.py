import json
from pathlib import Path
from urllib.parse import urlsplit

import sqlalchemy as sa
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import UUID4

from mealie.db.models.household.shopping_list import ShoppingList
from mealie.db.models.household.video import RecipeVideo, ShoppingListVideo, Video, VideoDownloadSettings
from mealie.db.models.recipe.recipe import RecipeModel
from mealie.routes._base import controller
from mealie.routes._base.base_controllers import BaseUserController
from mealie.schema.household.video import (
    VideoBrowserPageRequest,
    VideoCreate,
    VideoDeletePreview,
    VideoDownloadSettingsBase,
    VideoDownloadSettingsOut,
    VideoOut,
    VideoUpdate,
)
from mealie.services.recipe.recipe_service import RecipeService
from mealie.services.videos import run_video_processing
from mealie.services.videos.video_library_service import delete_video_files, normalize_video_url, video_storage_dir

router = APIRouter(prefix="/households/videos", tags=["Households: Videos"])
ACTIVE_STATUSES = {"pending", "metadata", "downloading", "processing"}


def _json_list(value: str | None) -> list[str]:
    try:
        parsed = json.loads(value or "[]")
    except (TypeError, ValueError):
        return []
    return [str(item) for item in parsed if str(item).strip()] if isinstance(parsed, list) else []


@controller(router)
class VideosController(BaseUserController):
    def _get_or_404(self, video_id: UUID4) -> Video:
        video = self.session.execute(
            sa.select(Video).where(Video.id == video_id, Video.group_id == self.group_id)
        ).scalar_one_or_none()
        if not video:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Video not found")
        return video

    def _settings_model(self) -> VideoDownloadSettings | None:
        return self.session.execute(
            sa.select(VideoDownloadSettings).where(VideoDownloadSettings.user_id == self.user.id)
        ).scalar_one_or_none()

    def _to_out(self, video: Video) -> VideoOut:
        recipe_rows = self.session.execute(
            sa.select(RecipeModel.id, RecipeModel.slug)
            .join(RecipeVideo, RecipeVideo.recipe_id == RecipeModel.id)
            .where(RecipeVideo.video_id == video.id)
            .order_by(RecipeModel.name)
        ).all()
        return VideoOut(
            id=video.id,
            group_id=video.group_id,
            household_id=video.household_id,
            user_id=video.user_id,
            title=video.title,
            url=video.url,
            description=video.description,
            original_description=video.original_description,
            platform=video.platform,
            creator=video.creator,
            duration_seconds=video.duration_seconds,
            published_at=video.published_at,
            language=video.language,
            thumbnail_url=video.thumbnail_url,
            thumbnail_file_name=video.thumbnail_file_name,
            categories=_json_list(video.categories_json),
            tags=_json_list(video.tags_json),
            process_with_ai=video.process_with_ai,
            download_enabled=video.download_enabled,
            create_recipe=video.create_recipe,
            create_shopping_list=video.create_shopping_list,
            organize_shopping_list=video.organize_shopping_list,
            include_ai_tips=video.include_ai_tips,
            include_mise_en_place=video.include_mise_en_place,
            target_language=video.target_language,
            processing_status=video.processing_status,
            processing_progress=video.processing_progress,
            processing_error=video.processing_error,
            local_file_name=video.local_file_name,
            local_format=video.local_format,
            local_resolution=video.local_resolution,
            local_file_size=video.local_file_size,
            recipe_detected=video.recipe_detected,
            recipe_ids=[row.id for row in recipe_rows],
            recipe_slugs=[row.slug for row in recipe_rows],
            shopping_list_ids=[link.shopping_list_id for link in video.shopping_list_links],
            created_at=video.created_at,
            updated_at=video.updated_at,
            has_local_media=bool(video.local_file_name),
            has_local_thumbnail=bool(video.thumbnail_file_name),
        )

    def _default_download_enabled(self) -> bool:
        settings = self._settings_model()
        return settings.download_by_default if settings else True

    def _create_or_update(self, data: VideoCreate, background_tasks: BackgroundTasks) -> VideoOut:
        try:
            normalized_url = normalize_video_url(data.url)
        except ValueError as error:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

        existing = self.session.execute(
            sa.select(Video).where(Video.group_id == self.group_id, Video.url == normalized_url)
        ).scalar_one_or_none()
        title = (data.title or "").strip()
        if not title:
            title = urlsplit(normalized_url).netloc.removeprefix("www.") or "Saved video"
        video = existing or Video(
            group_id=self.group_id,
            household_id=self.household_id,
            user_id=self.user.id,
            url=normalized_url,
            title=title[:500],
            session=self.session,
        )
        video.title = title[:500]
        video.description = (data.description or "").strip()[:50000] or None
        video.process_with_ai = data.process_with_ai
        video.download_enabled = (
            data.download_video if data.download_video is not None else self._default_download_enabled()
        )
        video.create_recipe = data.create_recipe
        video.create_shopping_list = data.create_shopping_list and data.create_recipe
        video.organize_shopping_list = data.organize_shopping_list and video.create_shopping_list
        video.include_ai_tips = data.include_ai_tips
        video.include_mise_en_place = data.include_mise_en_place
        video.target_language = (data.target_language or "").strip()[:64] or None
        if video.processing_status not in ACTIVE_STATUSES:
            video.processing_status = "pending"
            video.processing_progress = 0
            video.processing_error = None
            video.cancel_requested = False
        self.session.add(video)
        self.session.commit()
        self.session.refresh(video)
        if video.processing_status == "pending":
            background_tasks.add_task(run_video_processing, video.id)
        return self._to_out(video)

    @router.get("/settings", response_model=VideoDownloadSettingsOut)
    def get_settings(self) -> VideoDownloadSettingsOut:
        settings = self._settings_model()
        return VideoDownloadSettingsOut.model_validate(settings) if settings else VideoDownloadSettingsOut()

    @router.put("/settings", response_model=VideoDownloadSettingsOut)
    def update_settings(self, data: VideoDownloadSettingsBase) -> VideoDownloadSettingsOut:
        settings = self._settings_model() or VideoDownloadSettings(
            group_id=self.group_id,
            household_id=self.household_id,
            user_id=self.user.id,
            session=self.session,
        )
        for field, value in data.model_dump().items():
            setattr(settings, field, value)
        self.session.add(settings)
        self.session.commit()
        self.session.refresh(settings)
        return VideoDownloadSettingsOut.model_validate(settings)

    @router.get("", response_model=list[VideoOut])
    def get_all(self, search: str | None = Query(None)) -> list[VideoOut]:
        query = (search or "").strip()
        statement = sa.select(Video).where(Video.group_id == self.group_id)
        if query:
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            statement = statement.where(
                sa.or_(
                    Video.title.ilike(pattern, escape="\\"),
                    Video.description.ilike(pattern, escape="\\"),
                    Video.creator.ilike(pattern, escape="\\"),
                    Video.platform.ilike(pattern, escape="\\"),
                    Video.tags_json.ilike(pattern, escape="\\"),
                    Video.categories_json.ilike(pattern, escape="\\"),
                )
            )
        videos = self.session.execute(statement.order_by(Video.created_at.desc(), Video.title.asc())).scalars().all()
        return [self._to_out(video) for video in videos]

    @router.post("", response_model=VideoOut, status_code=status.HTTP_202_ACCEPTED)
    def create(self, data: VideoCreate, background_tasks: BackgroundTasks) -> VideoOut:
        return self._create_or_update(data, background_tasks)

    @router.post("/browser-page", response_model=VideoOut, status_code=status.HTTP_202_ACCEPTED)
    def create_from_browser_page(self, data: VideoBrowserPageRequest, background_tasks: BackgroundTasks) -> VideoOut:
        payload = data.model_copy(update={"title": data.title or data.page_title})
        return self._create_or_update(payload, background_tasks)

    @router.get("/{video_id}", response_model=VideoOut)
    def get_one(self, video_id: UUID4) -> VideoOut:
        return self._to_out(self._get_or_404(video_id))

    @router.put("/{video_id}", response_model=VideoOut)
    def update(self, video_id: UUID4, data: VideoUpdate) -> VideoOut:
        video = self._get_or_404(video_id)
        video.title = data.title.strip()
        video.description = (data.description or "").strip() or None
        video.creator = (data.creator or "").strip() or None
        video.categories_json = json.dumps(data.categories, ensure_ascii=False)
        video.tags_json = json.dumps(data.tags, ensure_ascii=False)
        self.session.add(video)
        self.session.commit()
        self.session.refresh(video)
        return self._to_out(video)

    @router.post("/{video_id}/retry", response_model=VideoOut, status_code=status.HTTP_202_ACCEPTED)
    def retry(self, video_id: UUID4, background_tasks: BackgroundTasks) -> VideoOut:
        video = self._get_or_404(video_id)
        if video.processing_status in ACTIVE_STATUSES:
            return self._to_out(video)
        video.processing_status = "pending"
        video.processing_progress = 0
        video.processing_error = None
        video.cancel_requested = False
        self.session.add(video)
        self.session.commit()
        background_tasks.add_task(run_video_processing, video.id)
        return self._to_out(video)

    @router.post("/{video_id}/cancel", response_model=VideoOut)
    def cancel(self, video_id: UUID4) -> VideoOut:
        video = self._get_or_404(video_id)
        if video.processing_status in ACTIVE_STATUSES:
            video.cancel_requested = True
            self.session.add(video)
            self.session.commit()
        return self._to_out(video)

    @router.get("/{video_id}/media")
    def media(self, video_id: UUID4):
        video = self._get_or_404(video_id)
        if not video.local_file_name:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Downloaded video not found")
        path = video_storage_dir(video.group_id, video.id).joinpath(Path(video.local_file_name).name)
        if not path.is_file():
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Downloaded video not found")
        return FileResponse(path, filename=video.local_file_name, content_disposition_type="inline")

    @router.get("/{video_id}/thumbnail")
    def thumbnail(self, video_id: UUID4):
        video = self._get_or_404(video_id)
        if video.thumbnail_file_name:
            path = video_storage_dir(video.group_id, video.id).joinpath(Path(video.thumbnail_file_name).name)
            if path.is_file():
                return FileResponse(path)
        if video.thumbnail_url:
            return RedirectResponse(video.thumbnail_url)
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Video thumbnail not found")

    @router.get("/{video_id}/delete-preview", response_model=VideoDeletePreview)
    def delete_preview(self, video_id: UUID4) -> VideoDeletePreview:
        video = self._get_or_404(video_id)
        recipe_rows = self.session.execute(
            sa.select(RecipeModel.id, RecipeModel.name)
            .join(RecipeVideo, RecipeVideo.recipe_id == RecipeModel.id)
            .where(RecipeVideo.video_id == video.id)
        ).all()
        list_rows = self.session.execute(
            sa.select(ShoppingList.id, ShoppingList.name)
            .join(ShoppingListVideo, ShoppingListVideo.shopping_list_id == ShoppingList.id)
            .where(ShoppingListVideo.video_id == video.id)
        ).all()
        return VideoDeletePreview(
            recipe_ids=[row.id for row in recipe_rows],
            recipe_names=[row.name for row in recipe_rows],
            shopping_list_ids=[row.id for row in list_rows],
            shopping_list_names=[row.name or "" for row in list_rows],
        )

    @router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete(
        self,
        video_id: UUID4,
        delete_recipes: bool = Query(False),
        delete_shopping_lists: bool = Query(False),
    ) -> None:
        video = self._get_or_404(video_id)
        if video.processing_status in ACTIVE_STATUSES:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Cancel video processing before deleting it")
        preview = self.delete_preview(video_id)
        if delete_recipes and preview.recipe_ids:
            recipe_slugs = list(
                self.session.execute(
                    sa.select(RecipeModel.slug).where(
                        RecipeModel.id.in_(preview.recipe_ids),
                        RecipeModel.group_id == self.group_id,
                    )
                ).scalars()
            )
            RecipeService(self.repos, self.user, self.household, translator=self.translator).delete_many(recipe_slugs)
        if delete_shopping_lists and preview.shopping_list_ids:
            self.repos.group_shopping_lists.delete_many(preview.shopping_list_ids)
        group_id = video.group_id
        self.session.delete(video)
        self.session.commit()
        delete_video_files(group_id, video_id)
