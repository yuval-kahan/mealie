import asyncio
import json
import mimetypes
import re
import shutil
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID

import httpx
import sqlalchemy as sa
import yt_dlp

import mealie.db.models._all_models  # noqa: F401
from mealie.core import exceptions
from mealie.core.config import get_app_dirs
from mealie.core.root_logger import get_logger
from mealie.db.db_setup import session_context
from mealie.db.models.household.video import RecipeVideo, ShoppingListVideo, Video, VideoDownloadSettings
from mealie.lang import get_locale_provider
from mealie.repos.all_repositories import get_repositories
from mealie.schema.household.group_shopping_list import ShoppingListAddRecipeParamsBulk, ShoppingListCreate
from mealie.schema.openai.video import OpenAIVideoAnalysis
from mealie.services.household_services.shopping_lists import ShoppingListService
from mealie.services.openai import OpenAIService
from mealie.services.recipe.recipe_service import OpenAIRecipeService, RecipeService

logger = get_logger("video-library")
MAX_DESCRIPTION_CHARS = 50_000
GEMINI_FILE_POLL_SECONDS = 3
GEMINI_FILE_WAIT_SECONDS = 900
PROGRESS_UPDATE_SECONDS = 1.5
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
NON_MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | {".vtt", ".srt", ".ass", ".ttml", ".json", ".part", ".ytdl"}
ACTIVE_PROCESSING_STATUSES = {"pending", "metadata", "downloading", "processing"}
MAX_CONCURRENT_VIDEO_PROCESSING = 2
_background_video_tasks: set[asyncio.Task[None]] = set()
_video_processing_semaphore: asyncio.Semaphore | None = None


def _processing_semaphore() -> asyncio.Semaphore:
    global _video_processing_semaphore
    if _video_processing_semaphore is None:
        _video_processing_semaphore = asyncio.Semaphore(MAX_CONCURRENT_VIDEO_PROCESSING)
    return _video_processing_semaphore


class VideoProcessingCancelled(Exception):
    pass


def normalize_video_url(value: str) -> str:
    raw = value.strip()
    parts = urlsplit(raw)
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        raise ValueError("A valid HTTP or HTTPS video address is required")
    host = parts.netloc.lower().removeprefix("www.")
    path = parts.path or "/"
    query = dict(parse_qsl(parts.query, keep_blank_values=False))

    youtube_id = ""
    if host in {"youtube.com", "m.youtube.com", "youtube-nocookie.com"}:
        if path == "/watch":
            youtube_id = query.get("v", "")
        elif path.startswith(("/shorts/", "/embed/")):
            youtube_id = path.split("/", 2)[2]
    elif host == "youtu.be":
        youtube_id = path.strip("/").split("/", 1)[0]
    if youtube_id:
        return f"https://youtube.com/watch?v={youtube_id}"

    tracking_keys = {"fbclid", "gclid", "igshid", "mc_cid", "mc_eid", "ref", "ref_src", "si"}
    cleaned_query = [
        (key, item)
        for key, item in parse_qsl(parts.query, keep_blank_values=False)
        if not key.lower().startswith("utm_") and key.lower() not in tracking_keys
    ]
    return urlunsplit((parts.scheme.lower(), host, path, urlencode(cleaned_query, doseq=True), ""))


def _is_youtube_url(value: str) -> bool:
    host = urlsplit(value).netloc.lower().removeprefix("www.")
    return host in {"youtube.com", "m.youtube.com", "youtube-nocookie.com", "youtu.be"}


def _youtube_video_id(value: str) -> str:
    parts = urlsplit(value)
    host = parts.netloc.lower().removeprefix("www.")
    if host == "youtu.be":
        return parts.path.strip("/").split("/", 1)[0]
    query = dict(parse_qsl(parts.query, keep_blank_values=False))
    if query.get("v"):
        return query["v"]
    match = re.match(r"^/(?:shorts|embed)/([^/?#]+)", parts.path)
    return match.group(1) if match else ""


def _storage_dir(group_id: UUID | str, video_id: UUID | str) -> Path:
    path = get_app_dirs().DATA_DIR.joinpath("videos", str(group_id), str(video_id))
    path.mkdir(parents=True, exist_ok=True)
    return path


