import type { ComputedRef, Ref } from "vue";

export const DEFAULT_LIST_PAGE_SIZE = 100;
export const LIST_PAGE_SIZE_OPTIONS = [25, 50, 100, 200];

export function usePersistedListPageSize(
  defaultPageSize = DEFAULT_LIST_PAGE_SIZE,
  storageScope?: string,
) {
  const route = useRoute();
  const auth = useMealieAuth();
  const storedPageSizes = useLocalStorage<Record<string, number>>(
    "mealie-list-page-sizes",
    {},
    { deep: true },
  );
  const routeKey = computed(() => storageScope || String(route.name || route.path || "list"));
  const preferenceKey = computed(() => {
    const userKey = auth.user.value?.id || "anonymous";
    return `${userKey}:${routeKey.value}`;
  });
  const anonymousPreferenceKey = computed(() => `anonymous:${routeKey.value}`);

  return computed<number>({
    get() {
      const stored = Number(storedPageSizes.value[preferenceKey.value]);
      if (LIST_PAGE_SIZE_OPTIONS.includes(stored)) {
        return stored;
      }

      const anonymousStored = Number(storedPageSizes.value[anonymousPreferenceKey.value]);
      return LIST_PAGE_SIZE_OPTIONS.includes(anonymousStored)
        ? anonymousStored
        : defaultPageSize;
    },
    set(value) {
      if (!LIST_PAGE_SIZE_OPTIONS.includes(value)) {
        return;
      }
      storedPageSizes.value = {
        ...storedPageSizes.value,
        [preferenceKey.value]: value,
      };
    },
  });
}

export function useListPagination<T>(
  source: Ref<readonly T[]> | ComputedRef<readonly T[]>,
  defaultPageSize = DEFAULT_LIST_PAGE_SIZE,
  storageScope?: string,
) {
  const page = ref(1);
  const itemsPerPage = usePersistedListPageSize(defaultPageSize, storageScope);
  const totalItems = computed(() => source.value.length);
  const pageCount = computed(() => Math.max(1, Math.ceil(totalItems.value / itemsPerPage.value)));
  const paginatedItems = computed(() => {
    const start = (page.value - 1) * itemsPerPage.value;
    return source.value.slice(start, start + itemsPerPage.value);
  });

  watch(source, () => {
    page.value = 1;
  });

  watch(itemsPerPage, () => {
    page.value = 1;
  });

  watch(pageCount, (count) => {
    if (page.value > count) {
      page.value = count;
    }
  });

  return {
    page,
    itemsPerPage,
    totalItems,
    pageCount,
    paginatedItems,
  };
}
