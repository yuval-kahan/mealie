export default defineNuxtPlugin((nuxtApp) => {
  if (!import.meta.dev) {
    return;
  }

  function logClientError(prefix: string, error: unknown, info?: string) {
    if (error instanceof Error) {
      console.error(prefix, info || "", error.message, error.stack || "");
      return;
    }

    console.error(prefix, info || "", String(error));
  }

  nuxtApp.hook("vue:error", (error, _instance, info) => {
    logClientError("[Mealie Vue error]", error, info);
  });

  nuxtApp.hook("app:error", (error) => {
    logClientError("[Mealie app error]", error);
  });

  const trackedWindow = window as Window & { __mealieUnhandledRejectionLogger?: boolean };
  if (!trackedWindow.__mealieUnhandledRejectionLogger) {
    trackedWindow.__mealieUnhandledRejectionLogger = true;
    window.addEventListener("unhandledrejection", (event) => {
      logClientError("[Mealie unhandled promise rejection]", event.reason);
    });
  }
});
