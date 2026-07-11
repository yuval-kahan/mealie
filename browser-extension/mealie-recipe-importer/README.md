# Mealie AI Browser Importer Extension

Chrome/Edge extension for importing a recipe or article from the page that is open in the user's browser.

Why this exists:

- Some recipe sites block server-side scrapers or AI fetchers.
- The browser can often see the page because the user opened it manually.
- This extension extracts structured recipe data, visible page text, and source metadata, then sends that text to Mealie's AI creation endpoints.

## Install Locally

1. Open Chrome or Edge.
2. Go to `chrome://extensions` or `edge://extensions`.
3. Enable Developer mode.
4. Click **Load unpacked**.
5. Select this folder: `browser-extension/mealie-recipe-importer`.

## Usage

1. Open a recipe or article page in the browser.
2. Click the Mealie AI extension button.
3. Set the Mealie URL, usually `http://localhost:3000`.
4. Make sure you are logged in to Mealie in the same browser.
5. Choose whether to auto-detect the page type, extract a recipe, or extract an article.
6. Keep the interface language on **Automatic** to follow the Mealie site language, with the browser language as a fallback, or select one of Mealie's existing 42 locales.
7. Choose a target translation language from the same locales supported by Mealie.
8. Choose whether to create a shopping list, organize it with AI, and add AI tips / ingredient-variety notes.
9. Click the primary **Send to AI** action in the selected interface language.

## Languages

- The popup, status messages, errors, result links, preview labels, and extraction metadata are translated into exactly the same 42 locales that already exist in Mealie.
- No extension-only language is added. The locale lists are checked for exact parity with `frontend/app/lang/messages`.
- Automatic mode follows Mealie's locale cookie first and the browser language second. A manual popup selection changes only the extension.
- Arabic and Hebrew switch the complete popup to RTL automatically.
- Chrome manifest metadata is generated for the 37 locale codes supported by the Chrome Web Store. Afrikaans, Galician, Icelandic, and regional French variants remain fully available inside the popup through the runtime locale selector; Chrome uses its closest supported manifest locale for store metadata.
- Runtime messages fall back to `en-US` only if a locale file cannot be loaded.

If the page language already matches the selected translation language, the extension sends the recipe without a translation target.

The extension also exposes a browser bridge to Mealie pages. When Mealie's regular server-side link import fails because a site blocks the server, Mealie can ask the installed extension to open the link in the user's browser, extract the page, and send it back automatically.

The popup checks whether Mealie has an active AI provider before enabling its primary send action. It reads the existing Mealie login cookie through the browser and falls back to reading the login token from an open Mealie tab. It does not store a separate AI key. If the extension cannot find an active Mealie login, it shows a connect button that opens or focuses Mealie. If AI is not configured in Mealie, the extension shows a localized message and blocks sending.

The extension calls:

`POST /api/recipes/create/browser-page`

or:

`POST /api/households/articles/browser-page`

The recipe endpoint creates a recipe from extracted page text and can optionally create an AI-organized shopping list.

The article endpoint creates an article from extracted page text, translates it when needed, adds categories/tags, and can also create a recipe and AI-organized shopping list when the article includes a complete recipe. When a page is only a recipe, the article endpoint can create only the recipe instead of saving a fake article. The auto-detect mode uses this article endpoint so the AI can classify the page.

The extension does not use a separate OpenAI/Gemini key. It calls your Mealie site, and Mealie uses the AI provider configured inside the site.
