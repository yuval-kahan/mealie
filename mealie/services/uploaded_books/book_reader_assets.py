# ruff: noqa: E501

import html
import json

BOOK_READER_ID_PLACEHOLDER = "__MEALIE_BOOK_READER_ID__"


def book_reader_labels(rtl: bool) -> dict[str, str]:
    if rtl:
        return {
            "settings": "הגדרות קריאה",
            "open_settings": "פתח הגדרות קריאה",
            "close_settings": "מזער הגדרות קריאה",
            "font_size": "גודל גופן",
            "font_family": "סגנון גופן",
            "font_serif": "ספרותי",
            "font_sans": "נקי",
            "font_dyslexic": "נגיש",
            "line_height": "רווח בין שורות",
            "word_spacing": "רווח בין מילים",
            "page_width": "רוחב עמוד",
            "enable_ask_ai": "הצג ASK AI בעת סימון טקסט",
            "answer_length": "אורך תשובת AI",
            "answer_short": "קצרה",
            "answer_medium": "בינונית",
            "answer_long": "ארוכה ומפורטת",
            "show_ai_hover": "הצג הסבר AI בבועה במעבר עכבר",
            "ask_question": "שאלה על הטקסט המסומן (אופציונלי)",
            "default_question": "הסבר את הטקסט המסומן בשפה פשוטה וברורה",
            "ask_ai": "ASK AI",
            "asking_ai": "שואל את ה-AI...",
            "ask_failed": "ה-AI לא הצליח להסביר את הטקסט המסומן",
            "target_language": "Hebrew",
            "reset": "איפוס",
            "annotations": "הערות ומרקרים",
            "open_annotations": "פתח הערות ומרקרים",
            "close_annotations": "מזער הערות ומרקרים",
            "notes": "הערות",
            "highlights": "מרקרים",
            "note_title": "כותרת ההערה",
            "note_text": "כתוב הערה לפרק או לעמוד הנוכחי",
            "add_note": "הוסף הערה",
            "add_highlight": "מרקר את הטקסט המסומן",
            "no_annotations": "עדיין אין הערות או מרקרים",
            "delete": "מחק",
            "chapter_progress": "פרקים שנקראו",
            "chapter_complete": "סמן פרק כנקרא",
            "save_failed": "השמירה באתר נכשלה; השינויים נשמרו זמנית בדפדפן",
        }
    return {
        "settings": "Reading settings",
        "open_settings": "Open reading settings",
        "close_settings": "Collapse reading settings",
        "font_size": "Font size",
        "font_family": "Font family",
        "font_serif": "Serif",
        "font_sans": "Sans serif",
        "font_dyslexic": "Accessible",
        "line_height": "Line spacing",
        "word_spacing": "Word spacing",
        "page_width": "Page width",
        "enable_ask_ai": "Show ASK AI for selected text",
        "answer_length": "AI answer length",
        "answer_short": "Short",
        "answer_medium": "Medium",
        "answer_long": "Long and detailed",
        "show_ai_hover": "Show the AI explanation in a hover bubble",
        "ask_question": "Question about the selected text (optional)",
        "default_question": "Explain the selected text in clear, simple language",
        "ask_ai": "ASK AI",
        "asking_ai": "Asking AI...",
        "ask_failed": "AI could not explain the selected text",
        "target_language": "English",
        "reset": "Reset",
        "annotations": "Notes and highlights",
        "open_annotations": "Open notes and highlights",
        "close_annotations": "Collapse notes and highlights",
        "notes": "Notes",
        "highlights": "Highlights",
        "note_title": "Note title",
        "note_text": "Write a note for the current chapter or page",
        "add_note": "Add note",
        "add_highlight": "Highlight selected text",
        "no_annotations": "No notes or highlights yet",
        "delete": "Delete",
        "chapter_progress": "Chapters read",
        "chapter_complete": "Mark chapter as read",
        "save_failed": "Saving to Mealie failed; changes were kept temporarily in this browser",
    }


