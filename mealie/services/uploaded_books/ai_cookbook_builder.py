# ruff: noqa: E501

import html
import json
import math
import re
import shutil
from collections import defaultdict
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa

from mealie.db.models._model_utils.datetime import get_utc_now
from mealie.db.models.household.uploaded_book import UploadedBook
from mealie.lang.providers import Translator
from mealie.repos.repository_factory import AllRepositories
from mealie.schema.cookbook.uploaded_book import AICookbookGenerateRequest, UploadedBookOut
from mealie.schema.household.household import HouseholdInDB
from mealie.schema.openai.general import OpenAICookbookChapter, OpenAICookbookPlan
from mealie.schema.recipe.recipe import Recipe
from mealie.schema.user import PrivateUser
from mealie.services._base_service import BaseService
from mealie.services.openai import OpenAIService
from mealie.services.recipe.recipe_service import OpenAIRecipeService, RecipeService
from mealie.services.uploaded_books.book_reader_assets import (
    BOOK_READER_ID_PLACEHOLDER,
    book_reader_css,
    book_reader_labels,
    book_reader_panels,
    book_reader_script,
)


class AICookbookBuilder(BaseService):
    PLAN_BATCH_SIZE = 80

    def __init__(
        self,
        repos: AllRepositories,
        user: PrivateUser,
        household: HouseholdInDB,
        translator: Translator,
    ) -> None:
        self.repos = repos
        self.user = user
        self.household = household
        self.translator = translator
        self.recipe_service = RecipeService(repos, user, household, translator)
        self.ai_recipe_service = OpenAIRecipeService(repos, user, household, translator)
        super().__init__()

    @staticmethod
    def _metadata(book: UploadedBook) -> dict:
        try:
            value = json.loads(book.book_metadata_json or "{}")
            return value if isinstance(value, dict) else {}
        except (TypeError, ValueError):
            return {}

    def _existing_series(self, series_id: str) -> list[UploadedBook]:
        books = (
            self.repos.session.execute(
                sa.select(UploadedBook).where(
                    UploadedBook.group_id == self.user.group_id,
                    UploadedBook.book_metadata_json.like(f"%{series_id}%"),
                )
            )
            .scalars()
            .all()
        )
        books = [book for book in books if self._metadata(book).get("series_id") == series_id]
        return sorted(books, key=lambda book: int(self._metadata(book).get("volume_number", 1)))

    @staticmethod
    def _query(data: AICookbookGenerateRequest) -> str:
        return (data.prompt if data.mode == "prompt" else data.preset or "").strip()

    async def _select_recipe_slugs(self, query: str, previous_slugs: list[str]) -> list[str]:
        slugs = await self.ai_recipe_service.select_recipe_slugs_for_ai_collection(query)
        for slug in previous_slugs:
            if slug not in slugs:
                slugs.append(slug)
        return slugs

    async def _build_plan(self, query: str, requested_title: str | None, recipes: list[Recipe]) -> OpenAICookbookPlan:
        openai_service = OpenAIService(self.repos)
        prompt = (
            "Design a practical cookbook structure from the supplied recipes. "
            "Include every supplied slug exactly once, "
            "group recipes into clear chapters, and return a concise introduction and literal cookbook title. "
            "Never invent recipe slugs."
        )
        seen: set[str] = set()
        chapters: list[OpenAICookbookChapter] = []
        generated_title = ""
        introduction = ""
        batch_count = math.ceil(len(recipes) / self.PLAN_BATCH_SIZE)
        for batch_index, offset in enumerate(range(0, len(recipes), self.PLAN_BATCH_SIZE), start=1):
            batch = recipes[offset : offset + self.PLAN_BATCH_SIZE]
            catalog = [
                {
                    "slug": recipe.slug,
                    "name": (recipe.name or "")[:160],
                    "description": (recipe.description or "")[:500],
                    "categories": [(item.name or "")[:80] for item in recipe.recipe_category[:12]],
                    "tags": [(item.name or "")[:80] for item in recipe.tags[:12]],
                }
                for recipe in batch
            ]
            message = (
                f"User request: {query}\nRequested title: {requested_title or '[choose a literal title]'}\n"
                f"Planning batch {batch_index} of {batch_count}.\n"
                f"Recipes JSON: {json.dumps(catalog, ensure_ascii=False)}"
            )
            try:
                response = await openai_service.get_response(prompt, message, response_schema=OpenAICookbookPlan)
            except Exception:
                self.logger.exception(
                    "AI cookbook planning batch %s/%s failed; using category fallback",
                    batch_index,
                    batch_count,
                )
                continue

            if not response:
                continue
            generated_title = generated_title or response.title.strip()
            introduction = introduction or response.introduction.strip()
            batch_slugs = {recipe.slug for recipe in batch}
            for chapter in response.chapters:
                slugs = [slug for slug in chapter.recipe_slugs if slug in batch_slugs and slug not in seen]
                if not slugs:
                    continue
                seen.update(slugs)
                chapters.append(OpenAICookbookChapter(title=chapter.title.strip() or "Recipes", recipe_slugs=slugs))

        missing = [recipe for recipe in recipes if recipe.slug not in seen]
        if missing:
            grouped: dict[str, list[str]] = defaultdict(list)
            for recipe in missing:
                title = next((category.name for category in recipe.recipe_category if category.name), "More recipes")
                grouped[title].append(recipe.slug)
            chapters.extend(OpenAICookbookChapter(title=title, recipe_slugs=slugs) for title, slugs in grouped.items())

        title = (requested_title or generated_title or query or "AI Cookbook").strip()[:255]
        return OpenAICookbookPlan(title=title, introduction=introduction, chapters=chapters)

    @staticmethod
    def _estimated_recipe_pages(recipe: Recipe) -> int:
        return max(
            1,
            1
            + math.ceil(len(recipe.recipe_ingredient or []) / 16)
            + math.ceil(len(recipe.recipe_instructions or []) / 6),
        )

    def _split_volumes(
        self,
        plan: OpenAICookbookPlan,
        recipe_by_slug: dict[str, Recipe],
        max_recipes: int,
        max_pages: int,
    ) -> list[list[tuple[str, Recipe]]]:
        volumes: list[list[tuple[str, Recipe]]] = [[]]
        current_pages = 0
        for chapter in plan.chapters:
            for slug in chapter.recipe_slugs:
                recipe = recipe_by_slug.get(slug)
                if not recipe:
                    continue
                recipe_pages = self._estimated_recipe_pages(recipe)
                current = volumes[-1]
                if current and (len(current) >= max_recipes or current_pages + recipe_pages > max_pages):
                    volumes.append([])
                    current = volumes[-1]
                    current_pages = 0
                current.append((chapter.title, recipe))
                current_pages += recipe_pages
        return [volume for volume in volumes if volume]

    @staticmethod
    def _ingredient_text(ingredient) -> str:
        if ingredient.display:
            return str(ingredient.display)
        parts = []
        if ingredient.quantity is not None:
            parts.append(str(ingredient.quantity))
        if ingredient.unit:
            parts.append(ingredient.unit.name or ingredient.unit.abbreviation or "")
        if ingredient.food:
            parts.append(ingredient.food.name or "")
        if ingredient.note:
            parts.append(ingredient.note)
        return " ".join(str(part) for part in parts if part)

    def _render_html(
        self,
        title: str,
        introduction: str,
        volume_number: int,
        volume_count: int,
        entries: list[tuple[str, Recipe]],
    ) -> str:
        display_title = f"{title} - Vol. {volume_number}" if volume_count > 1 else title
        chapter_entries: dict[str, list[Recipe]] = defaultdict(list)
        for chapter, recipe in entries:
            chapter_entries[chapter].append(recipe)

        sample = " ".join(
            [display_title, introduction, *chapter_entries.keys(), *(recipe.name or "" for _, recipe in entries[:12])]
        )
        rtl = bool(re.search(r"[\u0590-\u05ff]", sample))
        direction = "rtl" if rtl else "ltr"
        labels = {
            "contents": "תוכן עניינים" if rtl else "Table of Contents",
            "ingredients": "מרכיבים" if rtl else "Ingredients",
            "method": "אופן ההכנה" if rtl else "Method",
            "source": "מקור" if rtl else "Source",
            "reading_progress": "התקדמות בקריאה" if rtl else "Reading progress",
            "chapter_progress": "פרקים שנקראו" if rtl else "Chapters read",
            "chapter_complete": "סמן פרק כנקרא" if rtl else "Mark chapter as read",
        }
        reader_labels = book_reader_labels(rtl)
        toc: list[str] = []
        body: list[str] = []
        position_index = 0
        for chapter_index, (chapter, recipes) in enumerate(chapter_entries.items(), start=1):
            chapter_id = f"chapter-{chapter_index}"
            position_index += 1
            chapter_position = position_index
            toc.append(
                f'<li class="toc-chapter" data-chapter-id="{chapter_id}"><div class="toc-row">'
                f'<input class="chapter-checkbox" type="checkbox" data-chapter-id="{chapter_id}" '
                f'data-chapter-order="{chapter_index}" title="{html.escape(labels["chapter_complete"])}" '
                f'aria-label="{html.escape(labels["chapter_complete"])}: {html.escape(chapter)}">'
                f'<a href="#{chapter_id}" data-position-target="{chapter_position}">{html.escape(chapter)}</a>'
                "</div><ol>"
            )
            body.append(
                f'<section class="chapter reading-position" id="{chapter_id}" data-page-number="{chapter_position}" '
                f'data-page-index="{chapter_position}" data-chapter-id="{chapter_id}"><h2>{html.escape(chapter)}</h2>'
            )
            for recipe_index, recipe in enumerate(recipes, start=1):
                recipe_id = f"{chapter_id}-recipe-{recipe_index}"
                position_index += 1
                toc.append(
                    f'<li><div class="toc-row"><a href="#{recipe_id}" data-position-target="{position_index}">'
                    f'{html.escape(recipe.name or "Recipe")}</a></div></li>'
                )
                ingredients = "".join(
                    f"<li>{html.escape(self._ingredient_text(ingredient))}</li>"
                    for ingredient in recipe.recipe_ingredient or []
                    if not ingredient.title
                )
                instructions = "".join(
                    f"<li><strong>{html.escape(step.title or '')}</strong> "
                    f"{html.escape(step.text or step.summary or '')}</li>"
                    for step in recipe.recipe_instructions or []
                    if step.text or step.summary or step.title
                )
                source = ""
                if recipe.source:
                    source = (
                        f'<p class="source"><strong>{html.escape(labels["source"])}:</strong> '
                        f'{html.escape(recipe.source)}</p>'
                    )
                body.append(
                    f'<article class="recipe reading-position" id="{recipe_id}" data-page-number="{position_index}" '
                    f'data-page-index="{position_index}" data-chapter-id="{chapter_id}">'
                    f'<div class="recipe-body"><h3>{html.escape(recipe.name or "Recipe")}</h3>'
                    f"<p>{html.escape(recipe.description or '')}</p>{source}"
                    f'<div class="columns"><section><h4>{html.escape(labels["ingredients"])}</h4><ul>{ingredients}</ul></section>'
                    f'<section><h4>{html.escape(labels["method"])}</h4><ol>{instructions}</ol></section></div>'
                    "</div></article>"
                )
            toc.append("</ol></li>")
            body.append("</section>")

        return f"""<!doctype html>
<html lang="auto" dir="{direction}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(display_title)}</title><style>
*{{box-sizing:border-box}}body{{background:#f3f0e9;font-family:Arial,sans-serif;line-height:1.65;margin:0;padding:32px;color:#24211f}}
.book-shell{{max-width:1100px;margin:0 auto}}
h1,h2,h3,h4{{line-height:1.25}} h1{{font-size:2.4rem}} h2{{border-bottom:2px solid #e98018;padding-bottom:8px}}
a{{color:#a64d00}} .cover{{min-height:60vh;display:flex;flex-direction:column;justify-content:center}}
.toc{{background:#fff;border:1px solid #ddd1c1;border-radius:6px;padding:28px;page-break-after:always}}
.toc-row a{{display:flex;flex:1;justify-content:space-between;text-decoration:none}}
.recipe{{background:#fff;border:1px solid #ddd1c1;border-radius:6px;margin:28px 0;padding:28px;page-break-before:always;scroll-margin-top:18px}}
.chapter{{scroll-margin-top:18px}}
.columns{{display:grid;grid-template-columns:1fr 1.5fr;gap:36px}}
.source{{font-size:.9rem;color:#666}} li{{margin:.4rem 0}}
.generated-progress{{background:rgba(255,253,248,.98);border:1px solid #d9cebc;border-radius:6px;bottom:12px;box-shadow:0 8px 26px rgba(61,45,29,.16);direction:{direction};font-family:Arial,sans-serif;left:12px;padding:9px 10px;position:fixed;width:300px;z-index:31}}
.generated-progress.is-collapsed{{width:90px}}.generated-progress__header{{align-items:center;display:flex;gap:8px}}
.generated-progress__title{{flex:1;font-size:13px;font-weight:700}}.generated-progress__percent{{color:#8f3f1f;font-weight:700}}
.generated-progress__toggle{{background:transparent;border:0;color:#8f3f1f;cursor:pointer;font-size:20px}}
.generated-progress.is-collapsed .generated-progress__title,.generated-progress.is-collapsed .generated-progress__details{{display:none}}
.progress-track{{background:#e8dfd3;border-radius:3px;height:6px;margin-top:7px;overflow:hidden}}.progress-fill{{background:#a94f29;height:100%;width:0}}
{book_reader_css(direction)}
@media(max-width:720px){{body{{padding:18px 8px 72px}}.columns{{grid-template-columns:1fr}}.generated-progress{{bottom:8px;left:8px;max-width:calc(100vw - 16px)}}}}
@media print{{body{{background:#fff;max-width:none}}.recipe{{break-before:page}}.generated-progress,.reader-panel{{display:none}}}}
</style></head><body>
<section class="generated-progress" id="generatedProgress" aria-label="{html.escape(labels['reading_progress'])}">
  <div class="generated-progress__header"><strong class="generated-progress__title">{html.escape(labels['reading_progress'])}</strong>
    <span class="generated-progress__percent" id="generatedProgressPercent">0%</span>
    <button class="generated-progress__toggle" id="generatedProgressToggle" type="button" aria-expanded="true">−</button></div>
  <div class="generated-progress__details"><div id="generatedProgressPosition">0 / {position_index}</div>
    <div class="progress-track"><div class="progress-fill" id="generatedProgressFill"></div></div>
    <div class="progress-chapters"><div class="progress-chapters__row"><span>{html.escape(labels['chapter_progress'])}</span>
      <span><span id="chapterProgressDetails">0 / {len(chapter_entries)}</span> · <strong id="chapterProgressPercent">0%</strong></span></div>
      <div class="progress-track"><div class="progress-fill progress-chapters__fill" id="chapterProgressFill"></div></div></div>
  </div>
</section>
{book_reader_panels(reader_labels)}
<main class="book-shell"><header class="cover reading-position" id="cover" data-page-number="0" data-page-index="0">
  <h1>{html.escape(display_title)}</h1><p>{html.escape(introduction)}</p></header>
<nav class="toc"><h2>{html.escape(labels['contents'])}</h2><ol>{"".join(toc)}</ol></nav>{"".join(body)}</main>
{book_reader_script(reader_labels)}
<script>(()=>{{
  const positions=[...document.querySelectorAll('.reading-position')];
  const links=[...document.querySelectorAll('.toc a[data-position-target]')];
  const total={position_index};
  const panel=document.getElementById('generatedProgress');
  const toggle=document.getElementById('generatedProgressToggle');
  let collapsed=false;
  try{{collapsed=localStorage.getItem('generatedBookProgressCollapsed')==='true';}}catch(_error){{}}
  const applyCollapsed=()=>{{panel.classList.toggle('is-collapsed',collapsed);toggle.textContent=collapsed?'+':'−';toggle.setAttribute('aria-expanded',String(!collapsed));}};
  toggle.addEventListener('click',()=>{{collapsed=!collapsed;try{{localStorage.setItem('generatedBookProgressCollapsed',String(collapsed));}}catch(_error){{}}applyCollapsed();}});
  const update=(position)=>{{
    const pageIndex=Number(position.dataset.pageIndex||0);const percent=pageIndex&&total?Math.round(pageIndex/total*100):0;
    document.getElementById('generatedProgressPercent').textContent=`${{percent}}%`;
    document.getElementById('generatedProgressPosition').textContent=`${{pageIndex}} / ${{total}}`;
    document.getElementById('generatedProgressFill').style.width=`${{percent}}%`;
    links.forEach(link=>link.classList.toggle('is-active',Number(link.dataset.positionTarget)===pageIndex));
    window.dispatchEvent(new CustomEvent('mealie:book-position',{{detail:{{pageIndex,pageNumber:pageIndex,chapterId:position.dataset.chapterId||null,percent}}}}));
  }};
  const observer=new IntersectionObserver(entries=>{{const visible=entries.filter(entry=>entry.isIntersecting).sort((a,b)=>b.intersectionRatio-a.intersectionRatio);if(visible[0])update(visible[0].target);}},{{rootMargin:'-20% 0px -55% 0px',threshold:[0,.01,.25]}});
  positions.forEach(position=>observer.observe(position));
  links.forEach(link=>link.addEventListener('click',event=>{{const target=document.querySelector(link.getAttribute('href'));if(!target)return;event.preventDefault();target.scrollIntoView({{behavior:'smooth',block:'start'}});history.pushState(null,'',link.getAttribute('href'));update(target);}}));
  window.addEventListener('pagehide',()=>observer.disconnect(),{{once:true}});applyCollapsed();if(positions[0])update(positions[0]);
}})();</script></body></html>"""

    def _write_volume(
        self,
        book: UploadedBook | None,
        root: Path,
        title: str,
        html_content: str,
        metadata: dict,
    ) -> UploadedBook:
        if book is None:
            book_id = uuid4()
            safe_title = re.sub(r"[^\w\-]+", "-", title, flags=re.UNICODE).strip("-") or "ai-cookbook"
            book = UploadedBook(
                group_id=self.user.group_id,
                household_id=self.user.household_id,
                user_id=self.user.id,
                name=title,
                file_name=f"{book_id}.html",
                original_file_name=f"{safe_title}.html",
                extension=".html",
                content_type="text/html",
                size=0,
                classification_status="completed",
                session=self.repos.session,
            )
            book.id = book_id
        else:
            book.name = title

        target_dir = root.joinpath(str(book.group_id), str(book.id))
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir.joinpath(book.file_name)
        target_path.write_text(
            html_content.replace(BOOK_READER_ID_PLACEHOLDER, str(book.id)),
            encoding="utf-8",
        )
        book.size = target_path.stat().st_size
        book.book_metadata_json = json.dumps(metadata, ensure_ascii=False)
        book.classification_updated_at = get_utc_now()
        self.repos.session.add(book)
        self.repos.session.commit()
        self.repos.session.refresh(book)
        return book

    async def generate(
        self,
        data: AICookbookGenerateRequest,
        uploaded_books_root: Path,
        series_id: str | None = None,
    ) -> list[UploadedBookOut]:
        query = self._query(data)
        series_id = series_id or str(uuid4())
        existing = self._existing_series(series_id)
        previous_slugs = [
            slug
            for book in existing
            for slug in self._metadata(book).get("included_recipe_slugs", [])
            if isinstance(slug, str)
        ]
        slugs = await self._select_recipe_slugs(query, previous_slugs)
        recipes = []
        for slug in slugs:
            try:
                recipes.append(self.recipe_service.get_one(slug))
            except Exception:
                continue
        if not recipes:
            raise ValueError("No matching recipes were found")

        plan = await self._build_plan(query, data.title, recipes)
        recipe_by_slug = {recipe.slug: recipe for recipe in recipes}
        volumes = self._split_volumes(
            plan,
            recipe_by_slug,
            data.max_recipes_per_volume,
            data.max_estimated_pages_per_volume,
        )
        results: list[UploadedBookOut] = []
        for index, entries in enumerate(volumes, start=1):
            volume_title = f"{plan.title} - Vol. {index}" if len(volumes) > 1 else plan.title
            included_slugs = [recipe.slug for _, recipe in entries]
            metadata = {
                "generated_by_ai": True,
                "series_id": series_id,
                "volume_number": index,
                "volume_count": len(volumes),
                "included_recipe_slugs": included_slugs,
                "generation_config": data.model_dump(),
                "classification": {
                    "book_type": "ai_generated_cookbook",
                    "categories": [data.preset] if data.preset else [],
                    "tags": ["AI generated"],
                    "summary": plan.introduction,
                },
            }
            content = self._render_html(plan.title, plan.introduction, index, len(volumes), entries)
            book = self._write_volume(
                existing[index - 1] if index <= len(existing) else None,
                uploaded_books_root,
                volume_title,
                content,
                metadata,
            )
            results.append(UploadedBookOut.model_validate(book))

        for obsolete in existing[len(volumes) :]:
            obsolete_dir = uploaded_books_root.joinpath(str(obsolete.group_id), str(obsolete.id)).resolve()
            expected_root = uploaded_books_root.joinpath(str(obsolete.group_id)).resolve()
            self.repos.session.delete(obsolete)
            self.repos.session.commit()
            if obsolete_dir.is_relative_to(expected_root):
                shutil.rmtree(obsolete_dir, ignore_errors=True)
        return results

    async def refresh(self, book: UploadedBook, uploaded_books_root: Path) -> list[UploadedBookOut]:
        metadata = self._metadata(book)
        config = metadata.get("generation_config")
        series_id = metadata.get("series_id")
        if not isinstance(config, dict) or not series_id:
            raise ValueError("This is not an AI-generated cookbook")
        return await self.generate(
            AICookbookGenerateRequest.model_validate(config), uploaded_books_root, str(series_id)
        )

    async def set_recipe_membership(
        self,
        book: UploadedBook,
        recipe_slug: str,
        included: bool,
        uploaded_books_root: Path,
    ) -> UploadedBookOut:
        metadata = self._metadata(book)
        if not metadata.get("generated_by_ai"):
            raise ValueError("This is not an AI-generated cookbook")

        slugs = [
            slug
            for slug in metadata.get("included_recipe_slugs", [])
            if isinstance(slug, str) and slug
        ]
        if included and recipe_slug not in slugs:
            slugs.append(recipe_slug)
        elif not included:
            slugs = [slug for slug in slugs if slug != recipe_slug]

        recipes: list[Recipe] = []
        retained_slugs: list[str] = []
        for slug in slugs:
            try:
                recipes.append(self.recipe_service.get_one(slug))
                retained_slugs.append(slug)
            except Exception:
                continue

        config = metadata.get("generation_config")
        query = ""
        requested_title = re.sub(r"\s+-\s+Vol\.\s+\d+$", "", book.name or "AI Cookbook")
        if isinstance(config, dict):
            request = AICookbookGenerateRequest.model_validate(config)
            query = self._query(request)
            requested_title = request.title or requested_title

        entries: list[tuple[str, Recipe]] = []
        introduction = str((metadata.get("classification") or {}).get("summary") or "")
        if recipes:
            plan = await self._build_plan(query, requested_title, recipes)
            recipe_by_slug = {recipe.slug: recipe for recipe in recipes}
            for chapter in plan.chapters:
                entries.extend(
                    (chapter.title, recipe_by_slug[slug])
                    for slug in chapter.recipe_slugs
                    if slug in recipe_by_slug
                )
            introduction = plan.introduction or introduction

        metadata["included_recipe_slugs"] = retained_slugs
        classification = metadata.setdefault("classification", {})
        if isinstance(classification, dict) and introduction:
            classification["summary"] = introduction

        volume_number = int(metadata.get("volume_number") or 1)
        volume_count = int(metadata.get("volume_count") or 1)
        content = self._render_html(requested_title, introduction, volume_number, volume_count, entries)
        updated = self._write_volume(book, uploaded_books_root, book.name, content, metadata)
        return UploadedBookOut.model_validate(updated)
