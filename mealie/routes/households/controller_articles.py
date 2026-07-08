import json
import re

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import UUID4
from slugify import slugify

from mealie.db.models.household.article import Article
from mealie.routes._base import controller
from mealie.routes._base.base_controllers import BaseUserController
from mealie.schema.household.article import (
    ArticleAIRequest,
    ArticleAISearchItem,
    ArticleAISearchRequest,
    ArticleAISearchResponse,
    ArticleCreate,
    ArticleOut,
    ArticleUpdate,
)
from mealie.schema.openai.article import OpenAIArticle, OpenAIArticleSearchResponse
from mealie.schema.response.responses import ErrorResponse
from mealie.services.openai import OpenAIDataInjection, OpenAIService

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
        suffix = 2
        while True:
            query = sa.select(Article.id).where(Article.group_id == self.group_id, Article.slug == slug)
            if current_article_id:
                query = query.where(Article.id != current_article_id)
            exists = self.session.execute(query).scalar_one_or_none()
            if not exists:
                return slug
            slug = f"{base_slug}-{suffix}"
            suffix += 1

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

    async def _article_from_ai(self, data: ArticleAIRequest) -> ArticleCreate:
        text = (data.text or "").strip()
        url = (data.url or "").strip()

        if url:
            fetched_text = await self._fetch_url_text(url)
            text = f"Source URL: {url}\n\n{fetched_text}"

        if not text:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ErrorResponse.respond("Article text cannot be empty"))

        openai_service = OpenAIService(self.repos)
        prompt = openai_service.get_prompt("articles.parse-article")
        target_language = (data.translate_language or "").strip()
        message = text
        if target_language:
            message = f"Target language: {target_language}\n\n{message}"

        response = await openai_service.get_response(prompt, message, response_schema=OpenAIArticle)
        if not response or not response.is_article or not response.title.strip() or not response.content.strip():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("The provided text does not look like an article"),
            )

        return ArticleCreate(
            title=response.title,
            summary=response.summary or None,
            content=response.content,
            source=response.source or url or None,
            author=response.author or None,
            categories=response.categories,
            tags=response.tags,
        )

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

    @router.post("/ai-create", response_model=ArticleOut, status_code=status.HTTP_201_CREATED)
    async def create_article_with_ai(self, data: ArticleAIRequest) -> ArticleOut:
        ai_settings = self.group.ai_provider_settings
        if not (ai_settings and ai_settings.ai_enabled):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ErrorResponse.respond("OpenAI services are not enabled"))

        article_data = await self._article_from_ai(data)
        return self.create_article(article_data)

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
        ai_settings = self.group.ai_provider_settings
        if not (ai_settings and ai_settings.ai_enabled):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ErrorResponse.respond("OpenAI services are not enabled"))

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
