import json
import re
from uuid import uuid4

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import UUID4
from slugify import slugify

from mealie.core import exceptions
from mealie.db.models.household.article import Article
from mealie.routes._base import controller
from mealie.routes._base.base_controllers import BaseUserController
from mealie.schema.household.article import (
    ArticleAIRequest,
    ArticleAISearchItem,
    ArticleAISearchRequest,
    ArticleAISearchResponse,
    ArticleBrowserPageRequest,
    ArticleBrowserPageResponse,
    ArticleCreate,
    ArticleOut,
    ArticleUpdate,
)
from mealie.schema.household.group_shopping_list import ShoppingListAddRecipeParamsBulk, ShoppingListCreate
from mealie.schema.openai.article import OpenAIArticle, OpenAIArticleSearchResponse
from mealie.schema.recipe import Recipe
from mealie.schema.response import PaginationQuery
from mealie.schema.response.responses import ErrorResponse
from mealie.services.household_services.shopping_lists import ShoppingListService
from mealie.services.item_image_service import ItemImageService
from mealie.services.openai import OpenAIDataInjection, OpenAIService
from mealie.services.recipe.recipe_service import RecipeService

router = APIRouter(prefix="/households/articles", tags=["Households: Articles"])

HTML_SCRIPT_STYLE_RE = re.compile(r"<(script|style).*?</\1>", re.IGNORECASE | re.DOTALL)
HTML_TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"[ \t]+")


