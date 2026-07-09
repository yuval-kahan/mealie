import { alert } from "~/composables/use-toast";
import { useUserApi } from "~/composables/api/api-client";

export function useRecipeShoppingList() {
  const api = useUserApi();
  const i18n = useI18n();

  async function openOrCreateRecipeShoppingList(recipeSlug: string) {
    if (!recipeSlug) {
      return;
    }

    const { data, error } = await api.recipes.openOrCreateShoppingList(recipeSlug);
    const shoppingListId = data?.shoppingListId || data?.shopping_list_id;
    const shoppingListError = data?.shoppingListError || data?.shopping_list_error;

    if (error || !shoppingListId) {
      alert.error(i18n.t("recipe.shopping-list-open-failed"));
      return;
    }

    if (shoppingListError) {
      alert.error(shoppingListError);
    }
    else if (data?.shoppingListCreated || data?.shopping_list_created) {
      alert.success(i18n.t("recipe.shopping-list-created"));
    }

    window.dispatchEvent(new CustomEvent("mealie:shopping-lists-updated"));
    await navigateTo(`/shopping-lists/${shoppingListId}`);
  }

  return {
    openOrCreateRecipeShoppingList,
  };
}
