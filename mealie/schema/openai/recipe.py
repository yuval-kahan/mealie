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
        description="Recipe name or title. Make your best guess if not obvious.",
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
            "The credited creator, chef, author, book, show, publisher, or organization, if explicitly available. "
            "Do not invent."
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


class OpenAIBookTranslationChunkParse(OpenAIBase):
    pages: list[OpenAIBookTranslatedPage] = Field(
        default_factory=list,
        description="Translated pages from the requested chunk, preserving original page numbers.",
    )
