from pydantic import Field

from ._base import OpenAIBase


class OpenAIShoppingListAssignment(OpenAIBase):
    item_id: str = Field(..., description="The exact shopping list item id from the provided JSON.")
    category: str = Field(..., description="The best shopping category label for this item.")


class OpenAIShoppingListOrganization(OpenAIBase):
    assignments: list[OpenAIShoppingListAssignment] = Field(
        default_factory=list,
        description="One category assignment for each shopping list item.",
    )
