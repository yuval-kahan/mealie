<template>
  <div>
    <RecipeMergeDialog
      v-if="isOwnGroup"
      v-model="recipeMergeDialog"
      @updated="loadRecipePage"
    />
    <v-row
      v-if="!disableToolbar"
      class="align-center pb-2"
    >
      <v-icon
        v-if="title"
        size="large"
        start
      >
        {{ displayTitleIcon }}
      </v-icon>
      <span class="text-headline-small">{{ title }}</span>
      <v-spacer />
      <v-btn
        v-if="isOwnGroup"
        variant="text"
        :icon="$vuetify.display.xs"
        :to="aiCookbookRoute"
        :title="$t('cookbook.create-book-with-ai')"
      >
        <v-icon :start="!$vuetify.display.xs">
          {{ $globals.icons.book }}
        </v-icon>
        {{ $vuetify.display.xs ? null : $t("cookbook.create-book-with-ai") }}
      </v-btn>
      <v-btn
        v-if="isOwnGroup"
        variant="text"
        :icon="$vuetify.display.xs"
        :title="$t('recipe.merge-recipes')"
        @click="recipeMergeDialog = true"
      >
        <v-icon :start="!$vuetify.display.xs">
          {{ $globals.icons.merge }}
        </v-icon>
        {{ $vuetify.display.xs ? null : $t("recipe.merge-recipes") }}
      </v-btn>
      <v-btn
        :icon="$vuetify.display.xs"
        variant="text"
        :disabled="recipes.length === 0"
        @click="navigateRandom"
      >
        <v-icon :start="!$vuetify.display.xs">
          {{ $globals.icons.diceMultiple }}
        </v-icon>
        {{ $vuetify.display.xs ? null : $t("general.random") }}
      </v-btn>
      <v-menu
        v-if="!disableSort"
        offset-y
        start
      >
        <template #activator="{ props: activatorProps }">
          <v-btn
            variant="text"
            :icon="$vuetify.display.xs"
            v-bind="activatorProps"
            :loading="sortLoading"
          >
            <v-icon :start="!$vuetify.display.xs">
              {{ preferences.sortIcon }}
            </v-icon>
            {{ $vuetify.display.xs ? null : $t("general.sort") }}
          </v-btn>
        </template>
        <v-list>
          <v-list-item @click="sortRecipes(EVENTS.az)">
            <div class="d-flex align-center flex-nowrap">
              <v-icon class="mr-2" inline>
                {{ $globals.icons.orderAlphabeticalAscending }}
              </v-icon>
              <v-list-item-title>{{ $t("general.sort-alphabetically") }}</v-list-item-title>
            </div>
          </v-list-item>
          <v-list-item @click="sortRecipes(EVENTS.rating)">
            <div class="d-flex align-center flex-nowrap">
              <v-icon class="mr-2" inline>
                {{ $globals.icons.star }}
              </v-icon>
              <v-list-item-title>{{ $t("general.rating") }}</v-list-item-title>
            </div>
          </v-list-item>
          <v-list-item @click="sortRecipes(EVENTS.created)">
            <div class="d-flex align-center flex-nowrap">
              <v-icon class="mr-2" inline>
                {{ $globals.icons.newBox }}
              </v-icon>
              <v-list-item-title>{{ $t("general.created") }}</v-list-item-title>
            </div>
          </v-list-item>
          <v-list-item @click="sortRecipes(EVENTS.updated)">
            <div class="d-flex align-center flex-nowrap">
              <v-icon class="mr-2" inline>
                {{ $globals.icons.update }}
              </v-icon>
              <v-list-item-title>{{ $t("general.updated") }}</v-list-item-title>
            </div>
          </v-list-item>
          <v-list-item @click="sortRecipes(EVENTS.lastMade)">
            <div class="d-flex align-center flex-nowrap">
              <v-icon class="mr-2" inline>
                {{ $globals.icons.chefHat }}
              </v-icon>
              <v-list-item-title>{{ $t("general.last-made") }}</v-list-item-title>
            </div>
          </v-list-item>
          <v-list-item @click="sortRecipes(EVENTS.shuffle)">
            <div class="d-flex align-center flex-nowrap">
              <v-icon class="mr-2" inline>
                {{ $globals.icons.diceMultiple }}
              </v-icon>
              <v-list-item-title>{{ $t("general.random") }}</v-list-item-title>
            </div>
          </v-list-item>
        </v-list>
      </v-menu>
      <v-btn
        variant="text"
        :icon="$vuetify.display.xs"
        :color="userExperiencePreferences.showRecipeItemImages ? 'primary' : undefined"
        :title="$t('recipe.toggle-item-images')"
        :aria-label="$t('recipe.toggle-item-images')"
        @click="userExperiencePreferences.showRecipeItemImages = !userExperiencePreferences.showRecipeItemImages"
      >
        <v-icon :start="!$vuetify.display.xs">
          {{ $globals.icons.fileImage }}
        </v-icon>
        {{ $vuetify.display.xs ? null : $t("recipe.item-images") }}
      </v-btn>
      <ContextMenu
        v-if="!$vuetify.display.smAndDown"
        :items="[
          {
            title: $t('general.toggle-view'),
            icon: $globals.icons.eye,
            event: 'toggle-dense-view',
          },
        ]"
        @toggle-dense-view="toggleMobileCards()"
      />
    </v-row>
    <div v-if="recipes && ready">
      <div class="mt-2">
        <template
          v-for="group in recipeGroups"
          :key="group.key"
        >
          <button
            v-if="showBookGroups"
            type="button"
            class="recipe-book-group"
            :aria-expanded="isBookGroupExpanded(group.key)"
            @click="toggleBookGroup(group.key)"
          >
            <v-icon>
              {{ isBookGroupExpanded(group.key) ? $globals.icons.chevronDown : $globals.icons.chevronRight }}
            </v-icon>
            <v-icon>{{ group.bookId ? $globals.icons.book : $globals.icons.silverwareForkKnife }}</v-icon>
            <strong>{{ group.title }}</strong>
            <span>{{ group.recipes.length }}</span>
          </button>
          <v-expand-transition>
            <div v-show="!showBookGroups || isBookGroupExpanded(group.key)">
              <v-row v-if="!useMobileCards">
                <v-col
                  v-for="recipe in group.recipes"
                  :key="recipe.id!"
                  :sm="6"
                  :md="6"
                  :lg="4"
                  :xl="3"
                >
                  <RecipeCard
                    :name="recipe.name!"
                    :description="recipe.description!"
                    :slug="recipe.slug!"
                    :rating="recipe.rating!"
                    :image="recipe.image!"
                    :tags="recipe.tags!"
                    :categories="recipe.recipeCategory!"
                    :recipe-id="recipe.id!"
                    :extras="recipe.extras"
                    @delete="$emit('delete', $event)"
                    @renamed="$emit('renamed', $event)"
                  />
                </v-col>
              </v-row>
              <v-row
                v-else
                density="comfortable"
              >
                <v-col
                  v-for="recipe in group.recipes"
                  :key="recipe.id!"
                  cols="12"
                  :sm="singleColumn ? '12' : '12'"
                  :md="singleColumn ? '12' : '6'"
                  :lg="singleColumn ? '12' : '4'"
                  :xl="singleColumn ? '12' : '3'"
                >
                  <RecipeCardMobile
                    :name="recipe.name!"
                    :description="recipe.description!"
                    :slug="recipe.slug!"
                    :rating="recipe.rating!"
                    :image="recipe.image!"
                    :tags="recipe.tags!"
                    :categories="recipe.recipeCategory!"
                    :recipe-id="recipe.id!"
                    :extras="recipe.extras"
                    @delete="$emit('delete', $event)"
                    @renamed="$emit('renamed', $event)"
                  />
                </v-col>
              </v-row>
            </div>
          </v-expand-transition>
        </template>
      </div>
      <BaseListPagination
        :page="page"
        :items-per-page="perPage"
        :total-items="totalRecipes"
        @update:page="changeRecipePage"
        @update:items-per-page="changeRecipePageSize"
      />
    </div>
    <v-fade-transition>
      <AppLoader
        v-if="loading"
        :loading="loading"
      />
    </v-fade-transition>
    <AppScrollToTop />
  </div>
