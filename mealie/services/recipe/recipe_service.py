import asyncio
import hashlib
import json
import math
import os
import re
import shutil
import time
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from html import unescape
from pathlib import Path
from shutil import copytree, rmtree
from textwrap import dedent
from typing import Any
from urllib.parse import urljoin
from uuid import UUID, uuid4
from zipfile import ZipFile

import httpx
import sqlalchemy as sa
from fastapi import UploadFile
from slugify import slugify
from sqlalchemy.orm import selectinload

from mealie.core import exceptions
from mealie.core.dependencies.dependencies import get_temporary_path
from mealie.db.models.recipe.ai_search_index import RecipeAISearchIndex
from mealie.db.models.recipe.ingredient import RecipeIngredientModel
from mealie.lang.providers import Translator
from mealie.pkgs import cache, safehttp
from mealie.repos.all_repositories import get_repositories
from mealie.repos.repository_factory import AllRepositories
from mealie.repos.repository_generic import RepositoryGeneric
from mealie.schema.household.household import HouseholdInDB, HouseholdRecipeUpdate
from mealie.schema.openai.general import OpenAIText
from mealie.schema.openai.recipe import OpenAIRecipe, OpenAIRecipeTextParse
from mealie.schema.openai.recipe_search import OpenAIRecipeSearchResponse
from mealie.schema.recipe.recipe import CreateRecipe, Recipe, RecipeSummary, create_recipe_slug
from mealie.schema.recipe.recipe_ai_search import RecipeAISearchResponse, RecipeAISearchResult
from mealie.schema.recipe.recipe_category import CategorySave, TagSave
from mealie.schema.recipe.recipe_ingredient import RecipeIngredient
from mealie.schema.recipe.recipe_notes import RecipeNote
from mealie.schema.recipe.recipe_settings import RecipeSettings
from mealie.schema.recipe.recipe_step import RecipeStep
from mealie.schema.recipe.recipe_timeline_events import RecipeTimelineEventCreate, TimelineEventType
from mealie.schema.recipe.recipe_tool import RecipeToolSave
from mealie.schema.recipe.request_helpers import RecipeDuplicate
from mealie.schema.user.user import PrivateUser, UserRatingCreate
from mealie.services._base_service import BaseService
from mealie.services.household_services.household_service import HouseholdService
from mealie.services.openai import OpenAILocalImage, OpenAIService
from mealie.services.recipe.recipe_data_service import RecipeDataService

from .template_service import TemplateService

RECIPE_CREATED_EVENT_SUBJECT = "recipe.recipe-created"
AUTO_IMAGE_SEARCH_URL = "https://api.openverse.org/v1/images/"
AUTO_IMAGE_MAX_CANDIDATES = 12
SOURCE_PAGE_MAX_BYTES = 1_500_000
SOURCE_IMAGE_META_KEYS = {
    "og:image",
    "og:image:url",
    "twitter:image",
    "twitter:image:src",
    "image",
}


def is_external_recipe_image(image: object) -> bool:
    return isinstance(image, str) and image.lower().startswith(("http://", "https://"))


def external_url_from_text(value: str | None) -> str | None:
    if not value:
        return None

    match = re.search(r"https?://[^\s<>'\")\]]+", value.strip())
    if not match:
        return None

    return match.group(0).rstrip(".,;:")


class RecipeServiceBase(BaseService):
    def __init__(self, repos: AllRepositories, user: PrivateUser, household: HouseholdInDB, translator: Translator):
        self.repos = repos
        self.user = user
        self.household = household

        if repos.group_id != user.group_id != household.group_id:
            raise Exception("group ids do not match")
        if repos.household_id != user.household_id != household.id:
            raise Exception("household ids do not match")

        self.group_recipes = get_repositories(repos.session, group_id=repos.group_id, household_id=None).recipes
        """Recipes repo without a Household filter"""

        self.translator = translator
        self.t = translator.t

        super().__init__()


