const STORAGE_KEYS = {
  mealieUrl: "mealieUrl",
  extractMode: "extractMode",
  translateLanguage: "translateLanguage",
  createShoppingList: "createShoppingList",
  organizeShoppingList: "organizeShoppingList",
  includeAiTips: "includeAiTips",
  includeItemImages: "includeItemImages",
};

const DEFAULT_SETTINGS = {
  mealieUrl: "http://localhost:3000",
  extractMode: "auto",
  translateLanguage: "he-IL",
  createShoppingList: true,
  organizeShoppingList: true,
  includeAiTips: true,
  includeItemImages: true,
};

const MAX_EXTRACTED_TEXT_LENGTH = 180000;
const AUTH_COOKIE_NAME = "mealie.access_token";
const LOCALE_CODES = [
  "af-ZA",
  "ar-SA",
  "bg-BG",
  "ca-ES",
  "cs-CZ",
  "da-DK",
  "de-DE",
  "el-GR",
  "en-GB",
  "en-US",
  "es-ES",
  "et-EE",
  "fi-FI",
  "fr-BE",
  "fr-CA",
  "fr-FR",
  "gl-ES",
  "he-IL",
  "hr-HR",
  "hu-HU",
  "is-IS",
  "it-IT",
  "ja-JP",
  "ko-KR",
  "lt-LT",
  "lv-LV",
  "nl-NL",
  "no-NO",
  "pl-PL",
  "pt-BR",
  "pt-PT",
  "ro-RO",
  "ru-RU",
  "sk-SK",
  "sl-SI",
  "sr-SP",
  "sv-SE",
  "tr-TR",
  "uk-UA",
  "vi-VN",
  "zh-CN",
  "zh-TW",
];

const elements = {
  mealieUrl: document.getElementById("mealieUrl"),
  extractMode: document.getElementById("extractMode"),
  translateLanguage: document.getElementById("translateLanguage"),
  createShoppingList: document.getElementById("createShoppingList"),
  organizeShoppingList: document.getElementById("organizeShoppingList"),
  includeAiTips: document.getElementById("includeAiTips"),
  includeItemImages: document.getElementById("includeItemImages"),
  extractOnly: document.getElementById("extractOnly"),
  sendToMealie: document.getElementById("sendToMealie"),
  connectMealie: document.getElementById("connectMealie"),
  previewPanel: document.getElementById("previewPanel"),
  previewText: document.getElementById("previewText"),
  status: document.getElementById("status"),
  recipeLink: document.getElementById("recipeLink"),
};

let lastExtraction = null;
let isBusy = false;
let mealieSiteReady = false;
let statusCheckTimer = null;

init();

async function init() {
  populateLanguageOptions();
  const settings = await loadSettings();
  applySettings(settings);
  await chrome.storage.sync.remove("apiToken");

  [
    elements.mealieUrl,
    elements.extractMode,
    elements.translateLanguage,
    elements.createShoppingList,
    elements.organizeShoppingList,
    elements.includeAiTips,
    elements.includeItemImages,
  ].forEach((element) => {
    element.addEventListener("change", saveSettingsFromForm);
    element.addEventListener("input", saveSettingsFromForm);
  });

  elements.extractOnly.addEventListener("click", handleExtractOnly);
  elements.sendToMealie.addEventListener("click", handleSendToMealie);
  elements.connectMealie.addEventListener("click", handleConnectMealie);
  elements.extractMode.addEventListener("change", updateModeText);
  elements.mealieUrl.addEventListener("input", scheduleMealieStatusCheck);
  elements.mealieUrl.addEventListener("change", checkMealieStatus);

  await checkMealieStatus();
}

async function loadSettings() {
  const stored = await chrome.storage.sync.get(Object.values(STORAGE_KEYS));
  return {
    ...DEFAULT_SETTINGS,
    ...stored,
  };
}

function populateLanguageOptions() {
  const displayNames = typeof Intl !== "undefined" && Intl.DisplayNames
    ? new Intl.DisplayNames([navigator.language || "he-IL"], { type: "language" })
    : null;

  elements.translateLanguage.replaceChildren(
    ...LOCALE_CODES.map((code) => {
      const option = document.createElement("option");
      option.value = code;
      option.textContent = `${languageDisplayName(code, displayNames)} - ${code}`;
      return option;
    }),
  );
}