def video_storage_dir(group_id: UUID | str, video_id: UUID | str) -> Path:
    return _storage_dir(group_id, video_id)


def _settings_dict(settings: VideoDownloadSettings | None) -> dict[str, Any]:
    return {
        "download_by_default": settings.download_by_default if settings else True,
        "quality": settings.quality if settings else "best",
        "container": settings.container if settings else "mp4",
        "codec": settings.codec if settings else "auto",
        "audio_only": settings.audio_only if settings else False,
        "audio_quality": settings.audio_quality if settings else "best",
        "save_subtitles": settings.save_subtitles if settings else False,
        "save_thumbnail": settings.save_thumbnail if settings else True,
        "save_metadata": settings.save_metadata if settings else True,
        "fallback_to_lower_quality": settings.fallback_to_lower_quality if settings else True,
    }


def _update_video(video_id: UUID, **values: Any) -> None:
    with session_context() as session:
        session.execute(sa.update(Video).where(Video.id == video_id).values(**values))
        session.commit()


def _cancel_requested(video_id: UUID) -> bool:
    with session_context() as session:
        return bool(session.execute(sa.select(Video.cancel_requested).where(Video.id == video_id)).scalar_one_or_none())


def _quality_format(settings: dict[str, Any], *, temporary_audio: bool) -> str:
    audio_quality = settings["audio_quality"]
    audio_filter = "bestaudio"
    if audio_quality != "best":
        audio_filter = f"bestaudio[abr<={audio_quality}]"

    if settings["audio_only"] or temporary_audio:
        return f"{audio_filter}/bestaudio/best"

    height = settings["quality"]
    height_filter = "" if height == "best" else f"[height<={height}]"
    codec_filters = {
        "h264": "[vcodec^=avc1]",
        "h265": "[vcodec^=hev1]",
        "vp9": "[vcodec^=vp9]",
        "av1": "[vcodec^=av01]",
    }
    codec_filter = codec_filters.get(settings["codec"], "")
    preferred = f"bestvideo{height_filter}{codec_filter}+bestaudio/best{height_filter}{codec_filter}"
    if settings["fallback_to_lower_quality"]:
        return f"{preferred}/bestvideo{height_filter}+bestaudio/best{height_filter}/best"
    return preferred


def _metadata_payload(info: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "id",
        "title",
        "webpage_url",
        "original_url",
        "extractor",
        "extractor_key",
        "uploader",
        "channel",
        "channel_url",
        "duration",
        "upload_date",
        "timestamp",
        "language",
        "view_count",
        "like_count",
        "categories",
        "tags",
        "thumbnail",
        "width",
        "height",
        "ext",
        "format_id",
    )
    payload: dict[str, Any] = {}
    for key in keys:
        value = info.get(key)
        if isinstance(value, (str, int, float, bool, list, dict)) or value is None:
            payload[key] = value
    return payload


def _published_at(info: dict[str, Any]) -> str | None:
    upload_date = str(info.get("upload_date") or "")
    if re.fullmatch(r"\d{8}", upload_date):
        return f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
    return None


def _find_file(root: Path, extensions: set[str], *, largest: bool = False) -> Path | None:
    candidates = [path for path in root.iterdir() if path.is_file() and path.suffix.lower() in extensions]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_size) if largest else sorted(candidates)[0]


def _find_media(root: Path) -> Path | None:
    candidates = [
        path
        for path in root.iterdir()
        if path.is_file()
        and path.suffix.lower() not in NON_MEDIA_EXTENSIONS
        and not path.name.startswith("transcription.")
    ]
    return max(candidates, key=lambda path: path.stat().st_size) if candidates else None


