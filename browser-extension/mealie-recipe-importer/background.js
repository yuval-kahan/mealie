importScripts("i18n.js");

const BRIDGE_REQUEST = "MEALIE_EXTENSION_IMPORT_RECIPE_URL";
const IMAGE_BRIDGE_REQUEST = "MEALIE_EXTENSION_IMPORT_RECIPE_IMAGE_URL";
const POPUP_IMPORT_REQUEST = "MEALIE_EXTENSION_POPUP_IMPORT";
const POPUP_SAVE_WEBSITE_REQUEST = "MEALIE_EXTENSION_POPUP_SAVE_WEBSITE";
const POPUP_SAVE_RESTAURANT_REQUEST = "MEALIE_EXTENSION_POPUP_SAVE_RESTAURANT";
const POPUP_SAVE_WANTED_BOOK_REQUEST = "MEALIE_EXTENSION_POPUP_SAVE_WANTED_BOOK";
const POPUP_SAVE_CHEF_REQUEST = "MEALIE_EXTENSION_POPUP_SAVE_CHEF";
const POPUP_SAVE_VIDEO_REQUEST = "MEALIE_EXTENSION_POPUP_SAVE_VIDEO";
const MAX_EXTRACTED_TEXT_LENGTH = 180000;
const MAX_RETURNED_PREVIEW_LENGTH = 30000;
const MAX_RECIPE_IMAGE_BYTES = 20 * 1024 * 1024;
const AUTH_COOKIE_NAME = "mealie.access_token";
const SITE_LOCALE_COOKIE_NAME = "i18n_redirected";
const extensionI18n = globalThis.MealieExtensionI18n;
let activeBackgroundJobs = 0;
let backgroundKeepAliveTimer = null;

void updateActionTitle();
void injectBridgeIntoConfiguredMealieTabs();
chrome.runtime.onInstalled.addListener(() => {
  void updateActionTitle();
  void injectBridgeIntoConfiguredMealieTabs();
});
chrome.runtime.onStartup.addListener(() => {
  void updateActionTitle();
  void injectBridgeIntoConfiguredMealieTabs();
});
chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName === "sync" && (changes.interfaceLanguage || changes.mealieUrl)) {
    void updateActionTitle();
    if (changes.mealieUrl) {
      void injectBridgeIntoConfiguredMealieTabs();
    }
  }
});

async function injectBridgeIntoConfiguredMealieTabs() {
  try {
    const settings = await chrome.storage.sync.get(["mealieUrl"]);
    const mealieUrl = normalizeBaseUrl(settings.mealieUrl);
    if (!mealieUrl) {
      return;
    }
    const mealieOrigin = new URL(mealieUrl).origin;
    const tabs = await chrome.tabs.query({});
    const matchingTabs = tabs.filter(tab => tab.id && tab.url && sameOrigin(tab.url, mealieOrigin));
    await Promise.allSettled(matchingTabs.map(tab => chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ["i18n.js", "mealie-bridge.js"],
    })));
  }
  catch {
    // Static content scripts still load on the next Mealie page refresh.
  }
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  const handler = message?.type === POPUP_SAVE_WEBSITE_REQUEST
    ? saveWebsiteFromUrl
    : message?.type === POPUP_SAVE_RESTAURANT_REQUEST
      ? saveRestaurantFromUrl
      : message?.type === POPUP_SAVE_WANTED_BOOK_REQUEST
        ? saveWantedBookFromUrl
        : message?.type === POPUP_SAVE_CHEF_REQUEST
          ? saveChefFromUrl
      : message?.type === POPUP_SAVE_VIDEO_REQUEST
          ? saveVideoFromUrl
          : message?.type === IMAGE_BRIDGE_REQUEST
            ? updateRecipeImageFromBrowser
            : message?.type === BRIDGE_REQUEST || message?.type === POPUP_IMPORT_REQUEST
              ? importRecipeFromUrl
              : null;
  if (!handler) {
    return false;
  }

  runBackgroundJob(() => handler(message.payload))
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