function languageDisplayName(code, displayNames) {
  const language = languagePrimary(code);
  if (!language || !displayNames) {
    return code;
  }

  try {
    return displayNames.of(language) || code;
  }
  catch {
    return code;
  }
}

function applySettings(settings) {
  elements.mealieUrl.value = settings.mealieUrl || DEFAULT_SETTINGS.mealieUrl;
  elements.extractMode.value = settings.extractMode || DEFAULT_SETTINGS.extractMode;
  elements.translateLanguage.value = settings.translateLanguage || DEFAULT_SETTINGS.translateLanguage;
  if (!elements.translateLanguage.value) {
    elements.translateLanguage.value = DEFAULT_SETTINGS.translateLanguage;
  }
  elements.createShoppingList.checked = settings.createShoppingList !== false;
  elements.organizeShoppingList.checked = settings.organizeShoppingList !== false;
  elements.includeAiTips.checked = settings.includeAiTips !== false;
  elements.includeItemImages.checked = settings.includeItemImages !== false;
  updateModeText();
  updateActionState();
}

async function saveSettingsFromForm() {
  await chrome.storage.sync.set(currentSettings());
}

function currentSettings() {
  return {
    mealieUrl: normalizeBaseUrl(elements.mealieUrl.value || DEFAULT_SETTINGS.mealieUrl),
    extractMode: elements.extractMode.value || DEFAULT_SETTINGS.extractMode,
    translateLanguage: elements.translateLanguage.value,
    createShoppingList: elements.createShoppingList.checked,
    organizeShoppingList: elements.organizeShoppingList.checked,
    includeAiTips: elements.includeAiTips.checked,
    includeItemImages: elements.includeItemImages.checked,
  };
}

function updateModeText() {
  const mode = elements.extractMode.value;
  if (mode === "article") {
    elements.sendToMealie.textContent = "חלץ מאמר ל-AI";
    return;
  }
  if (mode === "recipe") {
    elements.sendToMealie.textContent = "חלץ מתכון ל-AI";
    return;
  }
  elements.sendToMealie.textContent = "זהה ושלח ל-AI";
}

function normalizeBaseUrl(value) {
  return String(value || "").trim().replace(/\/+$/, "");
}

async function findMealieAuthToken(mealieUrl) {
  let origin = "";
  try {
    origin = new URL(normalizeBaseUrl(mealieUrl)).origin;
  }
  catch {
    return null;
  }

  try {
    const cookie = await chrome.cookies?.get({ url: origin, name: AUTH_COOKIE_NAME });
    if (cookie?.value) {
      return decodeURIComponent(cookie.value);
    }
  }
  catch {
    // Fall back to reading from an open Mealie tab.
  }

  const tabs = await chrome.tabs.query({});
  const mealieTabs = tabs.filter(tab => tab.id && tab.url && sameOrigin(tab.url, origin));
  for (const tab of mealieTabs) {
    try {
      const [result] = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: readCookieValue,
        args: [AUTH_COOKIE_NAME],
      });
      if (result?.result) {
        return result.result;
      }
    }
    catch {
      // Try the next open Mealie tab.
    }
  }

  return null;
}

function sameOrigin(url, origin) {
  try {
    return new URL(url).origin === origin;
  }
  catch {
    return false;
  }
}

function readCookieValue(name) {
  const prefix = `${name}=`;
  const cookie = document.cookie
    .split(";")
    .map(part => part.trim())
    .find(part => part.startsWith(prefix));

  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : null;
}

function authHeaders(authToken) {
  return authToken ? { Authorization: `Bearer ${authToken}` } : {};
}

function scheduleMealieStatusCheck() {
  clearTimeout(statusCheckTimer);
  statusCheckTimer = setTimeout(checkMealieStatus, 500);
}

