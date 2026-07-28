from pydantic import Field

from ._base import OpenAIBase


class OpenAIRecipeIngredient(OpenAIBase):
    title: str | None = Field(
        None,
        description="Ingredient section title (e.g., 'Dry Ingredients'). Only set on the first item in each section.",
    )

    text: str = Field(
        ...,
        description="The complete ingredient text, e.g., '1 cup of flour' or '2 cups of onions, chopped'.",
    )

    recommended_variety: str | None = Field(
        None,
        description=(
            "Optional recommended variety/type for this ingredient when useful, especially for vegetables, fruit, "
            "cheese, meat cuts, pasta shapes, or similar choices. Examples: 'ripe Roma tomatoes', "
            "'red bell pepper', 'baby spinach'. Leave null when no specific type is useful."
        ),
    )


class OpenAIRecipeInstruction(OpenAIBase):
    title: str | None = Field(
        None,
        description="Instruction section title. Only set on the first step in each section.",
    )

    text: str = Field(
        ...,
        description=(
            "One instruction step. Do not include numeric prefixes like '1.' or 'Step 1', "
            "but do include word-based prefixes like 'First' or 'Second'."
        ),
    )


class OpenAIRecipeNotes(OpenAIBase):
    title: str | None = Field(
        None,
        description="Note title. Ignore generic titles like 'Note' or 'Info' and leave blank.",
    )

    text: str = Field(
        ...,
        description="The note content, such as tips, variations, or preparation advice.",
    )


class OpenAIRecipe(OpenAIBase):
    name: str = Field(
        ...,
        description=(
            "Recipe name or title. Make your best guess if not obvious. When a credited chef, restaurant, or source "
            "site is explicitly available, keep the core dish name concise and include that attribution once. "
            "Never invent an attribution."
        ),
    )

    description: str | None = Field(
        None,
        description="A brief description of the recipe in a few words or sentences.",
    )

    source: str | None = Field(
        None,
        description=(
            "Where the recipe came from, if explicitly available. Examples: website name, blog name, TV show, "
            "book title with page number, magazine, article, or other source record. When the input contains a URL, "
            "preserve the complete URL together with a concise human-readable source name. Do not invent."
        ),
    )

    created_by: str | None = Field(
        None,
        description=(
            "The credited creator, chef, restaurant, author, book, show, publisher, or organization, if explicitly "
            "available. Do not invent."
        ),
    )

    recipe_yield: str | None = Field(
        None,
        description="Recipe yield, e.g., '12 cookies' or '4 servings'.",
    )

    total_time: str | None = Field(
        None,
        description="Total time as text (e.g., '1 hour 30 minutes'). Use if only one time is available.",
    )

    prep_time: str | None = Field(
        None,
        description="Prep time as text, e.g., '30 minutes'. Do not duplicate total_time.",
    )

    perform_time: str | None = Field(
        None,
        description="Cook/perform time as text, e.g., '1 hour'. Do not duplicate total_time.",
    )

    ingredients: list[OpenAIRecipeIngredient] = Field(
        default_factory=list,
        description="List of ingredients in order.",
    )

    instructions: list[OpenAIRecipeInstruction] = Field(
        default_factory=list,
        description="List of instruction steps in order.",
    )

    notes: list[OpenAIRecipeNotes] = Field(
        default_factory=list,
        description="List of notes, tips, or variations.",
    )

    categories: list[str] = Field(
        default_factory=list,
        description=(
            "A short list of obvious recipe categories written in Hebrew only, regardless of the recipe output "
            "language. Examples: מנה עיקרית, קינוחים, פסטה, רטבים. Never return English category names."
        ),
    )

    tags: list[str] = Field(
        default_factory=list,
        description=(
            "A short list of useful recipe tags written in Hebrew whenever possible. Chef and restaurant proper "
            "names may additionally appear in their original language, but general discovery tags must be Hebrew."
        ),
    )

    core_dish_name: str | None = Field(
        None,
        description=(
            "The concise food/dish name in Hebrew, without chef, restaurant, site, book, channel, or show "
            "attribution. This is mandatory whenever a usable dish name can be identified, even when the rest of "
            "the recipe is returned in another language, because this value is used as a Hebrew discovery tag."
        ),
    )

    primary_category: str | None = Field(
        None,
        description=(
            "One broad, useful recipe category written in Hebrew only, such as מנה עיקרית, תוספות, קינוחים, "
            "פסטה, מרקים, רטבים, לחמים, ארוחות בוקר, or משקאות."
        ),
    )

    is_michelin_dish: bool = Field(
        False,
        description=(
            "True only when the supplied source explicitly or reliably identifies the dish, restaurant, or credited "
            "chef with Michelin-star or Michelin Guide recognition. Fine dining or fame alone is not enough."
        ),
    )

    is_gourmet_dish: bool = Field(
        False,
        description=(
            "True when the dish genuinely uses refined restaurant-style technique, composition, ingredients, or "
            "presentation. Do not mark ordinary home cooking as gourmet."
        ),
    )

    is_complete_meal: bool = Field(
        False,
        description=(
            "True when the recipe can reasonably serve as a substantial standalone meal, "
            "not merely a component."
        ),
    )

    meal_periods: list[str] = Field(
        default_factory=list,
        description=(
            "One or more meal periods for which the recipe is suitable. Use only the canonical values breakfast, "
            "lunch, and dinner. Include every genuinely suitable period; a recipe may fit more than one."
        ),
    )

    media_source_type: str | None = Field(
        None,
        description=(
            "Explicit source medium when supported: television, instagram, youtube, tiktok, website, cookbook, "
            "magazine, or other concise type. Use null when unknown."
        ),
    )

    media_source_name: str | None = Field(
        None,
        description=(
            "Explicit TV show, Instagram account, YouTube channel, TikTok account, site, book, or magazine name. "
            "Never invent it."
        ),
    )

    tools: list[str] = Field(
        default_factory=list,
        description="A short list of required kitchen tools or equipment explicitly mentioned in the recipe.",
    )

    mise_en_place: str | None = Field(
        None,
        description=(
            "Legacy combined Markdown preparation-ahead plan. Prefer mise_en_place_food and "
            "mise_en_place_tools for new responses."
        ),
    )

    mise_en_place_food: list[str] = Field(
        default_factory=list,
        description=(
            "Concise food preparation tasks to complete before cooking starts, one useful task per item, such as "
            "washing, cutting, measuring, chilling, or preparing a sauce. Do not include equipment-only items."
        ),
    )

    mise_en_place_tools: list[str] = Field(
        default_factory=list,
        description=(
            "Kitchen tools and equipment that should be ready before cooking starts, one concise item per entry. "
            "Do not repeat ingredients or food preparation tasks."
        ),
    )

    source_image_is_finished_dish: bool = Field(
        False,
        description=(
            "For image-based imports only: true when at least one supplied image clearly shows the finished, "
            "ready-to-serve dish and is suitable as a recipe cover. False for scans, screenshots, text pages, "
            "ingredient layouts, packaging, equipment, or preparation-only photos."
        ),
    )

    explicit_ten_minute_claim: bool = Field(
        False,
        description=(
            "True only when the supplied source explicitly states that this recipe takes 10 minutes. "
            "Never infer this from simplicity, short instructions, or estimated times."
        ),
    )


