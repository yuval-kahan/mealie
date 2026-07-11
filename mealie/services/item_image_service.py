import asyncio
import hashlib
import re
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

import httpx
import orjson
from PIL import Image
from pydantic import UUID4
from slugify import slugify

from mealie.pkgs import img, safehttp
from mealie.repos.repository_factory import AllRepositories
from mealie.schema.household.group_shopping_list import ShoppingListItemOut, ShoppingListOut
from mealie.schema.openai.general import OpenAIImageSearchQueries
from mealie.schema.recipe.recipe import Recipe
from mealie.services._base_service import BaseService
from mealie.services.openai import OpenAIService

ITEM_IMAGE_MAX_BYTES = 8 * 1024 * 1024
ITEM_IMAGE_MAX_PIXELS = 25_000_000
ITEM_IMAGE_SEARCH_URL = "https://api.openverse.org/v1/images/"
ITEM_IMAGE_MAX_CANDIDATES = 8
ITEM_IMAGE_CONCURRENCY = 4
ITEM_IMAGE_BATCH_SIZE = 40

ItemImageKind = str


@dataclass(frozen=True)
class ItemImageRequest:
    kind: ItemImageKind
    name: str
    context: str | None = None


@dataclass
class ItemImageEnsureResult:
    existing: int = 0
    created: int = 0
    failed: int = 0

    def add(self, other: "ItemImageEnsureResult") -> None:
        self.existing += other.existing
        self.created += other.created
        self.failed += other.failed