</template>

<script setup lang="ts">
import RecipeCard from "./RecipeCard.vue";
import RecipeCardMobile from "./RecipeCardMobile.vue";
import { useLoggedInState } from "~/composables/use-logged-in-state";
import { useLazyRecipes } from "~/composables/recipes";
import type { Recipe } from "~/lib/api/types/recipe";
import { useUserExperiencePreferences, useUserSortPreferences } from "~/composables/use-users/preferences";
import type { RecipeSearchQuery } from "~/lib/api/user/recipes/recipe";
import { useUserApi } from "~/composables/api/api-client";
import type { UploadedBook } from "~/lib/api/types/uploaded-book";
import { usePersistedListPageSize } from "~/composables/use-list-pagination";

const REPLACE_RECIPES_EVENT = "replaceRecipes";

interface Props {
  disableToolbar?: boolean;
  disableSort?: boolean;
  icon?: string | null;
  title?: string | null;
  singleColumn?: boolean;
  recipes?: Recipe[];
  query?: RecipeSearchQuery | null;
}
const props = withDefaults(defineProps<Props>(), {
  disableToolbar: false,
  disableSort: false,
  icon: null,
  title: null,
  singleColumn: false,
  recipes: () => [],
  query: null,
});

const emit = defineEmits<{
  replaceRecipes: [recipes: Recipe[]];
  appendRecipes: [recipes: Recipe[]];
  delete: [slug: string];
  renamed: [{ slug: string; name: string; recipe?: Recipe }];
}>();

