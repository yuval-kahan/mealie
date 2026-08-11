from __future__ import annotations

from collections.abc import Mapping

BOOK_LIBRARY_CATEGORIES = (
    "לימוד, יסודות ומדע",
    "מטבחים לפי מדינה",
    "שפים, מסעדות וספרי מתכונים כלליים",
    "אפייה, לחם ווינואזרי",
    "פסטה",
    "פיצה",
    "ראמן, נודלס ופו",
    "אורז",
    "סנדוויצ׳ים",
    "מטבלים, ממרחים ומזטים",
    "טעם, רטבים, תבלינים וצירים",
    "התססה ושימור",
    "גבינות וחלב",
    "בשר, עוף וברביקיו",
    "ירקות וצמחונות",
    "סלטים",
    "מרקים ותבשילים",
    "כיסונים, טופו וקימצ׳י",
    "פשטידות, פאי, קישים וטארטים",
    "גלידה וקינוחים קפואים",
    "עוגיות",
    "קינוחים",
    "משקאות",
)

UNCATEGORIZED_BOOK_CATEGORY = "ללא קטגוריה"


_CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("פסטה", ("pasta", "פסטה")),
    ("פיצה", ("pizza", "פיצה")),
    ("ראמן, נודלס ופו", ("ramen", "noodle", "pho", "ראמן", "נודל", "פו")),
    ("אורז", ("rice", "risotto", "אורז", "ריזוטו")),
    ("סנדוויצ׳ים", ("sandwich", "burger", "סנדוויץ", "המבורגר")),
    ("התססה ושימור", ("ferment", "preserv", "pickle", "התסס", "שימור", "כביש")),
    ("גבינות וחלב", ("cheese", "dairy", "milk", "גבינ", "חלב")),
    ("בשר, עוף וברביקיו", ("meat", "poultry", "barbecue", "bbq", "בשר", "עוף", "ברביקיו")),
    ("ירקות וצמחונות", ("vegetable", "vegetarian", "vegan", "ירקות", "צמחונ", "טבעונ")),
    ("סלטים", ("salad", "סלט")),
    ("מרקים ותבשילים", ("soup", "stew", "מרק", "תבשיל")),
    ("כיסונים, טופו וקימצ׳י", ("dumpling", "tofu", "kimchi", "כיסונ", "טופו", "קימצ")),
    ("פשטידות, פאי, קישים וטארטים", ("pie", "quiche", "tart", "פשטיד", "קיש", "טארט")),
    ("גלידה וקינוחים קפואים", ("ice cream", "gelato", "frozen dessert", "גלידה", "ג׳לאטו")),
    ("עוגיות", ("cookie", "biscuit", "עוגי")),
    ("משקאות", ("drink", "cocktail", "wine", "beverage", "משקה", "קוקטייל", "יין")),
    ("אפייה, לחם ווינואזרי", ("baking", "bread", "pastry", "viennoiserie", "אפייה", "לחם", "מאפ")),
    ("טעם, רטבים, תבלינים וצירים", ("sauce", "spice", "stock", "flavor", "רוטב", "תבלין", "ציר", "טעם")),
    ("מטבלים, ממרחים ומזטים", ("dip", "spread", "mezze", "מטבל", "ממרח", "מזט")),
    ("קינוחים", ("dessert", "cake", "sweet", "קינוח", "עוגה", "מתוק")),
)


def resolve_library_category_name(classification: Mapping[str, object]) -> str:
    requested = str(classification.get("library_category") or "").strip()
    by_normalized_name = {name.casefold(): name for name in BOOK_LIBRARY_CATEGORIES}
    if requested.casefold() in by_normalized_name:
        return by_normalized_name[requested.casefold()]

    searchable_parts: list[str] = []
    for key in ("summary", "book_type", "teaching_level", "restaurant", "author_or_chef"):
        value = classification.get(key)
        if value:
            searchable_parts.append(str(value))
    for key in ("cuisines", "techniques", "categories", "tags"):
        value = classification.get(key)
        if isinstance(value, list):
            searchable_parts.extend(str(item) for item in value)
    haystack = " ".join(searchable_parts).casefold()

    for category, keywords in _CATEGORY_KEYWORDS:
        if any(keyword.casefold() in haystack for keyword in keywords):
            return category

    if any(term in haystack for term in ("science", "technique", "reference", "יסודות", "מדע", "לימוד")):
        return "לימוד, יסודות ומדע"
    if classification.get("restaurant") or classification.get("author_or_chef"):
        return "שפים, מסעדות וספרי מתכונים כלליים"
    if classification.get("cuisines"):
        return "מטבחים לפי מדינה"
    return UNCATEGORIZED_BOOK_CATEGORY
