const STORAGE_KEYS = {
  mealieUrl: "mealieUrl",
  extractMode: "extractMode",
  interfaceLanguage: "interfaceLanguage",
  translateLanguage: "translateLanguage",
  createShoppingList: "createShoppingList",
  organizeShoppingList: "organizeShoppingList",
  includeAiTips: "includeAiTips",
  includeItemImages: "includeItemImages",
};

const DEFAULT_SETTINGS = {
  mealieUrl: "http://localhost:3000",
  extractMode: "auto",
  interfaceLanguage: "auto",
  translateLanguage: "he-IL",
  createShoppingList: true,
  organizeShoppingList: true,
  includeAiTips: true,
  includeItemImages: true,
};

const MAX_EXTRACTED_TEXT_LENGTH = 180000;
const AUTH_COOKIE_NAME = "mealie.access_token";
const SITE_LOCALE_COOKIE_NAME = "i18n_redirected";
const extensionI18n = globalThis.MealieExtensionI18n;

const elements = {
  mealieUrl: document.getElementById("mealieUrl"),
  extractMode: document.getElementById("extractMode"),
  interfaceLanguage: document.getElementById("interfaceLanguage"),
  translateLanguage: document.getElementById("translateLanguage"),
  createShoppingList: document.getElementById("createShoppingList"),
  organizeShoppingList: document.getElementById("organizeShoppingList"),
  includeAiTips: document.getElementById("includeAiTips"),
  includeItemImages: document.getElementById("includeItemImages"),
  extractOnly: document.getElementById("extractOnly"),
  sendToMealie: document.getElementById("sendToMealie"),
  saveWebsite: document.getElementById("saveWebsite"),
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
let statusCheckController = null;
let statusCheckRunId = 0;
let translator = null;

init();

async function init() {
  const settings = await loadSettings();
  await applyPreferredInterfaceLanguage(settings);
  populateInterfaceLanguageOptions();
  populateLanguageOptions();
  applySettings(settings);
  await chrome.storage.sync.remove("apiToken");

  [
    elements.mealieUrl,
    elements.extractMode,
    elements.interfaceLanguage,
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
  elements.saveWebsite.addEventListener("click", handleSaveWebsite);
  elements.connectMealie.addEventListener("click", handleConnectMealie);
  elements.extractMode.addEventListener("change", updateModeText);
  elements.interfaceLanguage.addEventListener("change", handleInterfaceLanguageChange);
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
    ? new Intl.DisplayNames([translator?.locale || extensionI18n.DEFAULT_LOCALE], { type: "language" })
    : null;

  elements.translateLanguage.replaceChildren(
    ...extensionI18n.LOCALE_CODES.map((code) => {
      const option = document.createElement("option");
      option.value = code;
      option.textContent = `${languageDisplayName(code, displayNames)} - ${code}`;
      return option;
    }),
  );
}

function populateInterfaceLanguageOptions() {
  const selected = elements.interfaceLanguage.value || DEFAULT_SETTINGS.interfaceLanguage;
  const displayNames = typeof Intl !== "undefined" && Intl.DisplayNames
    ? new Intl.DisplayNames([translator?.locale || extensionI18n.DEFAULT_LOCALE], { type: "language" })
    : null;
  const automatic = document.createElement("option");
  automatic.value = extensionI18n.AUTOMATIC_LOCALE;
  automatic.textContent = translator.t("settings.automatic-language");
  const options = extensionI18n.LOCALE_CODES.map((code) => {
    const option = document.createElement("option");
    option.value = code;
    option.textContent = `${languageDisplayName(code, displayNames)} - ${code}`;
    return option;
  });
  elements.interfaceLanguage.replaceChildren(automatic, ...options);
  elements.interfaceLanguage.value = selected;
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
  elements.interfaceLanguage.value = settings.interfaceLanguage || DEFAULT_SETTINGS.interfaceLanguage;
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

async function applyInterfaceLanguage(preferred) {
  translator = await extensionI18n.create(preferred || DEFAULT_SETTINGS.interfaceLanguage);
  extensionI18n.localizeDocument(translator);
  await chrome.action?.setTitle?.({ title: translator.t("extension.action-title") });
}

async function applyPreferredInterfaceLanguage(settings) {
  const preferred = settings.interfaceLanguage === extensionI18n.AUTOMATIC_LOCALE
    ? await findMealieLocale(settings.mealieUrl) || extensionI18n.AUTOMATIC_LOCALE
    : settings.interfaceLanguage;
  await applyInterfaceLanguage(preferred);
}

async function handleInterfaceLanguageChange() {
  const targetLanguage = elements.translateLanguage.value;
  await saveSettingsFromForm();
  await applyPreferredInterfaceLanguage(currentSettings());
  populateInterfaceLanguageOptions();
  populateLanguageOptions();
  elements.translateLanguage.value = targetLanguage || DEFAULT_SETTINGS.translateLanguage;
  updateModeText();
  setStatus("");
}

function currentSettings() {
  return {
    mealieUrl: normalizeBaseUrl(elements.mealieUrl.value || DEFAULT_SETTINGS.mealieUrl),
    extractMode: elements.extractMode.value || DEFAULT_SETTINGS.extractMode,
    interfaceLanguage: elements.interfaceLanguage.value || DEFAULT_SETTINGS.interfaceLanguage,
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
    elements.sendToMealie.textContent = translator.t("actions.send-article");
    return;
  }
  if (mode === "recipe") {
    elements.sendToMealie.textContent = translator.t("actions.send-recipe");
    return;
  }
  elements.sendToMealie.textContent = translator.t("actions.send-auto");
}

function normalizeBaseUrl(value) {
  return String(value || "").trim().replace(/\/+$/, "");
}

async function findMealieLocale(mealieUrl) {
  let origin = "";
  try {
    origin = new URL(normalizeBaseUrl(mealieUrl)).origin;
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
  statusCheckController?.abort();
  statusCheckController = null;
  statusCheckRunId += 1;
  statusCheckTimer = setTimeout(() => {
    statusCheckTimer = null;
    void checkMealieStatus();
  }, 500);
}

async function checkMealieStatus() {
  clearTimeout(statusCheckTimer);
  statusCheckTimer = null;
  statusCheckController?.abort();
  const controller = new AbortController();
  const runId = ++statusCheckRunId;
  statusCheckController = controller;
  const settings = currentSettings();
  if (settings.interfaceLanguage === extensionI18n.AUTOMATIC_LOCALE) {
    const previousLocale = translator.locale;
    await applyPreferredInterfaceLanguage(settings);
    if (runId !== statusCheckRunId) {
      return false;
    }
    if (translator.locale !== previousLocale) {
      populateInterfaceLanguageOptions();
      populateLanguageOptions();
      applySettings(settings);
    }
  }
  mealieSiteReady = false;
  elements.connectMealie.hidden = true;
  updateActionState();

  try {
    const authToken = await findMealieAuthToken(settings.mealieUrl);
    if (controller.signal.aborted || runId !== statusCheckRunId) {
      return false;
    }
    if (!authToken) {
      setStatus(translator.t("status.open-and-login"), "error");
      elements.connectMealie.hidden = false;
      return false;
    }

    const response = await fetch(`${settings.mealieUrl}/api/recipes/create/browser-page/status`, {
      credentials: "include",
      headers: authHeaders(authToken),
      signal: controller.signal,
    });
    const payload = await safeJson(response);
    if (controller.signal.aborted || runId !== statusCheckRunId) {
      return false;
    }

    if (response.status === 401 || response.status === 403) {
      setStatus(translator.t("status.login-required"), "error");
      elements.connectMealie.hidden = false;
      return false;
    }

    if (!response.ok) {
      setStatus(translator.t("status.check-failed", { status: response.status }), "error");
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
  catch (error) {
    if (error?.name === "AbortError") {
      return false;
    }
    setStatus(translator.t("status.connection-failed"), "error");
    elements.connectMealie.hidden = false;
    return false;
  }
  finally {
    if (runId === statusCheckRunId) {
      statusCheckController = null;
      updateActionState();
    }
  }
}

function aiProviderStatusMessage(payload) {
  if (statusProviderCount(payload) > 0 && !statusDefaultProviderConfigured(payload)) {
    return translator.t("status.provider-no-default");
  }

  return translator.t("status.provider-required");
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
  setStatus(translator.t("status.mealie-opened"), "success");
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
  setStatus(translator.t("status.extracting"));

  try {
    lastExtraction = await extractCurrentTab();
    showPreview(lastExtraction.markdown);
    setStatus(
      translator.t("status.extracted", {
        title: lastExtraction.title || translator.t("status.untitled"),
      }),
      "success",
    );
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
  setStatus(translator.t("status.extracting-and-sending"));

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
        messages.push(translator.t("status.article-created", { title: article.title }));
      }
      if (recipeSlug) {
        messages.push(translator.t("status.recipe-created-too", { name: recipeSlug }));
      }
      if (shoppingListName) {
        messages.push(translator.t("status.shopping-list", { name: shoppingListName }));
      }
      if (recipeError) {
        messages.push(translator.t("status.attention", { message: recipeError }));
      }
      if (shoppingListError) {
        messages.push(translator.t("status.attention", { message: shoppingListError }));
      }

      setStatus(
        messages.join("\n") || translator.t("status.extraction-finished"),
        recipeError || shoppingListError ? "" : "success",
      );
      if (article?.id) {
        showArticleLink(settings.mealieUrl, article.id);
      }
      else if (recipeSlug) {
        showRecipeLink(settings.mealieUrl, recipeSlug, response.groupSlug || response.group_slug);
      }
      return;
    }

    const response = await createRecipeFromBrowserPage(settings, extraction);
    const messages = [
      translator.t("status.recipe-created", { name: response.recipeSlug || response.recipe_slug }),
    ];
    const shoppingListName = response.shoppingListName || response.shopping_list_name;
    const shoppingListError = response.shoppingListError || response.shopping_list_error;

    if (shoppingListName) {
      messages.push(translator.t("status.shopping-list", { name: shoppingListName }));
    }
    if (shoppingListError) {
      messages.push(translator.t("status.attention", { message: shoppingListError }));
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

async function handleSaveWebsite() {
  setBusy(true);
  hideRecipeLink();
  setStatus(translator.t("status.saving-website"));

  try {
    const settings = currentSettings();
    await chrome.storage.sync.set(settings);
    if (!await checkMealieStatus()) {
      return;
    }

    const extraction = lastExtraction || await extractCurrentTab();
    lastExtraction = extraction;
    showPreview(extraction.markdown);
    const website = await createShoppingWebsiteFromBrowserPage(settings, extraction);
    setStatus(translator.t("status.website-saved", { name: website.name }), "success");
    showWebsiteLink(settings.mealieUrl);
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
    return translator.t("status.processing-article");
  }
  if (mode === "recipe") {
    return translator.t("status.processing-recipe");
  }
  return translator.t("status.processing-auto");
}

async function extractCurrentTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) {
    throw new Error(translator.t("errors.active-tab-missing"));
  }

  if (!tab.url || /^chrome:|^edge:|^about:|^chrome-extension:/i.test(tab.url)) {
    throw new Error(translator.t("errors.unsupported-page"));
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

async function createRecipeFromBrowserPage(settings, extraction) {
  const endpoint = `${settings.mealieUrl}/api/recipes/create/browser-page`;
  const authToken = await findMealieAuthToken(settings.mealieUrl);
  if (!authToken) {
    throw new Error(translator.t("status.open-and-login"));
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
    throw new Error(translator.t("status.open-and-login"));
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

async function createShoppingWebsiteFromBrowserPage(settings, extraction) {
  const authToken = await findMealieAuthToken(settings.mealieUrl);
  if (!authToken) {
    throw new Error(translator.t("status.open-and-login"));
  }

  const response = await fetch(`${settings.mealieUrl}/api/households/shopping-websites/browser-page`, {
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
    return translator.t("errors.request-unauthorized");
  }
  return translator.t("errors.request-failed", { status });
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
  elements.saveWebsite.disabled = isBusy || !mealieSiteReady;
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
    translator.t("links.open-recipe"),
  );
}

function showArticleLink(baseUrl, articleId) {
  if (!articleId) {
    hideRecipeLink();
    return;
  }

  showResultLink(
    `${normalizeBaseUrl(baseUrl)}/articles/${encodeURIComponent(articleId)}`,
    translator.t("links.open-article"),
  );
}

function showWebsiteLink(baseUrl) {
  showResultLink(
    `${normalizeBaseUrl(baseUrl)}/shopping-websites`,
    translator.t("links.open-websites"),
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
  elements.recipeLink.textContent = translator.t("links.open-recipe");
}

function errorMessage(error) {
  return error?.message || translator.t("errors.unexpected");
}

function translationLanguageForRequest(targetLanguage, _pageLanguage) {
  const target = languagePrimary(targetLanguage);
  if (!target) {
    return null;
  }

  // The selected language is an output-language contract, not merely a request
  // to translate a page that appears to be in another language. Always send it
  // so Mealie can force every recipe field into the selected locale.
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