class ItemImageService(BaseService):
    """Shared image cache for ingredients, tools, and shopping-list items."""

    valid_kinds = {"food", "tool"}

    def __init__(self, group_id: UUID4 | str, repos: AllRepositories | None = None):
        super().__init__()
        self.repos = repos
        self.group_id = str(group_id)
        self.root_dir = self.directories.DATA_DIR.joinpath("item-images", self.group_id)
        self.minifier = img.PillowMinifier(purge=True, logger=self.logger)
        self._wikimedia_lock = asyncio.Lock()
        self._wikimedia_last_request = 0.0

    @classmethod
    def normalize_name(cls, name: str | None) -> str:
        return re.sub(r"\s+", " ", str(name or "")).strip().casefold()

    @classmethod
    def image_key(cls, name: str | None) -> str:
        normalized = cls.normalize_name(name)
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
        readable = slugify(normalized)[:60].strip("-") or "item"
        return f"{readable}-{digest}"

    @classmethod
    def image_dir(cls, root: Path, kind: ItemImageKind, name: str | None) -> Path:
        return root.joinpath(kind, cls.image_key(name))

    @classmethod
    def image_path(
        cls,
        root: Path,
        kind: ItemImageKind,
        name: str | None,
        file_name: str = "tiny-original.webp",
    ) -> Path:
        return cls.image_dir(root, kind, name).joinpath(file_name)

    def get_image_path(self, kind: ItemImageKind, name: str | None, file_name: str = "tiny-original.webp") -> Path:
        if kind not in self.valid_kinds:
            raise ValueError("Invalid item image kind")

        return self.image_path(self.root_dir, kind, name, file_name)

    async def ensure_recipe_images(self, recipe: Recipe) -> ItemImageEnsureResult:
        return await self.ensure_many(self._recipe_image_requests(recipe))

    async def ensure_recipes_images(self, recipes: Iterable[Recipe]) -> ItemImageEnsureResult:
        requests: list[ItemImageRequest] = []

        for recipe in recipes:
            requests.extend(self._recipe_image_requests(recipe))
        return await self.ensure_many(requests)

    def _recipe_image_requests(self, recipe: Recipe) -> list[ItemImageRequest]:
        requests: list[ItemImageRequest] = []

        for ingredient in recipe.recipe_ingredient or []:
            if ingredient.title:
                continue

            name = ingredient.food.name if ingredient.food else ingredient.display or ingredient.note
            if not name:
                continue

            context_parts = [ingredient.recommended_variety, ingredient.note, recipe.name]
            requests.append(ItemImageRequest("food", name, " ".join(part for part in context_parts if part)))

        for tool in recipe.tools or []:
            if tool.name:
                requests.append(ItemImageRequest("tool", tool.name, recipe.name or None))

        return requests

    async def ensure_shopping_list_images(self, shopping_list: ShoppingListOut) -> ItemImageEnsureResult:
        requests = [
            ItemImageRequest("food", self._shopping_item_name(item), item.note or None)
            for item in shopping_list.list_items or []
            if self._shopping_item_name(item)
        ]
        return await self.ensure_many(requests)

    def _shopping_item_name(self, item: ShoppingListItemOut) -> str:
        if item.food and item.food.name:
            return item.food.name

        return item.display or item.note or ""

    async def ensure_many(self, requests: Iterable[ItemImageRequest]) -> ItemImageEnsureResult:
        unique_requests = self._dedupe_requests(requests)
        result = ItemImageEnsureResult()
        missing: list[ItemImageRequest] = []

        for request in unique_requests:
            if request.kind not in self.valid_kinds or not self.normalize_name(request.name):
                continue

            if self.get_image_path(request.kind, request.name, "tiny-original.webp").exists():
                result.existing += 1
            else:
                missing.append(request)

        if not missing:
            return result

        ai_queries = await self._build_ai_search_queries(missing)
        limits = httpx.Limits(
            max_connections=ITEM_IMAGE_CONCURRENCY,
            max_keepalive_connections=ITEM_IMAGE_CONCURRENCY,
        )
        semaphore = asyncio.Semaphore(ITEM_IMAGE_CONCURRENCY)

        async with (
            httpx.AsyncClient(timeout=6.0, follow_redirects=True, limits=limits) as search_client,
            httpx.AsyncClient(
                transport=safehttp.AsyncSafeTransport(impersonate="chrome"),
                timeout=8.0,
                follow_redirects=True,
                limits=limits,
            ) as download_client,
        ):

            async def ensure_one(request: ItemImageRequest) -> bool:
                async with semaphore:
                    return await self._ensure_one(
                        request,
                        ai_queries.get(self._request_key(request)),
                        search_client,
                        download_client,
                    )

            for start in range(0, len(missing), ITEM_IMAGE_BATCH_SIZE):
                batch = missing[start : start + ITEM_IMAGE_BATCH_SIZE]
                outcomes = await asyncio.gather(*(ensure_one(request) for request in batch), return_exceptions=True)
                for outcome in outcomes:
                    if outcome is True:
                        result.created += 1
                    else:
                        result.failed += 1

        return result

    def _dedupe_requests(self, requests: Iterable[ItemImageRequest]) -> list[ItemImageRequest]:
        seen: set[tuple[str, str]] = set()
        deduped: list[ItemImageRequest] = []
        for request in requests:
            key = (request.kind, self.normalize_name(request.name))
            if not key[1] or key in seen:
                continue
            seen.add(key)
            deduped.append(request)
        return deduped

    def _request_key(self, request: ItemImageRequest) -> str:
        return f"{request.kind}:{self.normalize_name(request.name)}"

    async def _build_ai_search_queries(self, requests: list[ItemImageRequest]) -> dict[str, str]:
        if not requests:
            return {}

        if not self.repos:
            return {}

        openai_service = OpenAIService(self.repos)
        if not (openai_service.provider_settings and openai_service.provider_settings.ai_enabled):
            return {}

        payload = [
            {
                "key": self._request_key(request),
                "kind": request.kind,
                "name": request.name,
                "context": request.context,
            }
            for request in requests[:80]
        ]
        prompt = (
            "Create concise English public image-search phrases for ingredients and kitchen tools. "
            "Return one entry for every supplied item. Copy each provided key exactly into the matching entry. "
            "For food, prefer isolated ingredient/product photos. For tools, prefer clear kitchen equipment photos. "
            "Remove quantities, measurements, recipe names, and preparation instructions from the search phrase. "
            "Do not use brand names unless they are part of the item itself."
        )
        message = orjson.dumps(payload).decode("utf-8")

        try:
            response = await openai_service.get_response(prompt, message, response_schema=OpenAIImageSearchQueries)
        except Exception:
            self.logger.exception("Failed to build item image AI search queries")
            return {}

        if not response:
            return {}

        valid_keys = {item["key"] for item in payload}
        return {
            item.key: item.query.strip()
            for item in response.queries
            if item.key in valid_keys and item.query.strip()
        }

    async def _ensure_one(
        self,
        request: ItemImageRequest,
        ai_query: str | None,
        search_client: httpx.AsyncClient,
        download_client: httpx.AsyncClient,
    ) -> bool:
        queries = self._search_queries(request, ai_query)
        candidates: list[str] = []
        for query in queries:
            for candidate in await self._find_public_image_urls(query, search_client):
                if candidate not in candidates:
                    candidates.append(candidate)
                if len(candidates) >= ITEM_IMAGE_MAX_CANDIDATES:
                    break
            if candidates:
                break

        for candidate in candidates:
            try:
                if await self._download_image(request.kind, request.name, candidate, download_client):
                    return True
            except Exception:
                self.logger.exception("Failed to cache item image from %s", candidate)

        return False

    def _search_queries(self, request: ItemImageRequest, ai_query: str | None) -> list[str]:
        suffix = "ingredient isolated food photo" if request.kind == "food" else "kitchen tool equipment photo"
        values = [
            ai_query,
            f"{request.context} {request.name} {suffix}" if request.context else None,
            f"{request.name} {suffix}",
        ]
        queries: list[str] = []
        for value in values:
            query = re.sub(r"\s+", " ", value or "").strip()
            if query and query not in queries:
                queries.append(query[:160])
        return queries

    async def _find_public_image_urls(self, query: str, client: httpx.AsyncClient) -> list[str]:
        payload: dict = {}
        try:
            response = await client.get(
                ITEM_IMAGE_SEARCH_URL,
                params={"q": query, "page_size": 6, "mature": "false"},
                headers={"User-Agent": "Mealie item image search"},
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            self.logger.exception("Failed to search for item image")

        urls: list[str] = []
        for result in payload.get("results", []):
            # Openverse thumbnails are proxied and considerably more reliable
            # than hot-linking arbitrary origin servers. Keep the original as
            # a fallback when the thumbnail is unavailable.
            for value in (result.get("thumbnail"), result.get("url")):
                candidate = str(value or "").strip()
                if not candidate.lower().startswith(("http://", "https://")):
                    continue
                if candidate.lower().split("?", 1)[0].endswith(".svg"):
                    continue
                if candidate not in urls:
                    urls.append(candidate)
        if urls:
            return urls
        return await self._find_wikimedia_image_urls(query, client)

    async def _find_wikimedia_image_urls(self, query: str, client: httpx.AsyncClient) -> list[str]:
        try:
            async with self._wikimedia_lock:
                response = None
                for attempt in range(3):
                    elapsed = time.monotonic() - self._wikimedia_last_request
                    if elapsed < 1.1:
                        await asyncio.sleep(1.1 - elapsed)
                    response = await client.get(
                        "https://commons.wikimedia.org/w/api.php",
                        params={
                            "action": "query",
                            "format": "json",
                            "generator": "search",
                            "gsrsearch": query,
                            "gsrnamespace": 6,
                            "gsrlimit": 6,
                            "prop": "imageinfo",
                            "iiprop": "url",
                            "iiurlwidth": 1200,
                        },
                        headers={"User-Agent": "Mealie item image search"},
                    )
                    self._wikimedia_last_request = time.monotonic()
                    if response.status_code != 429 or attempt == 2:
                        break
                    retry_after = int(response.headers.get("retry-after", "0") or 0)
                    await asyncio.sleep(min(max(retry_after, 3 * (attempt + 1)), 30))
                assert response is not None
            response.raise_for_status()
            payload = response.json()
        except Exception:
            self.logger.exception("Failed to search Wikimedia Commons for an item image")
            return []

        urls: list[str] = []
        for page in payload.get("query", {}).get("pages", {}).values():
            image_info = page.get("imageinfo") or []
            if not image_info:
                continue
            candidate = (image_info[0].get("thumburl") or image_info[0].get("url") or "").strip()
            if not candidate.lower().startswith(("http://", "https://")):
                continue
            if candidate.lower().split("?", 1)[0].endswith(".svg"):
                continue
            urls.append(candidate)
        return urls

    async def _download_image(
        self,
        kind: ItemImageKind,
        name: str,
        url: str,
        client: httpx.AsyncClient,
    ) -> bool:
        image_dir = self.image_dir(self.root_dir, kind, name)
        image_dir.mkdir(parents=True, exist_ok=True)

        suffix = Path(url.split("?", 1)[0]).suffix.lower()
        if suffix not in img.IMAGE_EXTENSIONS:
            suffix = ".jpg"

        temp_path: Path | None = None
        try:
            with NamedTemporaryFile(delete=False, dir=image_dir, suffix=suffix) as temp_file:
                temp_path = Path(temp_file.name)
                total = 0

                async with client.stream("GET", url, headers={"User-Agent": "Mealie item image cache"}) as response:
                    if response.status_code != 200:
                        return False

                    content_type = response.headers.get("content-type", "").lower()
                    if "image" not in content_type:
                        return False

                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > ITEM_IMAGE_MAX_BYTES:
                            return False
                        temp_file.write(chunk)

            await asyncio.to_thread(self._validate_and_minify, temp_path)
            return self.get_image_path(kind, name, "tiny-original.webp").exists()
        finally:
            if temp_path:
                temp_path.unlink(missing_ok=True)

    def _validate_and_minify(self, image_path: Path) -> None:
        with Image.open(image_path) as image:
            if image.width * image.height > ITEM_IMAGE_MAX_PIXELS:
                raise ValueError("Item image exceeds the pixel limit")
            image.verify()

        self.minifier.minify(image_path)
