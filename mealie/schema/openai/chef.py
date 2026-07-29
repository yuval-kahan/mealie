from pydantic import Field

from ._base import OpenAIBase


class OpenAIChef(OpenAIBase):
    is_chef: bool = Field(
        True,
        description="False when the supplied request is not about a real chef or culinary professional.",
    )
    name: str = Field("", description="The chef's concise, real public name.")
    aliases: list[str] = Field(default_factory=list, description="Useful alternate public spellings or names.")
    rank: str = Field(
        "good",
        description="One canonical value: world_class, excellent, good, medium, or emerging.",
    )
    country: str | None = None
    cuisines: list[str] = Field(default_factory=list, description="Cuisine fields in Hebrew only.")
    specialties: list[str] = Field(default_factory=list, description="Culinary specialties in Hebrew only.")
    biography: str | None = Field(None, description="Detailed, factual biography in natural Hebrew.")
    career_summary: str | None = Field(None, description="Detailed career history in natural Hebrew.")
    awards: list[str] = Field(default_factory=list)
    notable_restaurants: list[str] = Field(default_factory=list)
    book_titles: list[str] = Field(default_factory=list)
    website_url: str | None = None
    wikipedia_url: str | None = Field(
        None,
        description="Canonical Wikipedia URL when a matching article is known.",
    )
    instagram_url: str | None = None
    has_michelin_restaurant: bool = False
    michelin_star_count: int = Field(
        0,
        ge=0,
        description="Highest reliably supported Michelin star count associated with a restaurant led by the chef.",
    )
    michelin_summary: str | None = Field(
        None,
        description="Factual Michelin history in Hebrew, with uncertainty stated rather than guessed.",
    )


class OpenAIEquipment(OpenAIBase):
    is_kitchen_tool: bool = True
    name: str = Field("", description="One concise canonical tool name in Hebrew, without quantities or counts.")
    category: str = Field("", description="One concise kitchen-equipment category in Hebrew only.")
    description: str = Field("", description="A concise practical explanation in natural Hebrew.")
    image_search_query: str = Field("", description="A concise English public-image search phrase.")
