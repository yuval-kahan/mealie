import asyncio
import json
import re
from collections import defaultdict, deque
from html import escape
from typing import Any

import sqlalchemy as sa
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import UUID4

from mealie.db.models.household.notebook import Notebook, NotebookNode, NotebookRevision
from mealie.routes._base import controller
from mealie.routes._base.base_controllers import BaseUserController
from mealie.schema.household.notebook import (
    NotebookCreate,
    NotebookDetail,
    NotebookHighlightCategory,
    NotebookNodeBulkMoveRequest,
    NotebookNodeCreate,
    NotebookNodeMoveRequest,
    NotebookNodeOut,
    NotebookNodeUpdate,
    NotebookRevisionOut,
    NotebookSearchResult,
    NotebookSummary,
    NotebookTOCChunk,
    NotebookTOCEntry,
    NotebookTOCRequest,
    NotebookTOCResponse,
    NotebookUpdate,
)
from mealie.schema.group.ai_providers import AIProviderOut
from mealie.schema.response.responses import ErrorResponse
from mealie.services.openai.openai import OpenAIService

router = APIRouter(prefix="/households/notebooks", tags=["Households: Notebooks"])

SPACE_RE = re.compile(r"\s+")
MAX_REVISIONS_PER_PAGE = 20
DEFAULT_HIGHLIGHT_CATEGORIES = [
    {"id": "important", "name": "Important", "color": "#fff59d"},
    {"id": "question", "name": "Question", "color": "#90caf9"},
    {"id": "idea", "name": "Idea", "color": "#a5d6a7"},
]


def _normalize_terms(values: list[str] | None) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        normalized = SPACE_RE.sub(" ", str(value).strip())[:100]
        key = normalized.casefold()
        if normalized and key not in seen:
            seen.add(key)
            result.append(normalized)
    return result[:100]


def _safe_json_loads(value: str, fallback: Any):
    try:
        parsed = json.loads(value or "")
    except (TypeError, ValueError):
        return fallback
    return parsed if isinstance(parsed, type(fallback)) else fallback


def _safe_json_dumps(value: Any, *, max_chars: int = 250_000) -> str:
    serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if len(serialized) > max_chars:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse.respond("Notebook settings are too large"),
        )
    return serialized


def _sanitize_html(value: str) -> str:
    if not value:
        return ""
    soup = BeautifulSoup(value[:5_000_000], "html.parser")
    for tag in soup.find_all(["script", "style", "iframe", "object", "embed", "form", "input", "button"]):
        tag.decompose()
    for tag in soup.find_all(True):
        for attribute in list(tag.attrs):
            attribute_name = str(attribute).lower()
            attribute_value = str(tag.attrs.get(attribute, "")).strip().lower()
            if attribute_name.startswith("on") or attribute_name in {"srcdoc", "formaction"}:
                del tag.attrs[attribute]
            elif attribute_name in {"href", "src", "xlink:href"} and attribute_value.startswith(
                ("javascript:", "vbscript:")
            ):
                del tag.attrs[attribute]
    return str(soup)


