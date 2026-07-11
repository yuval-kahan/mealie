"""Fill missing Mealie locale keys with an OpenAI-compatible translation model."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import logging
import os
import queue
import re
import tempfile
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Iterable
from pathlib import Path
from typing import Any

PROVIDER_ENV = "MEALIE_TRANSLATION_PROVIDER"
PLACEHOLDER_RE = re.compile(r"\{[^{}]+\}")
FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
LOGGER = logging.getLogger(__name__)
LANGUAGE_NAMES = {
    "af-ZA": "Afrikaans (South Africa)",
    "ar-SA": "Arabic (Saudi Arabia)",
    "bg-BG": "Bulgarian",
    "ca-ES": "Catalan",
    "cs-CZ": "Czech",
    "da-DK": "Danish",
    "de-DE": "German",
    "el-GR": "Greek",
    "en-GB": "British English",
    "en-US": "American English",
    "es-ES": "Spanish (Spain)",
    "et-EE": "Estonian",
    "fi-FI": "Finnish",
    "fr-BE": "French (Belgium)",
    "fr-CA": "French (Canada)",
    "fr-FR": "French (France)",
    "gl-ES": "Galician",
    "he-IL": "Hebrew",
    "hr-HR": "Croatian",
    "hu-HU": "Hungarian",
    "is-IS": "Icelandic",
    "it-IT": "Italian",
    "ja-JP": "Japanese",
    "ko-KR": "Korean",
    "lt-LT": "Lithuanian",
    "lv-LV": "Latvian",
    "nl-NL": "Dutch",
    "no-NO": "Norwegian",
    "pl-PL": "Polish",
    "pt-BR": "Brazilian Portuguese",
    "pt-PT": "European Portuguese",
    "ro-RO": "Romanian",
    "ru-RU": "Russian",
    "sk-SK": "Slovak",
    "sl-SI": "Slovenian",
    "sr-SP": "Serbian",
    "sv-SE": "Swedish",
    "tr-TR": "Turkish",
    "uk-UA": "Ukrainian",
    "vi-VN": "Vietnamese",
    "zh-CN": "Simplified Chinese",
    "zh-TW": "Traditional Chinese",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("messages_dir", type=Path)
    parser.add_argument("--source-locale", default="en-US")
    parser.add_argument("--locales", nargs="*")
    parser.add_argument("--batch-size", type=int, default=70)
    parser.add_argument("--max-workers", type=int, default=0)
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument(
        "--translate-identical",
        action="store_true",
        help="Also translate non-English values that are still identical to en-US",
    )
    return parser.parse_args()


def flatten(value: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in value.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(item, dict):
            result.update(flatten(item, path))
        else:
            result[path] = item
    return result


def set_path(value: dict[str, Any], path: str, translated: Any) -> None:
    parts = path.split(".")
    current = value
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = translated


def chunks(items: list[tuple[str, str]], size: int) -> Iterable[dict[str, str]]:
    for index in range(0, len(items), size):
        yield dict(items[index : index + size])


def provider_config() -> dict[str, Any]:
    raw = os.environ.get(PROVIDER_ENV, "")
    if not raw:
        raise RuntimeError(f"Set {PROVIDER_ENV} to a provider JSON object")
    provider = json.loads(raw)
    required = ("base_url", "model", "api_keys")
    if any(not provider.get(key) for key in required):
        raise RuntimeError(f"{PROVIDER_ENV} must contain {', '.join(required)}")
    provider["api_keys"] = list(dict.fromkeys(key.strip() for key in provider["api_keys"] if key.strip()))
    return provider


def request_json(
    url: str,
    api_key: str,
    payload: dict[str, Any] | None = None,
    *,
    timeout: int = 180,
) -> tuple[int, str]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as error:
        return 0, str(error.reason)


def validate_api_key(base_url: str, model: str, api_key: str) -> bool:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply OK"}],
        "max_tokens": 2,
        "temperature": 0,
    }
    status, _ = request_json(f"{base_url.rstrip('/')}/chat/completions", api_key, payload, timeout=60)
    return status in {200, 429}


def translated_content(response_text: str) -> dict[str, str]:
    payload = json.loads(response_text)
    content = payload["choices"][0]["message"]["content"].strip()
    content = FENCE_RE.sub("", content).strip()
    result = json.loads(content)
    if not isinstance(result, dict):
        raise ValueError("Translation response is not a JSON object")
    return result


def placeholders(value: str) -> list[str]:
    return sorted(set(PLACEHOLDER_RE.findall(value)))


def needs_translation(
    key: str,
    source_value: Any,
    target_flat: dict[str, Any],
    locale: str,
    translate_identical: bool,
) -> bool:
    target_value = target_flat.get(key)
    if not isinstance(source_value, str):
        return False
    if not isinstance(target_value, str) or not target_value.strip():
        return True
    if placeholders(source_value) != placeholders(target_value):
        return True
    return translate_identical and locale != "en-GB" and target_value == source_value and len(source_value.strip()) >= 2


def validate_translation(source: dict[str, str], translated: dict[str, Any]) -> dict[str, str]:
    if set(source) != set(translated):
        missing = sorted(set(source) - set(translated))
        extra = sorted(set(translated) - set(source))
        raise ValueError(f"Translation keys differ; missing={missing[:5]}, extra={extra[:5]}")

    validated: dict[str, str] = {}
    for key, source_value in source.items():
        translated_value = translated[key]
        if not isinstance(translated_value, str) or not translated_value.strip():
            raise ValueError(f"Translation for {key} is empty or not text")
        if placeholders(source_value) != placeholders(translated_value):
            raise ValueError(f"Placeholders changed for {key}")
        validated[key] = translated_value.strip()
    return validated


def locale_examples(source: dict[str, Any], target: dict[str, Any], limit: int = 12) -> dict[str, dict[str, str]]:
    source_flat = flatten(source)
    target_flat = flatten(target)
    examples: dict[str, dict[str, str]] = {}
    for key, translated in target_flat.items():
        original = source_flat.get(key)
        if isinstance(original, str) and isinstance(translated, str) and original != translated:
            examples[key] = {"source": original, "translation": translated}
        if len(examples) >= limit:
            break
    return examples


class Translator:
    def __init__(self, provider: dict[str, Any], max_workers: int) -> None:
        self.base_url = provider["base_url"].rstrip("/")
        self.model = provider["model"]
        all_keys = provider["api_keys"]
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(all_keys)) as executor:
            valid = list(executor.map(lambda key: validate_api_key(self.base_url, self.model, key), all_keys))
        self.keys = [key for key, is_valid in zip(all_keys, valid, strict=True) if is_valid]
        if not self.keys:
            raise RuntimeError("No valid API keys are available")

        self.key_pool: queue.Queue[str] = queue.Queue()
        for key in self.keys:
            self.key_pool.put(key)
        self.max_workers = min(max_workers or len(self.keys), len(self.keys))
        self.print_lock = threading.Lock()
        LOGGER.info("Using %s valid API keys with %s workers", len(self.keys), self.max_workers)

    def translate_batch(
        self,
        locale: str,
        source: dict[str, str],
        examples: dict[str, dict[str, str]],
        batch_number: int,
    ) -> dict[str, str]:
        language = LANGUAGE_NAMES.get(locale, locale)
        system = (
            f"You are a professional software UI translator. Translate every JSON value into {language} "
            f"for locale {locale}. Return only one valid JSON object with exactly the original keys. "
            "Keep Mealie, AI, API, Gemini, OpenAI, URLs, file formats, Markdown/HTML, and all placeholders "
            "such as {count}, {name}, {start}, and {end} intact. Use concise, natural interface language. "
            "Never translate placeholder names and never add curly-brace placeholders to a string that has none. "
            "Match the terminology and regional variety shown in the examples. Never add explanations."
        )
        user = json.dumps(
            {"existing_style_examples": examples, "strings_to_translate": source},
            ensure_ascii=False,
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        last_error = "unknown error"
        for attempt in range(1, 9):
            api_key = self.key_pool.get()
            try:
                status, response_text = request_json(
                    f"{self.base_url}/chat/completions",
                    api_key,
                    payload,
                )
            finally:
                self.key_pool.put(api_key)

            if status == 200:
                try:
                    result = validate_translation(source, translated_content(response_text))
                    with self.print_lock:
                        LOGGER.info("%s: batch %s translated", locale, batch_number)
                    return result
                except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                    last_error = str(error)
                    payload["messages"].append(
                        {
                            "role": "user",
                            "content": (
                                f"The previous response failed validation: {last_error}. "
                                "Return the complete JSON object again. Keep the exact keys and exact placeholder "
                                "names from the source; do not invent curly-brace placeholders."
                            ),
                        }
                    )
            else:
                last_error = f"HTTP {status}: {response_text[:240]}"

            if attempt < 8:
                delay = min(15 * attempt, 60) if status == 429 else min(2**attempt, 30)
                time.sleep(delay)

        raise RuntimeError(f"{locale} batch {batch_number} failed: {last_error}")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent, newline="\n") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")
        temporary_path = Path(file.name)
    temporary_path.replace(path)


def main() -> None:
    args = parse_args()
    source_path = args.messages_dir / f"{args.source_locale}.json"
    source_nested = json.loads(source_path.read_text(encoding="utf-8"))
    source_flat = flatten(source_nested)
    if args.locales:
        locale_paths = [args.messages_dir / f"{locale}.json" for locale in args.locales]
    else:
        locale_paths = sorted(args.messages_dir.glob("*.json"))

    audits: list[tuple[Path, dict[str, Any], list[tuple[str, str]]]] = []
    for path in locale_paths:
        if path.stem == args.source_locale:
            continue
        target = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        target_flat = flatten(target)
        missing = [
            (key, value)
            for key, value in source_flat.items()
            if needs_translation(key, value, target_flat, path.stem, args.translate_identical)
        ]
        LOGGER.info("%s: %s missing keys", path.stem, len(missing))
        audits.append((path, target, missing))

    if args.audit_only:
        if any(missing for _, _, missing in audits):
            raise SystemExit(1)
        return

    pending = [(path, target, missing) for path, target, missing in audits if missing]
    if not pending:
        LOGGER.info("All locale files already match the source locale")
        return

    translator = Translator(provider_config(), args.max_workers)
    for path, target, missing in pending:
        batches = list(chunks(missing, args.batch_size))
        examples = locale_examples(source_nested, target)
        translated: dict[str, str] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=translator.max_workers) as executor:
            futures = {
                executor.submit(translator.translate_batch, path.stem, batch, examples, index): index
                for index, batch in enumerate(batches, start=1)
            }
            for future in concurrent.futures.as_completed(futures):
                translated.update(future.result())

        for key, value in translated.items():
            set_path(target, key, value)
        write_json(path, target)
        LOGGER.info("%s: saved %s translations", path.stem, len(translated))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