async function runBackgroundJob(job) {
  activeBackgroundJobs += 1;
  startBackgroundKeepAlive();
  await updateBackgroundJobBadge();
  try {
    return await job();
  }
  finally {
    activeBackgroundJobs = Math.max(0, activeBackgroundJobs - 1);
    if (!activeBackgroundJobs) {
      stopBackgroundKeepAlive();
    }
    await updateBackgroundJobBadge();
  }
}

function startBackgroundKeepAlive() {
  if (backgroundKeepAliveTimer !== null) {
    return;
  }

  backgroundKeepAliveTimer = setInterval(() => {
    void chrome.runtime.getPlatformInfo().catch(() => {
      // The next tick can retry while a job is still active.
    });
  }, 20000);
}

function stopBackgroundKeepAlive() {
  if (backgroundKeepAliveTimer === null) {
    return;
  }
  clearInterval(backgroundKeepAliveTimer);
  backgroundKeepAliveTimer = null;
}

async function updateBackgroundJobBadge() {
  try {
    await chrome.action.setBadgeBackgroundColor({ color: "#ef8a17" });
    await chrome.action.setBadgeText({ text: activeBackgroundJobs ? String(activeBackgroundJobs) : "" });
  }
  catch {
    // Badge feedback is optional and must never interrupt an import.
  }
}

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
    const result = await importArticlePage(mealieUrl, authToken, payload, extraction, t);
    return withExtractionPreview(result, extraction);
  }

  const result = await importRecipePage(mealieUrl, authToken, payload, extraction, t);
  return withExtractionPreview(result, extraction);
}

async function updateRecipeImageFromBrowser(payload) {
  const translator = await extensionI18n.create(payload?.interfaceLanguage);
  const t = translator.t;
  const mealieUrl = normalizeBaseUrl(payload?.mealieUrl);
  const imageUrl = String(payload?.url || "").trim();
  const recipeSlug = String(payload?.recipeSlug || "").trim();
  if (!mealieUrl || !/^https?:\/\//i.test(mealieUrl)) {
    throw new Error(t("errors.invalid-mealie-url"));
  }
  if (!imageUrl || !/^https?:\/\//i.test(imageUrl)) {
    throw new Error(t("errors.invalid-recipe-url"));
  }
  if (!recipeSlug || recipeSlug.length > 255) {
    throw new Error(t("errors.request-failed", { status: 400 }));
  }

  const authToken = payload?.authToken || await findMealieAuthToken(mealieUrl);
  if (!authToken) {
    throw new Error(t("status.open-and-login"));
  }

  const downloaded = await downloadImageInBackgroundTab(imageUrl, translator);
  const imageBlob = dataUrlToBlob(downloaded.dataUrl, downloaded.contentType);
  const extension = imageExtension(downloaded.contentType, downloaded.finalUrl || imageUrl);
  if (!extension) {
    throw new Error(t("errors.request-failed", { status: 415 }));
  }
  const formData = new FormData();
  formData.append("image", imageBlob, `recipe-image.${extension}`);
  formData.append("extension", extension);

  const response = await fetch(
    `${mealieUrl}/api/recipes/${encodeURIComponent(recipeSlug)}/image`,
    {
      method: "PUT",
      credentials: "include",
      headers: authHeaders(authToken),
      body: formData,
    },
  );
  const body = await safeJson(response);
  if (!response.ok) {
    throw new Error(apiErrorMessage(body, response.status, t));
  }

  return { ok: true, image: body?.image || null };
}

async function saveWebsiteFromUrl(payload) {
  const translator = await extensionI18n.create(
    payload?.interfaceLanguage || payload?.translateLanguage,
  );
  const t = translator.t;
  const mealieUrl = normalizeBaseUrl(payload?.mealieUrl);
  const pageUrl = String(payload?.url || "").trim();
  if (!mealieUrl || !/^https?:\/\//i.test(mealieUrl)) {
    throw new Error(t("errors.invalid-mealie-url"));
  }
  if (!pageUrl || !/^https?:\/\//i.test(pageUrl)) {
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

  const extraction = await extractPageInBackgroundTab(pageUrl, translator);
  const response = await fetch(`${mealieUrl}/api/households/shopping-websites/browser-page`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(authToken),
    },
    body: JSON.stringify({
      url: extraction.url,
      page_title: extraction.title,
      page_text: extraction.markdown,
      ...websiteTypeOverrides(payload?.websiteType),
    }),
  });
  const body = await safeJson(response);
  if (!response.ok) {
    throw new Error(apiErrorMessage(body, response.status, t));
  }

  return withExtractionPreview({ ok: true, website: body }, extraction);
}

