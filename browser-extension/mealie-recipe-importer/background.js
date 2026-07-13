importScripts("i18n.js");

const BRIDGE_REQUEST = "MEALIE_EXTENSION_IMPORT_RECIPE_URL";
const MAX_EXTRACTED_TEXT_LENGTH = 180000;
const AUTH_COOKIE_NAME = "mealie.access_token";
const SITE_LOCALE_COOKIE_NAME = "i18n_redirected";
const extensionI18n = globalThis.MealieExtensionI18n;

void updateActionTitle();
chrome.runtime.onInstalled.addListener(updateActionTitle);
chrome.runtime.onStartup.addListener(updateActionTitle);
chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName === "sync" && (changes.interfaceLanguage || changes.mealieUrl)) {
    void updateActionTitle();
  }
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== BRIDGE_REQUEST) {
    return false;
  }

  importRecipeFromUrl(message.payload)
    .then(sendResponse)
    .catch(async (error) => {
      const translator = await extensionI18n.create(
        message.payload?.interfaceLanguage || message.payload?.translateLanguage,
      );
      sendResponse({
        ok: false,
        error: error?.message || translator.t("errors.import-failed"),
      });
    });

  return true;
});

async function importRecipeFromUrl(payload) {
  const translator = await extensionI18n.create(
    payload?.interfaceLanguage || payload?.translateLanguage,
  );
  const t = translator.t;
  const mealieUrl = normalizeBaseUrl(payload?.mealieUrl);
  const recipeUrl = String(payload?.url || "").trim();
  const extractMode = payload?.extractMode || "recipe";
  if (!mealieUrl || !/^https?:\/\//i.test(mealieUrl)) {
    throw new Error(t("errors.invalid-mealie-url"));
  }
  if (!recipeUrl || !/^https?:\/\//i.test(recipeUrl)) {
    throw new Error(t("errors.invalid-recipe-url"));
  }

  const authToken = payload?.authToken || await findMealieAuthToken(mealieUrl);
  if (!authToken) {
    throw new Error(t("status.open-and-login"));
  }

  const status = await checkMealieStatus(mealieUrl, authToken, t);
  if (!statusAiEnabled(status)) {
    throw new Error(aiProviderStatusMessage(status, t));
  }

  const extraction = await extractPageInBackgroundTab(recipeUrl, translator);
  if (extractMode === "article" || extractMode === "auto") {
    return await importArticlePage(mealieUrl, authToken, payload, extraction, t);
  }

  return await importRecipePage(mealieUrl, authToken, payload, extraction, t);
}

async function updateActionTitle() {
  const stored = await chrome.storage.sync.get(["interfaceLanguage", "mealieUrl"]);
  const preferred = stored.interfaceLanguage === extensionI18n.AUTOMATIC_LOCALE
    ? await findMealieLocale(stored.mealieUrl) || extensionI18n.AUTOMATIC_LOCALE
    : stored.interfaceLanguage;
  const translator = await extensionI18n.create(preferred);
  await chrome.action.setTitle({ title: translator.t("extension.action-title") });
}

async function findMealieLocale(mealieUrl) {
  let origin = "";
  try {
    origin = new URL(normalizeBaseUrl(mealieUrl || "http://localhost:3000")).origin;
  }
  catch {
    return null;
  }

  try {
    const cookie = await chrome.cookies?.get({ url: origin, name: SITE_LOCALE_COOKIE_NAME });
    const locale = decodeURIComponent(cookie?.value || "");
    return extensionI18n.LOCALE_CODES.includes(locale) ? locale : null;
  }
  catch {
    return null;
  }
}

function aiProviderStatusMessage(payload, t) {
  if (statusProviderCount(payload) > 0 && !statusDefaultProviderConfigured(payload)) {
    return t("status.provider-no-default");
  }

  return t("status.provider-required");
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

async function importRecipePage(mealieUrl, authToken, payload, extraction, t) {
  const translateLanguage = translationLanguageForRequest(payload.translateLanguage, extraction.language);
  const response = await fetch(`${mealieUrl}/api/recipes/create/browser-page`, {
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
      include_ai_tips: payload.includeAiTips !== false,
      include_item_images: payload.includeItemImages !== false,
      create_shopping_list: payload.createShoppingList !== false,
      organize_shopping_list_with_ai: payload.organizeShoppingListWithAi !== false,
    }),
  });

  const body = await safeJson(response);
  if (!response.ok) {
    throw new Error(apiErrorMessage(body, response.status, t));
  }

  return {
    ok: true,
    recipeSlug: body.recipeSlug || body.recipe_slug,
    groupSlug: body.groupSlug || body.group_slug,
    shoppingListId: body.shoppingListId || body.shopping_list_id,
    shoppingListName: body.shoppingListName || body.shopping_list_name,
    shoppingListOrganized: body.shoppingListOrganized || body.shopping_list_organized,
    shoppingListError: body.shoppingListError || body.shopping_list_error,
  };
}

async function importArticlePage(mealieUrl, authToken, payload, extraction, t) {
  const translateLanguage = translationLanguageForRequest(payload.translateLanguage, extraction.language);
  const response = await fetch(`${mealieUrl}/api/households/articles/browser-page`, {
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
      create_shopping_list: payload.createShoppingList !== false,
      organize_shopping_list_with_ai: payload.organizeShoppingListWithAi !== false,
      include_ai_tips: payload.includeAiTips !== false,
      include_item_images: payload.includeItemImages !== false,
    }),
  });

  const body = await safeJson(response);
  if (!response.ok) {
    throw new Error(apiErrorMessage(body, response.status, t));
  }

  return {
    ok: true,
    articleId: body.article?.id,
    recipeSlug: body.recipeSlug || body.recipe_slug,
    groupSlug: body.groupSlug || body.group_slug,
    shoppingListId: body.shoppingListId || body.shopping_list_id,
    shoppingListName: body.shoppingListName || body.shopping_list_name,
    shoppingListOrganized: body.shoppingListOrganized || body.shopping_list_organized,
    shoppingListError: body.shoppingListError || body.shopping_list_error,
    contentKind: body.contentKind || body.content_kind,
    containsRecipe: body.containsRecipe || body.contains_recipe,
  };
}