const display = useDisplay();
const preferences = useUserSortPreferences();
const userExperiencePreferences = useUserExperiencePreferences();

const EVENTS = {
  az: "az",
  rating: "rating",
  created: "created",
  updated: "updated",
  lastMade: "lastMade",
  shuffle: "shuffle",
};

const { $globals } = useNuxtApp();
const { isOwnGroup, groupSlug } = useLoggedInState();
const i18n = useI18n();
const api = useUserApi();
const uploadedBooks = ref<UploadedBook[]>([]);
const expandedBookGroups = ref<Set<string>>(new Set());
const aiCookbookRoute = computed(() => `/g/${groupSlug.value}/cookbooks?generate=true`);
const useMobileCards = computed(() => {
  return display.smAndDown.value || preferences.value.useMobileCards;
});

const displayTitleIcon = computed(() => {
  return props.icon || $globals.icons.tags;
});

const sortLoading = ref(false);
const recipeMergeDialog = ref(false);
const randomSeed = ref(Date.now().toString());

const page = ref(1);
const perPage = usePersistedListPageSize();
const totalRecipes = ref(0);
const ready = ref(false);
const loading = ref(false);
let recipeRequestId = 0;

interface RecipeBookGroup {
  key: string;
  bookId: string | null;
  title: string;
  recipes: Recipe[];
}

const recipeGroups = computed<RecipeBookGroup[]>(() => {
  const bookNames = new Map(uploadedBooks.value.map(book => [book.id, book.name]));
  const groups = new Map<string, RecipeBookGroup>();
  const unlinked: Recipe[] = [];

  for (const recipe of props.recipes) {
    const rawBookId = recipe.extras?.uploadedBookSourceId;
    const bookId = typeof rawBookId === "string" ? rawBookId.trim() : "";
    if (!bookId) {
      unlinked.push(recipe);
      continue;
    }
    let group = groups.get(bookId);
    if (!group) {
      group = {
        key: `book:${bookId}`,
        bookId,
        title: i18n.t("recipe.recipes-from-book", {
          book: bookNames.get(bookId) || i18n.t("cookbook.cookbook"),
        }),
        recipes: [],
      };
      groups.set(bookId, group);
    }
    group.recipes.push(recipe);
  }

  const result = Array.from(groups.values());
  if (unlinked.length) {
    result.push({
      key: "unlinked",
      bookId: null,
      title: i18n.t("recipe.recipes-not-from-book"),
      recipes: unlinked,
    });
  }
  return result;
});
const showBookGroups = computed(() => recipeGroups.value.some(group => Boolean(group.bookId)));

