import re

SPACE_RE = re.compile(r"\s+")
LEADING_QUANTITY_RE = re.compile(
    r"^\s*(?:\d+(?:[.,]\d+)?|[¼½¾⅓⅔⅛⅜⅝⅞])\s*(?:[x×]\s*)?",
)
TRAILING_QUANTITY_RE = re.compile(r"\s*[x×]\s*\d+(?:[.,]\d+)?\s*$", re.IGNORECASE)


def normalize_equipment_name(value: str | None) -> str:
    """Return a canonical tool name without a recipe-specific item count."""
    original = SPACE_RE.sub(" ", str(value or "")).strip()
    if not original:
        return ""

    normalized = LEADING_QUANTITY_RE.sub("", original)
    normalized = TRAILING_QUANTITY_RE.sub("", normalized)
    normalized = normalized.strip(" \t\r\n-–—")
    return normalized or original
