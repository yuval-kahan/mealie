(() => {
if (globalThis.__MEALIE_EXTENSION_BRIDGE_INSTALLED__) {
  return;
}
globalThis.__MEALIE_EXTENSION_BRIDGE_INSTALLED__ = true;

const BRIDGE_REQUEST = "MEALIE_EXTENSION_IMPORT_RECIPE_URL";
const BRIDGE_ACK = "MEALIE_EXTENSION_IMPORT_RECIPE_URL_ACK";
const BRIDGE_RESULT = "MEALIE_EXTENSION_IMPORT_RECIPE_URL_RESULT";
const IMAGE_BRIDGE_REQUEST = "MEALIE_EXTENSION_IMPORT_RECIPE_IMAGE_URL";
const IMAGE_BRIDGE_ACK = "MEALIE_EXTENSION_IMPORT_RECIPE_IMAGE_URL_ACK";
const IMAGE_BRIDGE_RESULT = "MEALIE_EXTENSION_IMPORT_RECIPE_IMAGE_URL_RESULT";
const AUTH_COOKIE_NAME = "mealie.access_token";
const extensionI18n = globalThis.MealieExtensionI18n;

window.addEventListener("message", (event) => {
  void handleBridgeMessage(event);
});

async function handleBridgeMessage(event) {
  const bridgeTypes = {
    [BRIDGE_REQUEST]: { ack: BRIDGE_ACK, result: BRIDGE_RESULT },
    [IMAGE_BRIDGE_REQUEST]: { ack: IMAGE_BRIDGE_ACK, result: IMAGE_BRIDGE_RESULT },
  };
  const bridge = event?.data ? bridgeTypes[event.data.type] : null;
  if (event.source !== window || !bridge) {
    return;
  }

  const requestId = event.data.requestId;
  const payload = event.data.payload || {};
  if (!requestId || !isSameOrigin(payload.mealieUrl, window.location.origin)) {
    return;
  }
  window.postMessage({ type: bridge.ack, requestId }, window.location.origin);

  let translator;
  try {
    translator = await extensionI18n.create(
      payload.interfaceLanguage || payload.translateLanguage,
    );
  }
  catch {
    translator = { t: key => key };
  }

  try {
    chrome.runtime.sendMessage(
      {
        type: event.data.type,
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
            type: bridge.result,
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
  catch (error) {
    window.postMessage(
      {
        type: bridge.result,
        requestId,
        response: { ok: false, error: error?.message || translator.t("errors.bridge-failed") },
      },
      window.location.origin,
    );
  }
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
})();