async function checkMealieStatus() {
  clearTimeout(statusCheckTimer);
  const settings = currentSettings();
  mealieSiteReady = false;
  elements.connectMealie.hidden = true;
  updateActionState();

  try {
    const authToken = await findMealieAuthToken(settings.mealieUrl);
    if (!authToken) {
      setStatus("צריך לפתוח את Mealie בטאב באותו דפדפן ולהתחבר לפני שימוש בתוסף.", "error");
      elements.connectMealie.hidden = false;
      return false;
    }

    const response = await fetch(`${settings.mealieUrl}/api/recipes/create/browser-page/status`, {
      credentials: "include",
      headers: authHeaders(authToken),
    });
    const payload = await safeJson(response);

    if (response.status === 401 || response.status === 403) {
      setStatus("צריך להתחבר ל-Mealie באותו דפדפן לפני שימוש בתוסף.", "error");
      elements.connectMealie.hidden = false;
      return false;
    }

    if (!response.ok) {
      setStatus(`לא הצלחתי לבדוק את Mealie (${response.status}). ודא שהאתר פתוח בכתובת הנכונה.`, "error");
      return false;
    }

    if (!statusAiEnabled(payload)) {
      setStatus(aiProviderStatusMessage(payload), "error");
      return false;
    }

    mealieSiteReady = true;
    setStatus("");
    return true;
  }
  catch {
    setStatus("לא הצלחתי להתחבר ל-Mealie. בדוק שהכתובת נכונה ושהאתר פתוח.", "error");
    elements.connectMealie.hidden = false;
    return false;
  }
  finally {
    updateActionState();
  }
}

function aiProviderStatusMessage(payload) {
  if (statusProviderCount(payload) > 0 && !statusDefaultProviderConfigured(payload)) {
    return "יש ספקי AI שמורים באתר, אבל לא נבחר ספק ברירת מחדל. בחר ספק ברירת מחדל בהגדרות API של Mealie.";
  }

  return "צריך להגדיר ספק API/AI באתר Mealie לפני שימוש בתוסף.";
}

function statusAiEnabled(payload) {
  return Boolean(payload?.ai_enabled ?? payload?.aiEnabled);
}

function statusProviderCount(payload) {
  return Number(payload?.provider_count ?? payload?.providerCount ?? 0);
}

function statusDefaultProviderConfigured(payload) {
  return Boolean(payload?.default_provider_configured ?? payload?.defaultProviderConfigured);
}

async function handleConnectMealie() {
  const settings = currentSettings();
  await openOrFocusMealieTab(settings.mealieUrl);
  setStatus("פתחתי את Mealie. התחבר שם אם צריך, ואז לחץ שוב על התוסף.", "success");
}

async function openOrFocusMealieTab(mealieUrl) {
  const baseUrl = normalizeBaseUrl(mealieUrl || DEFAULT_SETTINGS.mealieUrl);
  let origin = "";
  try {
    origin = new URL(baseUrl).origin;
  }
  catch {
    await chrome.tabs.create({ url: DEFAULT_SETTINGS.mealieUrl });
    return;
  }

  const tabs = await chrome.tabs.query({});
  const existingTab = tabs.find(tab => tab.id && tab.url && sameOrigin(tab.url, origin));
  if (existingTab?.id) {
    await chrome.tabs.update(existingTab.id, { active: true });
    if (existingTab.windowId) {
      await chrome.windows.update(existingTab.windowId, { focused: true });
    }
    return;
  }

  await chrome.tabs.create({ url: baseUrl });
}

async function handleExtractOnly() {
  setBusy(true);
  setStatus("מחלץ תוכן מהעמוד...");

  try {
    lastExtraction = await extractCurrentTab();
    showPreview(lastExtraction.markdown);
    setStatus(`חולץ תוכן מהעמוד: ${lastExtraction.title || "ללא כותרת"}`, "success");
  }
  catch (error) {
    setStatus(errorMessage(error), "error");
  }
  finally {
    setBusy(false);
  }
}

