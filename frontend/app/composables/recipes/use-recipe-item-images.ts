import { alert } from "~/composables/use-toast";
import { useUserApi } from "~/composables/api/api-client";
import type { ItemImagesEnsureResponse } from "~/lib/api/user/recipes/recipe";

const ITEM_IMAGES_ENSURED_EXTRA_KEY = "itemImagesEnsured";
const ITEM_IMAGES_ENSURED_AT_EXTRA_KEY = "itemImagesEnsuredAt";

export function recipeItemImagesEnsured(extras?: Record<string, unknown> | null) {
  const value = extras?.[ITEM_IMAGES_ENSURED_EXTRA_KEY];
  return value === true || value === "true";
}

export function markRecipeItemImagesEnsured(recipeLike: { extras?: Record<string, unknown> | null }) {
  recipeLike.extras = {
    ...(recipeLike.extras || {}),
    [ITEM_IMAGES_ENSURED_EXTRA_KEY]: true,
    [ITEM_IMAGES_ENSURED_AT_EXTRA_KEY]: new Date().toISOString(),
  };
}

export function itemImagesEnsureSucceeded(result?: ItemImagesEnsureResponse | null) {
  return !!result && result.failed === 0;
}

export function useRecipeItemImages() {
  const api = useUserApi();
  const i18n = useI18n();

  async function ensureRecipeItemImages(recipeSlug: string) {
    const { data, error } = await api.recipes.ensureItemImages(recipeSlug);
    if (error || !itemImagesEnsureSucceeded(data)) {
      alert.error(i18n.t("recipe.item-images-create-failed"));
      return null;
    }

    alert.success(i18n.t("recipe.item-images-created"));
    return data;
  }

  return {
    ensureRecipeItemImages,
  };
}
