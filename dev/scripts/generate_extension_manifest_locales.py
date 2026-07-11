"""Generate Chrome manifest locale files from the extension's runtime locales."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

CHROME_LOCALES = {
    "ar": "ar-SA",
    "bg": "bg-BG",
    "ca": "ca-ES",
    "cs": "cs-CZ",
    "da": "da-DK",
    "de": "de-DE",
    "el": "el-GR",
    "en": "en-US",
    "en_GB": "en-GB",
    "es": "es-ES",
    "et": "et-EE",
    "fi": "fi-FI",
    "fr": "fr-FR",
    "he": "he-IL",
    "hr": "hr-HR",
    "hu": "hu-HU",
    "it": "it-IT",
    "ja": "ja-JP",
    "ko": "ko-KR",
    "lt": "lt-LT",
    "lv": "lv-LV",
    "nl": "nl-NL",
    "no": "no-NO",
    "pl": "pl-PL",
    "pt_BR": "pt-BR",
    "pt_PT": "pt-PT",
    "ro": "ro-RO",
    "ru": "ru-RU",
    "sk": "sk-SK",
    "sl": "sl-SI",
    "sr": "sr-SP",
    "sv": "sv-SE",
    "tr": "tr-TR",
    "uk": "uk-UA",
    "vi": "vi-VN",
    "zh_CN": "zh-CN",
    "zh_TW": "zh-TW",
}
LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime_locales", type=Path)
    parser.add_argument("manifest_locales", type=Path)
    return parser.parse_args()


def message(value: str) -> dict[str, str]:
    return {"message": value}


def manifest_messages(runtime: dict[str, Any]) -> dict[str, dict[str, str]]:
    extension = runtime["extension"]
    return {
        "extensionName": message(extension["manifest-name"]),
        "extensionDescription": message(extension["description"]),
        "actionTitle": message(extension["action-title"]),
    }


def main() -> None:
    args = parse_args()
    args.manifest_locales.mkdir(parents=True, exist_ok=True)

    for chrome_locale, runtime_locale in CHROME_LOCALES.items():
        source = args.runtime_locales / f"{runtime_locale}.json"
        runtime = json.loads(source.read_text(encoding="utf-8"))
        target = args.manifest_locales / chrome_locale / "messages.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(manifest_messages(runtime), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    LOGGER.info("Generated %s Chrome manifest locales", len(CHROME_LOCALES))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