function websiteTypeOverrides(value) {
  if (value === "recipe") {
    return { is_recipe_site: true, is_shopping_site: false };
  }
  if (value === "shopping") {
    return { is_recipe_site: false, is_shopping_site: true };
  }
  if (value === "both") {
    return { is_recipe_site: true, is_shopping_site: true };
  }
  return {};
}

async function saveRestaurantFromUrl(payload) {
  const translator = await extensionI18n.create(
    payload?.interfaceLanguage || payload?.translateLanguage,
  );
  const t = translator.t;
  const mealieUrl = normalizeBaseUrl(payload?.mealieUrl);
  const pageUrl = String(payload?.url || "").trim();
  if (!mealieUrl || !/^https?:\/\//i.test(mealieUrl)) {
    throw new Error(t("errors.invalid-mealie-url"));
  }
  if (!pageUrl || !/^https?:\/\//i.test(pageUrl)) {
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

  const extraction = await extractPageInBackgroundTab(pageUrl, translator);
  const response = await fetch(`${mealieUrl}/api/households/restaurants/browser-page`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(authToken),
    },
    body: JSON.stringify({
      url: extraction.url,
      page_title: extraction.title,
      page_text: extraction.markdown,
    }),
  });
  const body = await safeJson(response);
  if (!response.ok) {
    throw new Error(apiErrorMessage(body, response.status, t));
  }

  return withExtractionPreview({ ok: true, restaurant: body }, extraction);
}

async function saveWantedBookFromUrl(payload) {
  return saveExtractedEntity(
    payload,
    "/api/households/wanted-books/browser-page",
    "book",
  );
}

async function saveChefFromUrl(payload) {
  return saveExtractedEntity(
    payload,
    "/api/households/chefs/browser-page",
    "chef",
  );
}

async function saveExtractedEntity(payload, endpoint, resultKey) {
  const translator = await extensionI18n.create(
    payload?.interfaceLanguage || payload?.translateLanguage,
  );
  const t = translator.t;
  const mealieUrl = normalizeBaseUrl(payload?.mealieUrl);
  const pageUrl = String(payload?.url || "").trim();
  if (!mealieUrl || !/^https?:\/\//i.test(mealieUrl)) {
    throw new Error(t("errors.invalid-mealie-url"));
  }
  if (!pageUrl || !/^https?:\/\//i.test(pageUrl)) {
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

  const extraction = await extractPageInBackgroundTab(pageUrl, translator);
  const response = await fetch(`${mealieUrl}${endpoint}`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(authToken),
    },
    body: JSON.stringify({
      url: extraction.url,
      page_title: extraction.title,
      page_text: extraction.markdown,
      page_image_url: extraction.imageUrl || null,
    }),
  });
  const body = await safeJson(response);
  if (!response.ok) {
    throw new Error(apiErrorMessage(body, response.status, t));
  }
  return withExtractionPreview({ ok: true, [resultKey]: body }, extraction);
}

