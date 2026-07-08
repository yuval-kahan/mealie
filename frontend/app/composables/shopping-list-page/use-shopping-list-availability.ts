import { useUserApi } from "~/composables/api/api-client";
import type { ShoppingListOut } from "~/lib/api/types/household";

const READY_EXTRAS_KEY = "allGroceriesReady";
const READY_AT_EXTRAS_KEY = "allGroceriesReadyAt";

function normalizeListRecipeName(name?: string | null) {
  return (name || "").trim().toLocaleLowerCase();
}

export function isShoppingListGroceriesReady(list?: Pick<ShoppingListOut, "extras"> | null) {
  const value = list?.extras?.[READY_EXTRAS_KEY];
  return value === true || value === "true";
}

export function buildShoppingListReadyExtras(list: Pick<ShoppingListOut, "extras">, ready: boolean) {
  return {
    ...(list.extras || {}),
    [READY_EXTRAS_KEY]: ready,
    [READY_AT_EXTRAS_KEY]: ready ? new Date().toISOString() : null,
  };
}

export function useShoppingListAvailability() {
  const userApi = useUserApi();
  const readyRecipeNames = useState<Record<string, true>>("shopping-list-ready-recipe-names", () => ({}));
  const loaded = useState("shopping-list-ready-recipe-names-loaded", () => false);
  const loading = useState("shopping-list-ready-recipe-names-loading", () => false);

  async function refreshAvailability() {
    if (loading.value) {
      return;
    }

    loading.value = true;
    try {
      const { data } = await userApi.shopping.lists.getAll(1, -1, { orderBy: "name", orderDirection: "asc" });
      const next: Record<string, true> = {};

      data?.items?.forEach((list) => {
        const nameKey = normalizeListRecipeName(list.name);
        if (nameKey && isShoppingListGroceriesReady(list)) {
          next[nameKey] = true;
        }
      });

      readyRecipeNames.value = next;
      loaded.value = true;
    }
    finally {
      loading.value = false;
    }
  }

  async function ensureAvailability() {
    if (!loaded.value) {
      await refreshAvailability();
    }
  }

  function hasAllGroceriesForRecipe(recipeName?: string | null) {
    return Boolean(readyRecipeNames.value[normalizeListRecipeName(recipeName)]);
  }

  function updateAvailabilityForListName(listName?: string | null, ready = false) {
    const nameKey = normalizeListRecipeName(listName);
    if (!nameKey) {
      return;
    }

    const next = { ...readyRecipeNames.value };
    if (ready) {
      next[nameKey] = true;
    }
    else {
      readyRecipeNames.value = Object.fromEntries(
        Object.entries(next).filter(([key]) => key !== nameKey),
      ) as Record<string, true>;
      loaded.value = true;
      return;
    }

    readyRecipeNames.value = next;
    loaded.value = true;
  }

  return {
    refreshAvailability,
    ensureAvailability,
    hasAllGroceriesForRecipe,
    updateAvailabilityForListName,
  };
}