class RecipeService(RecipeServiceBase):
    def _get_recipe(self, data: str | UUID, key: str | None = None) -> Recipe:
        recipe = self.group_recipes.get_one(data, key)
        if recipe is None:
            raise exceptions.NoEntryFound("Recipe not found.")
        return recipe

    def can_delete(self, recipe_slugs: list[str]) -> bool:
        if self.user.admin:
            return True

        # Deletion requires ownership; collaborative editing rules (can_update) do not apply
        model = self.group_recipes.model
        owned_count = self.group_recipes.session.scalar(
            sa.select(sa.func.count())
            .select_from(model)
            .where(
                model.slug.in_(recipe_slugs),
                model.group_id == self.user.group_id,
                model.user_id == self.user.id,
            )
        )
        return owned_count == len(recipe_slugs)

    def can_update(self, recipe_slugs: list[str]) -> bool:
        sql = dedent(
            """
            SELECT
                CASE
                    WHEN COUNT(*) = SUM(
                        CASE
                            -- User owns the recipe
                            WHEN r.user_id = :user_id THEN 1

                            -- Not owner: check if recipe is locked
                            WHEN COALESCE(rs.locked, TRUE) = TRUE THEN 0

                            -- Different household: check household policy
                            WHEN
                                u.household_id != :household_id
                                AND COALESCE(hp.lock_recipe_edits_from_other_households, TRUE) = TRUE
                            THEN 0

                            -- All other cases: can update
                            ELSE 1
                        END
                    ) THEN 1
                    ELSE 0
                END AS all_can_update
            FROM recipes r
            LEFT JOIN recipe_settings rs ON rs.recipe_id = r.id
            LEFT JOIN users u ON u.id = r.user_id
            LEFT JOIN households h ON h.id = u.household_id
            LEFT JOIN household_preferences hp ON hp.household_id = h.id
            WHERE r.slug IN :recipe_slugs AND r.group_id = :group_id;
            """
        )

        result = self.repos.session.execute(
            sa.text(sql).bindparams(sa.bindparam("recipe_slugs", expanding=True)),
            params={
                "user_id": self.repos.uuid_to_str(self.user.id),
                "household_id": self.repos.uuid_to_str(self.household.id),
                "group_id": self.repos.uuid_to_str(self.user.group_id),
                "recipe_slugs": recipe_slugs,
            },
        ).scalar()

        return bool(result)

    def can_lock_unlock(self, recipe: Recipe) -> bool:
        return recipe.user_id == self.user.id

    def check_assets(self, recipe: Recipe, original_slug: str) -> None:
        """Checks if the recipe slug has changed, and if so moves the assets to a new file with the new slug."""
        if original_slug != recipe.slug:
            current_dir = self.directories.RECIPE_DATA_DIR.joinpath(original_slug)

            try:
                copytree(current_dir, recipe.directory, dirs_exist_ok=True)
                self.logger.debug(f"Renaming Recipe Directory: {original_slug} -> {recipe.slug}")
            except FileNotFoundError:
                self.logger.error(f"Recipe Directory not Found: {original_slug}")

        if recipe.assets is None:
            recipe.assets = []

        all_asset_files = [x.file_name for x in recipe.assets]

        for file in recipe.asset_dir.iterdir():
            if file.is_dir():
                continue
            if file.name not in all_asset_files:
                file.unlink()

    def delete_assets(self, recipe: Recipe) -> None:
        recipe_dir = recipe.directory
        rmtree(recipe_dir, ignore_errors=True)
        self.logger.info(f"Recipe Directory Removed: {recipe.slug}")

    def _recipe_creation_factory(self, name: str, additional_attrs: dict | None = None) -> Recipe:
        """
        The main creation point for recipes. The factor method returns an instance of the
        Recipe Schema class with the appropriate defaults set. Recipes should not be created
        elsewhere to avoid conflicts.
        """
        additional_attrs = additional_attrs or {}
        additional_attrs["name"] = name
        additional_attrs["user_id"] = self.user.id
        additional_attrs["household_id"] = self.household.id
        additional_attrs["group_id"] = self.household.group_id

        for organizer_key in ("recipe_category", "tags", "tools"):
            for item in additional_attrs.get(organizer_key, []) or []:
                if isinstance(item, dict):
                    item["group_id"] = self.user.group_id

        if not additional_attrs.get("recipe_ingredient"):
            additional_attrs["recipe_ingredient"] = [
                RecipeIngredient(note=self.t("recipe.recipe-defaults.ingredient-note"))
            ]

        if not additional_attrs.get("recipe_instructions"):
            additional_attrs["recipe_instructions"] = [RecipeStep(text=self.t("recipe.recipe-defaults.step-text"))]

        return Recipe(**additional_attrs)

    def get_one(self, slug_or_id: str | UUID) -> Recipe:
        if isinstance(slug_or_id, str):
            try:
                slug_or_id = UUID(slug_or_id)
            except ValueError:
                pass

        if isinstance(slug_or_id, UUID):
            return self._get_recipe(slug_or_id, "id")

        else:
            return self._get_recipe(slug_or_id, "slug")

    def create_one(self, create_data: Recipe | CreateRecipe) -> Recipe:
        if create_data.name is None:
            create_data.name = "New Recipe"

        data: Recipe = self._recipe_creation_factory(name=create_data.name, additional_attrs=create_data.model_dump())

        if isinstance(create_data, CreateRecipe) or create_data.settings is None:
            if self.household.preferences is not None:
                data.settings = RecipeSettings(
                    public=self.household.preferences.recipe_public,
                    show_nutrition=self.household.preferences.recipe_show_nutrition,
                    show_assets=self.household.preferences.recipe_show_assets,
                    landscape_view=self.household.preferences.recipe_landscape_view,
                    disable_comments=self.household.preferences.recipe_disable_comments,
                )
            else:
                data.settings = RecipeSettings()

        rating_input = data.rating
        data.last_made = None
        new_recipe = self.repos.recipes.create(data)

        # convert rating into user rating
        if rating_input:
            self.repos.user_ratings.create(
                UserRatingCreate(
                    user_id=self.user.id,
                    recipe_id=new_recipe.id,
                    rating=rating_input,
                    is_favorite=False,
                )
            )

        # create first timeline entry
        timeline_event_data = RecipeTimelineEventCreate(
            user_id=new_recipe.user_id,
            recipe_id=new_recipe.id,
            subject=RECIPE_CREATED_EVENT_SUBJECT,
            event_type=TimelineEventType.system,
            timestamp=new_recipe.created_at or datetime.now(UTC),
        )

        self.repos.recipe_timeline_events.create(timeline_event_data)
        return new_recipe

    def _transform_user_id(self, user_id: str) -> str:
        query = self.repos.users.get_one(user_id)
        if query:
            return user_id
        else:
            # default to the current user
            return str(self.user.id)

    def _transform_category_or_tag(self, data: dict, repo: RepositoryGeneric) -> dict:
        slug = data.get("slug")
        if not slug:
            return data

        # if the item exists, return the actual data
        query = repo.get_one(slug, "slug")
        if query:
            return query.model_dump()

        # otherwise, create the item
        new_item = repo.create(data)
        return new_item.model_dump()

    def _process_recipe_data(self, key: str, data: list | dict | Any):
        if isinstance(data, list):
            return [self._process_recipe_data(key, item) for item in data]

        elif isinstance(data, str):
            # make sure the user is valid
            if key == "user_id":
                return self._transform_user_id(str(data))

            return data

        elif not isinstance(data, dict):
            return data

        # force group_id and household_id to match the group id of the current user
        data["group_id"] = str(self.user.group_id)
        data["household_id"] = str(self.user.household_id)

        # make sure categories and tags are valid
        if key == "recipe_category":
            return self._transform_category_or_tag(data, self.repos.categories)
        elif key == "tags":
            return self._transform_category_or_tag(data, self.repos.tags)

        # recursively process other objects
        for k, v in data.items():
            data[k] = self._process_recipe_data(k, v)

        return data

    def clean_recipe_dict(self, recipe: dict[str, Any]) -> dict[str, Any]:
        return self._process_recipe_data("recipe", recipe)

    def create_from_zip(self, archive: UploadFile, temp_path: Path) -> Recipe:
        """
        `create_from_zip` creates a recipe in the database from a zip file exported from Mealie. This is NOT
        a generic import from a zip file.
        """
        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(archive.file, buffer)

        recipe_dict: dict | None = None
        recipe_image: bytes | None = None

        with ZipFile(temp_path) as myzip:
            for file in myzip.namelist():
                if file.endswith(".json"):
                    with myzip.open(file) as myfile:
                        recipe_dict = json.loads(myfile.read())
                elif file.endswith(".webp"):
                    with myzip.open(file) as myfile:
                        recipe_image = myfile.read()

        if recipe_dict is None:
            raise exceptions.UnexpectedNone("No json data found in Zip")

        recipe = self.create_one(Recipe(**self.clean_recipe_dict(recipe_dict)))

        if recipe and recipe.id:
            data_service = RecipeDataService(recipe.id)

        if recipe_image:
            data_service.write_image(recipe_image, "webp")

        return recipe

    async def create_from_images(
        self,
        images: list[UploadFile],
        translate_language: str | None = None,
        include_ai_tips: bool = True,
        notes: str | None = None,
    ) -> Recipe:
        openai_recipe_service = OpenAIRecipeService(self.repos, self.user, self.household, self.translator)
        with get_temporary_path() as temp_path:
            local_images: list[Path] = []
            for image in images:
                safe_filename = Path(image.filename).name
                image_path = temp_path.joinpath(safe_filename)
                with image_path.open("wb") as buffer:
                    shutil.copyfileobj(image.file, buffer)
                local_images.append(image_path)

            recipe_data = await openai_recipe_service.build_recipe_from_images(
                local_images,
                translate_language=translate_language,
                include_ai_tips=include_ai_tips,
                notes=notes,
            )

            recipe = self.create_one(recipe_data)
            data_service = RecipeDataService(recipe.id)

            with open(local_images[0], "rb") as f:
                data_service.write_image(f.read(), "webp")
            return recipe

    async def create_from_text(
        self,
        text: str,
        translate_language: str | None = None,
        include_ai_tips: bool = True,
        auto_image: bool = True,
    ) -> Recipe:
        openai_recipe_service = OpenAIRecipeService(self.repos, self.user, self.household, self.translator)
        recipe_data = await openai_recipe_service.build_recipe_from_text(text, translate_language, include_ai_tips)
        recipe = self.create_one(recipe_data)
        if auto_image:
            await self.attach_best_effort_image(recipe, search_query=recipe.name)
        return recipe

    async def attach_best_effort_image(
        self,
        recipe: Recipe,
        image_url: str | None = None,
        search_query: str | None = None,
        search_queries: Sequence[str | None] | None = None,
        source_url: str | None = None,
    ) -> bool:
        """Attach a recipe image from a direct/source URL, or find a best-effort public image.

        Image import should never block recipe creation; failures are logged and ignored.
        """

        if not recipe or not recipe.id:
            return False

        data_service = RecipeDataService(recipe.id, self.logger)
        source_candidates = self._unique_image_urls([image_url])
        source_page_url = external_url_from_text(source_url) or external_url_from_text(recipe.source)
        if source_page_url:
            source_candidates = self._unique_image_urls(
                [*source_candidates, *(await self._find_source_page_image_urls(source_page_url))]
            )

        fallback_candidates: list[str] = []
        for candidate in source_candidates:
            fallback_candidates.append(candidate)
            try:
                image_downloaded = await data_service.scrape_image(candidate)
            except Exception:
                self.logger.exception("Failed to attach automatic recipe image from %s", candidate)
                continue

            if not image_downloaded:
                continue

            recipe.image = cache.cache_key.new_key()
            self.update_one(recipe.slug, recipe)
            return True

        search_candidates: list[str] = []
        query_values = list(search_queries or [search_query or recipe.name or recipe.slug])
        normalized_queries = self._normalized_image_search_queries(query_values)
        for query in normalized_queries:
            for candidate in await self._find_public_recipe_image_urls(query):
                if candidate not in search_candidates:
                    search_candidates.append(candidate)
                if len(search_candidates) >= AUTO_IMAGE_MAX_CANDIDATES:
                    break

            if len(search_candidates) >= AUTO_IMAGE_MAX_CANDIDATES:
                break

        if not search_candidates:
            for query in await self._build_ai_image_search_queries(recipe, normalized_queries):
                for candidate in await self._find_public_recipe_image_urls(query):
                    if candidate not in search_candidates:
                        search_candidates.append(candidate)
                    if len(search_candidates) >= AUTO_IMAGE_MAX_CANDIDATES:
                        break

                if len(search_candidates) >= AUTO_IMAGE_MAX_CANDIDATES:
                    break

        for candidate in search_candidates:
            fallback_candidates.append(candidate)
            try:
                image_downloaded = await data_service.scrape_image(candidate)
            except Exception:
                self.logger.exception("Failed to attach searched recipe image from %s", candidate)
                continue

            if not image_downloaded:
                continue

            recipe.image = cache.cache_key.new_key()
            self.update_one(recipe.slug, recipe)
            return True

        for candidate in fallback_candidates:
            if is_external_recipe_image(candidate):
                recipe.image = candidate
                self.update_one(recipe.slug, recipe)
                return True

        return False

    def _unique_image_urls(self, values: Sequence[str | None]) -> list[str]:
        urls: list[str] = []
        for value in values:
            candidate = (value or "").strip()
            if not candidate:
                continue
            if not candidate.lower().startswith(("http://", "https://")):
                continue
            if candidate.lower().split("?", 1)[0].endswith(".svg"):
                continue
            if candidate not in urls:
                urls.append(candidate)

        return urls

    def _normalized_image_search_queries(self, values: Sequence[str | None]) -> list[str]:
        queries: list[str] = []
        for value in values:
            text = re.sub(r"https?://\S+", " ", value or "")
            text = re.sub(r"\s+", " ", text).strip(" -|,.;:")
            if not text:
                continue

            if len(text) > 120:
                text = text[:120].rsplit(" ", 1)[0].strip(" -|,.;:")

            if text and text not in queries:
                queries.append(text)

        return queries

    async def _build_ai_image_search_queries(self, recipe: Recipe, base_queries: Sequence[str]) -> list[str]:
        try:
            openai_service = OpenAIService(self.repos)
            if not (openai_service.provider_settings and openai_service.provider_settings.ai_enabled):
                return []

            prompt = dedent(
                """
                You create short public image search queries for recipe photos.
                Return only concise English search phrases, one per line.
                Translate non-English recipe names when useful.
                Do not describe people, brands, websites, or copyrighted pages.
                Prefer generic dish/photo keywords that would find a similar finished food.
                """
            ).strip()
            ingredient_preview = [
                ingredient.display or ingredient.note or (ingredient.food.name if ingredient.food else "")
                for ingredient in (recipe.recipe_ingredient or [])[:8]
            ]
            message = dedent(
                f"""
                Recipe name: {recipe.name or recipe.slug}
                Existing search phrases: {json.dumps(list(base_queries), ensure_ascii=False)}
                Description: {recipe.description or ""}
                Categories: {", ".join(category.name for category in recipe.recipe_category or [] if category.name)}
                Tags: {", ".join(tag.name for tag in recipe.tags or [] if tag.name)}
                Main ingredients: {", ".join(item for item in ingredient_preview if item)}

                Return 3 to 5 image search phrases.
                """
            ).strip()
            response = await openai_service.get_response(prompt, message, response_schema=OpenAIText)
        except Exception:
            self.logger.exception("Failed to build AI image search queries")
            return []

        if not response or not response.text:
            return []

        raw_queries = [
            re.sub(r"^\s*[-*\d.)]+", "", part).strip()
            for part in re.split(r"[\n;,]+", response.text)
            if part.strip()
        ]
        return self._normalized_image_search_queries(raw_queries)[:5]

    async def _find_source_page_image_urls(self, source_url: str | None) -> list[str]:
        source_url = external_url_from_text(source_url)
        if not source_url:
            return []

        try:
            async with httpx.AsyncClient(
                transport=safehttp.AsyncSafeTransport(impersonate="chrome"),
                timeout=8.0,
                follow_redirects=True,
                headers={"User-Agent": "Mealie personal recipe image fetcher"},
            ) as client:
                async with client.stream("GET", source_url) as response:
                    response.raise_for_status()

                    content_type = response.headers.get("content-type", "").lower()
                    if "html" not in content_type and "text" not in content_type:
                        return []

                    chunks: list[bytes] = []
                    total_bytes = 0
                    async for chunk in response.aiter_bytes():
                        remaining = SOURCE_PAGE_MAX_BYTES - total_bytes
                        if remaining <= 0:
                            break

                        chunks.append(chunk[:remaining])
                        total_bytes += len(chunks[-1])
                        if total_bytes >= SOURCE_PAGE_MAX_BYTES:
                            break

                    html = b"".join(chunks).decode(response.encoding or "utf-8", errors="ignore")
        except httpx.HTTPStatusError as e:
            self.logger.warning("Source page did not allow automatic recipe image inspection: %s", e.response.url)
            return []
        except Exception:
            self.logger.exception("Failed to inspect source page for automatic recipe image: %s", source_url)
            return []

        return self._extract_image_urls_from_html(source_url, html)

    def _extract_image_urls_from_html(self, page_url: str, html: str) -> list[str]:
        candidates: list[str] = []

        for match in re.finditer(r"<meta\b[^>]*>", html, flags=re.IGNORECASE):
            attrs = self._html_attrs(match.group(0))
            key = (attrs.get("property") or attrs.get("name") or attrs.get("itemprop") or "").lower()
            if key in SOURCE_IMAGE_META_KEYS:
                self._add_page_image_candidate(candidates, page_url, attrs.get("content") or attrs.get("value"))
            if len(candidates) >= AUTO_IMAGE_MAX_CANDIDATES:
                return candidates[:AUTO_IMAGE_MAX_CANDIDATES]

        for match in re.finditer(
            r"<script\b[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        ):
            raw_json = match.group(1)
            raw_json = re.sub(r"^\s*<!--|-->\s*$", "", unescape(raw_json.strip()))
            try:
                self._collect_json_image_urls(candidates, page_url, json.loads(raw_json))
            except Exception:
                continue
            if len(candidates) >= AUTO_IMAGE_MAX_CANDIDATES:
                return candidates[:AUTO_IMAGE_MAX_CANDIDATES]

        if candidates:
            return candidates[:AUTO_IMAGE_MAX_CANDIDATES]

        # Last resort: try visible page images. This is intentionally after metadata/JSON-LD
        # because generic pages often include logos and navigation images before the recipe image.
        for match in re.finditer(r"<img\b[^>]*>", html, flags=re.IGNORECASE):
            attrs = self._html_attrs(match.group(0))
            self._add_page_image_candidate(
                candidates,
                page_url,
                attrs.get("src") or attrs.get("data-src") or attrs.get("data-lazy-src"),
            )
            if attrs.get("srcset"):
                for part in attrs["srcset"].split(","):
                    self._add_page_image_candidate(candidates, page_url, part.strip().split(" ", 1)[0])

            if len(candidates) >= AUTO_IMAGE_MAX_CANDIDATES:
                break

        return candidates[:AUTO_IMAGE_MAX_CANDIDATES]

    def _html_attrs(self, tag: str) -> dict[str, str]:
        return {
            name.lower(): unescape(value.strip())
            for name, _quote, value in re.findall(r"([\w:-]+)\s*=\s*([\"'])(.*?)\2", tag, flags=re.DOTALL)
        }

    def _collect_json_image_urls(
        self,
        candidates: list[str],
        page_url: str,
        node: object,
        *,
        allow_string: bool = False,
    ) -> None:
        if len(candidates) >= AUTO_IMAGE_MAX_CANDIDATES:
            return

        if isinstance(node, str):
            if allow_string:
                self._add_page_image_candidate(candidates, page_url, node)
            return

        if isinstance(node, list):
            for item in node:
                if len(candidates) >= AUTO_IMAGE_MAX_CANDIDATES:
                    break
                self._collect_json_image_urls(candidates, page_url, item, allow_string=allow_string)
            return

        if not isinstance(node, dict):
            return

        node_type = node.get("@type")
        node_types = [node_type] if isinstance(node_type, str) else node_type if isinstance(node_type, list) else []
        normalized_types = {str(item).lower() for item in node_types}

        for key in ("image", "thumbnailUrl"):
            if key in node:
                self._collect_json_image_urls(candidates, page_url, node[key], allow_string=True)

        if "imageobject" in normalized_types:
            self._collect_json_image_urls(
                candidates,
                page_url,
                node.get("url") or node.get("contentUrl"),
                allow_string=True,
            )

        for value in node.values():
            if len(candidates) >= AUTO_IMAGE_MAX_CANDIDATES:
                break
            if isinstance(value, dict | list):
                self._collect_json_image_urls(candidates, page_url, value)

    def _add_page_image_candidate(self, candidates: list[str], page_url: str, value: str | None) -> None:
        if len(candidates) >= AUTO_IMAGE_MAX_CANDIDATES:
            return

        candidate = unescape((value or "").strip())
        if not candidate or candidate.startswith(("data:", "blob:")):
            return

        candidate = urljoin(page_url, candidate)
        if not candidate.lower().startswith(("http://", "https://")):
            return
        if candidate.lower().split("?", 1)[0].endswith(".svg"):
            return
        if candidate not in candidates:
            candidates.append(candidate)

    async def _find_public_recipe_image_urls(self, query: str | None) -> list[str]:
        query = (query or "").strip()
        if not query:
            return []

        if " recipe" not in query.lower() and " food" not in query.lower():
            query = f"{query} recipe food"

        payload: dict = {}
        try:
            async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
                response = await client.get(
                    AUTO_IMAGE_SEARCH_URL,
                    params={
                        "q": query,
                        "page_size": 8,
                        "mature": "false",
                    },
                    headers={"User-Agent": "Mealie personal recipe image search"},
                )
                response.raise_for_status()
                payload = response.json()
        except Exception:
            self.logger.exception("Failed to search for automatic recipe image")

        urls: list[str] = []
        for result in payload.get("results", []):
            candidate = (result.get("thumbnail") or result.get("url") or "").strip()
            if not candidate.lower().startswith(("http://", "https://")):
                continue
            if candidate.lower().split("?")[0].endswith(".svg"):
                continue
            urls.append(candidate)

        if urls:
            return urls
        return await self._find_wikimedia_recipe_image_urls(query)

    async def _find_wikimedia_recipe_image_urls(self, query: str) -> list[str]:
        """Use Wikimedia Commons when the anonymous Openverse quota is exhausted."""

        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                response = None
                for attempt in range(3):
                    elapsed = time.monotonic() - getattr(self, "_wikimedia_last_request", 0.0)
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
                            "gsrlimit": 8,
                            "prop": "imageinfo",
                            "iiprop": "url",
                            "iiurlwidth": 1400,
                        },
                        headers={"User-Agent": "Mealie personal recipe image search"},
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
            self.logger.exception("Failed to search Wikimedia Commons for an automatic recipe image")
            return []

        urls: list[str] = []
        pages = payload.get("query", {}).get("pages", {})
        for page in pages.values():
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

    async def search_with_ai(self, query: str, limit: int) -> RecipeAISearchResponse:
        openai_recipe_service = OpenAIRecipeService(self.repos, self.user, self.household, self.translator)
        return await openai_recipe_service.search_recipes_with_ai(query, limit)

    def duplicate_one(self, old_slug_or_id: str | UUID, dup_data: RecipeDuplicate) -> Recipe:
        """Duplicates a recipe and returns the new recipe."""

        old_recipe = self.get_one(old_slug_or_id)
        new_recipe_data = old_recipe.model_dump(exclude={"id", "name", "slug", "image", "comments"}, round_trip=True)
        new_recipe = Recipe.model_validate(new_recipe_data)

        # Asset images in steps directly link to the original recipe, so we
        # need to update them to references to the assets we copy below
        def replace_recipe_step(step: RecipeStep) -> RecipeStep:
            new_id = uuid4()
            new_text = step.text.replace(str(old_recipe.id), str(new_recipe.id))
            new_step = step.model_copy(update={"id": new_id, "text": new_text})
            return new_step

        # Copy ingredients to make them independent of the original
        def copy_recipe_ingredient(ingredient: RecipeIngredient):
            new_reference_id = uuid4()
            new_ingredient = ingredient.model_copy(update={"reference_id": new_reference_id})
            return new_ingredient

        new_name = dup_data.name if dup_data.name else old_recipe.name or ""
        new_recipe.id = uuid4()
        new_recipe.slug = create_recipe_slug(new_name)
        new_recipe.image = (
            old_recipe.image
            if is_external_recipe_image(old_recipe.image)
            else cache.cache_key.new_key()
            if old_recipe.image
            else None
        )
        new_recipe.recipe_instructions = (
            None
            if old_recipe.recipe_instructions is None
            else list(map(replace_recipe_step, old_recipe.recipe_instructions))
        )
        new_recipe.recipe_ingredient = (
            None
            if old_recipe.recipe_ingredient is None
            else list(map(copy_recipe_ingredient, old_recipe.recipe_ingredient))
        )
        new_recipe.last_made = None

        new_recipe = self._recipe_creation_factory(new_name, additional_attrs=new_recipe.model_dump())

        new_recipe = self.repos.recipes.create(new_recipe)

        # Copy all assets (including images) to the new recipe directory
        # This assures that replaced links in recipe steps continue to work when the old recipe is deleted
        try:
            new_service = RecipeDataService(new_recipe.id)
            old_service = RecipeDataService(old_recipe.id)
            copytree(
                old_service.dir_data,
                new_service.dir_data,
                dirs_exist_ok=True,
            )
        except Exception as e:
            self.logger.error(f"Failed to copy assets from {old_recipe.slug} to {new_recipe.slug}: {e}")

        return new_recipe

    def has_recursive_recipe_link(self, recipe: Recipe, path: set[str] | None = None):
        """Recursively checks if a recipe links to itself through its ingredients."""
        if path is None:
            path = set()

        recipe_id = str(getattr(recipe, "id", None))

        # Check if this recipe is already in the current path (cycle detected)
        if recipe_id in path:
            return True

        # Add to the current path
        path.add(recipe_id)

        try:
            ingredients = getattr(recipe, "recipe_ingredient", [])
            for ing in ingredients:
                try:
                    sub_recipe = self.get_one(ing.referenced_recipe.id)
                except (AttributeError, exceptions.NoEntryFound):
                    continue

                # Recursively check - path is modified in place and cleaned up via backtracking
                if self.has_recursive_recipe_link(sub_recipe, path):
                    return True
        finally:
            # Backtrack: remove this recipe from the path when done exploring this branch
            path.discard(recipe_id)

        return False

    def _pre_update_check(self, slug_or_id: str | UUID, new_data: Recipe) -> Recipe:
        """
        gets the recipe from the database and performs a check to see if the user can update the recipe.
        If the user can't update the recipe, an exception is raised.

        Checks:
            - That the recipe exists
            - That the user can update the recipe (recipe is not locked or the user is the owner)
            - _if_ the user is locking the recipe, that they can lock the recipe (user is the owner)

        Args:
            slug_or_id (str | UUID): recipe slug or id
            new_data (Recipe): the new recipe data

        Raises:
            exceptions.PermissionDenied (403)
        """

        recipe = self.get_one(slug_or_id)

        if recipe is None or recipe.settings is None:
            raise exceptions.NoEntryFound("Recipe not found.")

        if not self.can_update([recipe.slug]):
            raise exceptions.PermissionDenied("You do not have permission to edit this recipe.")

        setting_lock = new_data.settings is not None and recipe.settings.locked != new_data.settings.locked
        if setting_lock and not self.can_lock_unlock(recipe):
            raise exceptions.PermissionDenied("You do not have permission to lock/unlock this recipe.")

        if self.has_recursive_recipe_link(new_data):
            raise exceptions.RecursiveRecipe("Recursive recipe link detected. Update aborted.")

        return recipe

    def _remove_non_existent_ingredient_references(self, update_data: Recipe) -> Recipe:
        """Removes the references of ingredients from steps that no longer exist."""

        current_ingredient_reference_ids = set()  # set of current ingredient(s) reference id's
        for ingredient in update_data.recipe_ingredient:
            current_ingredient_reference_ids.add(ingredient.reference_id)

        recipe_instructions = update_data.recipe_instructions
        if recipe_instructions is not None:
            for instruction in recipe_instructions:
                instruction.ingredient_references = [
                    ref
                    for ref in instruction.ingredient_references
                    if ref.reference_id in current_ingredient_reference_ids
                ]

        return update_data

    def _resolve_ingredient_sub_recipes(self, update_data: Recipe) -> Recipe:
        """Resolve all referenced_recipe slugs to IDs within the current group."""
        if not update_data.recipe_ingredient:
            return update_data

        for ingredient in update_data.recipe_ingredient:
            if ingredient.referenced_recipe:
                ref = ingredient.referenced_recipe
                # If no id, resolve by slug
                if not ref.id and ref.slug:
                    recipe = self.group_recipes.get_by_slug(self.user.group_id, ref.slug)
                    if not recipe:
                        raise exceptions.NoEntryFound(f"Referenced recipe '{ref.slug}' not found in this group")
                    ref.id = recipe.id
                # If id is provided, verify it belongs to this group
                elif ref.id:
                    recipe = self.group_recipes.get_one(ref.id, key="id")
                    if not recipe:
                        raise exceptions.NoEntryFound(f"Referenced recipe with id '{ref.id}' not found in this group")

        return update_data

    def update_one(self, slug_or_id: str | UUID, update_data: Recipe) -> Recipe:
        recipe = self._pre_update_check(slug_or_id, update_data)

        update_data = self._remove_non_existent_ingredient_references(update_data)
        update_data = self._resolve_ingredient_sub_recipes(update_data)

        new_data = self.group_recipes.update(recipe.slug, update_data)
        self.check_assets(new_data, recipe.slug)
        return new_data

    def update_recipe_image(self, slug: str, image: bytes, extension: str):
        recipe = self.get_one(slug)
        if not self.can_update([recipe.slug]):
            raise exceptions.PermissionDenied("You do not have permission to edit this recipe.")

        data_service = RecipeDataService(recipe.id)
        data_service.write_image(image, extension)

        return self.group_recipes.update_image(slug, extension)

    def delete_recipe_image(self, slug: str) -> None:
        recipe = self.get_one(slug)
        if not self.can_update([recipe.slug]):
            raise exceptions.PermissionDenied("You do not have permission to edit this recipe.")

        data_service = RecipeDataService(recipe.id)
        data_service.delete_image()

        self.group_recipes.delete_image(slug)
        return None

    def patch_one(self, slug_or_id: str | UUID, patch_data: Recipe) -> Recipe:
        recipe: Recipe = self._pre_update_check(slug_or_id, patch_data)

        new_data = self.group_recipes.patch(recipe.slug, patch_data.model_dump(exclude_unset=True))

        self.check_assets(new_data, recipe.slug)
        return new_data

    def update_last_made(self, slug_or_id: str | UUID, timestamp: datetime) -> Recipe:
        # we bypass the pre update check since any user can update a recipe's last made date, even if it's locked,
        # or if the user belongs to a different household

        household_service = HouseholdService(self.user.group_id, self.user.household_id, self.repos)
        household_service.set_household_recipe(slug_or_id, HouseholdRecipeUpdate(last_made=timestamp))

        return self.get_one(slug_or_id)

    def delete_one(self, slug_or_id: str | UUID) -> Recipe:
        recipe = self.get_one(slug_or_id)
        resp = self.delete_many([recipe.slug])
        return resp[0]

    def delete_many(self, recipe_slugs: list[str]) -> list[Recipe]:
        if not self.can_delete(recipe_slugs):
            if len(recipe_slugs) == 1:
                msg = "You do not have permission to delete this recipe."
            else:
                msg = "You do not have permission to delete all of these recipes."
            raise exceptions.PermissionDenied(msg)

        data = self.group_recipes.delete_many(recipe_slugs)
        for r in data:
            try:
                self.delete_assets(r)
            except Exception:
                self.logger.exception(f"Failed to delete recipe assets for {r.slug}")

        return data

    # =================================================================
    # Recipe Template Methods

    def render_template(self, recipe: Recipe, temp_dir: Path, template: str) -> Path:
        t_service = TemplateService(temp_dir)
        return t_service.render(recipe, template)


