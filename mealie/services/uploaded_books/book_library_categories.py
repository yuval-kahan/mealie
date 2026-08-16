from __future__ import annotations

from collections.abc import Mapping

BOOK_LIBRARY_SUBCATEGORIES: Mapping[str, tuple[str, ...]] = {
    "לימוד, יסודות ומדע": (
        "יסודות, טכניקה ומדע הבישול",
        "מדעי המזון / אקדמי",
        "ציוד, סכינים וכלי מטבח",
        "Modernist Cuisine",
    ),
    "מטבחים לפי מדינה ואזור": (
        "צרפתי / צרפתי-אמריקאי",
        "איטלקי",
        "תאילנדי",
        "הודי / סרי לנקי",
        "יפני",
        "סיני",
        "מזרח תיכון / פרסי / טורקי",
        "מרוקאי",
        "מקסיקני",
        "ספרדי",
        "נורדי",
    ),
    "שפים, מסעדות וספרי מתכונים כלליים": ("שפים", "מסעדות", "כללי"),
    "אפייה, לחם ווינואזרי": (
        "לחם ובולנז׳רי",
        "Modernist Bread",
        "קרואסון, למינציה, בריוש ווינואזרי",
        "מדע וטכניקת אפייה",
        "אפייה וקונדיטוריה כללית",
    ),
    "פסטה": ("פסטה",),
    "פיצה": ("פיצה",),
    "ראמן, נודלס ופו": ("ראמן", "נודלס אסייתיים", "פו וייטנאמי"),
    "אורז, ריזוטו ופולנטה": ("אורז כללי", "ריזוטו", "פולנטה"),
    "סנדוויצ׳ים": (
        "סנדוויצ׳ים כלליים",
        "איטלקיים / Panini",
        "יפניים / Sando",
        "וייטנאמיים / Bánh mì",
        "Grilled Cheese",
        "פיתה",
    ),
    "מטבלים, ממרחים ומזטים": ("מטבלים וממרחים", "חומוס", "מזטים", "פלאפל"),
    "טעם, רטבים, תבלינים וצירים": (
        "שילובי טעמים ויצירתיות",
        "רטבים",
        "צירים",
        "תבלינים ועשבי תיבול",
    ),
    "התססה ושימור": ("התססה וטעם", "חומצים והתססה", "שימור ומזווה"),
    "גבינות וחלב": ("הכנת גבינות", "גבינות - ידע ו-Reference", "יוגורט ומוצרי חלב"),
    "בשר, עוף וברביקיו": (
        "בשר וברביקיו",
        "פירוק וקצבות",
        "עוף מטוגן",
        "שרקוטרי, פטה וטרין",
    ),
    "דגים ופירות ים": ("דגים", "פירוק ובישול מקצועי"),
    "ירקות וצמחונות": ("ירקות וצמחונות",),
    "סלטים": ("סלטים",),
    "מרקים ותבשילים": ("מרקים", "קדרות ותבשילים"),
    "כיסונים, טופו וקימצ׳י": ("כיסונים / Dumplings", "טופו", "קימצ׳י"),
    "פשטידות, פאי, קישים וטארטים": (
        "פאי ופשטידות",
        "טארטים וקישים",
        "אפייה מלוחה, קיש וטארט",
    ),
    "גלידה וקינוחים קפואים": ("גלידה, ג׳לטו וקפואים",),
    "עוגיות, בראוניז, דונאטס ופנקייקים": (
        "עוגיות",
        "בראוניז ובלונדיז",
        "דונאטס, Bomboloni ו-Beignets",
        "פנקייקים",
    ),
    "קינוחים": (
        "עוגות גבינה",
        "טירמיסו",
        "קינוחים איטלקיים",
        "קינוחים איטלקיים / קנולי",
        "קינוחים ופטיסרי צרפתי",
    ),
    "משקאות": (
        "מיצים, שייקים וטוניקים",
        "סודה ומשקאות מוגזים",
        "בובה ותה חלב",
        "משקאות ללא אלכוהול",
        "קומבוצ׳ה ומשקאות מותססים",
    ),
    "גרטנים ואוספי מתכונים": ("ספר / אוסף מרכזי", "קובצי מתכונים בתיקיית Gratin"),
}

BOOK_LIBRARY_CATEGORIES = tuple(BOOK_LIBRARY_SUBCATEGORIES)
UNCATEGORIZED_BOOK_CATEGORY = "ללא קטגוריה"

# Names used by the first version of the library map. Existing assignments are
# retained while the headings are upgraded to the complete map.
BOOK_LIBRARY_CATEGORY_ALIASES: Mapping[str, str] = {
    "מטבחים לפי מדינה": "מטבחים לפי מדינה ואזור",
    "אורז": "אורז, ריזוטו ופולנטה",
    "עוגיות": "עוגיות, בראוניז, דונאטס ופנקייקים",
}

_CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("פסטה", ("pasta", "פסטה")),
    ("פיצה", ("pizza", "פיצה")),
    ("ראמן, נודלס ופו", ("ramen", "noodle", "pho", "ראמן", "נודל", "פו")),
    ("אורז, ריזוטו ופולנטה", ("rice", "risotto", "polenta", "אורז", "ריזוטו", "פולנטה")),
    ("סנדוויצ׳ים", ("sandwich", "burger", "panini", "sando", "סנדוויץ", "המבורגר")),
    ("התססה ושימור", ("ferment", "preserv", "pickle", "התסס", "שימור", "כביש")),
    ("גבינות וחלב", ("cheese", "dairy", "milk", "גבינ", "חלב")),
    ("בשר, עוף וברביקיו", ("meat", "poultry", "barbecue", "bbq", "בשר", "עוף", "ברביקיו")),
    ("דגים ופירות ים", ("fish", "seafood", "shellfish", "דג", "פירות ים")),
    ("ירקות וצמחונות", ("vegetable", "vegetarian", "vegan", "ירקות", "צמחונ", "טבעונ")),
    ("סלטים", ("salad", "סלט")),
    ("מרקים ותבשילים", ("soup", "stew", "מרק", "תבשיל")),
    ("כיסונים, טופו וקימצ׳י", ("dumpling", "tofu", "kimchi", "כיסונ", "טופו", "קימצ")),
    ("פשטידות, פאי, קישים וטארטים", ("pie", "quiche", "tart", "פשטיד", "קיש", "טארט")),
    ("גלידה וקינוחים קפואים", ("ice cream", "gelato", "frozen dessert", "גלידה", "ג׳לאטו")),
    ("עוגיות, בראוניז, דונאטס ופנקייקים", ("cookie", "brownie", "donut", "pancake", "עוגי", "בראוני", "פנקייק")),
    ("משקאות", ("drink", "cocktail", "wine", "beverage", "משקה", "קוקטייל", "יין")),
    ("אפייה, לחם ווינואזרי", ("baking", "bread", "pastry", "viennoiserie", "אפייה", "לחם", "מאפ")),
    ("טעם, רטבים, תבלינים וצירים", ("sauce", "spice", "stock", "flavor", "רוטב", "תבלין", "ציר", "טעם")),
    ("מטבלים, ממרחים ומזטים", ("dip", "spread", "mezze", "מטבל", "ממרח", "מזט")),
    ("גרטנים ואוספי מתכונים", ("gratin", "collection", "גרטאן", "אוסף")),
    ("קינוחים", ("dessert", "cake", "sweet", "קינוח", "עוגה", "מתוק")),
)


def _classification_haystack(classification: Mapping[str, object]) -> str:
    searchable_parts: list[str] = []
    for key in ("summary", "book_type", "teaching_level", "restaurant", "author_or_chef"):
        if value := classification.get(key):
            searchable_parts.append(str(value))
    for key in ("cuisines", "techniques", "categories", "tags"):
        value = classification.get(key)
        if isinstance(value, list):
            searchable_parts.extend(str(item) for item in value)
    return " ".join(searchable_parts).casefold()


def resolve_library_category_name(classification: Mapping[str, object]) -> str:
    requested = str(classification.get("library_category") or "").strip()
    requested = BOOK_LIBRARY_CATEGORY_ALIASES.get(requested, requested)
    by_normalized_name = {name.casefold(): name for name in BOOK_LIBRARY_CATEGORIES}
    if requested.casefold() in by_normalized_name:
        return by_normalized_name[requested.casefold()]

    haystack = _classification_haystack(classification)
    for category, keywords in _CATEGORY_KEYWORDS:
        if any(keyword.casefold() in haystack for keyword in keywords):
            return category
    if any(term in haystack for term in ("science", "technique", "reference", "יסודות", "מדע", "לימוד")):
        return "לימוד, יסודות ומדע"
    if classification.get("restaurant") or classification.get("author_or_chef"):
        return "שפים, מסעדות וספרי מתכונים כלליים"
    if classification.get("cuisines"):
        return "מטבחים לפי מדינה ואזור"
    return UNCATEGORIZED_BOOK_CATEGORY


def resolve_library_subcategory_name(classification: Mapping[str, object], category_name: str) -> str | None:
    choices = BOOK_LIBRARY_SUBCATEGORIES.get(category_name, ())
    if not choices:
        return None
    requested = str(classification.get("library_subcategory") or "").strip()
    by_normalized_name = {name.casefold(): name for name in choices}
    if requested.casefold() in by_normalized_name:
        return by_normalized_name[requested.casefold()]

    haystack = _classification_haystack(classification)
    ranked = sorted(
        (
            (
                sum(part.strip().casefold() in haystack for part in name.replace("/", ",").split(",") if part.strip()),
                name,
            )
            for name in choices
        ),
        reverse=True,
    )
    return ranked[0][1] if ranked and ranked[0][0] else choices[0]
