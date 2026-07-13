from pydantic import Field

from ._base import OpenAIBase


class OpenAIShoppingWebsite(OpenAIBase):
    is_food_website: bool = Field(
        True,
        description="False when the page is not a food shop, food producer, restaurant shop, or food ordering website.",
    )
    name: str = Field("", description="The public name of the website, shop, restaurant, or food business.")
    page_food: str = Field(
        "",
        description="The food, product, menu, category, or offering shown on the current saved page.",
    )
    offered_foods: list[str] = Field(
        default_factory=list,
        description="Other food categories or offerings that the website visibly provides.",
    )
