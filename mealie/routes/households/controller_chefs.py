import json
import re
import shutil
from urllib.parse import urlsplit, urlunsplit

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from pydantic import UUID4
from sqlalchemy.orm import selectinload
from starlette.responses import FileResponse

from mealie.db.models.household.chef import Chef
from mealie.db.models.household.restaurant import Restaurant
from mealie.db.models.household.uploaded_book import UploadedBook
from mealie.pkgs import safehttp
from mealie.routes._base import controller
from mealie.routes._base.base_controllers import BaseUserController
from mealie.schema.household.chef import (
    ChefAIRequest,
    ChefBrowserPageRequest,
    ChefCreate,
    ChefImageURLRequest,
    ChefOut,
    ChefRelatedBook,
    ChefRelatedRestaurant,
    ChefUpdate,
)
from mealie.schema.openai.chef import OpenAIChef
from mealie.schema.response.responses import ErrorResponse
from mealie.services.entity_image_service import EntityImageService
from mealie.services.openai import OpenAIService

router = APIRouter(prefix="/households/chefs", tags=["Households: Chefs"])

SPACE_RE = re.compile(r"\s+")
HTML_SCRIPT_STYLE_RE = re.compile(r"<(script|style).*?</\1>", re.IGNORECASE | re.DOTALL)
HTML_TAG_RE = re.compile(r"<[^>]+>")
MAX_PAGE_BYTES = 2 * 1024 * 1024
MAX_PAGE_TEXT = 250000
VALID_RANKS = {"world_class", "excellent", "good", "medium", "emerging"}
WIKIPEDIA_API_TEMPLATE = "https://{language}.wikipedia.org/w/api.php"


def normalize_terms(values: list[str], *, limit: int = 80, item_limit: int = 500) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        item = SPACE_RE.sub(" ", str(value).strip())[:item_limit]
        key = item.casefold()
        if item and key not in seen:
            seen.add(key)
            normalized.append(item)
    return normalized[:limit]


def normalize_optional_url(value: str | None) -> str | None:
    raw = (value or "").strip()
    if not raw:
        return None
    parts = urlsplit(raw)
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse.respond("A valid HTTP or HTTPS address is required"),
        )
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, ""))


