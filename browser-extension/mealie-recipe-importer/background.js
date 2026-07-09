const BRIDGE_REQUEST = "MEALIE_EXTENSION_IMPORT_RECIPE_URL";
const MAX_EXTRACTED_TEXT_LENGTH = 180000;
const AUTH_COOKIE_NAME = "mealie.access_token";

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== BRIDGE_REQUEST) {
    return false;
  }

  importRecipeFromUrl(message.payload)
    .then(sendResponse)
    .catch((error) => {
      sendResponse({
        ok: false,
        error: error?.message || "Mealie extension import failed",
      });
    });

  return true;
});

async function importRecipeFromUrl(payload) {
  const mealieUrl = normalizeBaseUrl(payload?.mealieUrl);
  const recipeUrl = String(payload?.url || "").trim();
  const extractMode = payload?.extractMode || "recipe";
  if (!mealieUrl || !/^https?:\/\//i.test(mealieUrl)) {
    throw new Error("כתובת Mealie לא תקינה.");
  }
  if (!recipeUrl || !/^https?:\/\//i.test(recipeUrl)) {
    throw new Error("קישור המתכון לא תקין.");
  }

  const authToken = payload?.authToken || await findMealieAuthToken(mealieUrl);
  if (!authToken) {
    throw new Error("צריך לפתוח את Mealie בטאב באותו דפדפן ולהתחבר לפני שימוש בתוסף.");
  }

  const status = await checkMealieStatus(mealieUrl, authToken);
  if (!statusAiEnabled(status)) {
    throw new Error(aiProviderStatusMessage(status));
  }

  const extraction = await extractPageInBackgroundTab(recipeUrl);
  if (extractMode === "article" || extractMode === "auto") {
    return await importArticlePage(mealieUrl, authToken, payload, extraction);
  }

  return await importRecipePage(mealieUrl, authToken, payload, extraction);
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

async function importRecipePage(mealieUrl, authToken, payload, extraction) {
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
      create_shopping_list: payload.createShoppingList !== false,
      organize_shopping_list_with_ai: payload.organizeShoppingListWithAi !== false,
    }),
  });

  const body = await safeJson(response);
  if (!response.ok) {
    throw new Error(apiErrorMessage(body, response.status));
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

async function importArticlePage(mealieUrl, authToken, payload, extraction) {
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
    }),
  });

  const body = await safeJson(response);
  if (!response.ok) {
    throw new Error(apiErrorMessage(body, response.status));
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

async function checkMealieStatus(mealieUrl, authToken) {
  const response = await fetch(`${mealieUrl}/api/recipes/create/browser-page/status`, {
    credentials: "include",
    headers: authHeaders(authToken),
  });
  const body = await safeJson(response);
  if (!response.ok) {
    throw new Error(apiErrorMessage(body, response.status));
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

async function extractPageInBackgroundTab(url) {
  const tab = await chrome.tabs.create({ url, active: false });
  if (!tab?.id) {
    throw new Error("לא הצלחתי לפתוח את הקישור בדפדפן.");
  }

  try {
    if (tab.status !== "complete") {
      await waitForTabComplete(tab.id);
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
  finally {
    withChromeCallback(() => chrome.tabs.remove(tab.id));
  }
}

function waitForTabComplete(tabId) {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      cleanup();
      reject(new Error("טעינת העמוד נמשכה יותר מדי זמן."));
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
  if (status === 401 || status === 403) {
    return "צריך להתחבר ל-Mealie באותו דפדפן לפני שימוש בתוסף.";
  }
  return `הבקשה נכשלה (${status}). בדוק ש-Mealie פתוח ושאתה מחובר אליו באותו דפדפן.`;
}

function normalizeBaseUrl(value) {
  return String(value || "").trim().replace(/\/+$/, "");
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