async function handleSendToMealie() {
  setBusy(true);
  hideRecipeLink();
  setStatus("מחלץ תוכן ושולח ל-Mealie...");

  try {
    const settings = currentSettings();
    await chrome.storage.sync.set(settings);
    if (!await checkMealieStatus()) {
      return;
    }

    setStatus(statusTextForMode(settings.extractMode));
    const extraction = lastExtraction || await extractCurrentTab();
    lastExtraction = extraction;
    showPreview(extraction.markdown);

    if (settings.extractMode === "article" || settings.extractMode === "auto") {
      const response = await createArticleFromBrowserPage(settings, extraction);
      const article = response.article;
      const recipeSlug = response.recipeSlug || response.recipe_slug;
      const recipeError = response.recipeError || response.recipe_error;
      const shoppingListName = response.shoppingListName || response.shopping_list_name;
      const shoppingListError = response.shoppingListError || response.shopping_list_error;
      const messages = [];

      if (article?.title) {
        messages.push(`המאמר נוצר: ${article.title}`);
      }
      if (recipeSlug) {
        messages.push(`נוצר גם מתכון: ${recipeSlug}`);
      }
      if (shoppingListName) {
        messages.push(`רשימת קניות: ${shoppingListName}`);
      }
      if (recipeError) {
        messages.push(`שימו לב: ${recipeError}`);
      }
      if (shoppingListError) {
        messages.push(`שימו לב: ${shoppingListError}`);
      }

      setStatus(messages.join("\n") || "החילוץ הסתיים", recipeError || shoppingListError ? "" : "success");
      if (article?.id) {
        showArticleLink(settings.mealieUrl, article.id);
      }
      else if (recipeSlug) {
        showRecipeLink(settings.mealieUrl, recipeSlug, response.groupSlug || response.group_slug);
      }
      return;
    }

    const response = await createRecipeFromBrowserPage(settings, extraction);
    const messages = [`המתכון נוצר: ${response.recipeSlug || response.recipe_slug}`];
    const shoppingListName = response.shoppingListName || response.shopping_list_name;
    const shoppingListError = response.shoppingListError || response.shopping_list_error;

    if (shoppingListName) {
      messages.push(`רשימת קניות: ${shoppingListName}`);
    }
    if (shoppingListError) {
      messages.push(`שימו לב: ${shoppingListError}`);
    }

    setStatus(messages.join("\n"), shoppingListError ? "" : "success");
    showRecipeLink(
      settings.mealieUrl,
      response.recipeSlug || response.recipe_slug,
      response.groupSlug || response.group_slug,
    );
  }
  catch (error) {
    setStatus(errorMessage(error), "error");
  }
  finally {
    setBusy(false);
  }
}

function statusTextForMode(mode) {
  if (mode === "article") {
    return "מחלץ מאמר ושולח ל-Mealie...";
  }
  if (mode === "recipe") {
    return "מחלץ מתכון ושולח ל-Mealie...";
  }
  return "מחלץ את העמוד, מזהה סוג תוכן ושולח ל-Mealie...";
}

async function extractCurrentTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) {
    throw new Error("לא נמצא tab פעיל.");
  }

  if (!tab.url || /^chrome:|^edge:|^about:|^chrome-extension:/i.test(tab.url)) {
    throw new Error("אי אפשר לחלץ מהעמוד הזה. פתח עמוד מתכון רגיל ונסה שוב.");
  }

  const [result] = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: extractRecipePage,
    args: [MAX_EXTRACTED_TEXT_LENGTH],
  });

  if (!result?.result?.markdown) {
    throw new Error("לא הצלחתי לחלץ טקסט מהעמוד.");
  }

  return result.result;
}

async function createRecipeFromBrowserPage(settings, extraction) {
  const endpoint = `${settings.mealieUrl}/api/recipes/create/browser-page`;
  const authToken = await findMealieAuthToken(settings.mealieUrl);
  if (!authToken) {
    throw new Error("צריך לפתוח את Mealie בטאב באותו דפדפן ולהתחבר לפני שימוש בתוסף.");
  }

  const headers = {
    "Content-Type": "application/json",
    ...authHeaders(authToken),
  };
  const translateLanguage = translationLanguageForRequest(settings.translateLanguage, extraction.language);

  const response = await fetch(endpoint, {
    method: "POST",
    credentials: "include",
    headers,
    body: JSON.stringify({
      text: extraction.markdown,
      source_url: extraction.url,
      source_title: extraction.title,
      image_url: extraction.imageUrl,
      translate_language: translateLanguage,
      include_ai_tips: settings.includeAiTips,
      include_item_images: settings.includeItemImages !== false,
      create_shopping_list: settings.createShoppingList,
      organize_shopping_list_with_ai: settings.organizeShoppingList,
    }),
  });

  const payload = await safeJson(response);
  if (!response.ok) {
    throw new Error(apiErrorMessage(payload, response.status));
  }

  return payload;
}