def book_reader_css(direction: str) -> str:
    return r"""
    :root {
      --reader-font-size: 18px;
      --reader-line-height: 1.75;
      --reader-word-spacing: 0px;
      --reader-page-width: 980px;
      --reader-font-family: Georgia, "Times New Roman", serif;
    }
    .book-shell { max-width: var(--reader-page-width) !important; }
    .book-page pre, .reader-text, .recipe, .chapter {
      font-family: var(--reader-font-family) !important;
      font-size: var(--reader-font-size);
      line-height: var(--reader-line-height);
      word-spacing: var(--reader-word-spacing);
    }
    .toc-row { align-items: center; display: flex; gap: 6px; min-width: 0; }
    .toc-row > a { flex: 1; min-width: 0; }
    .chapter-checkbox {
      accent-color: #2e7d32;
      cursor: pointer;
      flex: 0 0 auto;
      height: 17px;
      width: 17px;
    }
    .chapter-checkbox:focus-visible { outline: 2px solid #2e7d32; outline-offset: 2px; }
    .reader-tools {
      align-items: stretch;
      border-bottom: 1px solid #dfd4c4;
      display: flex;
      flex: 0 0 auto;
      flex-direction: column;
      gap: 6px;
      max-height: min(62vh, 640px);
      pointer-events: auto;
      position: relative;
      width: 100%;
      z-index: 1;
    }
    .reader-tools__toggles {
      align-items: center;
      box-sizing: border-box;
      display: flex;
      gap: 6px;
      justify-content: flex-start;
      padding: 6px;
      width: 100%;
    }
    .reader-panel {
      background: rgba(255, 253, 248, 0.98);
      border: 1px solid #d9cebc;
      border-radius: 6px;
      box-sizing: border-box;
      box-shadow: 0 8px 26px rgba(61, 45, 29, 0.16);
      direction: __DIRECTION__;
      font-family: Arial, Helvetica, sans-serif;
      overflow: hidden;
      pointer-events: auto;
      position: relative;
      margin: 0 6px 6px;
      width: calc(100% - 12px);
    }
    .reader-annotations { max-height: min(52vh, 560px); }
    .reader-panel.is-collapsed { display: none; }
    .reader-panel__header {
      align-items: center;
      display: flex;
      gap: 8px;
      min-height: 46px;
      padding: 6px;
    }
    .reader-panel__header strong { flex: 1; font-size: 14px; }
    .reader-panel__toggle, .reader-tool-toggle {
      align-items: center;
      background: transparent;
      border: 0;
      border-radius: 4px;
      color: #8f3f1f;
      cursor: pointer;
      display: inline-flex;
      flex: 0 0 34px;
      font-size: 22px;
      height: 34px;
      justify-content: center;
      width: 34px;
    }
    .reader-tool-toggle {
      background: rgba(255, 253, 248, 0.98);
      border: 1px solid #d9cebc;
      box-shadow: 0 4px 14px rgba(61, 45, 29, 0.14);
    }
    .reader-panel__toggle:hover, .reader-panel__toggle:focus-visible,
    .reader-tool-toggle:hover, .reader-tool-toggle:focus-visible,
    .reader-tool-toggle[aria-expanded="true"],
    .reader-action:hover, .reader-action:focus-visible {
      background: #f1e5d6;
      outline: 2px solid #b95f35;
      outline-offset: 1px;
    }
    .reader-panel__body {
      border-top: 1px solid #dfd4c4;
      max-height: min(34vh, 420px);
      overflow: auto;
      overscroll-behavior: contain;
      padding: 12px;
      scrollbar-gutter: stable;
    }
    .reader-field { display: grid; gap: 5px; margin-bottom: 12px; }
    .reader-field label { font-size: 12px; font-weight: 700; }
    .reader-field input[type="range"], .reader-field select,
    .reader-field input[type="text"], .reader-field textarea { width: 100%; }
    .reader-field select, .reader-field input[type="text"], .reader-field textarea {
      background: #fff;
      border: 1px solid #cfc2af;
      border-radius: 4px;
      color: #211914;
      font: inherit;
      padding: 8px;
    }
    .reader-field textarea { min-height: 76px; resize: vertical; }
    .reader-range-value { color: #7d4a30; font-size: 12px; font-weight: 700; }
    .reader-actions { display: flex; flex-wrap: wrap; gap: 8px; }
    .reader-action {
      background: #fff8ef;
      border: 1px solid #d7b894;
      border-radius: 4px;
      color: #7f3418;
      cursor: pointer;
      font: inherit;
      font-size: 12px;
      font-weight: 700;
      padding: 7px 9px;
    }
    .reader-filters { display: flex; gap: 14px; margin-bottom: 10px; }
    .reader-filters label { align-items: center; display: flex; font-size: 12px; gap: 5px; }
    .reader-annotation-list { list-style: none; margin: 12px 0 0; padding: 0; }
    .reader-annotation-list li {
      border-top: 1px solid #eee4d5;
      display: grid;
      gap: 4px;
      grid-template-columns: 1fr auto;
      padding: 9px 0;
    }
    .reader-annotation-jump {
      background: transparent;
      border: 0;
      color: #2f261f;
      cursor: pointer;
      font: inherit;
      min-width: 0;
      padding: 0;
      text-align: start;
    }
    .reader-annotation-jump strong, .reader-annotation-jump span {
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .reader-annotation-jump span { color: #6d6157; font-size: 11px; }
    .reader-annotation-delete {
      background: transparent;
      border: 0;
      color: #a33131;
      cursor: pointer;
      font-size: 18px;
    }
    .reader-empty { color: #75695e; font-size: 12px; padding: 12px 0; text-align: center; }
    .reader-save-warning { color: #9b3f21; font-size: 11px; margin-top: 9px; }
    .reader-ai-answer {
      color: #4f4339;
      display: -webkit-box;
      font-size: 11px;
      line-height: 1.45;
      margin-top: 4px;
      overflow: hidden;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 3;
      white-space: normal;
    }
    .reader-ai-tooltip {
      background: rgba(38, 31, 25, 0.97);
      border: 1px solid rgba(255, 255, 255, 0.18);
      border-radius: 5px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.24);
      color: #fff;
      direction: __DIRECTION__;
      font: 13px/1.55 Arial, Helvetica, sans-serif;
      max-height: min(42vh, 340px);
      max-width: min(420px, calc(100vw - 24px));
      overflow: auto;
      padding: 10px 12px;
      pointer-events: none;
      position: fixed;
      white-space: pre-wrap;
      z-index: 9999;
    }
    .reader-ai-tooltip[hidden] { display: none; }
    ::highlight(mealie-reader-highlights) { background: #ffe36a; color: inherit; }
    .progress-chapters { margin-top: 8px; }
    .progress-chapters__row { display: flex; font-size: 12px; justify-content: space-between; }
    .progress-chapters__fill { background: #2e7d32; }
    @media (max-width: 720px) {
      .reader-tools { max-height: min(58vh, 560px); }
      .reader-panel { max-width: calc(100% - 12px); }
    }
    @media print { .reader-tools { display: none; } }
    """.replace("__DIRECTION__", direction)