def _download_assets(
    video_id: UUID,
    group_id: UUID,
    settings: dict[str, Any],
    options: dict[str, Any],
) -> dict[str, Any]:
    root = _storage_dir(group_id, video_id)
    is_youtube = _is_youtube_url(options["url"])
    temporary_media = not options["download_enabled"] and options["process_with_ai"] and not is_youtube
    should_download = options["download_enabled"] or temporary_media
    download_error = ""
    last_progress_update = 0.0
    last_cancel_check = 0.0
    last_percent = -1

    def progress_hook(data: dict[str, Any]) -> None:
        nonlocal last_cancel_check, last_progress_update, last_percent
        now = time.monotonic()
        if now - last_cancel_check >= 1:
            last_cancel_check = now
            if _cancel_requested(video_id):
                raise VideoProcessingCancelled("Video processing was cancelled")
        if data.get("status") != "downloading":
            return
        total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
        downloaded = data.get("downloaded_bytes") or 0
        percent = int(min(90, max(1, (downloaded / total) * 90))) if total else max(last_percent, 1)
        if percent != last_percent and (now - last_progress_update >= PROGRESS_UPDATE_SECONDS or percent >= 90):
            _update_video(video_id, processing_status="downloading", processing_progress=percent)
            last_percent = percent
            last_progress_update = now

    if is_youtube and options["process_with_ai"] and not options["download_enabled"]:
        youtube_id = _youtube_video_id(options["url"])
        return {
            "info": {
                "title": options.get("title") or "Saved YouTube video",
                "webpage_url": options["url"],
                "original_url": options["url"],
                "extractor": "youtube",
                "extractor_key": "Youtube",
                "thumbnail": f"https://i.ytimg.com/vi/{youtube_id}/hqdefault.jpg" if youtube_id else None,
            },
            "media": None,
            "thumbnail": None,
            "temporary_media": False,
            "download_error": "",
        }

    ydl_options: dict[str, Any] = {
        "format": _quality_format(settings, temporary_audio=False),
        "outtmpl": str(root.joinpath("media.%(ext)s")),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "skip_download": not should_download,
        "continuedl": True,
        "retries": 5,
        "fragment_retries": 5,
        "socket_timeout": 30,
        "progress_hooks": [progress_hook],
        # Gemini reads the audiovisual stream directly. yt-dlp is only used to
        # keep a local copy when the user explicitly requests one.
        "writesubtitles": False,
        "writeautomaticsub": False,
        "writethumbnail": bool(settings["save_thumbnail"]),
        "writeinfojson": bool(settings["save_metadata"]),
    }
    if not settings["audio_only"]:
        ydl_options["merge_output_format"] = settings["container"]

    try:
        with yt_dlp.YoutubeDL(ydl_options) as ydl:
            info = ydl.extract_info(options["url"], download=should_download)
    except yt_dlp.utils.DownloadError as final_error:
        info = None
        if info is None:
            if not (is_youtube and options["process_with_ai"]):
                raise final_error
            youtube_id = _youtube_video_id(options["url"])
            download_error = f"Local video download failed; Gemini analysis continued: {str(final_error)[:1000]}"
            logger.warning(download_error)
            info = {
                "title": options.get("title") or "Saved YouTube video",
                "webpage_url": options["url"],
                "original_url": options["url"],
                "extractor": "youtube",
                "extractor_key": "Youtube",
                "thumbnail": f"https://i.ytimg.com/vi/{youtube_id}/hqdefault.jpg" if youtube_id else None,
            }
    if not info:
        raise ValueError("yt-dlp returned no video information")

    media = _find_media(root)
    thumbnail = _find_file(root, IMAGE_EXTENSIONS)
    return {
        "info": info,
        "media": media,
        "thumbnail": thumbnail,
        "temporary_media": temporary_media,
        "download_error": download_error,
    }


def _target_language_text(target_language: str | None) -> str:
    if not target_language:
        return ""
    return f"\nTarget language: {target_language}. Return all generated text in that language."


def _gemini_api_root(provider) -> str:
    models_url = OpenAIService._gemini_models_url(provider)
    return models_url.rsplit("/models", 1)[0]