async function createArticleFromBrowserPage(settings, extraction) {
  const endpoint = `${settings.mealieUrl}/api/households/articles/browser-page`;
  const authToken = await findMealieAuthToken(settings.mealieUrl);
  if (!authToken) {
    throw new Error("צריך לפתוח את Mealie בטאב באותו דפדפן ולהתחבר לפני שימוש בתוסף.");
  }

  const translateLanguage = translationLanguageForRequest(settings.translateLanguage, extraction.language);
  const response = await fetch(endpoint, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(authToken),
    },
    body: JSON.stringify({
      text: extraction.markdown,
      source_url: extraction.url,
      source_title: extraction.title,
      image_url: extraction.imageUrl,
      translate_language: translateLanguage,
      create_recipe_if_present: true,
      create_shopping_list: settings.createShoppingList,
      organize_shopping_list_with_ai: settings.organizeShoppingList,
      include_ai_tips: settings.includeAiTips,
      include_item_images: settings.includeItemImages !== false,
    }),
  });

  const payload = await safeJson(response);
  if (!response.ok) {
    throw new Error(apiErrorMessage(payload, response.status));
  }

  return payload;
}

async function safeJson(response) {
  try {
    return await response.json();
  }
  catch {
    return null;
  }
}

function apiErrorMessage(payload, status) {
  const detail = payload?.detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (detail?.message) {
    return detail.message;
  }
  if (detail?.exception) {
    return detail.exception;
  }
  if (status === 401) {
    return "הבקשה נכשלה כי אין התחברות פעילה ל-Mealie. פתח את Mealie באותו דפדפן, התחבר, ואז נסה שוב.";
  }
  return `הבקשה נכשלה (${status}). בדוק ש-Mealie פתוח ושאתה מחובר אליו באותו דפדפן.`;
}

function showPreview(text) {
  elements.previewPanel.hidden = false;
  elements.previewText.value = text;
}

function setBusy(nextBusy) {
  isBusy = nextBusy;
  updateActionState();
}

function updateActionState() {
  elements.extractOnly.disabled = isBusy;
  elements.sendToMealie.disabled = isBusy || !mealieSiteReady;
}

function setStatus(message, type = "") {
  elements.status.textContent = message || "";
  elements.status.className = `status ${type}`.trim();
}

function showRecipeLink(baseUrl, slug, groupSlug) {
  if (!slug) {
    hideRecipeLink();
    return;
  }

  const recipeGroupSlug = groupSlug || "home";
  showResultLink(
    `${normalizeBaseUrl(baseUrl)}/g/${encodeURIComponent(recipeGroupSlug)}/r/${encodeURIComponent(slug)}`,
    "פתח את המתכון ב-Mealie",
  );
}

function showArticleLink(baseUrl, articleId) {
  if (!articleId) {
    hideRecipeLink();
    return;
  }

  showResultLink(
    `${normalizeBaseUrl(baseUrl)}/articles/${encodeURIComponent(articleId)}`,
    "פתח את המאמר ב-Mealie",
  );
}

function showResultLink(href, text) {
  elements.recipeLink.href = href;
  elements.recipeLink.textContent = text;
  elements.recipeLink.hidden = false;
}

function hideRecipeLink() {
  elements.recipeLink.hidden = true;
  elements.recipeLink.href = "#";
  elements.recipeLink.textContent = "פתח את המתכון ב-Mealie";
}

function errorMessage(error) {
  return error?.message || "משהו השתבש.";
}

function translationLanguageForRequest(targetLanguage, pageLanguage) {
  const target = languagePrimary(targetLanguage);
  if (!target) {
    return null;
  }

  const source = languagePrimary(pageLanguage);
  return source && source === target ? null : targetLanguage;
}

function languagePrimary(value) {
  return String(value || "")
    .trim()
    .replace("_", "-")
    .split("-")[0]
    .toLocaleLowerCase();
}