def book_reader_panels(labels: dict[str, str]) -> str:
    escaped = {key: html.escape(value) for key, value in labels.items()}
    return f"""
  <div class="reader-tools">
  <div class="reader-tools__toggles" aria-label="{escaped['settings']}">
    <button class="reader-tool-toggle" id="readerSettingsToggle" type="button"
      aria-controls="readerSettings" aria-expanded="false" title="{escaped['open_settings']}">Aa</button>
    <button class="reader-tool-toggle" id="readerAnnotationsToggle" type="button"
      aria-controls="readerAnnotations" aria-expanded="false" title="{escaped['open_annotations']}">✎</button>
  </div>
  <aside class="reader-panel reader-settings is-collapsed" id="readerSettings" aria-label="{escaped['settings']}">
    <div class="reader-panel__header">
      <strong>{escaped['settings']}</strong>
    </div>
    <div class="reader-panel__body">
      <div class="reader-field"><label for="readerFontSize">{escaped['font_size']}</label>
        <input id="readerFontSize" type="range" min="12" max="36" step="1">
        <span class="reader-range-value" id="readerFontSizeValue"></span></div>
      <div class="reader-field"><label for="readerFontFamily">{escaped['font_family']}</label>
        <select id="readerFontFamily">
          <option value="serif">{escaped['font_serif']}</option>
          <option value="sans-serif">{escaped['font_sans']}</option>
          <option value="dyslexic">{escaped['font_dyslexic']}</option>
        </select></div>
      <div class="reader-field"><label for="readerLineHeight">{escaped['line_height']}</label>
        <input id="readerLineHeight" type="range" min="1.2" max="2.6" step="0.05">
        <span class="reader-range-value" id="readerLineHeightValue"></span></div>
      <div class="reader-field"><label for="readerWordSpacing">{escaped['word_spacing']}</label>
        <input id="readerWordSpacing" type="range" min="0" max="12" step="0.5">
        <span class="reader-range-value" id="readerWordSpacingValue"></span></div>
      <div class="reader-field"><label for="readerPageWidth">{escaped['page_width']}</label>
        <input id="readerPageWidth" type="range" min="600" max="1500" step="20">
        <span class="reader-range-value" id="readerPageWidthValue"></span></div>
      <div class="reader-field"><label><input id="readerEnableAskAi" type="checkbox"> {escaped['enable_ask_ai']}</label></div>
      <div class="reader-field"><label for="readerAiLength">{escaped['answer_length']}</label>
        <select id="readerAiLength">
          <option value="short">{escaped['answer_short']}</option>
          <option value="medium">{escaped['answer_medium']}</option>
          <option value="long">{escaped['answer_long']}</option>
        </select></div>
      <div class="reader-field"><label><input id="readerShowAiHover" type="checkbox"> {escaped['show_ai_hover']}</label></div>
      <button class="reader-action" id="readerReset" type="button">{escaped['reset']}</button>
    </div>
  </aside>
  <aside class="reader-panel reader-annotations is-collapsed" id="readerAnnotations" aria-label="{escaped['annotations']}">
    <div class="reader-panel__header">
      <strong>{escaped['annotations']}</strong>
    </div>
    <div class="reader-panel__body">
      <div class="reader-filters">
        <label><input id="readerShowNotes" type="checkbox" checked> {escaped['notes']}</label>
        <label><input id="readerShowHighlights" type="checkbox" checked> {escaped['highlights']}</label>
      </div>
      <div class="reader-field"><label for="readerNoteTitle">{escaped['note_title']}</label>
        <input id="readerNoteTitle" type="text" maxlength="200"></div>
      <div class="reader-field"><label for="readerNoteText">{escaped['note_text']}</label>
        <textarea id="readerNoteText" maxlength="4000"></textarea></div>
      <div class="reader-actions">
        <button class="reader-action" id="readerAddNote" type="button">{escaped['add_note']}</button>
        <button class="reader-action" id="readerAddHighlight" type="button">{escaped['add_highlight']}</button>
      </div>
      <div class="reader-field" id="readerAskAiFields">
        <label for="readerAiQuestion">{escaped['ask_question']}</label>
        <input id="readerAiQuestion" type="text" maxlength="1000">
        <button class="reader-action" id="readerAskAi" type="button" disabled>{escaped['ask_ai']}</button>
      </div>
      <p class="reader-save-warning" id="readerSaveWarning" hidden>{escaped['save_failed']}</p>
      <p class="reader-save-warning" id="readerAiWarning" hidden>{escaped['ask_failed']}</p>
      <div class="reader-empty" id="readerAnnotationEmpty">{escaped['no_annotations']}</div>
      <ul class="reader-annotation-list" id="readerAnnotationList"></ul>
    </div>
  </aside>
  </div>
  <div class="reader-ai-tooltip" id="readerAiTooltip" role="tooltip" hidden></div>
    """


