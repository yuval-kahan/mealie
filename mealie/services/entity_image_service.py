import asyncio
import re
from html import unescape
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urljoin, urlsplit

import httpx
from PIL import Image, ImageOps

from mealie.pkgs import safehttp
from mealie.services._base_service import BaseService

ENTITY_IMAGE_FILE_NAME = "image.webp"
ENTITY_IMAGE_MAX_BYTES = 12 * 1024 * 1024
ENTITY_IMAGE_MAX_PIXELS = 30_000_000
ENTITY_PAGE_MAX_BYTES = 2 * 1024 * 1024
ENTITY_IMAGE_SEARCH_URL = "https://api.openverse.org/v1/images/"


class EntityImageService(BaseService):
    """Store bounded, normalized images for non-recipe library entities."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        super().__init__()

    def image_path(self, kind: str, group_id: object, entity_id: object) -> Path:
        root = self.data_dir.joinpath("entity-images", kind, str(group_id)).resolve()
        target_dir = root.joinpath(str(entity_id)).resolve()
        if not target_dir.is_relative_to(root):
            raise ValueError("Invalid entity image path")
        return target_dir.joinpath(ENTITY_IMAGE_FILE_NAME)

    async def save_content(self, target: Path, content: bytes) -> None:
        if not content or len(content) > ENTITY_IMAGE_MAX_BYTES:
            raise ValueError("Image is empty or exceeds the size limit")
        target.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(self._write_image, content, target)

    async def save_url(self, target: Path, url: str) -> str:
        normalized_url = self._validate_http_url(url)
        limits = httpx.Limits(max_connections=2, max_keepalive_connections=1)
        async with httpx.AsyncClient(
            transport=safehttp.AsyncSafeTransport(impersonate="chrome"),
            timeout=20.0,
            follow_redirects=True,
            limits=limits,
        ) as client:
            async with client.stream(
                "GET",
                normalized_url,
                headers={"User-Agent": "Mealie entity image cache"},
            ) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").lower()
                if "image" not in content_type:
                    raise ValueError("The address did not return an image")
                chunks: list[bytes] = []
                total = 0
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > ENTITY_IMAGE_MAX_BYTES:
                        raise ValueError("Image exceeds the size limit")
                    chunks.append(chunk)
        await self.save_content(target, b"".join(chunks))
        return normalized_url

    async def discover_and_save_page_image(self, target: Path, page_url: str) -> str:
        normalized_url = self._validate_http_url(page_url)
        limits = httpx.Limits(max_connections=2, max_keepalive_connections=1)
        async with httpx.AsyncClient(
            transport=safehttp.AsyncSafeTransport(impersonate="chrome"),
            timeout=20.0,
            follow_redirects=True,
            limits=limits,
        ) as client:
            chunks: list[bytes] = []
            total = 0
            async with client.stream(
                "GET",
                normalized_url,
                headers={"User-Agent": "Mealie website image discovery"},
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    remaining = ENTITY_PAGE_MAX_BYTES - total
                    if remaining <= 0:
                        break
                    chunks.append(chunk[:remaining])
                    total += min(len(chunk), remaining)
            html = b"".join(chunks).decode("utf-8", errors="replace")

        candidates = self._page_image_candidates(html, normalized_url)
        last_error: Exception | None = None
        for candidate in candidates[:12]:
            try:
                return await self.save_url(target, candidate)
            except Exception as error:
                last_error = error
        if last_error:
            raise ValueError("No usable image was found on the website") from last_error
        raise ValueError("No image was found on the website")

    async def search_and_save_public_image(self, target: Path, query: str) -> str:
        """Find a bounded public image candidate and cache it locally."""
        normalized_query = re.sub(r"\s+", " ", query).strip()[:240]
        if not normalized_query:
            raise ValueError("An image search phrase is required")

        limits = httpx.Limits(max_connections=2, max_keepalive_connections=1)
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True, limits=limits) as client:
            candidates = await self._openverse_candidates(client, normalized_query)
            if not candidates:
                candidates = await self._wikimedia_candidates(client, normalized_query)

        last_error: Exception | None = None
        for candidate in candidates[:12]:
            try:
                await self.save_url(target, candidate)
                return candidate
            except (ValueError, httpx.HTTPError) as error:
                last_error = error
        if last_error:
            raise ValueError("No usable public image was found") from last_error
        raise ValueError("No public image was found")

    @staticmethod
    async def _openverse_candidates(client: httpx.AsyncClient, query: str) -> list[str]:
        try:
            response = await client.get(
                ENTITY_IMAGE_SEARCH_URL,
                params={"q": query, "page_size": 8, "mature": "false"},
                headers={"User-Agent": "Mealie entity image search"},
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            return []

        candidates: list[str] = []
        for result in payload.get("results", []):
            for value in (result.get("thumbnail"), result.get("url")):
                candidate = str(value or "").strip()
                if candidate.lower().startswith(("http://", "https://")) and candidate not in candidates:
                    candidates.append(candidate)
        return candidates

    @staticmethod
    async def _wikimedia_candidates(client: httpx.AsyncClient, query: str) -> list[str]:
        try:
            response = await client.get(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query",
                    "format": "json",
                    "generator": "search",
                    "gsrsearch": query,
                    "gsrnamespace": 6,
                    "gsrlimit": 8,
                    "prop": "imageinfo",
                    "iiprop": "url",
                    "iiurlwidth": 1400,
                },
                headers={"User-Agent": "Mealie entity image search"},
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            return []

        candidates: list[str] = []
        for page in payload.get("query", {}).get("pages", {}).values():
            image_info = page.get("imageinfo") or []
            if not image_info:
                continue
            candidate = str(image_info[0].get("thumburl") or image_info[0].get("url") or "").strip()
            if candidate.lower().startswith(("http://", "https://")):
                candidates.append(candidate)
        return candidates

    @staticmethod
    def _validate_http_url(url: str) -> str:
        value = url.strip()
        parts = urlsplit(value)
        if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
            raise ValueError("A valid HTTP or HTTPS image address is required")
        return value

    @staticmethod
    def _page_image_candidates(html: str, page_url: str) -> list[str]:
        candidates: list[str] = []
        meta_tags = re.findall(r"<meta\b[^>]*>", html, flags=re.IGNORECASE)
        preferred_names = ("og:image:secure_url", "og:image", "twitter:image", "twitter:image:src")
        values_by_name: dict[str, list[str]] = {}
        for tag in meta_tags:
            attributes = {
                key.casefold(): unescape(value)
                for key, _quote, value in re.findall(
                    r"""([:\w-]+)\s*=\s*(["'])(.*?)\2""",
                    tag,
                    flags=re.IGNORECASE | re.DOTALL,
                )
            }
            name = (attributes.get("property") or attributes.get("name") or "").casefold()
            content = attributes.get("content", "").strip()
            if name and content:
                values_by_name.setdefault(name, []).append(content)
        for name in preferred_names:
            candidates.extend(values_by_name.get(name, []))

        for src in re.findall(
            r"""<img\b[^>]*\bsrc\s*=\s*(["'])(.*?)\1""",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        ):
            candidates.append(src[1])

        normalized: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            absolute = urljoin(page_url, unescape(candidate.strip()))
            if absolute.lower().startswith(("http://", "https://")) and absolute not in seen:
                seen.add(absolute)
                normalized.append(absolute)
        return normalized

    @staticmethod
    def _write_image(content: bytes, target: Path) -> None:
        with Image.open(BytesIO(content)) as image:
            if image.width * image.height > ENTITY_IMAGE_MAX_PIXELS:
                raise ValueError("Image exceeds the pixel limit")
            image = ImageOps.exif_transpose(image).convert("RGB")
            image.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
            with NamedTemporaryFile(delete=False, dir=target.parent, suffix=".webp") as temp_file:
                temp_path = Path(temp_file.name)
            try:
                image.save(temp_path, "WEBP", quality=88, method=6)
                temp_path.replace(target)
            finally:
                temp_path.unlink(missing_ok=True)