watch(
  () => recipeGroups.value.map(group => group.key),
  (keys) => {
    const next = new Set(expandedBookGroups.value);
    const currentKeys = new Set(keys);
    for (const key of keys) {
      if (!next.has(key)) next.add(key);
    }
    for (const key of next) {
      if (!currentKeys.has(key)) next.delete(key);
    }
    expandedBookGroups.value = next;
  },
  { immediate: true },
);

const { fetchPage, getRandom } = useLazyRecipes(isOwnGroup.value ? null : groupSlug.value);
const router = useRouter();

const queryFilter = computed(() => {
  return props.query?.queryFilter || null;

  // TODO: allow user to filter out null values when ordering by a value that may be null (such as lastMade)

  // const orderBy = props.query?.orderBy || preferences.value.orderBy;
  // const orderByFilter = preferences.value.filterNull && orderBy ? `${orderBy} IS NOT NULL` : null;

  // if (props.query.queryFilter && orderByFilter) {
  //   return `(${props.query.queryFilter}) AND ${orderByFilter}`;
  // } else if (props.query.queryFilter) {
  //   return props.query.queryFilter;
  // } else {
  //   return orderByFilter;
  // }
});

async function fetchRecipes() {
  const orderDir = props.query?.orderDirection || preferences.value.orderDirection;
  const orderByNullPosition = props.query?.orderByNullPosition || orderDir === "asc" ? "first" : "last";
  const orderBy = props.query?.orderBy || preferences.value.orderBy;
  const localQuery = { ...props.query };
  if (orderBy === "random") {
    localQuery._searchSeed = randomSeed.value;
  }
  return await fetchPage(
    page.value,
    perPage.value,
    orderBy,
    orderDir,
    orderByNullPosition,
    localQuery,
    // we use a computed queryFilter to filter out recipes that have a null value for the property we're sorting by
    queryFilter.value,
  );
}

onMounted(async () => {
  if (isOwnGroup.value) {
    void loadUploadedBooks();
  }
  loading.value = true;
  try {
    await initRecipes();
  }
  catch (error) {
    console.error("Failed to load recipe cards", error);
    emit(REPLACE_RECIPES_EVENT, []);
  }
  finally {
    ready.value = true;
    loading.value = false;
  }
});

async function loadUploadedBooks() {
  try {
    const { data } = await api.uploadedBooks.getAll();
    uploadedBooks.value = data || [];
  }
  catch (error) {
    console.error("Failed to load uploaded books for recipe grouping", error);
    uploadedBooks.value = [];
  }
}

function isBookGroupExpanded(key: string) {
  return expandedBookGroups.value.has(key);
}

function toggleBookGroup(key: string) {
  const next = new Set(expandedBookGroups.value);
  if (next.has(key)) next.delete(key);
  else next.add(key);
  expandedBookGroups.value = next;
}

let lastQuery: string | undefined = JSON.stringify(props.query);
watch(
  () => props.query,
  async (newValue: RecipeSearchQuery | undefined | null) => {
    const newValueString = JSON.stringify(newValue);
    if (lastQuery !== newValueString) {
      lastQuery = newValueString;
      ready.value = false;
      try {
        await initRecipes();
      }
      catch (error) {
        console.error("Failed to refresh recipe cards", error);
        emit(REPLACE_RECIPES_EVENT, []);
      }
      finally {
        ready.value = true;
      }
    }
  },
);

async function initRecipes() {
  if (preferences.value.orderBy === "random") {
    randomSeed.value = Date.now().toString();
  }
  page.value = 1;
  await loadRecipePage();
}

