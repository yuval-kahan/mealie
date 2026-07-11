const BRIDGE_REQUEST = "MEALIE_EXTENSION_IMPORT_RECIPE_URL";
const BRIDGE_ACK = "MEALIE_EXTENSION_IMPORT_RECIPE_URL_ACK";
const BRIDGE_RESULT = "MEALIE_EXTENSION_IMPORT_RECIPE_URL_RESULT";
const AUTH_COOKIE_NAME = "mealie.access_token";
const extensionI18n = globalThis.MealieExtensionI18n;

window.addEventListener("message", (event) => {
  void handleBridgeMessage(event);
});

async function handleBridgeMessage(event) {
  if (event.source !== window || !event.data || event.data.type !== BRIDGE_REQUEST) {
    return;
  }

  const requestId = event.data.requestId;
  const payload = event.data.payload || {};
  if (!requestId || !isSameOrigin(payload.mealieUrl, window.location.origin)) {
    return;
  }
  const translator = await extensionI18n.create(
    payload.interfaceLanguage || payload.translateLanguage,
  );

  window.postMessage({ type: BRIDGE_ACK, requestId }, window.location.origin);

  chrome.runtime.sendMessage(
    {
      type: BRIDGE_REQUEST,
      requestId,
      payload: {
        ...payload,
        authToken: readCookieValue(AUTH_COOKIE_NAME),
      },
    },
    (response) => {
      const runtimeError = chrome.runtime.lastError;
      window.postMessage(
        {
          type: BRIDGE_RESULT,
          requestId,
          response: runtimeError
            ? { ok: false, error: runtimeError.message || translator.t("errors.bridge-failed") }
            : response,
        },
        window.location.origin,
      );
    },
  );
}

function isSameOrigin(url, origin) {
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
