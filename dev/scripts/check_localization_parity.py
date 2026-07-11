"""Validate locale, key, value, and placeholder parity for Mealie and its extension."""

from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Any

PLACEHOLDER_RE = re.compile(r"\{[^{}]+\}")
LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site_messages", type=Path)
    parser.add_argument("extension_messages", type=Path)
    parser.add_argument("--source-locale", default="en-US")
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


def locales(directory: Path) -> list[str]:
    return sorted(path.stem for path in directory.glob("*.json"))


def placeholder_set(value: Any) -> set[str]:
    return set(PLACEHOLDER_RE.findall(value)) if isinstance(value, str) else set()


def validate_directory(directory: Path, source_locale: str) -> tuple[int, list[str]]:
    source_path = directory / f"{source_locale}.json"
    source = flatten(json.loads(source_path.read_text(encoding="utf-8")))
    expected_keys = set(source)
    errors: list[str] = []

    for locale in locales(directory):
        target = flatten(json.loads((directory / f"{locale}.json").read_text(encoding="utf-8")))
        target_keys = set(target)
        missing = sorted(expected_keys - target_keys)
        extra = sorted(target_keys - expected_keys)
        empty = sorted(
            key for key in expected_keys & target_keys if not isinstance(target[key], str) or not target[key].strip()
        )
        invalid_placeholders = sorted(
            key for key in expected_keys & target_keys if placeholder_set(source[key]) != placeholder_set(target[key])
        )
        if missing or extra or empty or invalid_placeholders:
            errors.append(
                f"{directory}/{locale}: missing={missing[:5]}, extra={extra[:5]}, "
                f"empty={empty[:5]}, placeholders={invalid_placeholders[:5]}"
            )

    return len(source), errors


def main() -> None:
    args = parse_args()
    site_locales = locales(args.site_messages)
    extension_locales = locales(args.extension_messages)
    errors: list[str] = []
    if site_locales != extension_locales:
        errors.append(
            "Locale sets differ: "
            f"site-only={sorted(set(site_locales) - set(extension_locales))}, "
            f"extension-only={sorted(set(extension_locales) - set(site_locales))}"
        )

    site_keys, site_errors = validate_directory(args.site_messages, args.source_locale)
    extension_keys, extension_errors = validate_directory(args.extension_messages, args.source_locale)
    errors.extend(site_errors)
    errors.extend(extension_errors)
    if errors:
        raise SystemExit("\n".join(errors))

    LOGGER.info(
        f"Localization parity passed: {len(site_locales)} locales, "
        f"{site_keys} site keys, {extension_keys} extension keys"
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