def book_reader_script(labels: dict[str, str]) -> str:
    labels_json = json.dumps(labels, ensure_ascii=False).replace("</", "<\\/")
    script = r"""
  <script>
    (() => {
      "use strict";
      const bookId = "__BOOK_ID__";
      if (!bookId || bookId.startsWith("__MEALIE_")) return;
      const labels = __LABELS__;
      const endpoint = `/api/households/uploaded-books/${encodeURIComponent(bookId)}/reading-state`;
      const askAiEndpoint = `/api/households/uploaded-books/${encodeURIComponent(bookId)}/ask-ai`;
      const storageKey = `mealieBookReader:${bookId}`;
      const defaults = {
        currentPage: 0, currentPageIndex: 0, currentChapterId: null, readingPercent: 0,
        completedChapters: [], totalChapters: 0, notes: [], highlights: [],
        preferences: {
          fontSize: 18, fontFamily: "serif", lineHeight: 1.75, wordSpacing: 0, pageWidth: 980,
          enableAskAi: true, aiAnswerLength: "short", showAiHover: true,
        }
      };
      const el = (id) => document.getElementById(id);
      const settings = el("readerSettings");
      const annotations = el("readerAnnotations");
      const warning = el("readerSaveWarning");
      const chapterBoxes = [...document.querySelectorAll(".chapter-checkbox[data-chapter-id]")];
      const chapterRows = [...new Map(chapterBoxes.map(box => [box.dataset.chapterId, {
        id: box.dataset.chapterId,
        order: Number(box.dataset.chapterOrder || 0),
      }])).values()].sort((a, b) => a.order - b.order);
      let state = structuredClone(defaults);
      let saveTimer = 0;
      let requestController = null;
      let aiRequestController = null;
      let lastSelection = null;
      let annotationTimer = 0;
      let hoverFrame = 0;
      let aiHoverRanges = [];
      let destroyed = false;

      const clamp = (value, min, max, fallback) => {
        const parsed = Number(value);
        return Number.isFinite(parsed) ? Math.min(max, Math.max(min, parsed)) : fallback;
      };
      const uniqueStrings = (values, max = 1000) => [...new Set(
        Array.isArray(values) ? values.filter(value => typeof value === "string" && value.length <= 160) : []
      )].slice(0, max);
      const normalizeState = (value) => ({
        ...structuredClone(defaults),
        ...(value && typeof value === "object" ? value : {}),
        currentPage: clamp(value?.currentPage ?? value?.current_page, 0, 100000, 0),
        currentPageIndex: clamp(value?.currentPageIndex ?? value?.current_page_index, 0, 100000, 0),
        currentChapterId: value?.currentChapterId ?? value?.current_chapter_id ?? null,
        readingPercent: clamp(value?.readingPercent ?? value?.reading_percent, 0, 100, 0),
        completedChapters: uniqueStrings(value?.completedChapters ?? value?.completed_chapters),
        totalChapters: clamp(value?.totalChapters ?? value?.total_chapters, 0, 1000, chapterRows.length),
        notes: (Array.isArray(value?.notes) ? value.notes : []).slice(0, 500),
        highlights: (Array.isArray(value?.highlights) ? value.highlights : []).slice(0, 500),
        preferences: {
          ...defaults.preferences,
          ...(value?.preferences && typeof value.preferences === "object" ? value.preferences : {}),
        },
      });
      const readLocal = () => {
        try { return normalizeState(JSON.parse(localStorage.getItem(storageKey) || "null")); }
        catch (_error) { return structuredClone(defaults); }
      };
      const writeLocal = () => {
        try { localStorage.setItem(storageKey, JSON.stringify(state)); }
        catch (_error) { /* private mode or quota limits are non-fatal */ }
      };
      const payload = () => ({
        currentPage: state.currentPage,
        currentPageIndex: state.currentPageIndex,
        currentChapterId: state.currentChapterId,
        readingPercent: state.readingPercent,
        completedChapters: uniqueStrings(state.completedChapters),
        totalChapters: chapterRows.length,
        notes: state.notes.slice(0, 500),
        highlights: state.highlights.slice(0, 500),
        preferences: state.preferences,
      });
      const saveNow = async () => {
        if (destroyed) return;
        window.clearTimeout(saveTimer);
        saveTimer = 0;
        writeLocal();
        if (requestController) requestController.abort();
        const controller = new AbortController();
        requestController = controller;
        try {
          const response = await fetch(endpoint, {
            method: "PUT", credentials: "same-origin",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload()), signal: controller.signal,
          });
          if (!response.ok) throw new Error(String(response.status));
          warning.hidden = true;
        }
        catch (error) {
          if (error?.name !== "AbortError") warning.hidden = false;
        }
        finally {
          if (requestController === controller) requestController = null;
        }
      };
      const scheduleSave = () => {
        writeLocal();
        window.clearTimeout(saveTimer);
        saveTimer = window.setTimeout(saveNow, 550);
      };
      const loadState = async () => {
        state = readLocal();
        const controller = new AbortController();
        try {
          requestController = controller;
          const response = await fetch(endpoint, { credentials: "same-origin", signal: controller.signal });
          if (response.ok) state = normalizeState(await response.json());
        }
        catch (_error) { /* local state remains available offline */ }
        finally {
          if (requestController === controller) requestController = null;
        }
      };

      const fontFamilies = {
        serif: 'Georgia, "Times New Roman", serif',
        "sans-serif": 'Arial, Helvetica, sans-serif',
        dyslexic: '"OpenDyslexic", "Comic Sans MS", Arial, sans-serif',
      };
      const applyPreferences = () => {
        const prefs = state.preferences;
        prefs.fontSize = clamp(prefs.fontSize, 12, 36, 18);
        prefs.fontFamily = fontFamilies[prefs.fontFamily] ? prefs.fontFamily : "serif";
        prefs.lineHeight = clamp(prefs.lineHeight, 1.2, 2.6, 1.75);
        prefs.wordSpacing = clamp(prefs.wordSpacing, 0, 12, 0);
        prefs.pageWidth = clamp(prefs.pageWidth, 600, 1500, 980);
        prefs.enableAskAi = prefs.enableAskAi !== false;
        prefs.aiAnswerLength = ["short", "medium", "long"].includes(prefs.aiAnswerLength)
          ? prefs.aiAnswerLength : "short";
        prefs.showAiHover = prefs.showAiHover !== false;
        const root = document.documentElement.style;
        root.setProperty("--reader-font-size", `${prefs.fontSize}px`);
        root.setProperty("--reader-font-family", fontFamilies[prefs.fontFamily]);
        root.setProperty("--reader-line-height", String(prefs.lineHeight));
        root.setProperty("--reader-word-spacing", `${prefs.wordSpacing}px`);
        root.setProperty("--reader-page-width", `${prefs.pageWidth}px`);
        el("readerFontSize").value = String(prefs.fontSize);
        el("readerFontFamily").value = prefs.fontFamily;
        el("readerLineHeight").value = String(prefs.lineHeight);
        el("readerWordSpacing").value = String(prefs.wordSpacing);
        el("readerPageWidth").value = String(prefs.pageWidth);
        el("readerFontSizeValue").textContent = `${prefs.fontSize}px`;
        el("readerLineHeightValue").textContent = prefs.lineHeight.toFixed(2);
        el("readerWordSpacingValue").textContent = `${prefs.wordSpacing}px`;
        el("readerPageWidthValue").textContent = `${prefs.pageWidth}px`;
        el("readerEnableAskAi").checked = prefs.enableAskAi;
        el("readerAiLength").value = prefs.aiAnswerLength;
        el("readerShowAiHover").checked = prefs.showAiHover;
        el("readerAskAiFields").hidden = !prefs.enableAskAi;
        el("readerAskAi").disabled = !prefs.enableAskAi || !lastSelection || Boolean(aiRequestController);
      };
      const bindPreference = (id, key, transform = Number) => {
        el(id).addEventListener("input", (event) => {
          state.preferences[key] = transform(event.target.value);
          applyPreferences();
          scheduleSave();
        });
      };

      const syncChapterBoxes = () => {
        const completed = new Set(state.completedChapters);
        chapterBoxes.forEach((box) => { box.checked = completed.has(box.dataset.chapterId); });
        const done = chapterRows.filter(chapter => completed.has(chapter.id)).length;
        const percent = chapterRows.length ? Math.round((done / chapterRows.length) * 100) : 0;
        const percentEl = el("chapterProgressPercent");
        const fillEl = el("chapterProgressFill");
        const detailEl = el("chapterProgressDetails");
        if (percentEl) percentEl.textContent = `${percent}%`;
        if (fillEl) fillEl.style.width = `${percent}%`;
        if (detailEl) detailEl.textContent = `${done} / ${chapterRows.length}`;
      };
      const handleChapterChange = (box) => {
        const id = box.dataset.chapterId;
        const order = Number(box.dataset.chapterOrder || 0);
        const completed = new Set(state.completedChapters);
        if (box.checked) chapterRows.filter(chapter => chapter.order <= order).forEach(chapter => completed.add(chapter.id));
        else completed.delete(id);
        state.completedChapters = [...completed];
        state.totalChapters = chapterRows.length;
        syncChapterBoxes();
        scheduleSave();
      };

      const pageForAnnotation = (annotation) => document.querySelector(
        annotation.page ? `[data-page-number="${CSS.escape(String(annotation.page))}"]` : `[data-page-index="${annotation.pageIndex || 0}"]`
      );
      const jumpToAnnotation = (annotation) => {
        const target = pageForAnnotation(annotation);
        if (!target) return;
        const top = target.getBoundingClientRect().top + window.scrollY - 64;
        window.scrollTo({ top: Math.max(0, top), behavior: "smooth" });
        target.classList.add("reader-annotation-target");
        window.clearTimeout(annotationTimer);
        annotationTimer = window.setTimeout(() => {
          target.classList.remove("reader-annotation-target");
          annotationTimer = 0;
        }, 1200);
      };
      const annotationLabel = (annotation, kind) => annotation.title || annotation.text || kind;
      const renderAnnotations = () => {
        const list = el("readerAnnotationList");
        list.replaceChildren();
        const items = [];
        if (el("readerShowNotes").checked) state.notes.forEach(item => items.push({ ...item, kind: "note" }));
        if (el("readerShowHighlights").checked) state.highlights.forEach(item => items.push({ ...item, kind: "highlight" }));
        items.sort((a, b) => (a.pageIndex || 0) - (b.pageIndex || 0) || String(a.createdAt || "").localeCompare(String(b.createdAt || "")));
        el("readerAnnotationEmpty").hidden = Boolean(items.length);
        items.forEach((item) => {
          const row = document.createElement("li");
          const jump = document.createElement("button");
          jump.type = "button";
          jump.className = "reader-annotation-jump";
          const title = document.createElement("strong");
          title.textContent = annotationLabel(item, item.kind === "note" ? labels.notes : labels.highlights).slice(0, 200);
          const meta = document.createElement("span");
          meta.textContent = item.page ? `#${item.page}` : `#${item.pageIndex || 0}`;
          jump.append(title, meta);
          if (item.aiAnswer) {
            const answer = document.createElement("span");
            answer.className = "reader-ai-answer";
            answer.textContent = item.aiAnswer;
            jump.append(answer);
          }
          jump.addEventListener("click", () => jumpToAnnotation(item));
          const remove = document.createElement("button");
          remove.type = "button";
          remove.className = "reader-annotation-delete";
          remove.title = labels.delete;
          remove.textContent = "×";
          remove.addEventListener("click", () => {
            const collection = item.kind === "note" ? "notes" : "highlights";
            state[collection] = state[collection].filter(candidate => candidate.id !== item.id);
            renderAnnotations();
            applyHighlights();
            scheduleSave();
          });
          row.append(jump, remove);
          list.append(row);
        });
      };
      const textOffsetRange = (container, start, end) => {
        const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
        let node;
        let offset = 0;
        let startNode = null, endNode = null, startOffset = 0, endOffset = 0;
        while ((node = walker.nextNode())) {
          const next = offset + node.nodeValue.length;
          if (!startNode && start >= offset && start <= next) { startNode = node; startOffset = start - offset; }
          if (end >= offset && end <= next) { endNode = node; endOffset = end - offset; break; }
          offset = next;
        }
        if (!startNode || !endNode) return null;
        const range = new Range();
        range.setStart(startNode, startOffset);
        range.setEnd(endNode, endOffset);
        return range;
      };
      const applyHighlights = () => {
        aiHoverRanges = [];
        if (!window.CSS?.highlights || typeof Highlight === "undefined") return;
        const ranges = state.highlights.map((item) => {
          const target = pageForAnnotation(item);
          const container = target?.querySelector("pre, .reader-text, .recipe-body") || target;
          const range = container ? textOffsetRange(container, item.start, item.end) : null;
          if (range && item.aiAnswer) aiHoverRanges.push({ item, range });
          return range;
        }).filter(Boolean);
        CSS.highlights.set("mealie-reader-highlights", new Highlight(...ranges));
      };
      const captureSelection = () => {
        const selection = getSelection();
        if (!selection || selection.rangeCount !== 1 || selection.isCollapsed) return;
        const range = selection.getRangeAt(0);
        const page = range.commonAncestorContainer.nodeType === Node.ELEMENT_NODE
          ? range.commonAncestorContainer.closest?.(".reading-position")
          : range.commonAncestorContainer.parentElement?.closest(".reading-position");
        const container = page?.querySelector("pre, .reader-text, .recipe-body") || page;
        if (!page || !container || !container.contains(range.commonAncestorContainer)) return;
        const prefix = range.cloneRange();
        prefix.selectNodeContents(container);
        prefix.setEnd(range.startContainer, range.startOffset);
        const text = range.toString().trim();
        if (!text) return;
        const start = prefix.toString().length;
        lastSelection = {
          text: text.slice(0, 2000), start, end: start + range.toString().length,
          page: Number(page.dataset.pageNumber || 0), pageIndex: Number(page.dataset.pageIndex || 0),
          chapterId: page.dataset.chapterId || null,
        };
        el("readerAskAi").disabled = !state.preferences.enableAskAi;
      };
      const askAi = async () => {
        if (!lastSelection || !state.preferences.enableAskAi || aiRequestController) return;
        const button = el("readerAskAi");
        const question = el("readerAiQuestion").value.trim() || labels.default_question;
        const controller = new AbortController();
        aiRequestController = controller;
        button.disabled = true;
        button.textContent = labels.asking_ai;
        el("readerAiWarning").hidden = true;
        try {
          const response = await fetch(askAiEndpoint, {
            method: "POST", credentials: "same-origin", signal: controller.signal,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              selectedText: lastSelection.text,
              question,
              answerLength: state.preferences.aiAnswerLength,
              targetLanguage: labels.target_language,
              page: lastSelection.page,
            }),
          });
          if (!response.ok) throw new Error(String(response.status));
          const result = await response.json();
          const answer = String(result.answer || "").trim();
          if (!answer) throw new Error("empty answer");
          state.highlights.push({
            id: makeId(), ...lastSelection, aiQuestion: question, aiAnswer: answer.slice(0, 6000),
            createdAt: new Date().toISOString(),
          });
          state.highlights = state.highlights.slice(-500);
          el("readerAiQuestion").value = "";
          renderAnnotations();
          applyHighlights();
          scheduleSave();
        }
        catch (error) {
          if (error?.name !== "AbortError") el("readerAiWarning").hidden = false;
        }
        finally {
          if (aiRequestController === controller) aiRequestController = null;
          button.textContent = labels.ask_ai;
          button.disabled = !lastSelection || !state.preferences.enableAskAi;
        }
      };
      const hideAiTooltip = () => { el("readerAiTooltip").hidden = true; };
      const renderAiHover = (event) => {
        hoverFrame = 0;
        if (!state.preferences.showAiHover || !aiHoverRanges.length) return hideAiTooltip();
        const match = aiHoverRanges.find(({ range }) => [...range.getClientRects()].some(rect => (
          event.clientX >= rect.left && event.clientX <= rect.right
          && event.clientY >= rect.top && event.clientY <= rect.bottom
        )));
        if (!match) return hideAiTooltip();
        const tooltip = el("readerAiTooltip");
        tooltip.textContent = match.item.aiAnswer;
        tooltip.hidden = false;
        const left = Math.min(window.innerWidth - tooltip.offsetWidth - 12, Math.max(12, event.clientX + 14));
        const top = Math.min(window.innerHeight - tooltip.offsetHeight - 12, Math.max(12, event.clientY + 14));
        tooltip.style.left = `${left}px`;
        tooltip.style.top = `${top}px`;
      };
      const handleAiHover = (event) => {
        if (hoverFrame) return;
        hoverFrame = requestAnimationFrame(() => renderAiHover(event));
      };
      const makeId = () => crypto.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
      const handleReadingPosition = (event) => {
        const detail = event.detail || {};
        state.currentPage = clamp(detail.pageNumber, 0, 100000, 0);
        state.currentPageIndex = clamp(detail.pageIndex, 0, 100000, 0);
        state.currentChapterId = typeof detail.chapterId === "string" ? detail.chapterId : null;
        state.readingPercent = clamp(detail.percent, 0, 100, 0);
        scheduleSave();
      };
      window.addEventListener("mealie:book-position", handleReadingPosition);

      const applyPanelState = (panel, toggle, key, openLabel, closeLabel) => {
        let collapsed = true;
        try { collapsed = localStorage.getItem(key) !== "false"; } catch (_error) { /* optional */ }
        const render = () => {
          panel.classList.toggle("is-collapsed", collapsed);
          toggle.setAttribute("aria-expanded", String(!collapsed));
          toggle.title = collapsed ? openLabel : closeLabel;
        };
        toggle.addEventListener("click", () => {
          collapsed = !collapsed;
          try { localStorage.setItem(key, String(collapsed)); } catch (_error) { /* optional */ }
          render();
        });
        render();
      };

      const initialize = async () => {
        await loadState();
        if (destroyed) return;
        state.totalChapters = chapterRows.length;
        applyPreferences();
        syncChapterBoxes();
        renderAnnotations();
        applyHighlights();
        chapterBoxes.forEach(box => box.addEventListener("change", () => handleChapterChange(box)));
        bindPreference("readerFontSize", "fontSize");
        bindPreference("readerFontFamily", "fontFamily", String);
        bindPreference("readerLineHeight", "lineHeight");
        bindPreference("readerWordSpacing", "wordSpacing");
        bindPreference("readerPageWidth", "pageWidth");
        bindPreference("readerAiLength", "aiAnswerLength", String);
        el("readerEnableAskAi").addEventListener("change", (event) => {
          state.preferences.enableAskAi = event.target.checked;
          applyPreferences();
          scheduleSave();
        });
        el("readerShowAiHover").addEventListener("change", (event) => {
          state.preferences.showAiHover = event.target.checked;
          if (!event.target.checked) hideAiTooltip();
          scheduleSave();
        });
        el("readerReset").addEventListener("click", () => {
          state.preferences = structuredClone(defaults.preferences);
          applyPreferences();
          scheduleSave();
        });
        applyPanelState(settings, el("readerSettingsToggle"), `${storageKey}:settingsCollapsed`, labels.open_settings, labels.close_settings);
        applyPanelState(annotations, el("readerAnnotationsToggle"), `${storageKey}:annotationsCollapsed`, labels.open_annotations, labels.close_annotations);
        el("readerShowNotes").addEventListener("change", renderAnnotations);
        el("readerShowHighlights").addEventListener("change", renderAnnotations);
        el("readerAddNote").addEventListener("click", () => {
          const text = el("readerNoteText").value.trim();
          if (!text) return;
          state.notes.push({
            id: makeId(), title: el("readerNoteTitle").value.trim().slice(0, 200), text: text.slice(0, 4000),
            page: state.currentPage, pageIndex: state.currentPageIndex, chapterId: state.currentChapterId,
            createdAt: new Date().toISOString(),
          });
          state.notes = state.notes.slice(-500);
          el("readerNoteTitle").value = "";
          el("readerNoteText").value = "";
          renderAnnotations();
          scheduleSave();
        });
        el("readerAddHighlight").addEventListener("mousedown", event => event.preventDefault());
        el("readerAskAi").addEventListener("mousedown", event => event.preventDefault());
        el("readerAskAi").addEventListener("click", askAi);
        el("readerAddHighlight").addEventListener("click", () => {
          if (!lastSelection) return;
          state.highlights.push({ id: makeId(), ...lastSelection, createdAt: new Date().toISOString() });
          state.highlights = state.highlights.slice(-500);
          renderAnnotations();
          applyHighlights();
          scheduleSave();
        });
        document.addEventListener("selectionchange", captureSelection, { passive: true });
        document.addEventListener("mousemove", handleAiHover, { passive: true });
        if (chapterRows.length && !state.totalChapters) scheduleSave();
      };

      window.addEventListener("pagehide", (event) => {
        window.clearTimeout(saveTimer);
        window.clearTimeout(annotationTimer);
        writeLocal();
        requestController?.abort();
        aiRequestController?.abort();
        if (hoverFrame) cancelAnimationFrame(hoverFrame);
        if (!event.persisted) {
          destroyed = true;
          window.removeEventListener("mealie:book-position", handleReadingPosition);
          document.removeEventListener("selectionchange", captureSelection);
          document.removeEventListener("mousemove", handleAiHover);
        }
      });
      void initialize();
    })();
  </script>
    """
    return script.replace("__BOOK_ID__", BOOK_READER_ID_PLACEHOLDER).replace("__LABELS__", labels_json)
