import json
import re
from urllib.parse import quote_plus, urlsplit, urlunsplit

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import UUID4

from mealie.db.models.household.restaurant import Restaurant
from mealie.routes._base import controller
from mealie.routes._base.base_controllers import BaseUserController
from mealie.schema.household.restaurant import (
    RestaurantAIRequest,
    RestaurantBrowserPageRequest,
    RestaurantCreate,
    RestaurantOut,
    RestaurantUpdate,
)
from mealie.schema.openai.restaurant import OpenAIRestaurant, OpenAIRestaurantHebrewMetadata
from mealie.schema.response.responses import ErrorResponse
from mealie.services.openai import OpenAIService

router = APIRouter(prefix="/households/restaurants", tags=["Households: Restaurants"])

HTML_SCRIPT_STYLE_RE = re.compile(r"<(script|style).*?</\1>", re.IGNORECASE | re.DOTALL)
HTML_TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"[ \t]+")
HEBREW_RE = re.compile(r"[\u0590-\u05ff]")
LATIN_RE = re.compile(r"[A-Za-z]")
TEL_AVIV_RE = re.compile(r"(?:תל[\s\-־]*אביב|tel[\s-]*aviv)", re.IGNORECASE)
MAX_PAGE_BYTES = 2 * 1024 * 1024
MAX_PAGE_TEXT = 250000
VALID_RECOMMENDATION_STATUSES = {
    "strongly_recommended",
    "recommended",
    "neutral",
    "not_recommended",
    "strongly_not_recommended",
}
VALID_VISIT_STATUSES = {"not_tried", "tried"}


def normalize_terms(values: list[str], *, limit: int = 60, item_limit: int = 500) -> list[str]:
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
            detail=ErrorResponse.respond("A valid HTTP or HTTPS restaurant address is required"),
        )
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, ""))


