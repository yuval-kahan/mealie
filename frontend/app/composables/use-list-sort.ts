import type { ComputedRef, Ref } from "vue";

export type ListSortDirection = "asc" | "desc";
export type ListSortValue = boolean | number | string | null | undefined;

interface StoredListSort {
  key: string;
  direction: ListSortDirection;
}

export function usePersistedListSort<T extends string>(
  allowedKeys: readonly T[],
  defaultKey: T,
  defaultDirection: ListSortDirection = "asc",
  storageScope?: string,
) {
  const route = useRoute();
  const auth = useMealieAuth();
  const storedSorts = useLocalStorage<Record<string, StoredListSort>>(
    "mealie-list-sort-preferences",
    {},
    { deep: true },
  );
  const routeKey = computed(() => storageScope || String(route.name || route.path || "list"));
  const preferenceKey = computed(() => {
    const userKey = auth.user.value?.id || "anonymous";
    return `${userKey}:${routeKey.value}`;
  });

  const storedPreference = computed(() => storedSorts.value[preferenceKey.value]);
  const sortBy = computed<T>({
    get() {
      const storedKey = storedPreference.value?.key as T | undefined;
      return storedKey && allowedKeys.includes(storedKey) ? storedKey : defaultKey;
    },
    set(value) {
      if (!allowedKeys.includes(value)) return;
      storedSorts.value = {
        ...storedSorts.value,
        [preferenceKey.value]: {
          key: value,
          direction: sortDirection.value,
        },
      };
    },
  });
  const sortDirection = computed<ListSortDirection>({
    get() {
      const direction = storedPreference.value?.direction;
      return direction === "asc" || direction === "desc" ? direction : defaultDirection;
    },
    set(value) {
      storedSorts.value = {
        ...storedSorts.value,
        [preferenceKey.value]: {
          key: sortBy.value,
          direction: value,
        },
      };
    },
  });

  return { sortBy, sortDirection };
}

export function sortListItems<T>(
  source: Ref<readonly T[]> | ComputedRef<readonly T[]>,
  valueFor: (item: T) => ListSortValue,
  direction: Ref<ListSortDirection>,
  locale: Ref<string>,
) {
  return computed(() => {
    const multiplier = direction.value === "asc" ? 1 : -1;
    return source.value
      .map((item, index) => ({ item, index }))
      .sort((left, right) => {
        const leftValue = valueFor(left.item);
        const rightValue = valueFor(right.item);
        const leftEmpty = leftValue === null || leftValue === undefined || leftValue === "";
        const rightEmpty = rightValue === null || rightValue === undefined || rightValue === "";

        if (leftEmpty !== rightEmpty) return leftEmpty ? 1 : -1;
        if (leftEmpty && rightEmpty) return left.index - right.index;

        const comparison = typeof leftValue === "number" && typeof rightValue === "number"
          ? leftValue - rightValue
          : String(leftValue).localeCompare(String(rightValue), locale.value, {
              numeric: true,
              sensitivity: "base",
            });
        return comparison === 0
          ? left.index - right.index
          : comparison * multiplier;
      })
      .map(entry => entry.item);
  });
}