function extractRecipePage(maxLength) {
  const url = location.href;
  const title = cleanText(document.querySelector("h1")?.innerText || document.title || "");
  const language = detectPageLanguage();
  const imageUrl = extractRecipeImage();
  const structured = extractStructuredRecipes();
  const readableText = extractReadableText();
  const sections = [
    `# ${title || "Recipe page"}`,
    `Source URL: ${url}`,
    imageUrl ? `Source image: ${imageUrl}` : "",
    structured ? `\n## Structured recipe data\n${structured}` : "",
    readableText ? `\n## Visible page text\n${readableText}` : "",
  ].filter(Boolean);

  return {
    title,
    url,
    language,
    imageUrl,
    markdown: clampText(sections.join("\n\n"), maxLength),
  };

  function detectPageLanguage() {
    const metaLanguage = document.querySelector("meta[http-equiv='content-language' i]")?.getAttribute("content");
    const ogLocale = document.querySelector("meta[property='og:locale' i]")?.getAttribute("content");
    return normalizeLanguage(document.documentElement.lang || metaLanguage || ogLocale || "");
  }

  function normalizeLanguage(value) {
    return String(value || "")
      .split(",")[0]
      .trim()
      .replace("_", "-");
  }

  function extractRecipeImage() {
    const structuredImages = Array.from(document.querySelectorAll("script[type='application/ld+json']"))
      .flatMap(script => parseJsonLd(script.textContent || ""))
      .flatMap(findRecipeObjects)
      .flatMap(recipe => imageValues(recipe.image || recipe.thumbnailUrl));

    const metaSelectors = [
      "meta[property='og:image' i]",
      "meta[property='og:image:url' i]",
      "meta[name='twitter:image' i]",
      "meta[name='twitter:image:src' i]",
      "link[rel='image_src' i]",
    ];
    const metaImages = metaSelectors
      .map(selector => document.querySelector(selector)?.getAttribute("content") || document.querySelector(selector)?.getAttribute("href"))
      .filter(Boolean);

    const visibleImages = Array.from(document.images)
      .map((image) => {
        const src = image.currentSrc || image.src || image.getAttribute("data-src") || image.getAttribute("data-lazy-src") || "";
        const rect = image.getBoundingClientRect();
        const area = Math.max(rect.width * rect.height, image.naturalWidth * image.naturalHeight);
        return { src, area };
      })
      .filter(item => item.src && item.area >= 40000)
      .sort((a, b) => b.area - a.area)
      .map(item => item.src);

    return uniqueUrls([...structuredImages, ...metaImages, ...visibleImages])[0] || null;
  }

  function imageValues(value) {
    if (!value) {
      return [];
    }
    if (Array.isArray(value)) {
      return value.flatMap(imageValues);
    }
    if (typeof value === "string") {
      return [value];
    }
    if (typeof value === "object") {
      return imageValues(value.url || value.contentUrl || value["@id"] || value.thumbnailUrl);
    }
    return [];
  }

  function uniqueUrls(values) {
    const seen = new Set();
    return values
      .map(resolveImageUrl)
      .filter(Boolean)
      .filter((value) => {
        const normalized = value.split("#")[0];
        if (seen.has(normalized)) {
          return false;
        }
        seen.add(normalized);
        return true;
      });
  }

  function resolveImageUrl(value) {
    try {
      const url = new URL(String(value || "").trim(), location.href);
      if (!["http:", "https:"].includes(url.protocol)) {
        return "";
      }
      if (url.pathname.toLocaleLowerCase().endsWith(".svg")) {
        return "";
      }
      return url.href;
    }
    catch {
      return "";
    }
  }

  function extractReadableText() {
    const documentClone = document.cloneNode(true);
    documentClone.querySelectorAll(
      "script, style, noscript, svg, canvas, iframe, nav, footer, header, aside, form, button, dialog",
    ).forEach(element => element.remove());

    const candidates = [
      documentClone.querySelector("[itemtype*='Recipe']"),
      documentClone.querySelector("[class*='recipe' i]"),
      documentClone.querySelector("article"),
      documentClone.querySelector("main"),
      documentClone.body,
    ].filter(Boolean);

    const best = candidates
      .map(element => cleanText(element.innerText || ""))
      .filter(Boolean)
      .sort((a, b) => b.length - a.length)[0] || "";

    return clampText(best, Math.floor(maxLength * 0.75));
  }

  function extractStructuredRecipes() {
    const jsonLdRecipes = Array.from(document.querySelectorAll("script[type='application/ld+json']"))
      .flatMap(script => parseJsonLd(script.textContent || ""))
      .flatMap(findRecipeObjects);

    return jsonLdRecipes.map(formatRecipeObject).filter(Boolean).join("\n\n---\n\n");
  }

  function parseJsonLd(text) {
    try {
      return [JSON.parse(text)];
    }
    catch {
      return [];
    }
  }

  function findRecipeObjects(value) {
    if (!value) {
      return [];
    }

    if (Array.isArray(value)) {
      return value.flatMap(findRecipeObjects);
    }

    if (typeof value !== "object") {
      return [];
    }

    const type = value["@type"];
    const types = Array.isArray(type) ? type : [type];
    const current = types.some((item) => {
      const normalizedType = String(item).toLocaleLowerCase();
      return normalizedType === "recipe" || normalizedType.endsWith("/recipe") || normalizedType.endsWith("#recipe");
    }) ? [value] : [];
    const graph = Array.isArray(value["@graph"]) ? value["@graph"].flatMap(findRecipeObjects) : [];
    return [...current, ...graph];
  }

  function formatRecipeObject(recipe) {
    const lines = [];
    appendLine(lines, "Name", recipe.name);
    appendLine(lines, "Description", recipe.description);
    appendLine(lines, "Author", formatValue(recipe.author));
    appendLine(lines, "Yield", formatValue(recipe.recipeYield || recipe.yield));
    appendLine(lines, "Prep time", recipe.prepTime);
    appendLine(lines, "Cook time", recipe.cookTime);
    appendLine(lines, "Total time", recipe.totalTime);
    appendLine(lines, "Category", recipe.recipeCategory);
    appendLine(lines, "Cuisine", recipe.recipeCuisine);
    appendLine(lines, "Keywords", recipe.keywords);
    appendLine(lines, "Image", imageValues(recipe.image || recipe.thumbnailUrl).join(", "));

    const ingredients = recipe.recipeIngredient || recipe.ingredients;
    if (ingredients?.length) {
      lines.push("\nIngredients:");
      ingredients.forEach(ingredient => lines.push(`- ${formatValue(ingredient)}`));
    }

    const instructions = recipe.recipeInstructions || recipe.instructions;
    if (instructions?.length) {
      lines.push("\nInstructions:");
      normalizeInstructions(instructions).forEach((instruction, index) => {
        lines.push(`${index + 1}. ${instruction}`);
      });
    }

    return lines.join("\n").trim();
  }

  function normalizeInstructions(instructions) {
    const values = Array.isArray(instructions) ? instructions : [instructions];
    return values.flatMap((instruction) => {
      if (!instruction) {
        return [];
      }
      if (typeof instruction === "string") {
        return [cleanText(instruction)];
      }
      if (Array.isArray(instruction.itemListElement)) {
        return normalizeInstructions(instruction.itemListElement);
      }
      return [cleanText(instruction.text || instruction.name || "")].filter(Boolean);
    });
  }

  function appendLine(lines, label, value) {
    const formatted = formatValue(value);
    if (formatted) {
      lines.push(`${label}: ${formatted}`);
    }
  }

  function formatValue(value) {
    if (!value) {
      return "";
    }
    if (Array.isArray(value)) {
      return value.map(formatValue).filter(Boolean).join(", ");
    }
    if (typeof value === "object") {
      return cleanText(value.name || value.text || JSON.stringify(value));
    }
    return cleanText(String(value));
  }

  function cleanText(value) {
    return String(value || "")
      .replace(/\u00a0/g, " ")
      .replace(/[ \t]+/g, " ")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }

  function clampText(value, limit) {
    const text = cleanText(value);
    if (text.length <= limit) {
      return text;
    }
    return `${text.slice(0, limit)}\n\n[Content truncated by Mealie extension]`;
  }
}
