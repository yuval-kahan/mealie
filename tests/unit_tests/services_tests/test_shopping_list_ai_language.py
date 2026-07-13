from mealie.services.household_services.shopping_lists import ShoppingListService


def test_shopping_list_ai_target_language_instruction_uses_requested_locale():
    instruction = ShoppingListService._target_language_instruction("he_IL")

    assert "Hebrew" in instruction
    assert "he-IL" in instruction
    assert "mandatory" in instruction


def test_shopping_list_ai_fallback_category_uses_target_language():
    assert ShoppingListService._fallback_ai_category("he-IL") == "שונות"
    assert ShoppingListService._fallback_ai_category("en-US") == "Other"