async function checkMealieStatus(mealieUrl, authToken, t) {
  const response = await fetch(`${mealieUrl}/api/recipes/create/browser-page/status`, {
    credentials: "include",
    headers: authHeaders(authToken),
  });
  const body = await safeJson(response);
  if (!response.ok) {
    throw new Error(apiErrorMessage(body, response.status, t));
  }
  return body || { ai_enabled: false };
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

async function extractPageInBackgroundTab(url, translator) {
  const tab = await chrome.tabs.create({ url, active: false });
  if (!tab?.id) {
    throw new Error(translator.t("errors.open-link-failed"));
  }

  try {
    if (tab.status !== "complete") {
      await waitForTabComplete(tab.id, translator.t);
    }

    const [result] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: extractRecipePage,
      args: [MAX_EXTRACTED_TEXT_LENGTH, extensionI18n.extractionLabels(translator)],
    });

    if (!result?.result?.markdown) {
      throw new Error(translator.t("errors.text-extraction-failed"));
    }

    return result.result;
  }
  finally {
    withChromeCallback(() => chrome.tabs.remove(tab.id));
  }
}

function waitForTabComplete(tabId, t) {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      cleanup();
      reject(new Error(t("errors.page-load-timeout")));
    }, 45000);

    const listener = (updatedTabId, changeInfo) => {
      if (updatedTabId === tabId && changeInfo.status === "complete") {
        cleanup();
        resolve();
      }
    };

    function cleanup() {
      clearTimeout(timeout);
      chrome.tabs.onUpdated.removeListener(listener);
    }

    chrome.tabs.onUpdated.addListener(listener);
  });
}

function withChromeCallback(action) {
  try {
    const result = action();
    if (result && typeof result.catch === "function") {
      result.catch(() => {});
    }
  }
  catch {
    // Best effort cleanup only.
  }
}

async function safeJson(response) {
  try {
    return await response.json();
  }
  catch {
    return null;
  }
}

function apiErrorMessage(payload, status, t) {
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
  if (status === 401 || status === 403) {
    return t("status.login-required");
  }
  return t("errors.request-failed", { status });
}

function normalizeBaseUrl(value) {
  return String(value || "").trim().replace(/\/+$/, "");
}

function translationLanguageForRequest(targetLanguage, _pageLanguage) {
  const target = languagePrimary(targetLanguage);
  if (!target) {
    return null;
  }

  // Always forward the user-selected output language. A same-language source
  // still needs an explicit constraint so the model does not default to English.
  return String(targetLanguage).trim().replace("_", "-");
}

function languagePrimary(value) {
  return String(value || "")
    .trim()
    .replace("_", "-")
    .split("-")[0]
    .toLocaleLowerCase();
}

function extractRecipePage(maxLength, localizedLabels = {}) {
  const labels = {
    recipePage: "Recipe page",
    sourceUrl: "Source URL",
    sourceImage: "Source image",
    structuredData: "Structured recipe data",
    visibleText: "Visible page text",
    name: "Name",
    description: "Description",
    author: "Author",
    yield: "Yield",
    prepTime: "Prep time",
    cookTime: "Cook time",
    totalTime: "Total time",
    category: "Category",
    cuisine: "Cuisine",
    keywords: "Keywords",
    image: "Image",
    ingredients: "Ingredients",
    instructions: "Instructions",
    contentTruncated: "Content truncated by the Mealie extension",
    ...localizedLabels,
  };
  const url = location.href;
  const title = cleanText(document.querySelector("h1")?.innerText || document.title || "");
  const language = detectPageLanguage();
  const imageUrl = extractRecipeImage();
  const structured = extractStructuredRecipes();
  const readableText = extractReadableText();
  const sections = [
    `# ${title || labels.recipePage}`,
    `${labels.sourceUrl}: ${url}`,
    imageUrl ? `${labels.sourceImage}: ${imageUrl}` : "",
    structured ? `\n## ${labels.structuredData}\n${structured}` : "",
    readableText ? `\n## ${labels.visibleText}\n${readableText}` : "",
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
    appendLine(lines, labels.name, recipe.name);
    appendLine(lines, labels.description, recipe.description);
    appendLine(lines, labels.author, formatValue(recipe.author));
    appendLine(lines, labels.yield, formatValue(recipe.recipeYield || recipe.yield));
    appendLine(lines, labels.prepTime, recipe.prepTime);
    appendLine(lines, labels.cookTime, recipe.cookTime);
    appendLine(lines, labels.totalTime, recipe.totalTime);
    appendLine(lines, labels.category, recipe.recipeCategory);
    appendLine(lines, labels.cuisine, recipe.recipeCuisine);
    appendLine(lines, labels.keywords, recipe.keywords);
    appendLine(lines, labels.image, imageValues(recipe.image || recipe.thumbnailUrl).join(", "));

    const ingredients = recipe.recipeIngredient || recipe.ingredients;
    if (ingredients?.length) {
      lines.push(`\n${labels.ingredients}:`);
      ingredients.forEach(ingredient => lines.push(`- ${formatValue(ingredient)}`));
    }

    const instructions = recipe.recipeInstructions || recipe.instructions;
    if (instructions?.length) {
      lines.push(`\n${labels.instructions}:`);
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
    return `${text.slice(0, limit)}\n\n[${labels.contentTruncated}]`;
  }
}
