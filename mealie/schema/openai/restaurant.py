from pydantic import Field

from ._base import OpenAIBase


class OpenAIRestaurant(OpenAIBase):
    is_restaurant: bool = Field(
        True,
        description="False when the supplied name or page is not a restaurant, cafe, bakery, bar, or food venue.",
    )
    name: str = Field("", description="The restaurant's real public name without marketing slogans.")
    website_url: str | None = Field(None, description="The supplied official website URL, or null when unknown.")
    cuisine_types: list[str] = Field(
        default_factory=list,
        description="Concise cuisine and food types clearly supported by the supplied information.",
    )
    addresses: list[str] = Field(
        default_factory=list,
        description="All explicitly supplied restaurant addresses. Never infer or invent an address.",
    )
    phone: str | None = Field(None, description="An explicitly supplied public phone number, otherwise null.")
    price_range: str | None = Field(None, description="A supported price range or price level, otherwise null.")
    description: str | None = Field(None, description="A concise factual description of the venue and its food.")
    michelin_info: str | None = Field(
        None,
        description=(
            "Michelin star, Bib Gourmand, or Michelin Guide information only when explicitly and reliably supported. "
            "Never infer Michelin recognition from fine dining language or a chef's reputation."
        ),
    )
    michelin_star_count: int = Field(
        0,
        ge=0,
        le=3,
        description="Current Michelin star count only when explicitly and reliably supported.",
    )
    is_michelin_listed: bool = Field(
        False,
        description="True only for a reliably supported current Michelin Guide listing.",
    )
    chef_names: list[str] = Field(
        default_factory=list,
        description="Chefs explicitly and reliably associated with the restaurant.",
    )
    book_titles: list[str] = Field(
        default_factory=list,
        description="Cookbooks explicitly and reliably associated with the restaurant or its chefs.",
    )
    google_rating: float | None = Field(
        None,
        ge=0,
        le=5,
        description=(
            "The current Google rating only when it is explicitly present in supplied page text or reliably known. "
            "Never estimate or invent it."
        ),
    )
    google_review_count: int | None = Field(
        None,
        ge=0,
        description="The Google review count only when explicitly supplied alongside the rating, otherwise null.",
    )
    google_maps_url: str | None = Field(
        None,
        description=(
            "An explicit Google Maps or Google business listing URL when supplied "
            "or reliably known, otherwise null."
        ),
    )


class OpenAIRestaurantHebrewMetadata(OpenAIBase):
    cuisine_types: list[str] = Field(
        default_factory=list,
        description="Short cuisine and food categories translated or transliterated entirely into Hebrew.",
    )
    description: str | None = Field(
        None,
        description="The supplied restaurant description translated entirely into natural Hebrew.",
    )


class OpenAIRestaurantSuggestions(OpenAIBase):
    items: list[OpenAIRestaurant] = Field(
        default_factory=list,
        description="Distinct restaurants matching the user's request.",
    )