async def _gemini_file_upload(client: httpx.AsyncClient, api_key: str, media: Path) -> tuple[str, str]:
    mime_type = mimetypes.guess_type(media.name)[0] or "video/mp4"
    size = media.stat().st_size
    start_response = await client.post(
        "https://generativelanguage.googleapis.com/upload/v1beta/files",
        headers={
            "x-goog-api-key": api_key,
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(size),
            "X-Goog-Upload-Header-Content-Type": mime_type,
            "Content-Type": "application/json",
        },
        json={"file": {"display_name": media.name}},
    )
    start_response.raise_for_status()
    upload_url = start_response.headers.get("X-Goog-Upload-URL")
    if not upload_url:
        raise ValueError("Gemini did not return a video upload URL")

    async def file_chunks():
        with media.open("rb") as handle:
            while chunk := await asyncio.to_thread(handle.read, 1024 * 1024):
                yield chunk

    upload_response = await client.post(
        upload_url,
        headers={
            "x-goog-api-key": api_key,
            "X-Goog-Upload-Offset": "0",
            "X-Goog-Upload-Command": "upload, finalize",
            "Content-Length": str(size),
        },
        content=file_chunks(),
    )
    upload_response.raise_for_status()
    file_info = upload_response.json().get("file") or {}
    file_uri = str(file_info.get("uri") or "")
    file_name = str(file_info.get("name") or "")
    if not file_uri or not file_name:
        raise ValueError("Gemini video upload returned incomplete file information")

    deadline = time.monotonic() + GEMINI_FILE_WAIT_SECONDS
    while str(file_info.get("state") or "").upper() not in {"ACTIVE", "FAILED"}:
        if time.monotonic() >= deadline:
            raise TimeoutError("Gemini timed out while processing the uploaded video")
        await asyncio.sleep(GEMINI_FILE_POLL_SECONDS)
        status_response = await client.get(
            f"https://generativelanguage.googleapis.com/v1beta/{file_name}",
            headers={"x-goog-api-key": api_key},
        )
        status_response.raise_for_status()
        file_info = status_response.json()
    if str(file_info.get("state") or "").upper() == "FAILED":
        raise ValueError("Gemini could not process the uploaded video")
    return file_uri, file_name


async def _delete_gemini_file(client: httpx.AsyncClient, api_key: str, file_name: str) -> None:
    if not file_name:
        return
    try:
        await client.delete(
            f"https://generativelanguage.googleapis.com/v1beta/{file_name}",
            headers={"x-goog-api-key": api_key},
        )
    except Exception:
        logger.warning("Could not remove temporary Gemini video file %s", file_name)