async function saveVideoFromUrl(payload) {
  const translator = await extensionI18n.create(
    payload?.interfaceLanguage || payload?.translateLanguage,
  );
  const t = translator.t;
  const mealieUrl = normalizeBaseUrl(payload?.mealieUrl);
  const videoUrl = String(payload?.url || "").trim();
  if (!mealieUrl || !/^https?:\/\//i.test(mealieUrl)) {
    throw new Error(t("errors.invalid-mealie-url"));
  }
  if (!videoUrl || !/^https?:\/\//i.test(videoUrl)) {
    throw new Error(t("errors.invalid-video-url"));
  }

  const authToken = payload?.authToken || await findMealieAuthToken(mealieUrl);
  if (!authToken) {
    throw new Error(t("status.open-and-login"));
  }

  const status = await checkMealieStatus(mealieUrl, authToken, t);
  if (!statusAiEnabled(status)) {
    throw new Error(aiProviderStatusMessage(status, t));
  }

  await updateVideoDownloadSettings(mealieUrl, authToken, payload, t);

  const response = await fetch(`${mealieUrl}/api/households/videos/browser-page`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(authToken),
    },
    body: JSON.stringify({
      url: videoUrl,
      page_title: String(payload?.pageTitle || "").trim() || null,
      process_with_ai: true,
      download_video: payload?.downloadVideo !== false,
      create_recipe: payload?.videoCreateRecipe !== false,
      create_shopping_list: payload?.videoCreateRecipe !== false && payload?.createShoppingList !== false,
      organize_shopping_list: payload?.videoCreateRecipe !== false
        && payload?.createShoppingList !== false
        && payload?.organizeShoppingList !== false,
      include_ai_tips: payload?.includeAiTips !== false,
      include_mise_en_place: payload?.includeMiseEnPlace !== false,
      target_language: translationLanguageForRequest(payload?.translateLanguage),
    }),
  });
  const body = await safeJson(response);
  if (!response.ok) {
    throw new Error(apiErrorMessage(body, response.status, t));
  }

  return { ok: true, video: body };
}

async function updateVideoDownloadSettings(mealieUrl, authToken, payload, t) {
  const response = await fetch(`${mealieUrl}/api/households/videos/settings`, {
    method: "PUT",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(authToken),
    },
    body: JSON.stringify({
      download_by_default: payload?.downloadVideo !== false,
      quality: payload?.videoQuality || "best",
      container: payload?.videoContainer || "mp4",
      codec: payload?.videoCodec || "auto",
      audio_only: payload?.videoAudioOnly === true,
      audio_quality: payload?.videoAudioQuality || "best",
      save_subtitles: false,
      save_thumbnail: payload?.videoSaveThumbnail !== false,
      save_metadata: payload?.videoSaveMetadata !== false,
      fallback_to_lower_quality: payload?.videoFallbackQuality !== false,
    }),
  });
  const body = await safeJson(response);
  if (!response.ok) {
    throw new Error(apiErrorMessage(body, response.status, t));
  }
}

function withExtractionPreview(result, extraction) {
  return {
    ...result,
    preview: String(extraction?.markdown || "").slice(0, MAX_RETURNED_PREVIEW_LENGTH),
  };
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
    origin = new URL(normalizeBaseUrl(mealieUrl || "http://localhost:9925")).origin;
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
      include_mise_en_place: payload.includeMiseEnPlace !== false,
      include_item_images: payload.includeItemImages !== false,
      create_shopping_list: payload.createShoppingList !== false,
      organize_shopping_list_with_ai: payload.organizeShoppingListWithAi !== false,
      recipe_section: payload.extractMode === "sauce" ? "sauce" : "recipes",
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
      include_mise_en_place: payload.includeMiseEnPlace !== false,
      include_item_images: payload.includeItemImages !== false,
    }),
  });

  const body = await safeJson(response);
  if (!response.ok) {
    throw new Error(apiErrorMessage(body, response.status, t));
  }

  return {
    ok: true,
    article: body.article,
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
  const openTabs = await chrome.tabs.query({});
  let tab = openTabs.find(candidate => candidate.id && candidate.url && samePage(candidate.url, url));
  let createdForExtraction = false;
  if (!tab) {
    tab = await chrome.tabs.create({ url, active: false });
    createdForExtraction = true;
  }
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
    if (createdForExtraction) {
      try {
        await chrome.tabs.remove(tab.id);
      }
      catch {
        // The user may have closed the temporary tab before extraction ended.
      }
    }
  }
}

