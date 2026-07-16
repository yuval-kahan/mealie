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
            "book title with page number, magazine, article, or other source record. Do not invent."
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
        description="A short list of obvious recipe categories, such as Dinner, Dessert, Pasta, or Sauce.",
    )

    tags: list[str] = Field(
        default_factory=list,
        description="A short list of useful recipe tags, such as vegetarian, Italian, quick, baking, or holiday.",
    )

    tools: list[str] = Field(
        default_factory=list,
        description="A short list of required kitchen tools or equipment explicitly mentioned in the recipe.",
    )

    source_image_is_finished_dish: bool = Field(
        False,
        description=(
            "For image-based imports only: true when at least one supplied image clearly shows the finished, "
            "ready-to-serve dish and is suitable as a recipe cover. False for scans, screenshots, text pages, "
            "ingredient layouts, packaging, equipment, or preparation-only photos."
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