class OpenAIRecipeTextParse(OpenAIBase):
    is_recipe: bool = Field(
        ...,
        description=(
            "True only when the pasted text contains enough recipe data to create a recipe. "
            "False when the text is not a recipe or is too incomplete."
        ),
    )

    reason: str | None = Field(
        None,
        description="Short practical reason when is_recipe is false, or a brief parsing note when useful.",
    )

    recipe: OpenAIRecipe | None = Field(
        None,
        description="The structured recipe when is_recipe is true. Use null when is_recipe is false.",
    )


class OpenAIRecipeIngredientScale(OpenAIBase):
    matched: bool = Field(
        ...,
        description="True only when one supplied ingredient and a positive requested quantity are unambiguous.",
    )
    ingredient_index: int | None = Field(
        None,
        ge=0,
        description="Exact ingredient_index from the supplied candidate list that the user wants to scale from.",
    )
    target_quantity_in_recipe_unit: float | None = Field(
        None,
        gt=0,
        description="Requested quantity converted into the selected ingredient's existing recipe unit.",
    )
    interpreted_ingredient: str = Field(
        "",
        description="Short ingredient name inferred from the user's request, in the user's language.",
    )
    reason: str = Field(
        "",
        description="A short explanation when matched is false.",
    )


class OpenAIRecipeIngredientAdjustmentItem(OpenAIBase):
    ingredient_index: int = Field(
        ...,
        ge=0,
        description=(
            "Exact ingredient_index from the supplied ingredient list. "
            "Return every supplied index exactly once."
        ),
    )
    title: str | None = Field(
        None,
        description="Ingredient section title, preserved from the supplied item when present.",
    )
    quantity: float | None = Field(
        None,
        ge=0,
        description="Adjusted numeric quantity. Use null for non-numeric quantities such as a pinch or as needed.",
    )
    unit: str | None = Field(
        None,
        description="Adjusted unit in the recipe's language. Use null when there is no unit.",
    )
    food: str | None = Field(
        None,
        description="Ingredient name in the recipe's language.",
    )
    note: str = Field(
        "",
        description=(
            "Preparation detail, non-numeric quantity wording, or other text that belongs with this ingredient."
        ),
    )
    recommended_variety: str | None = Field(
        None,
        description="Preserve or update the useful recommended type when one exists.",
    )
    original_text: str | None = Field(
        None,
        description="Complete adjusted ingredient text, preserving useful wording from the original ingredient.",
    )