def clean_html_text(value: str) -> str:
    value = HTML_SCRIPT_STYLE_RE.sub(" ", value)
    value = re.sub(r"</(p|div|h[1-6]|li|br|nav|section)>", "\n", value, flags=re.IGNORECASE)
    value = HTML_TAG_RE.sub(" ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    value = SPACE_RE.sub(" ", value)
    return value.strip()[:MAX_PAGE_TEXT]


def prioritize_tel_aviv_addresses(values: list[str]) -> list[str]:
    """Keep the AI's stable order while moving verified Tel Aviv branches first."""
    return sorted(values, key=lambda value: 0 if TEL_AVIV_RE.search(value) else 1)


def google_maps_search_url(name: str, addresses: list[str]) -> str:
    location = addresses[0] if addresses else "ישראל"
    query = SPACE_RE.sub(" ", f"{name.strip()} {location}".strip())
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"


def needs_hebrew_localization(cuisine_types: list[str], description: str | None) -> bool:
    fields = [*cuisine_types, description or ""]
    return any(LATIN_RE.search(value) or (value.strip() and not HEBREW_RE.search(value)) for value in fields)


@controller(router)
class RestaurantsController(BaseUserController):
    def _ai_enabled(self) -> bool:
        settings = (
            self.session.execute(
                sa.text("SELECT id, default_provider_id FROM ai_provider_settings WHERE group_id = :group_id"),
                {"group_id": self.repos.uuid_to_str(self.group_id)},
            )
            .mappings()
            .one_or_none()
        )
        if not settings or not settings["default_provider_id"]:
            return False
        return bool(
            self.session.execute(
                sa.text("SELECT 1 FROM ai_providers WHERE id = :provider_id AND settings_id = :settings_id LIMIT 1"),
                {"provider_id": settings["default_provider_id"], "settings_id": settings["id"]},
            ).scalar()
        )

    def _to_out(self, restaurant: Restaurant) -> RestaurantOut:
        return RestaurantOut(
            id=restaurant.id,
            group_id=restaurant.group_id,
            household_id=restaurant.household_id,
            user_id=restaurant.user_id,
            name=restaurant.name,
            website_url=restaurant.website_url,
            cuisine_types=json.loads(restaurant.cuisine_types_json or "[]"),
            addresses=json.loads(restaurant.addresses_json or "[]"),
            phone=restaurant.phone,
            price_range=restaurant.price_range,
            description=restaurant.description,
            notes=restaurant.notes,
            michelin_info=restaurant.michelin_info,
            google_rating=restaurant.google_rating,
            google_review_count=restaurant.google_review_count,
            google_maps_url=restaurant.google_maps_url,
            our_rating=restaurant.our_rating,
            recommendation_status=restaurant.recommendation_status,
            visit_status=restaurant.visit_status,
            created_at=restaurant.created_at,
            updated_at=restaurant.updated_at,
        )

    def _get_or_404(self, restaurant_id: UUID4) -> Restaurant:
        restaurant = self.session.execute(
            sa.select(Restaurant).where(Restaurant.id == restaurant_id, Restaurant.group_id == self.group_id)
        ).scalar_one_or_none()
        if restaurant is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        return restaurant

    def _apply(self, restaurant: Restaurant, data: RestaurantCreate | RestaurantUpdate) -> None:
        restaurant.name = data.name.strip()
        restaurant.website_url = normalize_optional_url(data.website_url)
        restaurant.cuisine_types_json = json.dumps(normalize_terms(data.cuisine_types), ensure_ascii=False)
        restaurant.addresses_json = json.dumps(
            normalize_terms(data.addresses, limit=100, item_limit=1000), ensure_ascii=False
        )
        restaurant.phone = (data.phone or "").strip() or None
        restaurant.price_range = (data.price_range or "").strip() or None
        restaurant.description = (data.description or "").strip() or None
        restaurant.notes = (data.notes or "").strip() or None
        restaurant.michelin_info = (data.michelin_info or "").strip() or None
        restaurant.google_rating = data.google_rating if data.google_rating and data.google_rating > 0 else None
        restaurant.google_review_count = data.google_review_count
        restaurant.google_maps_url = normalize_optional_url(data.google_maps_url)
        restaurant.our_rating = data.our_rating if data.our_rating and data.our_rating > 0 else None
        restaurant.recommendation_status = (
            data.recommendation_status
            if data.recommendation_status in VALID_RECOMMENDATION_STATUSES
            else "recommended"
        )
        restaurant.visit_status = data.visit_status if data.visit_status in VALID_VISIT_STATUSES else "not_tried"

    async def _fetch_url_text(self, url: str) -> str:
        chunks: list[bytes] = []
        total = 0
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            async with client.stream("GET", url, headers={"User-Agent": "Mealie Restaurants/1.0"}) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    remaining = MAX_PAGE_BYTES - total
                    if remaining <= 0:
                        break
                    chunks.append(chunk[:remaining])
                    total += min(len(chunk), remaining)
        return clean_html_text(b"".join(chunks).decode("utf-8", errors="replace"))

    async def _analyze(
        self,
        *,
        name: str | None = None,
        url: str | None = None,
        page_text: str | None = None,
        page_title: str | None = None,
    ) -> RestaurantCreate:
        if not self._ai_enabled():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("OpenAI services are not enabled"),
            )
        normalized_url = normalize_optional_url(url)
        message_parts: list[str] = []
        if name:
            message_parts.append(f"Restaurant name supplied by user: {name.strip()}")
        if normalized_url:
            message_parts.append(f"Restaurant URL: {normalized_url}")
        if page_title:
            message_parts.append(f"Page title: {page_title.strip()}")
        if page_text:
            message_parts.extend(["", page_text[:MAX_PAGE_TEXT]])
        message_parts.extend(
            [
                "",
                "Required metadata language: Hebrew only for cuisine_types and description.",
                (
                    "Location priority: verify Tel Aviv branches first, then other locations in Israel. "
                    "Try to return the verified address, current Google rating, "
                    "Google review count, and Google Maps URL."
                ),
            ]
        )
        openai_service = OpenAIService(self.repos)
        response = await openai_service.get_response(
            openai_service.get_prompt("restaurants.parse-restaurant"),
            "\n".join(message_parts),
            response_schema=OpenAIRestaurant,
        )
        if not response or not response.is_restaurant or not response.name.strip():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("The supplied information does not look like a restaurant"),
            )
        cuisine_types = normalize_terms(response.cuisine_types)
        description = (response.description or "").strip() or None
        if needs_hebrew_localization(cuisine_types, description):
            localized = await openai_service.get_response(
                openai_service.get_prompt("restaurants.localize-hebrew-metadata"),
                json.dumps(
                    {
                        "cuisine_types": cuisine_types,
                        "description": description,
                    },
                    ensure_ascii=False,
                ),
                response_schema=OpenAIRestaurantHebrewMetadata,
            )
            if localized:
                cuisine_types = normalize_terms(localized.cuisine_types)
                description = (localized.description or "").strip() or None

        addresses = prioritize_tel_aviv_addresses(
            normalize_terms(response.addresses, limit=100, item_limit=1000)
        )
        maps_url = response.google_maps_url or google_maps_search_url(response.name, addresses)
        return RestaurantCreate(
            name=response.name.strip(),
            website_url=normalized_url or response.website_url,
            cuisine_types=cuisine_types,
            addresses=addresses,
            phone=response.phone,
            price_range=response.price_range,
            description=description,
            michelin_info=response.michelin_info,
            google_rating=response.google_rating,
            google_review_count=response.google_review_count,
            google_maps_url=maps_url,
            our_rating=None,
            recommendation_status="recommended",
            visit_status="not_tried",
        )

    def _create_or_update(self, data: RestaurantCreate) -> RestaurantOut:
        normalized_url = normalize_optional_url(data.website_url)
        identity_filters = [sa.func.lower(Restaurant.name) == data.name.strip().lower()]
        if normalized_url:
            identity_filters.append(Restaurant.website_url == normalized_url)
        statement = sa.select(Restaurant).where(
            Restaurant.group_id == self.group_id,
            sa.or_(*identity_filters),
        )
        restaurant = self.session.execute(statement).scalar_one_or_none()
        if restaurant is None:
            restaurant = Restaurant(
                group_id=self.group_id,
                household_id=self.household_id,
                user_id=self.user.id,
                name=data.name.strip(),
                session=self.session,
            )
        self._apply(restaurant, data.model_copy(update={"website_url": normalized_url}))
        self.session.add(restaurant)
        self.session.commit()
        self.session.refresh(restaurant)
        return self._to_out(restaurant)

    @router.get("", response_model=list[RestaurantOut])
    def get_all(self, search: str | None = Query(None)) -> list[RestaurantOut]:
        query = (search or "").strip()
        statement = sa.select(Restaurant).where(Restaurant.group_id == self.group_id)
        if query and query.casefold() not in {"undefined", "null"}:
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            statement = statement.where(
                sa.or_(
                    Restaurant.name.ilike(pattern, escape="\\"),
                    Restaurant.website_url.ilike(pattern, escape="\\"),
                    Restaurant.cuisine_types_json.ilike(pattern, escape="\\"),
                    Restaurant.addresses_json.ilike(pattern, escape="\\"),
                    Restaurant.description.ilike(pattern, escape="\\"),
                    Restaurant.notes.ilike(pattern, escape="\\"),
                    Restaurant.michelin_info.ilike(pattern, escape="\\"),
                )
            )
        restaurants = (
            self.session.execute(statement.order_by(Restaurant.created_at.desc(), Restaurant.name.asc()))
            .scalars()
            .all()
        )
        return [self._to_out(item) for item in restaurants]

    @router.post("", response_model=RestaurantOut, status_code=status.HTTP_201_CREATED)
    def create(self, data: RestaurantCreate) -> RestaurantOut:
        return self._create_or_update(data)

    @router.post("/ai-create", response_model=RestaurantOut, status_code=status.HTTP_201_CREATED)
    async def create_with_ai(self, data: RestaurantAIRequest) -> RestaurantOut:
        normalized_url = normalize_optional_url(data.url)
        page_text = None
        if normalized_url:
            page_text = await self._fetch_url_text(normalized_url)
            if not page_text:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail=ErrorResponse.respond("The restaurant website returned no text"),
                )
        return self._create_or_update(
            await self._analyze(name=data.name, url=normalized_url, page_text=page_text)
        )

    @router.post("/browser-page", response_model=RestaurantOut, status_code=status.HTTP_201_CREATED)
    async def create_from_browser_page(self, data: RestaurantBrowserPageRequest) -> RestaurantOut:
        return self._create_or_update(
            await self._analyze(url=data.url, page_text=data.page_text, page_title=data.page_title)
        )

    @router.put("/{restaurant_id}", response_model=RestaurantOut)
    def update(self, restaurant_id: UUID4, data: RestaurantUpdate) -> RestaurantOut:
        restaurant = self._get_or_404(restaurant_id)
        self._apply(restaurant, data)
        self.session.add(restaurant)
        self.session.commit()
        self.session.refresh(restaurant)
        return self._to_out(restaurant)

    @router.delete("/{restaurant_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete(self, restaurant_id: UUID4) -> None:
        restaurant = self._get_or_404(restaurant_id)
        self.session.delete(restaurant)
        self.session.commit()
