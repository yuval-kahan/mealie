globalThis.MealieExtensionI18n = (() => {
  const DEFAULT_LOCALE = "en-US";
  const AUTOMATIC_LOCALE = "auto";
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
  const RTL_LANGUAGES = new Set(["ar", "he"]);
  const messageCache = new Map();

  function normalizeLocale(value) {
    return String(value || "").trim().replaceAll("_", "-");
  }

  function primaryLanguage(value) {
    return normalizeLocale(value).split("-")[0].toLocaleLowerCase();
  }

  function exactLocale(value) {
    const normalized = normalizeLocale(value).toLocaleLowerCase();
    return LOCALE_CODES.find(locale => locale.toLocaleLowerCase() === normalized) || null;
  }

  function localeFromCandidate(value) {
    const exact = exactLocale(value);
    if (exact) {
      return exact;
    }

    const normalized = normalizeLocale(value);
    const primary = primaryLanguage(normalized);
    const region = normalized.split("-")[1]?.toLocaleUpperCase();
    if (primary === "zh") {
      return ["TW", "HK", "MO"].includes(region) || /hant/i.test(normalized) ? "zh-TW" : "zh-CN";
    }
    if (primary === "pt") {
      return region === "BR" ? "pt-BR" : "pt-PT";
    }
    if (primary === "fr") {
      return region === "BE" ? "fr-BE" : region === "CA" ? "fr-CA" : "fr-FR";
    }
    if (primary === "en") {
      return region === "GB" ? "en-GB" : "en-US";
    }
    return LOCALE_CODES.find(locale => primaryLanguage(locale) === primary) || null;
  }

  function browserLanguageCandidates() {
    const candidates = [];
    if (typeof navigator !== "undefined") {
      candidates.push(...(navigator.languages || []), navigator.language);
    }
    try {
      candidates.push(chrome.i18n?.getUILanguage?.());
    }
    catch {
      // Browser locale detection is best effort.
    }
    return candidates.filter(Boolean);
  }

  function resolveLocale(preferred = AUTOMATIC_LOCALE) {
    const candidates = preferred && preferred !== AUTOMATIC_LOCALE
      ? [preferred, ...browserLanguageCandidates()]
      : browserLanguageCandidates();
    for (const candidate of candidates) {
      const locale = localeFromCandidate(candidate);
      if (locale) {
        return locale;
      }
    }
    return DEFAULT_LOCALE;
  }

  function valueAtPath(messages, path) {
    return String(path || "")
      .split(".")
      .reduce((value, key) => value?.[key], messages);
  }

  function interpolate(value, params = {}) {
    return String(value).replace(/\{([^{}]+)\}/g, (match, key) =>
      Object.hasOwn(params, key) ? String(params[key]) : match,
    );
  }

  async function loadLocale(locale) {
    const resolved = resolveLocale(locale);
    if (!messageCache.has(resolved)) {
      const url = chrome.runtime.getURL(`locales/${resolved}.json`);
      messageCache.set(
        resolved,
        fetch(url).then((response) => {
          if (!response.ok) {
            throw new Error(`Unable to load extension locale ${resolved}`);
          }
          return response.json();
        }),
      );
    }
    return await messageCache.get(resolved);
  }

  async function create(preferred = AUTOMATIC_LOCALE) {
    const locale = resolveLocale(preferred);
    const fallback = await loadLocale(DEFAULT_LOCALE);
    let messages = fallback;
    if (locale !== DEFAULT_LOCALE) {
      try {
        messages = await loadLocale(locale);
      }
      catch {
        messages = fallback;
      }
    }

    const t = (key, params = {}) => {
      const value = valueAtPath(messages, key) ?? valueAtPath(fallback, key) ?? key;
      return interpolate(value, params);
    };
    return {
      locale,
      direction: RTL_LANGUAGES.has(primaryLanguage(locale)) ? "rtl" : "ltr",
      messages,
      t,
    };
  }

  function localizeDocument(translator) {
    if (typeof document === "undefined") {
      return;
    }
    document.documentElement.lang = translator.locale;
    document.documentElement.dir = translator.direction;
    document.title = translator.t("extension.name");
    document.querySelectorAll("[data-i18n]").forEach((element) => {
      element.textContent = translator.t(element.dataset.i18n);
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
      element.setAttribute("placeholder", translator.t(element.dataset.i18nPlaceholder));
    });
    document.querySelectorAll("[data-i18n-title]").forEach((element) => {
      element.setAttribute("title", translator.t(element.dataset.i18nTitle));
    });
  }

  function extractionLabels(translator) {
    const t = translator.t;
    return {
      recipePage: t("extraction.recipe-page"),
      sourceUrl: t("extraction.source-url"),
      sourceImage: t("extraction.source-image"),
      structuredData: t("extraction.structured-data"),
      visibleText: t("extraction.visible-text"),
      name: t("extraction.name"),
      description: t("extraction.description"),
      author: t("extraction.author"),
      yield: t("extraction.yield"),
      prepTime: t("extraction.prep-time"),
      cookTime: t("extraction.cook-time"),
      totalTime: t("extraction.total-time"),
      category: t("extraction.category"),
      cuisine: t("extraction.cuisine"),
      keywords: t("extraction.keywords"),
      image: t("extraction.image"),
      ingredients: t("extraction.ingredients"),
      instructions: t("extraction.instructions"),
      contentTruncated: t("extraction.content-truncated"),
    };
  }

  return {
    AUTOMATIC_LOCALE,
    DEFAULT_LOCALE,
    LOCALE_CODES,
    create,
    extractionLabels,
    localizeDocument,
    primaryLanguage,
    resolveLocale,
  };
})();