class OpenAIRecipeService(RecipeServiceBase):
    _SEARCH_TOKEN_RE = re.compile(r"[\w\u0590-\u05ff]+", re.UNICODE)
    _MIN_AI_SEARCH_CANDIDATES = 80
    _MAX_AI_SEARCH_CANDIDATES = 400
    _AI_SEARCH_INDEX_TTL = timedelta(hours=24)
    _AI_COLLECTION_BATCH_SIZE = 60

    @staticmethod
    def _compact_text(value: Any, max_length: int = 240) -> str:
        text = " ".join(str(value or "").split())
        if len(text) <= max_length:
            return text
        return text[: max_length - 1].rstrip() + "..."

    def _ingredient_catalog_text(self, ingredient: RecipeIngredientModel) -> str:
        if ingredient.original_text:
            text = ingredient.original_text
        elif ingredient.note:
            text = ingredient.note
        else:
            parts: list[str] = []
            if ingredient.quantity:
                quantity = float(ingredient.quantity)
                parts.append(str(int(quantity)) if quantity.is_integer() else str(ingredient.quantity))
            if ingredient.unit:
                parts.append(ingredient.unit.name or ingredient.unit.abbreviation or "")
            if ingredient.food:
                parts.append(ingredient.food.name or ingredient.food.plural_name or "")
            text = " ".join(part for part in parts if part)

        if ingredient.title:
            text = f"{ingredient.title}: {text}"

        if ingredient.recommended_variety:
            text = f"{text} recommended type: {ingredient.recommended_variety}"

        return self._compact_text(text, 180)

    @classmethod
    def _search_tokens(cls, text: str) -> list[str]:
        return [token for token in cls._SEARCH_TOKEN_RE.findall((text or "").lower()) if len(token) > 1]

    @classmethod
    def _search_vector(cls, text: str) -> dict[str, float]:
        counts = Counter(cls._search_tokens(text))
        if not counts:
            return {}

        weights = {token: 1 + math.log(count) for token, count in counts.most_common(500)}
        norm = math.sqrt(sum(weight * weight for weight in weights.values()))
        if not norm:
            return {}

        return {token: round(weight / norm, 6) for token, weight in weights.items()}

    @staticmethod
    def _catalog_text(catalog: dict[str, Any]) -> str:
        parts: list[str] = []
        for key in (
            "name",
            "description",
            "source",
            "created_by",
            "original_url",
            "yield",
            "total_time",
        ):
            value = catalog.get(key)
            if value:
                parts.append(str(value))

        for key in ("categories", "tags", "tools", "ingredients", "instructions", "notes"):
            values = catalog.get(key) or []
            if values:
                parts.extend(str(value) for value in values if value)

        return " ".join(parts)

    def _recipe_catalog_entry(self, recipe: Any, large_catalog: bool) -> dict[str, Any]:
        ingredient_limit = 10 if large_catalog else 24
        instruction_limit = 2 if large_catalog else 6
        note_limit = 1 if large_catalog else 3

        return {
            "slug": recipe.slug,
            "name": self._compact_text(recipe.name, 180),
            "description": self._compact_text(recipe.description, 260 if not large_catalog else 140),
            "source": self._compact_text(recipe.source, 160),
            "created_by": self._compact_text(recipe.created_by, 160),
            "original_url": self._compact_text(recipe.org_url, 180),
            "categories": [category.name for category in recipe.recipe_category if category.name],
            "tags": [tag.name for tag in recipe.tags if tag.name],
            "tools": [tool.name for tool in recipe.tools if tool.name],
            "yield": self._compact_text(recipe.recipe_yield, 80),
            "total_time": self._compact_text(recipe.total_time, 60),
            "ingredients": [
                self._ingredient_catalog_text(ingredient) for ingredient in recipe.recipe_ingredient[:ingredient_limit]
            ],
            "instructions": [
                self._compact_text(
                    f"{instruction.title or ''} {instruction.text or instruction.summary or ''}",
                    220,
                )
                for instruction in recipe.recipe_instructions[:instruction_limit]
                if instruction.text or instruction.summary or instruction.title
            ],
            "notes": [
                self._compact_text(f"{note.title or ''} {note.text or ''}", 180)
                for note in recipe.notes[:note_limit]
                if note.title or note.text
            ],
        }

    def _recipe_index_payload(self, recipe: Any, large_catalog: bool) -> dict[str, str]:
        catalog = self._recipe_catalog_entry(recipe, large_catalog)
        catalog_json = json.dumps(catalog, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        search_text = self._catalog_text(catalog)
        search_vector = json.dumps(self._search_vector(search_text), ensure_ascii=False, separators=(",", ":"))
        content_hash = hashlib.sha256(catalog_json.encode("utf-8")).hexdigest()

        return {
            "catalog_json": catalog_json,
            "search_text": search_text,
            "search_vector": search_vector,
            "content_hash": content_hash,
        }

    def _ensure_ai_recipe_search_index(self) -> list[RecipeAISearchIndex]:
        model = self.group_recipes.model
        session = self.group_recipes.session
        recipe_meta_rows = session.execute(
            sa.select(model.id, model.slug, model.name, model.update_at)
            .filter(model.group_id == self.user.group_id)
            .filter(model.household_id.is_not(None))
            .order_by(model.name.asc())
        ).all()

        index_rows = session.execute(
            sa.select(RecipeAISearchIndex).filter(RecipeAISearchIndex.group_id == self.user.group_id)
        ).scalars().all()

        if not recipe_meta_rows:
            if index_rows:
                session.execute(
                    sa.delete(RecipeAISearchIndex).where(RecipeAISearchIndex.group_id == self.user.group_id)
                )
                session.commit()
            return []

        recipe_meta_by_id = {
            row.id: {
                "slug": row.slug,
                "name": row.name,
                "updated_at": row.update_at,
            }
            for row in recipe_meta_rows
        }
        current_recipe_ids = set(recipe_meta_by_id)
        index_by_recipe_id = {row.recipe_id: row for row in index_rows}

        changed = False
        for index_row in index_rows:
            if index_row.recipe_id not in current_recipe_ids:
                session.delete(index_row)
                changed = True

        stale_recipe_ids = []
        now = datetime.now(UTC)
        for recipe_id, meta in recipe_meta_by_id.items():
            index_row = index_by_recipe_id.get(recipe_id)
            if not index_row:
                stale_recipe_ids.append(recipe_id)
                continue

            index_expires_at = index_row.update_at + self._AI_SEARCH_INDEX_TTL if index_row.update_at else None
            if (
                index_row.recipe_slug != meta["slug"]
                or index_row.recipe_name != meta["name"]
                or index_row.recipe_updated_at != meta["updated_at"]
                or not index_expires_at
                or index_expires_at <= now
                or not index_row.catalog_json
                or not index_row.search_vector
            ):
                stale_recipe_ids.append(recipe_id)

        if stale_recipe_ids:
            large_catalog = len(recipe_meta_rows) > 100
            stale_recipes = session.execute(
                sa.select(model)
                .filter(model.id.in_(stale_recipe_ids))
                .options(
                    *RecipeSummary.loader_options(),
                    selectinload(model.recipe_ingredient).joinedload(RecipeIngredientModel.food),
                    selectinload(model.recipe_ingredient).joinedload(RecipeIngredientModel.unit),
                    selectinload(model.recipe_instructions),
                    selectinload(model.notes),
                )
                .order_by(model.name.asc())
            ).scalars().unique().all()

            for recipe in stale_recipes:
                payload = self._recipe_index_payload(recipe, large_catalog)
                index_row = index_by_recipe_id.get(recipe.id)
                if not index_row:
                    index_row = RecipeAISearchIndex(recipe_id=recipe.id, group_id=recipe.group_id)
                    session.add(index_row)

                index_row.recipe_slug = recipe.slug or ""
                index_row.recipe_name = recipe.name
                index_row.recipe_updated_at = recipe.update_at
                index_row.content_hash = payload["content_hash"]
                index_row.catalog_json = payload["catalog_json"]
                index_row.search_text = payload["search_text"]
                index_row.search_vector = payload["search_vector"]
                changed = True

        if changed:
            session.commit()

        return session.execute(
            sa.select(RecipeAISearchIndex)
            .filter(RecipeAISearchIndex.group_id == self.user.group_id)
            .order_by(RecipeAISearchIndex.recipe_name.asc())
        ).scalars().all()

    def _score_ai_search_index(
        self,
        query: str,
        query_vector: dict[str, float],
        index_row: RecipeAISearchIndex,
    ) -> float:
        try:
            recipe_vector = json.loads(index_row.search_vector or "{}")
        except ValueError:
            recipe_vector = {}

        score = sum(weight * recipe_vector.get(token, 0) for token, weight in query_vector.items())
        if not query_vector:
            return score

        query_tokens = set(query_vector)
        matched_tokens = sum(1 for token in query_tokens if token in recipe_vector)
        score += (matched_tokens / len(query_tokens)) * 0.75

        search_text = (index_row.search_text or "").lower()
        query_text = query.lower()
        if len(query_text) >= 3 and query_text in search_text:
            score += 1.5

        recipe_name = (index_row.recipe_name or "").lower()
        if any(token in recipe_name for token in query_tokens):
            score += 0.5

        return score

    def _build_ai_recipe_catalog(self, query: str, limit: int) -> tuple[int, list[dict[str, Any]], set[str]]:
        index_rows = self._ensure_ai_recipe_search_index()
        if not index_rows:
            return 0, [], set()

        candidate_limit = min(
            len(index_rows),
            max(self._MIN_AI_SEARCH_CANDIDATES, min(self._MAX_AI_SEARCH_CANDIDATES, limit * 8)),
        )
        query_vector = self._search_vector(query)
        scored_rows = [
            (self._score_ai_search_index(query, query_vector, index_row), index_row) for index_row in index_rows
        ]
        scored_rows.sort(key=lambda item: (-item[0], item[1].recipe_name or ""))

        candidates = [index_row for _, index_row in scored_rows[:candidate_limit]]
        catalog: list[dict[str, Any]] = []
        candidate_slugs: set[str] = set()

        for index_row in candidates:
            try:
                catalog_item = json.loads(index_row.catalog_json)
            except ValueError:
                continue

            if slug := catalog_item.get("slug"):
                candidate_slugs.add(slug)
                catalog.append(catalog_item)

        return len(index_rows), catalog, candidate_slugs

    def _load_ai_search_result_recipes(self, slugs: set[str]) -> dict[str, Any]:
        if not slugs:
            return {}

        model = self.group_recipes.model
        recipes = self.group_recipes.session.execute(
            sa.select(model)
            .filter(model.group_id == self.user.group_id)
            .filter(model.slug.in_(slugs))
            .options(
                *RecipeSummary.loader_options(),
            )
        ).scalars().unique().all()

        return {recipe.slug: recipe for recipe in recipes if recipe.slug}

    async def search_recipes_with_ai(self, query: str, limit: int) -> RecipeAISearchResponse:
        openai_service = OpenAIService(self.repos)
        if not (openai_service.provider_settings and openai_service.provider_settings.ai_enabled):
            raise ValueError("OpenAI services are not available")

        query = query.strip()
        if not query:
            raise ValueError("Search query cannot be empty")

        recipe_count, catalog, candidate_slugs = self._build_ai_recipe_catalog(query, limit)
        if not catalog:
            return RecipeAISearchResponse(query=query, items=[], recipe_count=recipe_count)

        prompt = openai_service.get_prompt("recipes.search-recipes")
        message = dedent(
            f"""
            User request:
            {query}

            Return at most {limit} recipes.

            The catalog below is a prefiltered shortlist from {recipe_count} indexed recipes.
            Choose only from this shortlist.

            Recipe shortlist JSON:
            {json.dumps(catalog, ensure_ascii=False)}
            """
        ).strip()

        try:
            response = await openai_service.get_response(
                prompt,
                message,
                response_schema=OpenAIRecipeSearchResponse,
            )
        except Exception as e:
            raise Exception("Failed to call OpenAI services") from e

        if not response:
            return RecipeAISearchResponse(query=query, items=[], recipe_count=recipe_count)

        recipe_by_slug = self._load_ai_search_result_recipes(candidate_slugs)
        seen_slugs: set[str] = set()
        items: list[RecipeAISearchResult] = []
        for result in response.results:
            if result.slug in seen_slugs:
                continue

            if result.slug not in candidate_slugs:
                continue

            recipe = recipe_by_slug.get(result.slug)
            if not recipe:
                continue

            seen_slugs.add(result.slug)
            items.append(
                RecipeAISearchResult(
                    recipe=RecipeSummary.model_validate(recipe),
                    reason=result.reason,
                    score=result.score,
                )
            )

            if len(items) >= limit:
                break

        return RecipeAISearchResponse(query=query, items=items, recipe_count=recipe_count)

    async def select_recipe_slugs_for_ai_collection(self, query: str) -> list[str]:
        """Select every matching recipe in bounded AI batches for generated collections."""

        openai_service = OpenAIService(self.repos)
        if not (openai_service.provider_settings and openai_service.provider_settings.ai_enabled):
            raise ValueError("OpenAI services are not available")

        query = query.strip()
        if not query:
            raise ValueError("Collection query cannot be empty")

        index_rows = self._ensure_ai_recipe_search_index()
        query_vector = self._search_vector(query)
        scored_rows = [
            (self._score_ai_search_index(query, query_vector, index_row), index_row) for index_row in index_rows
        ]
        scored_rows.sort(key=lambda item: (-item[0], item[1].recipe_name or ""))

        prompt = (
            f"{openai_service.get_prompt('recipes.search-recipes')}\n\n"
            "This request builds a cookbook. Include every recipe in each supplied batch that clearly matches, "
            "rather than returning only a representative variety."
        )
        selected: list[str] = []
        seen: set[str] = set()
        for batch_number, offset in enumerate(range(0, len(scored_rows), self._AI_COLLECTION_BATCH_SIZE), start=1):
            batch_rows = [row for _, row in scored_rows[offset : offset + self._AI_COLLECTION_BATCH_SIZE]]
            catalog: list[dict[str, Any]] = []
            valid_slugs: set[str] = set()
            for index_row in batch_rows:
                try:
                    item = json.loads(index_row.catalog_json)
                except ValueError:
                    continue
                if slug := item.get("slug"):
                    valid_slugs.add(slug)
                    catalog.append(item)

            if not catalog:
                continue

            message = dedent(
                f"""
                Cookbook definition:
                {query}

                Batch {batch_number} of {math.ceil(len(scored_rows) / self._AI_COLLECTION_BATCH_SIZE)}.
                Return every recipe in this batch that clearly belongs in the cookbook.

                Recipe batch JSON:
                {json.dumps(catalog, ensure_ascii=False)}
                """
            ).strip()
            response = await openai_service.get_response(
                prompt,
                message,
                response_schema=OpenAIRecipeSearchResponse,
            )
            if not response:
                raise RuntimeError(f"AI returned an empty response for cookbook batch {batch_number}")

            for result in response.results:
                if result.slug in valid_slugs and result.slug not in seen:
                    seen.add(result.slug)
                    selected.append(result.slug)

        return selected

    def _clean_organizer_names(self, names: list[str], max_items: int = 10) -> list[str]:
        cleaned_names: list[str] = []
        seen_slugs: set[str] = set()

        for name in names:
            cleaned_name = " ".join(str(name).split()).strip()
            slug = slugify(cleaned_name)
            if not cleaned_name or not slug or slug in seen_slugs:
                continue

            seen_slugs.add(slug)
            cleaned_names.append(cleaned_name)

            if len(cleaned_names) >= max_items:
                break

        return cleaned_names

    def _get_or_create_categories(self, names: list[str]):
        categories = []
        for name in self._clean_organizer_names(names):
            slug = slugify(name)
            if db_category := self.repos.categories.get_one(slug, "slug"):
                categories.append(db_category)
                continue

            categories.append(self.repos.categories.create(CategorySave(name=name, group_id=self.user.group_id)))

        return categories

    def _get_or_create_tags(self, names: list[str]):
        tags = []
        for name in self._clean_organizer_names(names):
            slug = slugify(name)
            if db_tag := self.repos.tags.get_one(slug, "slug"):
                tags.append(db_tag)
                continue

            tags.append(self.repos.tags.create(TagSave(name=name, group_id=self.user.group_id)))

        return tags

    def _get_or_create_tools(self, names: list[str]):
        tools = []
        for name in self._clean_organizer_names(names):
            slug = slugify(name)
            if db_tool := self.repos.tools.get_one(slug, "slug"):
                tools.append(db_tool)
                continue

            tools.append(
                self.repos.tools.create(
                    RecipeToolSave(name=name, group_id=self.user.group_id, households_with_tool=[]),
                ),
            )

        return tools

    def _convert_recipe(self, openai_recipe: OpenAIRecipe) -> Recipe:
        return Recipe(
            user_id=self.user.id,
            group_id=self.user.group_id,
            household_id=self.household.id,
            name=openai_recipe.name,
            slug=create_recipe_slug(openai_recipe.name),
            description=openai_recipe.description,
            source=openai_recipe.source,
            created_by=openai_recipe.created_by,
            recipe_yield=openai_recipe.recipe_yield,
            total_time=openai_recipe.total_time,
            prep_time=openai_recipe.prep_time,
            perform_time=openai_recipe.perform_time,
            recipe_ingredient=[
                RecipeIngredient(
                    title=ingredient.title,
                    note=ingredient.text,
                    recommended_variety=ingredient.recommended_variety,
                )
                for ingredient in openai_recipe.ingredients
                if ingredient.text
            ],
            recipe_instructions=[
                RecipeStep(title=instruction.title, text=instruction.text)
                for instruction in openai_recipe.instructions
                if instruction.text
            ],
            recipe_category=self._get_or_create_categories(openai_recipe.categories),
            tags=self._get_or_create_tags(openai_recipe.tags),
            tools=self._get_or_create_tools(openai_recipe.tools),
            notes=[RecipeNote(title=note.title or "", text=note.text) for note in openai_recipe.notes if note.text],
        )

    @staticmethod
    def _has_minimum_recipe_data(openai_recipe: OpenAIRecipe) -> bool:
        has_name = bool(openai_recipe.name and openai_recipe.name.strip())
        has_ingredients = any(ingredient.text.strip() for ingredient in openai_recipe.ingredients)
        has_instructions = any(instruction.text.strip() for instruction in openai_recipe.instructions)
        return has_name and has_ingredients and has_instructions

    async def build_recipe_from_images(
        self,
        images: list[Path],
        translate_language: str | None,
        include_ai_tips: bool = True,
        notes: str | None = None,
    ) -> Recipe:
        openai_service = OpenAIService(self.repos)
        if not (openai_service.provider_settings and openai_service.provider_settings.image_provider_enabled):
            raise ValueError("OpenAI image services are not available")

        prompt = openai_service.get_prompt("recipes.parse-recipe-image")

        openai_images = [OpenAILocalImage(filename=os.path.basename(image), path=image) for image in images]
        message = (
            f"Please extract the recipe from the {'images' if len(openai_images) > 1 else 'image'} provided."
            "There should be exactly one recipe."
        )

        if translate_language:
            message += f" Please translate the recipe to {translate_language}."
        if include_ai_tips:
            message += " Add concise AI cooking tips and practical recommended ingredient varieties when useful."
        if notes and notes.strip():
            message += (
                " The user supplied the following corrections or context. Treat explicit corrections as authoritative "
                f"when they conflict with the image: {notes.strip()}"
            )

        try:
            response = await openai_service.get_response(
                prompt,
                message,
                response_schema=OpenAIRecipe,
                attachments=openai_images,
            )
            if not response:
                raise ValueError("Received empty response from OpenAI")

        except Exception as e:
            raise Exception("Failed to call OpenAI services") from e

        try:
            recipe = self._convert_recipe(response)
        except Exception as e:
            raise ValueError("Unable to parse recipe from image") from e

        return recipe

    async def build_recipe_from_text(
        self,
        text: str,
        translate_language: str | None = None,
        include_ai_tips: bool = True,
    ) -> Recipe:
        openai_service = OpenAIService(self.repos)
        if not (openai_service.provider_settings and openai_service.provider_settings.ai_enabled):
            raise ValueError("OpenAI services are not available")

        prompt = openai_service.get_prompt("recipes.parse-recipe-text")
        message = "Please analyze the pasted text below and create a recipe only if it contains usable recipe data."

        if translate_language:
            message += f" Please translate the recipe to {translate_language}."
        if include_ai_tips:
            message += (
                " The user wants AI tips: add concise practical cooking notes and recommended ingredient varieties "
                "when they materially help the recipe."
            )

        message += f"\n\nPasted recipe text:\n{text.strip()}"

        try:
            response = await openai_service.get_response(
                prompt,
                message,
                response_schema=OpenAIRecipeTextParse,
            )
            if not response:
                raise ValueError("Received empty response from OpenAI")
            if not response.is_recipe or not response.recipe:
                raise exceptions.NotARecipe(response.reason or "The pasted text does not look like a recipe")
            openai_recipe = response.recipe
            if not self._has_minimum_recipe_data(openai_recipe):
                raise exceptions.NotARecipe(
                    "The pasted text does not contain enough recipe data. "
                    "Include a name, ingredients, and instructions."
                )

        except Exception as e:
            if isinstance(e, exceptions.NotARecipe):
                raise
            raise Exception("Failed to call OpenAI services") from e

        try:
            recipe = self._convert_recipe(openai_recipe)
        except Exception as e:
            raise ValueError("Unable to parse recipe from text") from e

        return recipe