@controller(router)
class NotebookController(BaseUserController):
    def _notebook_or_404(self, notebook_id: UUID4) -> Notebook:
        notebook = self.session.execute(
            sa.select(Notebook).where(
                Notebook.id == notebook_id,
                Notebook.group_id == self.group_id,
                Notebook.user_id == self.user.id,
            )
        ).scalar_one_or_none()
        if notebook is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        return notebook

    def _node_or_404(self, node_id: UUID4, notebook_id: UUID4 | None = None) -> NotebookNode:
        statement = sa.select(NotebookNode).where(
            NotebookNode.id == node_id,
            NotebookNode.group_id == self.group_id,
            NotebookNode.user_id == self.user.id,
        )
        if notebook_id is not None:
            statement = statement.where(NotebookNode.notebook_id == notebook_id)
        node = self.session.execute(statement).scalar_one_or_none()
        if node is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        return node

    def _node_out(self, node: NotebookNode) -> NotebookNodeOut:
        raw_highlights = _safe_json_loads(node.highlight_categories_json, [])
        highlights: list[NotebookHighlightCategory] = []
        for item in raw_highlights:
            try:
                highlights.append(NotebookHighlightCategory.model_validate(item))
            except (TypeError, ValueError):
                continue
        return NotebookNodeOut(
            id=node.id,
            notebook_id=node.notebook_id,
            group_id=node.group_id,
            household_id=node.household_id,
            user_id=node.user_id,
            parent_id=node.parent_id,
            node_type=node.node_type,
            title=node.title,
            content_html=node.content_html,
            position=node.position,
            is_collapsed=node.is_collapsed,
            is_favorite=node.is_favorite,
            is_pinned=node.is_pinned,
            color=node.color,
            tags=_safe_json_loads(node.tags_json, []),
            categories=_safe_json_loads(node.categories_json, []),
            highlight_categories=highlights,
            settings=_safe_json_loads(node.settings_json, {}),
            content_version=node.content_version,
            created_at=node.created_at,
            updated_at=node.updated_at,
        )

    def _summary(self, notebook: Notebook, counts: dict[str, tuple[int, int]] | None = None) -> NotebookSummary:
        node_count, page_count = (counts or {}).get(str(notebook.id), (0, 0))
        return NotebookSummary(
            id=notebook.id,
            group_id=notebook.group_id,
            household_id=notebook.household_id,
            user_id=notebook.user_id,
            title=notebook.title,
            description=notebook.description,
            color=notebook.color,
            icon=notebook.icon,
            is_favorite=notebook.is_favorite,
            is_pinned=notebook.is_pinned,
            position=notebook.position,
            settings=_safe_json_loads(notebook.settings_json, {}),
            node_count=node_count,
            page_count=page_count,
            created_at=notebook.created_at,
            updated_at=notebook.updated_at,
        )

    def _counts(self, notebook_ids: list[UUID4]) -> dict[str, tuple[int, int]]:
        if not notebook_ids:
            return {}
        rows = self.session.execute(
            sa.select(
                NotebookNode.notebook_id,
                sa.func.count(NotebookNode.id),
                sa.func.sum(sa.case((NotebookNode.node_type == "page", 1), else_=0)),
            )
            .where(NotebookNode.notebook_id.in_(notebook_ids))
            .group_by(NotebookNode.notebook_id)
        ).all()
        return {str(notebook_id): (int(total or 0), int(pages or 0)) for notebook_id, total, pages in rows}

    def _validate_parent(
        self,
        notebook_id: UUID4,
        node_type: str,
        parent_id: UUID4 | None,
        moving_node_id: UUID4 | None = None,
    ) -> None:
        if parent_id is None:
            return
        parent = self._node_or_404(parent_id, notebook_id)
        allowed_parents = {
            "section_group": {"section_group"},
            "section": {"section_group"},
            "page": {"section", "page"},
        }
        if parent.node_type not in allowed_parents[node_type]:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("This node cannot be placed under the selected parent"),
            )
        if moving_node_id is None:
            return
        current_parent_id = parent.parent_id
        visited: set[str] = {str(parent.id)}
        while current_parent_id is not None:
            if str(current_parent_id) == str(moving_node_id):
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail=ErrorResponse.respond("A notebook node cannot be moved below itself"),
                )
            if str(current_parent_id) in visited:
                break
            visited.add(str(current_parent_id))
            ancestor = self._node_or_404(current_parent_id, notebook_id)
            current_parent_id = ancestor.parent_id

    def _apply_notebook(self, notebook: Notebook, data: NotebookCreate | NotebookUpdate) -> None:
        notebook.title = SPACE_RE.sub(" ", data.title.strip())[:255]
        notebook.description = (data.description or "").strip() or None
        notebook.color = data.color.strip()[:32]
        notebook.icon = data.icon.strip()[:64]
        notebook.is_favorite = data.is_favorite
        notebook.is_pinned = data.is_pinned
        notebook.position = data.position
        notebook.settings_json = _safe_json_dumps(data.settings)

    def _apply_node(self, node: NotebookNode, data: NotebookNodeCreate | NotebookNodeUpdate) -> bool:
        content_changed = False
        supplied = data.model_fields_set
        if "parent_id" in supplied:
            node.parent_id = data.parent_id
        if data.node_type is not None:
            node.node_type = data.node_type
        if data.title is not None:
            title = SPACE_RE.sub(" ", data.title.strip())[:255]
            content_changed = content_changed or title != node.title
            node.title = title
        if data.content_html is not None:
            content = _sanitize_html(data.content_html)
            content_changed = content_changed or content != node.content_html
            node.content_html = content
        for field_name in ("position", "is_collapsed", "is_favorite", "is_pinned", "color"):
            value = getattr(data, field_name, None)
            if value is not None:
                setattr(node, field_name, value)
        if data.tags is not None:
            node.tags_json = _safe_json_dumps(_normalize_terms(data.tags))
        if data.categories is not None:
            node.categories_json = _safe_json_dumps(_normalize_terms(data.categories))
        if data.highlight_categories is not None:
            node.highlight_categories_json = _safe_json_dumps(
                [category.model_dump(mode="json") for category in data.highlight_categories]
            )
        if data.settings is not None:
            settings_json = _safe_json_dumps(data.settings)
            content_changed = content_changed or settings_json != node.settings_json
            node.settings_json = settings_json
        return content_changed

    def _save_revision(self, node: NotebookNode) -> None:
        revision = NotebookRevision(
            node_id=node.id,
            user_id=self.user.id,
            title=node.title,
            content_html=node.content_html,
            settings_json=node.settings_json,
            content_version=node.content_version,
            session=self.session,
        )
        self.session.add(revision)
        self.session.flush()
        stale_ids = self.session.execute(
            sa.select(NotebookRevision.id)
            .where(NotebookRevision.node_id == node.id)
            .order_by(NotebookRevision.created_at.desc(), NotebookRevision.id.desc())
            .offset(MAX_REVISIONS_PER_PAGE)
        ).scalars().all()
        if stale_ids:
            self.session.execute(sa.delete(NotebookRevision).where(NotebookRevision.id.in_(stale_ids)))

    @staticmethod
    def _toc_provider_slots(openai_service: OpenAIService) -> list[AIProviderOut]:
        provider = openai_service.default_provider
        if provider is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("Configure a default AI provider before creating a table of contents"),
            )
        if not OpenAIService._is_gemini_provider_data(provider):
            return [provider]
        keys = OpenAIService._split_api_keys(provider.api_key)
        if not keys:
            return [provider]
        return [provider.model_copy(update={"api_key": key}) for key in keys]

    @staticmethod
    def _toc_page_text(node: NotebookNode) -> str:
        plain_text = SPACE_RE.sub(" ", BeautifulSoup(node.content_html or "", "html.parser").get_text(" ")).strip()
        return plain_text[:4_000]

    @staticmethod
    def _toc_html(entries: list[NotebookTOCEntry], language: str, notebook_id: UUID4) -> str:
        is_hebrew = language.lower().startswith("he")
        current_section = ""
        sections: list[str] = []
        for entry in entries:
            section_title = entry.section_title.strip() or ("דפים" if is_hebrew else "Pages")
            if section_title != current_section:
                if current_section:
                    sections.append("</ol></section>")
                current_section = section_title
                sections.append(f'<section class="notebook-toc-section"><h2>{escape(section_title)}</h2><ol>')
            link = f"/notebooks?focus=1&notebook={notebook_id}&page={escape(entry.node_id)}"
            summary = entry.summary.strip()
            summary_html = f"<small>{escape(summary)}</small>" if summary else ""
            sections.append(
                '<li><a href="'
                f'{link}"><strong>{escape(entry.title.strip())}</strong>{summary_html}</a></li>'
            )
        if current_section:
            sections.append("</ol></section>")
        return '<nav class="notebook-generated-toc">' + "".join(sections) + "</nav>"

    @router.get("", response_model=list[NotebookSummary])
    def get_all(self, search: str | None = Query(None, max_length=255)) -> list[NotebookSummary]:
        statement = sa.select(Notebook).where(
            Notebook.group_id == self.group_id,
            Notebook.user_id == self.user.id,
        )
        query = (search or "").strip()
        if query:
            pattern = f"%{query.replace('%', r'\%').replace('_', r'\_')}%"
            statement = statement.where(
                sa.or_(Notebook.title.ilike(pattern, escape="\\"), Notebook.description.ilike(pattern, escape="\\"))
            )
        notebooks = self.session.execute(
            statement.order_by(Notebook.is_pinned.desc(), Notebook.position.asc(), Notebook.updated_at.desc())
        ).scalars().all()
        counts = self._counts([item.id for item in notebooks])
        return [self._summary(item, counts) for item in notebooks]

    @router.post("", response_model=NotebookDetail, status_code=status.HTTP_201_CREATED)
    def create_one(self, data: NotebookCreate) -> NotebookDetail:
        notebook = Notebook(
            group_id=self.group_id,
            household_id=self.household_id,
            user_id=self.user.id,
            title=data.title,
            session=self.session,
        )
        self._apply_notebook(notebook, data)
        self.session.add(notebook)
        self.session.flush()
        nodes: list[NotebookNode] = []
        if data.create_starter_page:
            section = NotebookNode(
                notebook_id=notebook.id,
                group_id=self.group_id,
                household_id=self.household_id,
                user_id=self.user.id,
                node_type="section",
                title="Quick notes",
                position=0,
                session=self.session,
            )
            self.session.add(section)
            self.session.flush()
            page = NotebookNode(
                notebook_id=notebook.id,
                parent_id=section.id,
                group_id=self.group_id,
                household_id=self.household_id,
                user_id=self.user.id,
                node_type="page",
                title="Untitled page",
                position=0,
                highlight_categories_json=_safe_json_dumps(DEFAULT_HIGHLIGHT_CATEGORIES),
                settings_json=_safe_json_dumps({
                    "fontFamily": "Arial",
                    "fontSize": 16,
                    "lineHeight": 1.6,
                    "wordSpacing": 0,
                    "paragraphSpacing": 12,
                    "pageWidth": 980,
                    "textDirection": "auto",
                    "spellcheck": True,
                    "zoom": 100,
                }),
                session=self.session,
            )
            self.session.add(page)
            nodes.extend([section, page])
        self.session.commit()
        self.session.refresh(notebook)
        for node in nodes:
            self.session.refresh(node)
        return NotebookDetail(**self._summary(notebook, {str(notebook.id): (len(nodes), 1)}).model_dump(), nodes=[self._node_out(node) for node in nodes])

    @router.get("/search", response_model=list[NotebookSearchResult])
    def search_pages(
        self,
        query: str = Query(..., min_length=1, max_length=255),
        notebook_id: UUID4 | None = None,
        limit: int = Query(100, ge=1, le=200),
    ) -> list[NotebookSearchResult]:
        cleaned = query.strip()
        pattern = f"%{cleaned.replace('%', r'\%').replace('_', r'\_')}%"
        statement = (
            sa.select(NotebookNode, Notebook.title)
            .join(Notebook, Notebook.id == NotebookNode.notebook_id)
            .where(
                NotebookNode.group_id == self.group_id,
                NotebookNode.user_id == self.user.id,
                sa.or_(
                    NotebookNode.title.ilike(pattern, escape="\\"),
                    NotebookNode.content_html.ilike(pattern, escape="\\"),
                    NotebookNode.tags_json.ilike(pattern, escape="\\"),
                    NotebookNode.categories_json.ilike(pattern, escape="\\"),
                ),
            )
            .order_by(NotebookNode.updated_at.desc())
            .limit(limit)
        )
        if notebook_id is not None:
            self._notebook_or_404(notebook_id)
            statement = statement.where(NotebookNode.notebook_id == notebook_id)
        rows = self.session.execute(statement).all()
        results: list[NotebookSearchResult] = []
        for node, notebook_title in rows:
            plain_text = SPACE_RE.sub(" ", BeautifulSoup(node.content_html or "", "html.parser").get_text(" ")).strip()
            results.append(NotebookSearchResult(
                notebook_id=node.notebook_id,
                notebook_title=notebook_title,
                node_id=node.id,
                node_title=node.title,
                node_type=node.node_type,
                excerpt=plain_text[:260],
                updated_at=node.updated_at,
            ))
        return results

    @router.get("/{notebook_id}", response_model=NotebookDetail)
    def get_one(self, notebook_id: UUID4) -> NotebookDetail:
        notebook = self._notebook_or_404(notebook_id)
        nodes = self.session.execute(
            sa.select(NotebookNode)
            .where(NotebookNode.notebook_id == notebook.id, NotebookNode.user_id == self.user.id)
            .order_by(NotebookNode.position.asc(), NotebookNode.created_at.asc())
        ).scalars().all()
        page_count = sum(node.node_type == "page" for node in nodes)
        return NotebookDetail(
            **self._summary(notebook, {str(notebook.id): (len(nodes), page_count)}).model_dump(),
            nodes=[self._node_out(node) for node in nodes],
        )

    @router.post("/{notebook_id}/generate-toc", response_model=NotebookTOCResponse)
    async def generate_toc(self, notebook_id: UUID4, data: NotebookTOCRequest) -> NotebookTOCResponse:
        notebook = self._notebook_or_404(notebook_id)
        pages = self.session.execute(
            sa.select(NotebookNode)
            .where(
                NotebookNode.notebook_id == notebook.id,
                NotebookNode.user_id == self.user.id,
                NotebookNode.node_type == "page",
            )
            .order_by(NotebookNode.position.asc(), NotebookNode.created_at.asc())
        ).scalars().all()
        pages = [page for page in pages if not _safe_json_loads(page.settings_json, {}).get("generatedToc")]
        if not pages:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("Add at least one notebook page before creating a table of contents"),
            )

        openai_service = OpenAIService(self.repos)
        providers = self._toc_provider_slots(openai_service)
        chunks = [pages[index : index + data.pages_per_chunk] for index in range(0, len(pages), data.pages_per_chunk)]
        worker_count = min(len(providers), len(chunks))
        prompt = (
            "You are organizing a personal notebook into a professional table of contents. "
            "Return exactly one entry for every page supplied, preserve the exact node_id, keep the original page "
            "order, group related pages under concise section titles, and write titles and summaries in the requested "
            "language. Do not invent subjects that are not supported by the page text."
        )

        async def analyze_chunk(chunk: list[NotebookNode], provider: AIProviderOut) -> NotebookTOCChunk | None:
            page_blocks = []
            for page in chunk:
                page_blocks.append(
                    f"NODE_ID: {page.id}\nCURRENT_TITLE: {page.title}\nCONTENT: {self._toc_page_text(page)}"
                )
            message = (
                f"Notebook title: {notebook.title}\nRequested language: {data.language}\n\n"
                + "\n\n--- PAGE ---\n".join(page_blocks)
            )
            return await openai_service.get_response(
                prompt,
                message,
                response_schema=NotebookTOCChunk,
                provider=provider,
            )

        responses: list[NotebookTOCChunk | Exception | None] = [None] * len(chunks)

        async def worker(slot: int) -> None:
            provider = providers[slot]
            for index in range(slot, len(chunks), worker_count):
                try:
                    responses[index] = await analyze_chunk(chunks[index], provider)
                except Exception as error:  # A failed chunk falls back without stopping the remaining notebook.
                    responses[index] = error

        await asyncio.gather(*(worker(slot) for slot in range(worker_count)))
        entries: list[NotebookTOCEntry] = []
        for chunk, response in zip(chunks, responses, strict=True):
            response_entries = response.entries if isinstance(response, NotebookTOCChunk) else []
            entries_by_id = {entry.node_id: entry for entry in response_entries}
            for page in chunk:
                entry = entries_by_id.get(str(page.id))
                if entry is None:
                    entry = NotebookTOCEntry(
                        node_id=str(page.id),
                        title=page.title,
                        section_title="דפים" if data.language.lower().startswith("he") else "Pages",
                        summary=self._toc_page_text(page)[:180],
                    )
                entries.append(entry)

        toc_title = "תוכן עניינים" if data.language.lower().startswith("he") else "Table of Contents"
        toc_html = self._toc_html(entries, data.language, notebook.id)
        existing_toc = next(
            (
                page
                for page in self.session.execute(
                    sa.select(NotebookNode).where(
                        NotebookNode.notebook_id == notebook.id,
                        NotebookNode.node_type == "page",
                    )
                ).scalars()
                if _safe_json_loads(page.settings_json, {}).get("generatedToc")
            ),
            None,
        )
        toc_settings = {
            "generatedToc": True,
            "tocEntries": [
                {
                    "nodeId": entry.node_id,
                    "title": entry.title,
                    "sectionTitle": entry.section_title,
                    "summary": entry.summary,
                }
                for entry in entries
            ],
            "fontFamily": "Arial",
            "fontSize": 16,
            "lineHeight": 1.6,
            "wordSpacing": 0,
            "paragraphSpacing": 12,
            "pageWidth": 980,
            "textDirection": "rtl" if data.language.lower().startswith("he") else "ltr",
            "spellcheck": True,
            "zoom": 100,
        }
        if existing_toc is None:
            existing_toc = NotebookNode(
                notebook_id=notebook.id,
                group_id=self.group_id,
                household_id=self.household_id,
                user_id=self.user.id,
                node_type="page",
                title=toc_title,
                content_html=toc_html,
                position=0,
                is_pinned=True,
                settings_json=_safe_json_dumps(toc_settings),
                highlight_categories_json=_safe_json_dumps(DEFAULT_HIGHLIGHT_CATEGORIES),
                session=self.session,
            )
        else:
            self._save_revision(existing_toc)
            existing_toc.title = toc_title
            existing_toc.content_html = toc_html
            existing_toc.settings_json = _safe_json_dumps(toc_settings)
            existing_toc.is_pinned = True
            existing_toc.content_version += 1
        self.session.add(existing_toc)
        self.session.commit()
        self.session.refresh(existing_toc)
        return NotebookTOCResponse(
            toc_node=self._node_out(existing_toc),
            chunk_count=len(chunks),
            provider_count=worker_count,
        )

    @router.put("/{notebook_id}", response_model=NotebookSummary)
    def update_one(self, notebook_id: UUID4, data: NotebookUpdate) -> NotebookSummary:
        notebook = self._notebook_or_404(notebook_id)
        self._apply_notebook(notebook, data)
        self.session.add(notebook)
        self.session.commit()
        self.session.refresh(notebook)
        return self._summary(notebook, self._counts([notebook.id]))

    @router.delete("/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_one(self, notebook_id: UUID4) -> None:
        notebook = self._notebook_or_404(notebook_id)
        self.session.delete(notebook)
        self.session.commit()

    @router.post("/{notebook_id}/nodes", response_model=NotebookNodeOut, status_code=status.HTTP_201_CREATED)
    def create_node(self, notebook_id: UUID4, data: NotebookNodeCreate) -> NotebookNodeOut:
        self._notebook_or_404(notebook_id)
        self._validate_parent(notebook_id, data.node_type, data.parent_id)
        node = NotebookNode(
            notebook_id=notebook_id,
            group_id=self.group_id,
            household_id=self.household_id,
            user_id=self.user.id,
            node_type=data.node_type,
            title=data.title,
            session=self.session,
        )
        self._apply_node(node, data)
        if data.node_type == "page" and not data.highlight_categories:
            node.highlight_categories_json = _safe_json_dumps(DEFAULT_HIGHLIGHT_CATEGORIES)
        self.session.add(node)
        self.session.commit()
        self.session.refresh(node)
        return self._node_out(node)

    @router.put("/{notebook_id}/nodes/{node_id}", response_model=NotebookNodeOut)
    def update_node(self, notebook_id: UUID4, node_id: UUID4, data: NotebookNodeUpdate) -> NotebookNodeOut:
        self._notebook_or_404(notebook_id)
        node = self._node_or_404(node_id, notebook_id)
        if data.expected_version is not None and data.expected_version != node.content_version:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail=ErrorResponse.respond("This page was updated elsewhere. Reload it before saving again."),
            )
        target_type = data.node_type or node.node_type
        target_parent = data.parent_id if "parent_id" in data.model_fields_set else node.parent_id
        self._validate_parent(notebook_id, target_type, target_parent, node.id)
        before = (node.title, node.content_html, node.settings_json)
        changed = self._apply_node(node, data)
        if changed and node.node_type == "page":
            old_title, old_content, old_settings = before
            current_title, current_content, current_settings = node.title, node.content_html, node.settings_json
            node.title, node.content_html, node.settings_json = old_title, old_content, old_settings
            self._save_revision(node)
            node.title, node.content_html, node.settings_json = current_title, current_content, current_settings
            node.content_version += 1
        self.session.add(node)
        self.session.commit()
        self.session.refresh(node)
        return self._node_out(node)

    @router.post("/{notebook_id}/nodes/{node_id}/move", response_model=NotebookNodeOut)
    def move_node(
        self,
        notebook_id: UUID4,
        node_id: UUID4,
        data: NotebookNodeMoveRequest,
    ) -> NotebookNodeOut:
        self._notebook_or_404(notebook_id)
        node = self._node_or_404(node_id, notebook_id)
        self._validate_parent(notebook_id, node.node_type, data.parent_id, node.id)
        node.parent_id = data.parent_id
        node.position = data.position
        self.session.add(node)
        self.session.commit()
        self.session.refresh(node)
        return self._node_out(node)

    @router.post("/{notebook_id}/nodes/move-bulk", response_model=list[NotebookNodeOut])
    def move_nodes(self, notebook_id: UUID4, data: NotebookNodeBulkMoveRequest) -> list[NotebookNodeOut]:
        self._notebook_or_404(notebook_id)
        nodes = [self._node_or_404(node_id, notebook_id) for node_id in data.node_ids]
        for offset, node in enumerate(nodes):
            self._validate_parent(notebook_id, node.node_type, data.parent_id, node.id)
            node.parent_id = data.parent_id
            node.position = data.start_position + offset
            self.session.add(node)
        self.session.commit()
        return [self._node_out(node) for node in nodes]

    @router.delete("/{notebook_id}/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_node(self, notebook_id: UUID4, node_id: UUID4) -> None:
        self._notebook_or_404(notebook_id)
        node = self._node_or_404(node_id, notebook_id)
        all_nodes = self.session.execute(
            sa.select(NotebookNode.id, NotebookNode.parent_id).where(NotebookNode.notebook_id == notebook_id)
        ).all()
        children: dict[str, list[UUID4]] = defaultdict(list)
        for child_id, parent_id in all_nodes:
            if parent_id is not None:
                children[str(parent_id)].append(child_id)
        to_delete: list[UUID4] = []
        queue: deque[UUID4] = deque([node.id])
        visited: set[str] = set()
        while queue:
            current = queue.popleft()
            if str(current) in visited:
                continue
            visited.add(str(current))
            to_delete.append(current)
            queue.extend(children.get(str(current), []))
        self.session.execute(sa.delete(NotebookRevision).where(NotebookRevision.node_id.in_(to_delete)))
        self.session.execute(sa.delete(NotebookNode).where(NotebookNode.id.in_(to_delete)))
        self.session.commit()

    @router.get("/{notebook_id}/nodes/{node_id}/revisions", response_model=list[NotebookRevisionOut])
    def get_revisions(self, notebook_id: UUID4, node_id: UUID4) -> list[NotebookRevisionOut]:
        self._notebook_or_404(notebook_id)
        self._node_or_404(node_id, notebook_id)
        revisions = self.session.execute(
            sa.select(NotebookRevision)
            .where(NotebookRevision.node_id == node_id)
            .order_by(NotebookRevision.created_at.desc(), NotebookRevision.id.desc())
            .limit(MAX_REVISIONS_PER_PAGE)
        ).scalars().all()
        return [NotebookRevisionOut(
            id=item.id,
            node_id=item.node_id,
            user_id=item.user_id,
            title=item.title,
            content_html=item.content_html,
            settings=_safe_json_loads(item.settings_json, {}),
            content_version=item.content_version,
            created_at=item.created_at,
        ) for item in revisions]

    @router.post("/{notebook_id}/nodes/{node_id}/revisions/{revision_id}/restore", response_model=NotebookNodeOut)
    def restore_revision(
        self,
        notebook_id: UUID4,
        node_id: UUID4,
        revision_id: UUID4,
    ) -> NotebookNodeOut:
        self._notebook_or_404(notebook_id)
        node = self._node_or_404(node_id, notebook_id)
        revision = self.session.execute(
            sa.select(NotebookRevision).where(
                NotebookRevision.id == revision_id,
                NotebookRevision.node_id == node.id,
            )
        ).scalar_one_or_none()
        if revision is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        self._save_revision(node)
        node.title = revision.title
        node.content_html = revision.content_html
        node.settings_json = revision.settings_json
        node.content_version += 1
        self.session.add(node)
        self.session.commit()
        self.session.refresh(node)
        return self._node_out(node)
