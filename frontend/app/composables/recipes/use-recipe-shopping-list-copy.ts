import { alert } from "~/composables/use-toast";
import { useUserApi } from "~/composables/api/api-client";
import { useShoppingListCopy } from "~/composables/shopping-list-page/sub-composables/use-shopping-list-copy";
import type { ShoppingListOut } from "~/lib/api/types/household";

function shoppingListIdFromResponse(data: any) {
  return data?.shoppingListId || data?.shopping_list_id || null;
}

function isAiOrganized(shoppingList?: ShoppingListOut | null) {
  const value = shoppingList?.extras?.aiOrganized;
  return value === true || value === "true";
}

export function useRecipeShoppingListCopy() {
  const api = useUserApi();
  const i18n = useI18n();
  const { copyShoppingList } = useShoppingListCopy();

  async function getAiOrganizedShoppingList(recipeSlug: string) {
    const { data: openData, error: openError } = await api.recipes.openOrCreateShoppingList(recipeSlug);
    const shoppingListId = shoppingListIdFromResponse(openData);
    if (openError || !shoppingListId) {
      alert.error(i18n.t("recipe.shopping-list-open-failed"));
      return null;
    }

    const { data: listData, error: listError } = await api.shopping.lists.getOne(shoppingListId, { suppressAlert: true });
    if (listError || !listData) {
      alert.error(i18n.t("recipe.shopping-list-open-failed"));
      return null;
    }

    if (isAiOrganized(listData)) {
      return listData;
    }

    const { data: organizedList, error: organizeError } = await api.shopping.lists.organizeWithAi(shoppingListId, true);
    if (organizeError || !organizedList || !isAiOrganized(organizedList)) {
      alert.error(i18n.t("recipe.ai-shopping-list-organize-failed"));
      return null;
    }

    return organizedList;
  }

  async function copyRecipeShoppingList(recipeSlug: string) {
    const shoppingList = await getAiOrganizedShoppingList(recipeSlug);
    if (!shoppingList) {
      return false;
    }

    copyShoppingList(shoppingList);
    return true;
  }

  return {
    copyRecipeShoppingList,
    getAiOrganizedShoppingList,
  };
}