def normalize_terms(values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values or []:
        item = SPACE_RE.sub(" ", str(value).strip())
        if item and item.lower() not in {existing.lower() for existing in normalized}:
            normalized.append(item[:80])
    return normalized[:30]


def clean_html_text(value: str) -> str:
    value = HTML_SCRIPT_STYLE_RE.sub(" ", value)
    value = re.sub(r"</(p|div|h[1-6]|li|br)>", "\n", value, flags=re.IGNORECASE)
    value = HTML_TAG_RE.sub(" ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    value = SPACE_RE.sub(" ", value)
    return value.strip()


@controller(router)
class ArticlesController(BaseUserController):
    def _ai_enabled(self) -> bool:
        settings = self.session.execute(
            sa.text(
                """
                SELECT id, default_provider_id
                FROM ai_provider_settings
                WHERE group_id = :group_id
                """
            ),
            {"group_id": self.repos.uuid_to_str(self.group_id)},
        ).mappings().one_or_none()
        if not settings or not settings["default_provider_id"]:
            return False

        provider_exists = self.session.execute(
            sa.text("SELECT 1 FROM ai_providers WHERE id = :provider_id AND settings_id = :settings_id LIMIT 1"),
            {"provider_id": settings["default_provider_id"], "settings_id": settings["id"]},
        ).scalar()
        return bool(provider_exists)

    def _article_to_out(self, article: Article) -> ArticleOut:
        return ArticleOut(
            id=article.id,
            group_id=article.group_id,
            household_id=article.household_id,
            user_id=article.user_id,
            title=article.title,
            slug=article.slug,
            summary=article.summary,
            content=article.content,
            source=article.source,
            author=article.author,
            categories=json.loads(article.categories_json or "[]"),
            tags=json.loads(article.tags_json or "[]"),
            created_at=article.created_at,
            updated_at=article.updated_at,
        )

    def _get_article_or_404(self, article_id: UUID4) -> Article:
        article = (
            self.session.execute(
                sa.select(Article).where(Article.id == article_id, Article.group_id == self.group_id)
            )
            .scalars()
            .one_or_none()
        )
        if article is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND)

        return article

    def _unique_slug(self, title: str, current_article_id: UUID4 | None = None) -> str:
        base_slug = slugify(title, max_length=80) or "article"
        slug = base_slug
        for suffix in range(2, 10_002):
            query = sa.select(Article.id).where(Article.group_id == self.group_id, Article.slug == slug)
            if current_article_id:
                query = query.where(Article.id != current_article_id)
            exists = self.session.execute(query).scalar_one_or_none()
            if not exists:
                return slug
            slug = f"{base_slug}-{suffix}"

        return f"{base_slug}-{uuid4().hex[:8]}"

    def _apply_article_data(self, article: Article, data: ArticleCreate | ArticleUpdate) -> Article:
        article.title = data.title.strip()
        article.summary = (data.summary or "").strip() or None
        article.content = data.content.strip()
        article.source = (data.source or "").strip() or None
        article.author = (data.author or "").strip() or None
        article.categories_json = json.dumps(normalize_terms(data.categories), ensure_ascii=False)
        article.tags_json = json.dumps(normalize_terms(data.tags), ensure_ascii=False)
        return article

    def _manual_search(self, articles: list[Article], search: str | None, categories: list[str], tags: list[str]):
        search_terms = [part.lower() for part in (search or "").split() if part.strip()]
        category_terms = {item.lower() for item in categories}
        tag_terms = {item.lower() for item in tags}

        def matches(article: Article) -> bool:
            article_categories = {item.lower() for item in json.loads(article.categories_json or "[]")}
            article_tags = {item.lower() for item in json.loads(article.tags_json or "[]")}
            text = " ".join(
                [
                    article.title or "",
                    article.summary or "",
                    article.content or "",
                    article.source or "",
                    article.author or "",
                    " ".join(article_categories),
                    " ".join(article_tags),
                ]
            ).lower()

            return (
                all(term in text for term in search_terms)
                and (not category_terms or bool(category_terms & article_categories))
                and (not tag_terms or bool(tag_terms & article_tags))
            )

        return [article for article in articles if matches(article)]

    async def _fetch_url_text(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "Mealie Articles/1.0"})
        response.raise_for_status()
        text = clean_html_text(response.text)
        return text[:250000]

    def _article_create_from_openai(self, response: OpenAIArticle, fallback_source: str | None = None) -> ArticleCreate:
        return ArticleCreate(
            title=response.title,
            summary=response.summary or None,
            content=response.content,
            source=response.source or fallback_source or None,
            author=response.author or None,
            categories=response.categories,
            tags=response.tags,
        )

    async def _parse_article_ai(self, data: ArticleAIRequest) -> tuple[OpenAIArticle, str | None]:
        text = (data.text or "").strip()
        url = (data.url or getattr(data, "source_url", None) or "").strip()
        source_title = (getattr(data, "source_title", None) or "").strip()

        if url and not text:
            fetched_text = await self._fetch_url_text(url)
            text = f"Source URL: {url}\n\n{fetched_text}"

        if not text:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("Article text cannot be empty"),
            )

        source_parts = []
        if source_title:
            source_parts.append(f"Source title: {source_title}")
        if url:
            source_parts.append(f"Source URL: {url}")
        if source_parts:
            text = "\n".join(source_parts + ["", text])

        openai_service = OpenAIService(self.repos)
        prompt = openai_service.get_prompt("articles.parse-article")
        target_language = (data.translate_language or "").strip()
        message = text
        if target_language:
            message = f"Target language: {target_language}\n\n{message}"

        response = await openai_service.get_response(prompt, message, response_schema=OpenAIArticle)
        if not response:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("The provided text does not look like an article"),
            )

        return response, url or None

    async def _article_from_ai(self, data: ArticleAIRequest) -> ArticleCreate:
        response, url = await self._parse_article_ai(data)
        if not response.is_article or not response.title.strip() or not response.content.strip():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("The provided text does not look like an article"),
            )

        return self._article_create_from_openai(response, url)

    @router.get("", response_model=list[ArticleOut])
    def get_articles(
        self,
        search: str | None = Query(None),
        categories: list[str] | None = Query(None),
        tags: list[str] | None = Query(None),
    ) -> list[ArticleOut]:
        articles = (
            self.session.execute(
                sa.select(Article)
                .where(Article.group_id == self.group_id)
                .order_by(Article.created_at.desc(), Article.title.asc())
            )
            .scalars()
            .all()
        )
        articles = self._manual_search(articles, search, categories or [], tags or [])
        return [self._article_to_out(article) for article in articles]

    @router.get("/{article_id}", response_model=ArticleOut)
    def get_article(self, article_id: UUID4) -> ArticleOut:
        return self._article_to_out(self._get_article_or_404(article_id))

    @router.post("", response_model=ArticleOut, status_code=status.HTTP_201_CREATED)
    def create_article(self, data: ArticleCreate) -> ArticleOut:
        article = Article(
            group_id=self.group_id,
            household_id=self.household_id,
            user_id=self.user.id,
            title=data.title.strip(),
            slug=self._unique_slug(data.title),
            content=data.content.strip(),
            session=self.session,
        )
        self._apply_article_data(article, data)
        self.session.add(article)
        self.session.commit()
        self.session.refresh(article)
        return self._article_to_out(article)

    @router.post("/ai-create", response_model=ArticleBrowserPageResponse, status_code=status.HTTP_201_CREATED)
    async def create_article_with_ai(self, data: ArticleAIRequest) -> ArticleBrowserPageResponse:
        if not self._ai_enabled():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("OpenAI services are not enabled"),
            )

        browser_data = ArticleBrowserPageRequest(
            text=data.text,
            url=data.url,
            source_url=data.url,
            translate_language=data.translate_language,
            create_recipe_if_present=data.create_recipe_if_present,
            create_shopping_list=data.create_shopping_list,
            organize_shopping_list_with_ai=data.organize_shopping_list_with_ai,
            include_ai_tips=data.include_ai_tips,
            include_mise_en_place=data.include_mise_en_place,
            include_item_images=data.include_item_images,
        )
        return await self.create_article_from_browser_page(browser_data)

    @router.post("/browser-page", response_model=ArticleBrowserPageResponse, status_code=status.HTTP_201_CREATED)
    async def create_article_from_browser_page(self, data: ArticleBrowserPageRequest) -> ArticleBrowserPageResponse:
        if not self._ai_enabled():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("OpenAI services are not enabled"),
            )

        response, url = await self._parse_article_ai(data)
        content_kind = (response.content_kind or "other").strip() or "other"
        has_recipe = response.contains_recipe or content_kind in {"recipe", "article_with_recipe"}
        result = ArticleBrowserPageResponse(
            content_kind=content_kind,
            contains_recipe=has_recipe,
            group_slug=getattr(self.group, "slug", None),
        )

        if response.is_article and response.title.strip() and response.content.strip():
            result.article = self.create_article(self._article_create_from_openai(response, url))

        if data.create_recipe_if_present and has_recipe:
            recipe_text = (response.recipe_text or "").strip() or (data.text or "").strip()
            if recipe_text:
                if data.source_title:
                    recipe_text = f"Source title: {data.source_title.strip()}\n{recipe_text}"
                if data.source_url:
                    recipe_text = f"Source URL: {data.source_url.strip()}\n{recipe_text}"

                try:
                    recipe_service = RecipeService(self.repos, self.user, self.household, self.translator)
                    recipe = await recipe_service.create_from_text(
                        recipe_text,
                        data.translate_language,
                        data.include_ai_tips,
                        data.include_mise_en_place,
                        auto_image=not data.image_url,
                    )
                    recipe = recipe_service.apply_source_metadata(
                        recipe,
                        source_title=data.source_title,
                        source_url=data.source_url,
                    )
                    if data.image_url:
                        await recipe_service.attach_best_effort_image(
                            recipe,
                            image_url=data.image_url,
                            search_query=recipe.name,
                        )
                    if data.include_item_images:
                        try:
                            await ItemImageService(self.group_id, self.repos).ensure_recipe_images(recipe)
                        except Exception:
                            self.logger.exception("Failed to ensure browser article recipe item images")
                            self.session.rollback()
                    result.recipe_slug = recipe.slug
                    if data.create_shopping_list:
                        result = await self._create_article_recipe_shopping_list(recipe, data, result)
                except exceptions.NotARecipe as e:
                    result.recipe_error = str(e) or "The article recipe could not be converted into a recipe"
                except Exception as e:
                    self.logger.exception("Failed to create recipe from browser article")
                    result.recipe_error = str(e) or "Recipe creation from article failed"

        if not result.article and not result.recipe_slug:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("The provided page does not look like an article or a complete recipe"),
            )

        return result

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

    async def _create_article_recipe_shopping_list(
        self,
        recipe: Recipe,
        data: ArticleBrowserPageRequest,
        response: ArticleBrowserPageResponse,
    ) -> ArticleBrowserPageResponse:
        shopping_service = ShoppingListService(self.repos)

        try:
            shopping_list = shopping_service.create_one_list(
                ShoppingListCreate(
                    name=self._browser_shopping_list_name(recipe, shopping_service),
                    extras={
                        "aiCreatedFromBrowserExtension": True,
                        "aiCreatedFromArticleImport": True,
                        "aiCreatedFromRecipeSlug": recipe.slug,
                        "aiCreatedFromRecipeId": str(recipe.id),
                        "sourceUrl": data.source_url,
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

            if data.organize_shopping_list_with_ai:
                try:
                    shopping_list, _items = await shopping_service.organize_with_ai(
                        shopping_list.id,
                        include_ai_tips=data.include_ai_tips,
                        target_language=data.translate_language,
                    )
                    response.shopping_list_id = shopping_list.id
                    response.shopping_list_name = shopping_list.name
                    response.shopping_list_organized = True
                except Exception as e:
                    self.logger.exception("Failed to organize browser article shopping list with AI")
                    self.session.rollback()
                    response.shopping_list_error = str(e) or "AI shopping list organization failed"
                    shopping_list = shopping_service.shopping_lists.get_one(shopping_list.id) or shopping_list

            if data.include_item_images:
                try:
                    await ItemImageService(self.group_id, self.repos).ensure_shopping_list_images(shopping_list)
                except Exception:
                    self.logger.exception("Failed to ensure browser article shopping list item images")
                    self.session.rollback()
        except Exception as e:
            self.logger.exception("Failed to create browser article shopping list")
            response.shopping_list_error = str(e) or "Shopping list creation failed"

        return response

    @router.put("/{article_id}", response_model=ArticleOut)
    def update_article(self, article_id: UUID4, data: ArticleUpdate) -> ArticleOut:
        article = self._get_article_or_404(article_id)
        if article.title.strip() != data.title.strip():
            article.slug = self._unique_slug(data.title, article.id)
        self._apply_article_data(article, data)
        self.session.add(article)
        self.session.commit()
        self.session.refresh(article)
        return self._article_to_out(article)

    @router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_article(self, article_id: UUID4) -> None:
        article = self._get_article_or_404(article_id)
        self.session.delete(article)
        self.session.commit()

    @router.post("/ai-search", response_model=ArticleAISearchResponse)
    async def search_articles_with_ai(self, data: ArticleAISearchRequest) -> ArticleAISearchResponse:
        if not self._ai_enabled():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("OpenAI services are not enabled"),
            )

        articles = self.get_articles()
        if not articles:
            return ArticleAISearchResponse(items=[])

        catalog = [
            {
                "id": str(article.id),
                "title": article.title,
                "summary": article.summary,
                "source": article.source,
                "author": article.author,
                "categories": article.categories,
                "tags": article.tags,
                "content": article.content[:1800],
            }
            for article in articles
        ]

        openai_service = OpenAIService(self.repos)
        prompt = openai_service.get_prompt(
            "articles.search-articles",
            [
                OpenAIDataInjection(
                    description="Article catalog JSON",
                    value=json.dumps(catalog, ensure_ascii=False),
                )
            ],
        )
        response = await openai_service.get_response(prompt, data.query, response_schema=OpenAIArticleSearchResponse)
        if not response:
            return ArticleAISearchResponse(items=[])

        valid_ids = {str(article.id): article for article in articles}
        items: list[ArticleAISearchItem] = []
        seen: set[str] = set()
        for item in response.results:
            if item.id not in valid_ids or item.id in seen:
                continue
            seen.add(item.id)
            items.append(ArticleAISearchItem(id=valid_ids[item.id].id, score=item.score, reason=item.reason))
            if len(items) >= data.limit:
                break

        return ArticleAISearchResponse(items=items)