async function downloadImageInBackgroundTab(url, translator) {
  const openTabs = await chrome.tabs.query({});
  let tab = openTabs.find(candidate => candidate.id && candidate.url && samePage(candidate.url, url));
  let createdForDownload = false;
  if (!tab) {
    tab = await chrome.tabs.create({ url, active: false });
    createdForDownload = true;
  }
  if (!tab?.id) {
    throw new Error(translator.t("errors.open-link-failed"));
  }

  try {
    if (tab.status !== "complete") {
      await waitForTabComplete(tab.id, translator.t);
    }
    const [result] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: readImageDocument,
      args: [MAX_RECIPE_IMAGE_BYTES],
    });
    if (!result?.result?.dataUrl || !result.result.contentType) {
      throw new Error(translator.t("errors.request-failed", { status: 422 }));
    }
    return result.result;
  }
  finally {
    if (createdForDownload) {
      try {
        await chrome.tabs.remove(tab.id);
      }
      catch {
        // The user may have closed the temporary image tab already.
      }
    }
  }
}

async function readImageDocument(maxBytes) {
  const candidates = [
    document.images?.[0]?.currentSrc,
    document.images?.[0]?.src,
    window.location.href,
  ].filter(Boolean);
  let lastError = null;

  for (const candidate of [...new Set(candidates)]) {
    try {
      const response = await fetch(candidate, {
        cache: "no-store",
        credentials: "include",
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const contentLength = Number(response.headers.get("content-length") || 0);
      if (contentLength > maxBytes) {
        throw new Error("Image is too large");
      }
      const blob = await response.blob();
      if (!blob.type.toLowerCase().startsWith("image/") || !blob.size || blob.size > maxBytes) {
        throw new Error("The downloaded file is not a supported image");
      }
      const dataUrl = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result || ""));
        reader.onerror = () => reject(reader.error || new Error("Image read failed"));
        reader.readAsDataURL(blob);
      });
      return {
        dataUrl,
        contentType: blob.type.toLowerCase(),
        finalUrl: response.url || candidate,
      };
    }
    catch (error) {
      lastError = error;
    }
  }

  throw lastError || new Error("Image download failed");
}

function dataUrlToBlob(dataUrl, fallbackType) {
  const separator = dataUrl.indexOf(",");
  if (separator < 0) {
    throw new Error("Invalid image data");
  }
  const metadata = dataUrl.slice(0, separator);
  const contentType = metadata.match(/^data:([^;,]+)/i)?.[1] || fallbackType || "image/jpeg";
  const encoded = dataUrl.slice(separator + 1);
  const binary = metadata.includes(";base64") ? atob(encoded) : decodeURIComponent(encoded);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return new Blob([bytes], { type: contentType });
}

function imageExtension(contentType, url) {
  const byType = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/avif": "avif",
    "image/heic": "heic",
    "image/heif": "heic",
  };
  if (byType[contentType]) {
    return byType[contentType];
  }

  try {
    const extension = new URL(url).pathname.split(".").pop()?.toLowerCase();
    if (["jpg", "jpeg", "png", "webp", "avif", "heic"].includes(extension)) {
      return extension === "jpeg" ? "jpg" : extension;
    }
  }
  catch {
    // A valid content type is enough when the final URL is unavailable.
  }
  return null;
}

function samePage(firstUrl, secondUrl) {
  try {
    const first = new URL(firstUrl);
    const second = new URL(secondUrl);
    return first.origin === second.origin
      && first.pathname.replace(/\/$/, "") === second.pathname.replace(/\/$/, "")
      && first.search === second.search;
  }
  catch {
    return false;
  }
}

function waitForTabComplete(tabId, t) {
  return new Promise((resolve, reject) => {
    let settled = false;
    const timeout = setTimeout(() => {
      finish(new Error(t("errors.page-load-timeout")));
    }, 45000);

    const listener = (updatedTabId, changeInfo) => {
      if (updatedTabId === tabId && changeInfo.status === "complete") {
        finish();
      }
    };

    function cleanup() {
      clearTimeout(timeout);
      chrome.tabs.onUpdated.removeListener(listener);
    }

    function finish(error) {
      if (settled) {
        return;
      }
      settled = true;
      cleanup();
      if (error) {
        reject(error);
      }
      else {
        resolve();
      }
    }

    chrome.tabs.onUpdated.addListener(listener);
    void chrome.tabs.get(tabId)
      .then((currentTab) => {
        if (currentTab.status === "complete") {
          finish();
        }
      })
      .catch(() => finish(new Error(t("errors.open-link-failed"))));
  });
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