async function loadRecipePage() {
  const requestId = ++recipeRequestId;
  loading.value = true;
  try {
    const result = await fetchRecipes();
    if (requestId !== recipeRequestId) return;
    totalRecipes.value = result?.total ?? 0;
    emit(REPLACE_RECIPES_EVENT, result?.items ?? []);
  }
  finally {
    if (requestId === recipeRequestId) {
      loading.value = false;
    }
  }
}

async function changeRecipePage(nextPage: number) {
  if (nextPage === page.value || loading.value) return;
  page.value = nextPage;
  await loadRecipePage();
}

async function changeRecipePageSize(nextPageSize: number) {
  if (nextPageSize === perPage.value || loading.value) return;
  perPage.value = nextPageSize;
  page.value = 1;
  await loadRecipePage();
}

async function sortRecipes(sortType: string) {
  if (sortLoading.value || loading.value) {
    return;
  }

  function setter(
    orderBy: string,
    ascIcon: string,
    descIcon: string,
    defaultOrderDirection = "asc",
    filterNull = false,
  ) {
    if (preferences.value.orderBy !== orderBy) {
      preferences.value.orderBy = orderBy;
      preferences.value.orderDirection = defaultOrderDirection;
      preferences.value.filterNull = filterNull;
    }
    else {
      preferences.value.orderDirection = preferences.value.orderDirection === "asc" ? "desc" : "asc";
    }
    preferences.value.sortIcon = preferences.value.orderDirection === "asc" ? ascIcon : descIcon;
  }

  switch (sortType) {
    case EVENTS.az:
      setter(
        "name",
        $globals.icons.sortAlphabeticalAscending,
        $globals.icons.sortAlphabeticalDescending,
        "asc",
        false,
      );
      break;
    case EVENTS.rating:
      setter("rating", $globals.icons.sortAscending, $globals.icons.sortDescending, "desc", true);
      break;
    case EVENTS.created:
      setter(
        "created_at",
        $globals.icons.sortCalendarAscending,
        $globals.icons.sortCalendarDescending,
        "desc",
        false,
      );
      break;
    case EVENTS.updated:
      setter("updated_at", $globals.icons.sortClockAscending, $globals.icons.sortClockDescending, "desc", false);
      break;
    case EVENTS.lastMade:
      setter(
        "last_made",
        $globals.icons.sortCalendarAscending,
        $globals.icons.sortCalendarDescending,
        "desc",
        true,
      );
      break;
    case EVENTS.shuffle:
      setter(
        "random",
        $globals.icons.diceMultiple,
        $globals.icons.diceMultiple, // icon in asc and desc is the same for random
      );
      // We update the seed value to have a different order
      randomSeed.value = Date.now().toString();
      break;
    default:
      console.log("Unknown Event", sortType);
      return;
  }

  page.value = 1;

  sortLoading.value = true;
  await loadRecipePage();
  sortLoading.value = false;
}

async function navigateRandom() {
  const recipe = await getRandom(props.query, queryFilter.value);
  if (!recipe?.slug) {
    return;
  }

  router.push(`/g/${groupSlug.value}/r/${recipe.slug}`);
}

function toggleMobileCards() {
  preferences.value.useMobileCards = !preferences.value.useMobileCards;
}
</script>

<style scoped>
.transparent {
  opacity: 1;
}

.recipe-book-group {
  align-items: center;
  background: rgb(var(--v-theme-surface));
  border: 0;
  border-block: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  color: inherit;
  cursor: pointer;
  display: flex;
  gap: 8px;
  margin: 12px 0 4px;
  min-height: 44px;
  padding: 8px 4px;
  text-align: start;
  width: 100%;
}

.recipe-book-group:hover,
.recipe-book-group:focus-visible {
  background: rgba(var(--v-theme-primary), 0.06);
}

.recipe-book-group span {
  color: rgb(var(--v-theme-on-surface-variant));
  margin-inline-start: auto;
}
</style>
