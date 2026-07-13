import { watchDebounced } from "@vueuse/core";
import type { UserApi } from "~/lib/api";
import type { ExploreApi } from "~/lib/api/public/explore";
import type { Recipe } from "~/lib/api/types/recipe";

export interface UseRecipeSearchReturn {
  query: Ref<string>;
  error: Ref<string>;
  loading: Ref<boolean>;
  data: Ref<Recipe[]>;
  trigger(): Promise<void>;
}

export interface UseRecipeSearchOptions {
  categories?: Ref<string[]>;
  tags?: Ref<string[]>;
  perPage?: number;
}

/**
 * `useRecipeSearch` constructs a basic reactive search query
 * that when `query` is changed, will search for recipes based
 * on the query. Useful for searchable list views. For advanced
 * search, use the `useRecipeQuery` composable.
 */
export function useRecipeSearch(api: UserApi | ExploreApi, options: UseRecipeSearchOptions = {}): UseRecipeSearchReturn {
  const query = ref("");
  const error = ref("");
  const loading = ref(false);
  const recipes = ref<Recipe[]>([]);
  let requestSequence = 0;

  async function searchRecipes(term: string) {
    const sequence = ++requestSequence;
    loading.value = true;
    error.value = "";
    try {
      const { data, error: responseError } = await api.recipes.search({
        search: term,
        categories: options.categories?.value.length ? [...options.categories.value] : undefined,
        tags: options.tags?.value.length ? [...options.tags.value] : undefined,
        page: 1,
        orderBy: "name",
        orderDirection: "asc",
        perPage: options.perPage ?? 20,
        _searchSeed: Date.now().toString(),
      });

      if (sequence !== requestSequence) {
        return;
      }

      if (responseError) {
        console.error(responseError);
        error.value = String(responseError);
        recipes.value = [];
        return;
      }

      recipes.value = data?.items || [];
    }
    catch (requestError) {
      if (sequence !== requestSequence) {
        return;
      }
      console.error(requestError);
      error.value = String(requestError);
      recipes.value = [];
    }
    finally {
      if (sequence === requestSequence) {
        loading.value = false;
      }
    }
  }

  watchDebounced(
    () => [
      query.value,
      options.categories?.value.join("|") || "",
      options.tags?.value.join("|") || "",
    ],
    async () => {
      await searchRecipes(query.value);
    },
    { debounce: 400 },
  );

  async function trigger() {
    await searchRecipes(query.value);
  }

  return {
    query,
    error,
    loading,
    data: recipes,
    trigger,
  };
}