def _gemini_response_text(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates") or []
    if not candidates:
        return ""
    parts = ((candidates[0].get("content") or {}).get("parts") or [])
    text = "\n".join(str(part.get("text") or "") for part in parts if part.get("text"))
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
    return text


async def _analyze_video_with_gemini(
    openai_service: OpenAIService,
    video: Video,
    info: dict[str, Any],
    media: Path | None,
) -> OpenAIVideoAnalysis:
    provider = openai_service.default_provider
    if not provider:
        raise ValueError("No default Gemini provider is configured")
    api_keys = OpenAIService._split_api_keys(provider.api_key)
    if not api_keys:
        raise ValueError("No Gemini API key is configured")

    prompt = openai_service.get_prompt("videos.analyze-video")
    schema = json.dumps(OpenAIVideoAnalysis.model_json_schema(), ensure_ascii=False)
    metadata = (
        f"Video URL: {video.url}\n"
        f"Original title: {info.get('title') or video.title}\n"
        f"Creator/channel: {info.get('channel') or info.get('uploader') or ''}\n"
        f"Original description: {str(info.get('description') or video.description or '')[:MAX_DESCRIPTION_CHARS]}"
        f"{_target_language_text(video.target_language)}"
    )
    message = (
        f"{prompt}\n\n{metadata}\n\n"
        + (
            "Add concise practical cooking notes and useful ingredient-variety recommendations.\n"
            if video.include_ai_tips
            else "Do not add new AI tips or ingredient-variety recommendations.\n"
        )
        + (
            "Add a concise mise en place plan with the ingredients and tools required for every task.\n"
            if video.include_mise_en_place
            else (
                "Return null for recipe.mise_en_place and empty lists for recipe.mise_en_place_food "
                "and recipe.mise_en_place_tools.\n"
            )
        )
        + "Return only valid JSON that matches this JSON Schema exactly:\n"
        f"{schema}"
    )
    model = provider.model.removeprefix("models/")
    endpoint = f"{_gemini_api_root(provider)}/models/{model}:generateContent"
    start_index = video.id.int % len(api_keys)
    ordered_keys = api_keys[start_index:] + api_keys[:start_index]
    last_error: Exception | None = None

    for api_key in ordered_keys:
        uploaded_name = ""
        try:
            async with httpx.AsyncClient(timeout=provider.timeout, follow_redirects=True) as client:
                if _is_youtube_url(video.url):
                    video_uri = video.url
                elif media:
                    video_uri, uploaded_name = await _gemini_file_upload(client, api_key, media)
                else:
                    raise ValueError("A local video file is required for non-YouTube Gemini analysis")

                response = await client.post(
                    endpoint,
                    headers={
                        "x-goog-api-key": api_key,
                        "Content-Type": "application/json",
                        **(provider.request_headers or {}),
                    },
                    params=provider.request_params or None,
                    json={
                        "contents": [
                            {
                                "role": "user",
                                "parts": [
                                    {"file_data": {"file_uri": video_uri}},
                                    {"text": message},
                                ],
                            }
                        ],
                        "generationConfig": {"responseMimeType": "application/json"},
                    },
                )
                if response.status_code == 429 or response.status_code >= 500:
                    last_error = exceptions.RateLimitError(OpenAIService._provider_error_message(response))
                    continue
                response.raise_for_status()
                response_text = _gemini_response_text(response.json())
                if not response_text:
                    raise ValueError("Gemini returned no video analysis")
                analysis = OpenAIVideoAnalysis.model_validate_json(response_text)
                if analysis.contains_complete_recipe and not analysis.recipe:
                    analysis.contains_complete_recipe = False
                if analysis.recipe and not video.include_mise_en_place:
                    analysis.recipe.mise_en_place = None
                    analysis.recipe.mise_en_place_food = []
                    analysis.recipe.mise_en_place_tools = []
                return analysis
        except (httpx.HTTPError, ValueError, exceptions.RateLimitError) as error:
            last_error = error
        finally:
            if uploaded_name:
                async with httpx.AsyncClient(timeout=30) as cleanup_client:
                    await _delete_gemini_file(cleanup_client, api_key, uploaded_name)

    raise last_error or RuntimeError("Gemini video analysis failed")


async def _analyze_video(
    repos,
    video: Video,
    info: dict[str, Any],
    media: Path | None,
) -> OpenAIVideoAnalysis | None:
    openai_service = OpenAIService(repos)
    if not (openai_service.provider_settings and openai_service.provider_settings.ai_enabled):
        return None
    if not openai_service.default_provider or not OpenAIService._is_gemini_provider_data(
        openai_service.default_provider
    ):
        raise ValueError("Direct video understanding requires a Google Gemini provider")
    return await _analyze_video_with_gemini(openai_service, video, info, media)


def _unique_terms(values: list[Any], limit: int = 60) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for value in values:
        term = " ".join(str(value).split()).strip()[:120]
        if term and term.casefold() not in seen:
            seen.add(term.casefold())
            terms.append(term)
        if len(terms) >= limit:
            break
    return terms


async def _create_linked_recipe_and_list(
    repos,
    user,
    household,
    video: Video,
    analysis: OpenAIVideoAnalysis,
    info: dict[str, Any],
) -> None:
    recipe_service = RecipeService(repos, user, household, get_locale_provider())
    if analysis.recipe:
        openai_recipe = analysis.recipe.model_copy(
            update={
                "source": analysis.recipe.source or video.url,
                "created_by": analysis.recipe.created_by or video.creator,
            }
        )
        converter = OpenAIRecipeService(repos, user, household, get_locale_provider())
        recipe = recipe_service.create_one(
            recipe_service.apply_ai_recipe_attribution(converter.convert_recipe(openai_recipe))
        )
    else:
        return

    await recipe_service.attach_best_effort_image(
        recipe,
        image_url=(
            str(info.get("thumbnail") or video.thumbnail_url or "") or None
            if analysis.recipe.source_image_is_finished_dish
            else None
        ),
        search_queries=[f"{recipe.name} finished plated dish", recipe.name],
        source_url=video.url,
    )
    repos.session.add(RecipeVideo(recipe_id=recipe.id, video_id=video.id))
    video.recipe_detected = True

    if not video.create_shopping_list:
        repos.session.commit()
        return

    shopping_service = ShoppingListService(repos)
    list_name = shopping_service.available_unique_list_name(recipe.name)
    shopping_list = shopping_service.create_one_list(
        ShoppingListCreate(
            name=list_name,
            extras={
                "aiCreatedFromVideo": True,
                "aiCreatedFromVideoId": str(video.id),
                "aiCreatedFromRecipeId": str(recipe.id),
            },
        ),
        user.id,
    )
    if not shopping_list:
        repos.session.commit()
        return

    shopping_list, _ = shopping_service.add_recipe_ingredients_to_list(
        shopping_list.id,
        [
            ShoppingListAddRecipeParamsBulk(
                recipe_id=recipe.id,
                recipe_increment_quantity=1,
                recipe_ingredients=recipe.recipe_ingredient or None,
            )
        ],
    )
    repos.session.add(ShoppingListVideo(shopping_list_id=shopping_list.id, video_id=video.id))
    repos.session.commit()

    if video.organize_shopping_list and shopping_list.list_items:
        try:
            await shopping_service.organize_with_ai(
                shopping_list.id,
                include_ai_tips=video.include_ai_tips,
                target_language=video.target_language,
            )
        except Exception:
            logger.exception("Failed to organize video shopping list %s", shopping_list.id)
            repos.session.rollback()


async def _run_video_processing(video_id: UUID) -> None:
    try:
        with session_context() as session:
            video = session.execute(sa.select(Video).where(Video.id == video_id)).scalar_one_or_none()
            if not video:
                return
            if video.cancel_requested:
                video.processing_status = "cancelled"
                video.processing_error = None
                video.cancel_requested = False
                session.add(video)
                session.commit()
                return
            settings_model = session.execute(
                sa.select(VideoDownloadSettings).where(VideoDownloadSettings.user_id == video.user_id)
            ).scalar_one_or_none()
            settings = _settings_dict(settings_model)
            options = {
                "url": video.url,
                "title": video.title,
                "download_enabled": video.download_enabled,
                "create_recipe": video.create_recipe and video.process_with_ai,
                "process_with_ai": video.process_with_ai,
                "target_language": video.target_language,
            }
            group_id = video.group_id
            session.execute(
                sa.update(Video)
                .where(Video.id == video_id)
                .values(
                    processing_status="metadata",
                    processing_progress=1,
                    processing_error=None,
                )
            )
            session.commit()

        result = await asyncio.to_thread(_download_assets, video_id, group_id, settings, options)
        if _cancel_requested(video_id):
            raise VideoProcessingCancelled("Video processing was cancelled")
        _update_video(video_id, processing_status="processing", processing_progress=92)

        info = result["info"]
        media: Path | None = result["media"]
        thumbnail: Path | None = result["thumbnail"]

        with session_context() as session:
            video = session.execute(sa.select(Video).where(Video.id == video_id)).scalar_one_or_none()
            if not video:
                return
            repos = get_repositories(session, group_id=video.group_id, household_id=video.household_id)
            user = repos.users.get_one(video.user_id, "id", any_case=False)
            household = repos.households.get_one(video.household_id)
            if not user or not household:
                raise ValueError("Video owner no longer exists")

            if _cancel_requested(video_id):
                raise VideoProcessingCancelled("Video processing was cancelled")
            if video.process_with_ai:
                video.title = str(info.get("title") or video.title or "Saved video")[:500]
            video.original_description = (
                str(info.get("description") or video.original_description or "")[:MAX_DESCRIPTION_CHARS] or None
            )
            video.description = video.description or video.original_description
            video.platform = str(info.get("extractor_key") or info.get("extractor") or "")[:120] or None
            video.creator = str(info.get("channel") or info.get("uploader") or video.creator or "")[:255] or None
            video.duration_seconds = int(info.get("duration") or 0) or None
            video.published_at = _published_at(info)
            video.language = str(info.get("language") or "")[:64] or None
            video.thumbnail_url = str(info.get("thumbnail") or video.thumbnail_url or "")[:2000] or None
            video.thumbnail_file_name = thumbnail.name if thumbnail else None
            video.metadata_json = json.dumps(_metadata_payload(info), ensure_ascii=False)
            video.transcript = None

            analysis: OpenAIVideoAnalysis | None = None
            processing_warnings = [str(result.get("download_error") or "").strip()]
            processing_warnings = [warning for warning in processing_warnings if warning]
            if video.process_with_ai:
                try:
                    analysis = await _analyze_video(repos, video, info, media)
                except Exception as error:
                    logger.exception("AI video analysis failed for %s", video.id)
                    processing_warnings.append(f"AI video analysis failed: {str(error)[:1000]}")
            if _cancel_requested(video_id):
                raise VideoProcessingCancelled("Video processing was cancelled")
            if analysis:
                if analysis.title.strip():
                    video.title = analysis.title.strip()[:500]
                if analysis.description.strip():
                    video.description = analysis.description.strip()[:MAX_DESCRIPTION_CHARS]
                video.categories_json = json.dumps(_unique_terms(analysis.categories), ensure_ascii=False)
                video.tags_json = json.dumps(_unique_terms(analysis.tags), ensure_ascii=False)
            else:
                video.categories_json = json.dumps(_unique_terms(info.get("categories") or []), ensure_ascii=False)
                video.tags_json = json.dumps(_unique_terms(info.get("tags") or []), ensure_ascii=False)

            if video.download_enabled and media:
                video.local_file_name = media.name
                video.local_format = media.suffix.lstrip(".")[:32] or None
                width = info.get("width")
                height = info.get("height")
                video.local_resolution = f"{width}x{height}" if width and height else None
                video.local_file_size = media.stat().st_size
            session.add(video)
            session.commit()
            session.refresh(video)

            if (
                analysis
                and analysis.is_food_video
                and analysis.contains_complete_recipe
                and video.create_recipe
                and not video.recipe_links
            ):
                try:
                    await _create_linked_recipe_and_list(repos, user, household, video, analysis, info)
                except exceptions.NotARecipe:
                    logger.info("Video %s did not contain enough recipe data", video.id)
                except Exception:
                    logger.exception("Failed to create a linked recipe for video %s", video.id)
                    session.rollback()

            video.processing_status = "failed" if video.process_with_ai and not analysis else "completed"
            video.processing_progress = 100
            video.processing_error = "\n".join(processing_warnings) or None
            session.add(video)
            session.commit()

        if result["temporary_media"] and media:
            media.unlink(missing_ok=True)
    except VideoProcessingCancelled:
        _update_video(video_id, processing_status="cancelled", processing_error=None, cancel_requested=False)
    except Exception as error:
        logger.exception("Video processing failed for %s", video_id)
        _update_video(
            video_id,
            processing_status="failed",
            processing_error=f"{error.__class__.__name__}: {str(error)[:1500]}",
            cancel_requested=False,
        )


async def run_video_processing(video_id: UUID) -> None:
    async with _processing_semaphore():
        await _run_video_processing(video_id)


def delete_video_files(group_id: UUID | str, video_id: UUID | str) -> None:
    root = get_app_dirs().DATA_DIR.joinpath("videos", str(group_id), str(video_id))
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)


def schedule_video_processing(video_id: UUID) -> None:
    task = asyncio.create_task(run_video_processing(video_id))
    _background_video_tasks.add(task)
    task.add_done_callback(_background_video_tasks.discard)


async def resume_interrupted_video_processing() -> None:
    with session_context() as session:
        interrupted = session.execute(
            sa.select(Video.id, Video.cancel_requested).where(Video.processing_status.in_(ACTIVE_PROCESSING_STATUSES))
        ).all()
        cancelled_ids = [row.id for row in interrupted if row.cancel_requested]
        video_ids = [row.id for row in interrupted if not row.cancel_requested]
        if cancelled_ids:
            session.execute(
                sa.update(Video)
                .where(Video.id.in_(cancelled_ids))
                .values(processing_status="cancelled", processing_error=None, cancel_requested=False)
            )
        if video_ids:
            session.execute(
                sa.update(Video)
                .where(Video.id.in_(video_ids))
                .values(processing_status="pending", processing_error=None)
            )
        if cancelled_ids or video_ids:
            session.commit()
    for video_id in video_ids:
        schedule_video_processing(video_id)