class OpenAIRecipeIngredientAdjustment(OpenAIBase):
    adjusted: bool = Field(
        ...,
        description=(
            "True only when the request can be applied to the complete supplied ingredient list without guessing."
        ),
    )
    reason: str = Field(
        "",
        description="Short explanation when adjusted is false, or a concise summary of the change when true.",
    )
    ingredients: list[OpenAIRecipeIngredientAdjustmentItem] = Field(
        default_factory=list,
        description=(
            "The complete replacement list, with every supplied ingredient_index exactly once and in the same order."
        ),
    )


class OpenAIBookRecipeChunkParse(OpenAIBase):
    recipes: list[OpenAIRecipe] = Field(
        default_factory=list,
        description=(
            "All complete, usable recipes found in this cookbook chunk. Return an empty list when no complete recipes "
            "are present."
        ),
    )


class OpenAIBookRecipeCatalogMatch(OpenAIBase):
    entry_index: int = Field(
        ...,
        ge=0,
        description="The exact entry_index supplied for this table-of-contents or heading entry.",
    )
    is_recipe: bool = Field(
        ...,
        description="True only when the entry is an individual recipe or a clearly named food preparation.",
    )
    matches_query: bool = Field(
        ...,
        description=(
            "True when the recipe semantically matches the user's query. "
            "For an empty query, use the same value as is_recipe."
        ),
    )
    display_title: str | None = Field(
        None,
        description="A concise literal translation of the supplied title into the requested display language.",
    )
    chapter: str | None = Field(
        None,
        description="The nearest supplied chapter or section title, translated when useful. Never invent one.",
    )
    reason: str | None = Field(
        None,
        description="A concise reason for a semantic query match when useful.",
    )


class OpenAIBookRecipeCatalogParse(OpenAIBase):
    matches: list[OpenAIBookRecipeCatalogMatch] = Field(
        default_factory=list,
        description="One classification result for every supplied entry_index.",
    )


class OpenAIBookRecipeSearchHint(OpenAIBase):
    title: str = Field(
        ...,
        description="A likely recipe title or literal title variant that may appear in the named cookbook.",
    )
    page_start: int | None = Field(
        None,
        ge=1,
        description="A possible printed page number only when confidently known; otherwise null.",
    )
    page_end: int | None = Field(
        None,
        ge=1,
        description="Optional possible final printed page number; otherwise null.",
    )


class OpenAIBookRecipeSearchPlan(OpenAIBase):
    search_terms: list[str] = Field(
        default_factory=list,
        description=(
            "Short literal terms, spelling variants, and useful Hebrew/English equivalents to search in the actual "
            "book text."
        ),
    )
    hints: list[OpenAIBookRecipeSearchHint] = Field(
        default_factory=list,
        description="Likely recipe titles and optional page hints. Empty when not confidently known.",
    )
    reason: str | None = Field(
        None,
        description="A concise note about the plan or uncertainty.",
    )


class OpenAIBookTranslatedPage(OpenAIBase):
    page: int = Field(..., description="Original page number.")
    text: str = Field(..., description="The full translated text for this page.")
    title: str | None = Field(
        None,
        description=(
            "A concise literal heading for this page when it begins a chapter, section, or recipe. "
            "Use null for continuation pages, credits, blank pages, and pages without a real heading."
        ),
    )
    entry_type: str = Field(
        "page",
        description=(
            "One of: contents, chapter, section, recipe, page. Use contents for a source table-of-contents page, "
            "chapter for a major division, recipe for a complete recipe beginning on this page, section for a "
            "meaningful subsection, and page otherwise."
        ),
    )
    parent_title: str | None = Field(
        None,
        description="Nearest chapter title when this page begins a section or recipe; otherwise null.",
    )
    include_in_contents: bool = Field(
        False,
        description=(
            "True only for a chapter, meaningful section, or recipe that belongs in a professional contents list."
        ),
    )


class OpenAIBookTranslationChunkParse(OpenAIBase):
    pages: list[OpenAIBookTranslatedPage] = Field(
        default_factory=list,
        description="Translated pages from the requested chunk, preserving original page numbers.",
    )