def clean_html_text(value: str) -> str:
    value = HTML_SCRIPT_STYLE_RE.sub(" ", value)
    value = re.sub(r"</(p|div|h[1-6]|li|br|nav|section)>", "\n", value, flags=re.IGNORECASE)
    value = HTML_TAG_RE.sub(" ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return SPACE_RE.sub(" ", value).strip()[:MAX_PAGE_TEXT]


@controller(router)
class ChefsController(BaseUserController):
    @property
    def image_service(self) -> EntityImageService:
        return EntityImageService(self.folders.DATA_DIR)

    def _image_path(self, chef: Chef):
        return self.image_service.image_path("chefs", chef.group_id, chef.id)

    def _ai_enabled(self) -> bool:
        settings = self.session.execute(
            sa.text("SELECT id, default_provider_id FROM ai_provider_settings WHERE group_id = :group_id"),
            {"group_id": self.repos.uuid_to_str(self.group_id)},
        ).mappings().one_or_none()
        if not settings or not settings["default_provider_id"]:
            return False
        return bool(
            self.session.execute(
                sa.text("SELECT 1 FROM ai_providers WHERE id = :provider_id AND settings_id = :settings_id LIMIT 1"),
                {"provider_id": settings["default_provider_id"], "settings_id": settings["id"]},
            ).scalar()
        )

    def _to_out(self, chef: Chef) -> ChefOut:
        image_path = self._image_path(chef)
        try:
            image_stat = image_path.stat()
        except FileNotFoundError:
            image_stat = None
        return ChefOut(
            id=chef.id,
            group_id=chef.group_id,
            household_id=chef.household_id,
            user_id=chef.user_id,
            name=chef.name,
            aliases=json.loads(chef.aliases_json or "[]"),
            rank=chef.rank,
            country=chef.country,
            cuisines=json.loads(chef.cuisines_json or "[]"),
            specialties=json.loads(chef.specialties_json or "[]"),
            biography=chef.biography,
            career_summary=chef.career_summary,
            awards=json.loads(chef.awards_json or "[]"),
            notable_restaurants=json.loads(chef.notable_restaurants_json or "[]"),
            book_titles=json.loads(chef.book_titles_json or "[]"),
            website_url=chef.website_url,
            wikipedia_url=chef.wikipedia_url,
            instagram_url=chef.instagram_url,
            has_michelin_restaurant=chef.has_michelin_restaurant,
            michelin_star_count=chef.michelin_star_count,
            michelin_summary=chef.michelin_summary,
            notes=chef.notes,
            restaurant_ids=[restaurant.id for restaurant in chef.restaurants],
            uploaded_book_ids=[book.id for book in chef.uploaded_books],
            restaurants=[
                ChefRelatedRestaurant(
                    id=restaurant.id,
                    name=restaurant.name,
                    michelin_star_count=restaurant.michelin_star_count,
                )
                for restaurant in chef.restaurants
            ],
            uploaded_books=[
                ChefRelatedBook(id=book.id, name=book.name, is_translated_book=book.is_translated_book)
                for book in chef.uploaded_books
            ],
            has_image=bool(image_stat and image_stat.st_size > 0),
            image_version=str(image_stat.st_mtime_ns) if image_stat else None,
            created_at=chef.created_at,
            updated_at=chef.updated_at,
        )

    def _statement(self):
        return sa.select(Chef).options(
            selectinload(Chef.restaurants),
            selectinload(Chef.uploaded_books),
        ).where(Chef.group_id == self.group_id)

    def _get_or_404(self, chef_id: UUID4) -> Chef:
        chef = self.session.execute(self._statement().where(Chef.id == chef_id)).scalar_one_or_none()
        if chef is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        return chef

    def _validated_restaurants(self, ids: list[UUID4]) -> list[Restaurant]:
        unique_ids = list(dict.fromkeys(ids))
        if not unique_ids:
            return []
        restaurants = list(
            self.session.execute(
                sa.select(Restaurant).where(Restaurant.group_id == self.group_id, Restaurant.id.in_(unique_ids))
            ).scalars()
        )
        if len(restaurants) != len(unique_ids):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="One or more restaurants were not found")
        by_id = {restaurant.id: restaurant for restaurant in restaurants}
        return [by_id[item_id] for item_id in unique_ids]

    def _validated_books(self, ids: list[UUID4]) -> list[UploadedBook]:
        unique_ids = list(dict.fromkeys(ids))
        if not unique_ids:
            return []
        books = list(
            self.session.execute(
                sa.select(UploadedBook).where(
                    UploadedBook.group_id == self.group_id,
                    UploadedBook.id.in_(unique_ids),
                )
            ).scalars()
        )
        if len(books) != len(unique_ids):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="One or more books were not found")
        by_id = {book.id: book for book in books}
        return [by_id[item_id] for item_id in unique_ids]

    def _apply(self, chef: Chef, data: ChefCreate | ChefUpdate) -> None:
        chef.name = SPACE_RE.sub(" ", data.name.strip())[:255]
        chef.aliases_json = json.dumps(normalize_terms(data.aliases), ensure_ascii=False)
        chef.rank = data.rank if data.rank in VALID_RANKS else "good"
        chef.country = SPACE_RE.sub(" ", (data.country or "").strip())[:120] or None
        chef.cuisines_json = json.dumps(normalize_terms(data.cuisines), ensure_ascii=False)
        chef.specialties_json = json.dumps(normalize_terms(data.specialties), ensure_ascii=False)
        chef.biography = (data.biography or "").strip() or None
        chef.career_summary = (data.career_summary or "").strip() or None
        chef.awards_json = json.dumps(normalize_terms(data.awards), ensure_ascii=False)
        restaurants = self._validated_restaurants(data.restaurant_ids)
        uploaded_books = self._validated_books(data.uploaded_book_ids)
        chef.notable_restaurants_json = json.dumps(
            normalize_terms([*data.notable_restaurants, *(restaurant.name for restaurant in restaurants)], limit=120),
            ensure_ascii=False,
        )
        chef.book_titles_json = json.dumps(
            normalize_terms([*data.book_titles, *(book.name for book in uploaded_books)], limit=120),
            ensure_ascii=False,
        )
        chef.website_url = normalize_optional_url(data.website_url)
        chef.wikipedia_url = normalize_optional_url(data.wikipedia_url)
        chef.instagram_url = normalize_optional_url(data.instagram_url)
        chef.has_michelin_restaurant = bool(data.has_michelin_restaurant)
        chef.michelin_star_count = max(0, int(data.michelin_star_count or 0))
        chef.michelin_summary = (data.michelin_summary or "").strip() or None
        chef.notes = (data.notes or "").strip() or None
        chef.restaurants = restaurants
        chef.uploaded_books = uploaded_books

    def _save(self, data: ChefCreate) -> Chef:
        chef = self.session.execute(
            self._statement().where(sa.func.lower(Chef.name) == data.name.strip().lower())
        ).scalar_one_or_none()
        if chef is None:
            chef = Chef(
                group_id=self.group_id,
                household_id=self.household_id,
                user_id=self.user.id,
                name=data.name.strip(),
                session=self.session,
            )
        self._apply(chef, data)
        self.session.add(chef)
        self.session.commit()
        return self._get_or_404(chef.id)

    async def _fetch_url_text(self, url: str) -> str:
        chunks: list[bytes] = []
        total = 0
        limits = httpx.Limits(max_connections=2, max_keepalive_connections=1)
        async with httpx.AsyncClient(
            transport=safehttp.AsyncSafeTransport(impersonate="chrome"),
            timeout=30,
            follow_redirects=True,
            limits=limits,
        ) as client:
            async with client.stream("GET", url, headers={"User-Agent": "Mealie Chefs/1.0"}) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    remaining = MAX_PAGE_BYTES - total
                    if remaining <= 0:
                        break
                    chunks.append(chunk[:remaining])
                    total += min(len(chunk), remaining)
        return clean_html_text(b"".join(chunks).decode("utf-8", errors="replace"))

    async def _lookup_wikipedia(self, name: str) -> tuple[str | None, str | None]:
        query = SPACE_RE.sub(" ", name.strip())[:255]
        if not query:
            return None, None
        limits = httpx.Limits(max_connections=2, max_keepalive_connections=1)
        async with httpx.AsyncClient(
            transport=safehttp.AsyncSafeTransport(impersonate="chrome"),
            timeout=20,
            follow_redirects=True,
            limits=limits,
        ) as client:
            for language in ("he", "en"):
                try:
                    response = await client.get(
                        WIKIPEDIA_API_TEMPLATE.format(language=language),
                        params={
                            "action": "query",
                            "generator": "search",
                            "gsrsearch": query,
                            "gsrnamespace": 0,
                            "gsrlimit": 3,
                            "prop": "extracts|info",
                            "exintro": 1,
                            "explaintext": 1,
                            "inprop": "url",
                            "format": "json",
                            "formatversion": 2,
                            "origin": "*",
                        },
                        headers={"User-Agent": "Mealie Chef Research/1.0"},
                    )
                    response.raise_for_status()
                    pages = response.json().get("query", {}).get("pages", [])
                except (httpx.HTTPError, ValueError, TypeError):
                    continue
                for page in pages:
                    extract = SPACE_RE.sub(" ", str(page.get("extract") or "").strip())
                    full_url = str(page.get("fullurl") or "").strip()
                    if extract and full_url:
                        return full_url[:2000], extract[:MAX_PAGE_TEXT]
        return None, None

    def _matching_restaurant_ids(self, names: list[str]) -> list[UUID4]:
        wanted = {name.casefold() for name in names if name.strip()}
        if not wanted:
            return []
        return [
            restaurant.id
            for restaurant in self.session.execute(
                sa.select(Restaurant).where(Restaurant.group_id == self.group_id)
            ).scalars()
            if restaurant.name.casefold() in wanted
        ]

    def _matching_book_ids(self, titles: list[str]) -> list[UUID4]:
        wanted = {title.casefold() for title in titles if title.strip()}
        if not wanted:
            return []
        result: list[UUID4] = []
        for book in self.session.execute(
            sa.select(UploadedBook).where(UploadedBook.group_id == self.group_id)
        ).scalars():
            candidates = {book.name.casefold(), book.original_file_name.casefold()}
            if wanted.intersection(candidates):
                result.append(book.id)
        return result

    async def _analyze(
        self,
        data: ChefAIRequest,
        *,
        page_title: str | None = None,
        page_text: str | None = None,
        page_image_url: str | None = None,
    ) -> ChefCreate:
        if not self._ai_enabled():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("OpenAI services are not enabled"),
            )
        normalized_url = normalize_optional_url(data.url)
        if normalized_url and not page_text:
            page_text = await self._fetch_url_text(normalized_url)
        wikipedia_url = normalized_url if normalized_url and "wikipedia.org/" in normalized_url else None
        wikipedia_text: str | None = None
        if (data.name or "").strip() and not wikipedia_url:
            wikipedia_url, wikipedia_text = await self._lookup_wikipedia(data.name or "")
        message_parts = [
            f"User research request:\n{data.prompt.strip()}" if (data.prompt or "").strip() else "",
            f"Chef name supplied by user: {data.name.strip()}" if (data.name or "").strip() else "",
            f"Reference URL: {normalized_url}" if normalized_url else "",
            f"Reference page title: {page_title.strip()}" if (page_title or "").strip() else "",
            f"Reference page text:\n{page_text}" if page_text else "",
            f"Wikipedia URL: {wikipedia_url}" if wikipedia_url else "",
            f"Wikipedia introduction:\n{wikipedia_text}" if wikipedia_text else "",
            f"Page image URL (use only as visual context): {page_image_url}" if page_image_url else "",
            "Required output language for all explanatory metadata: Hebrew.",
        ]
        openai_service = OpenAIService(self.repos)
        response = await openai_service.get_response(
            openai_service.get_prompt("chefs.parse-chef"),
            "\n\n".join(part for part in message_parts if part),
            response_schema=OpenAIChef,
        )
        if not response or not response.is_chef or not response.name.strip():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("The AI provider did not return a usable chef profile"),
            )
        restaurant_names = normalize_terms(response.notable_restaurants, limit=120)
        book_titles = normalize_terms(response.book_titles, limit=120)
        return ChefCreate(
            name=response.name,
            aliases=normalize_terms(response.aliases),
            rank=response.rank if response.rank in VALID_RANKS else "good",
            country=response.country,
            cuisines=normalize_terms(response.cuisines),
            specialties=normalize_terms(response.specialties),
            biography=response.biography,
            career_summary=response.career_summary,
            awards=normalize_terms(response.awards),
            notable_restaurants=restaurant_names,
            book_titles=book_titles,
            website_url=response.website_url or normalized_url,
            wikipedia_url=response.wikipedia_url or wikipedia_url,
            instagram_url=response.instagram_url,
            has_michelin_restaurant=response.has_michelin_restaurant,
            michelin_star_count=response.michelin_star_count,
            michelin_summary=response.michelin_summary,
            restaurant_ids=self._matching_restaurant_ids(restaurant_names),
            uploaded_book_ids=self._matching_book_ids(book_titles),
        )

    @router.get("", response_model=list[ChefOut])
    def get_all(
        self,
        search: str | None = Query(None),
        rank: str | None = Query(None),
        cuisine: str | None = Query(None),
        michelin_only: bool = Query(False),
    ) -> list[ChefOut]:
        statement = self._statement()
        query = (search or "").strip()
        if query:
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            statement = statement.where(
                sa.or_(
                    Chef.name.ilike(pattern, escape="\\"),
                    Chef.aliases_json.ilike(pattern, escape="\\"),
                    Chef.cuisines_json.ilike(pattern, escape="\\"),
                    Chef.specialties_json.ilike(pattern, escape="\\"),
                    Chef.biography.ilike(pattern, escape="\\"),
                    Chef.career_summary.ilike(pattern, escape="\\"),
                    Chef.notable_restaurants_json.ilike(pattern, escape="\\"),
                    Chef.book_titles_json.ilike(pattern, escape="\\"),
                )
            )
        if rank in VALID_RANKS:
            statement = statement.where(Chef.rank == rank)
        if cuisine:
            escaped = cuisine.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            statement = statement.where(Chef.cuisines_json.ilike(f"%{escaped}%", escape="\\"))
        if michelin_only:
            statement = statement.where(Chef.has_michelin_restaurant.is_(True))
        rank_order = sa.case(
            (Chef.rank == "world_class", 0),
            (Chef.rank == "excellent", 1),
            (Chef.rank == "good", 2),
            (Chef.rank == "medium", 3),
            else_=4,
        )
        rows = self.session.execute(statement.order_by(rank_order, Chef.name.asc())).scalars().all()
        return [self._to_out(row) for row in rows]

    @router.post("", response_model=ChefOut, status_code=status.HTTP_201_CREATED)
    def create(self, data: ChefCreate) -> ChefOut:
        return self._to_out(self._save(data))

    @router.post("/ai-create", response_model=ChefOut, status_code=status.HTTP_201_CREATED)
    async def create_with_ai(self, data: ChefAIRequest) -> ChefOut:
        chef = self._save(await self._analyze(data))
        if not self._image_path(chef).exists():
            try:
                await self.image_service.search_and_save_public_image(
                    self._image_path(chef),
                    f"{chef.name} chef portrait",
                )
            except (ValueError, httpx.HTTPError):
                self.logger.warning("Could not find a public portrait for chef %s", chef.name)
        return self._to_out(chef)

    @router.post("/browser-page", response_model=ChefOut, status_code=status.HTTP_201_CREATED)
    async def create_from_browser_page(self, data: ChefBrowserPageRequest) -> ChefOut:
        chef = self._save(
            await self._analyze(
                data,
                page_title=data.page_title,
                page_text=data.page_text,
                page_image_url=data.page_image_url,
            )
        )
        if not self._image_path(chef).exists() and data.page_image_url:
            try:
                await self.image_service.save_url(self._image_path(chef), data.page_image_url)
            except (ValueError, httpx.HTTPError):
                self.logger.warning("Could not save the supplied portrait for chef %s", chef.name)
        return self._to_out(chef)

    @router.put("/{chef_id}", response_model=ChefOut)
    def update(self, chef_id: UUID4, data: ChefUpdate) -> ChefOut:
        chef = self._get_or_404(chef_id)
        self._apply(chef, data)
        self.session.add(chef)
        self.session.commit()
        return self._to_out(self._get_or_404(chef.id))

    @router.get("/{chef_id}/image", response_class=FileResponse)
    def get_image(self, chef_id: UUID4) -> FileResponse:
        chef = self._get_or_404(chef_id)
        path = self._image_path(chef)
        if not path.exists():
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        return FileResponse(path, media_type="image/webp", content_disposition_type="inline")

    @router.post("/{chef_id}/image", response_model=ChefOut)
    async def upload_image(self, chef_id: UUID4, image: UploadFile = File(...)) -> ChefOut:
        chef = self._get_or_404(chef_id)
        content = await image.read(12 * 1024 * 1024 + 1)
        await image.close()
        try:
            await self.image_service.save_content(self._image_path(chef), content)
        except ValueError as error:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ErrorResponse.respond(str(error))) from error
        return self._to_out(chef)

    @router.post("/{chef_id}/image-url", response_model=ChefOut)
    async def save_image_url(self, chef_id: UUID4, data: ChefImageURLRequest) -> ChefOut:
        chef = self._get_or_404(chef_id)
        try:
            await self.image_service.save_url(self._image_path(chef), data.url)
        except (ValueError, httpx.HTTPError) as error:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ErrorResponse.respond(str(error))) from error
        return self._to_out(chef)

    @router.post("/{chef_id}/image-auto", response_model=ChefOut)
    async def find_image(self, chef_id: UUID4) -> ChefOut:
        chef = self._get_or_404(chef_id)
        try:
            await self.image_service.search_and_save_public_image(
                self._image_path(chef),
                f"{chef.name} chef portrait",
            )
        except (ValueError, httpx.HTTPError) as error:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ErrorResponse.respond(str(error))) from error
        return self._to_out(chef)

    @router.delete("/{chef_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete(self, chef_id: UUID4) -> None:
        chef = self._get_or_404(chef_id)
        image_dir = self._image_path(chef).parent
        self.session.delete(chef)
        self.session.commit()
        shutil.rmtree(image_dir, ignore_errors=True)
