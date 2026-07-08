<template>
  <v-container
    fluid
    class="recipe-finder-panel px-0"
  >
    <BasePageTitle
      v-if="showTitle"
      divider
    >
      <template #header>
        <v-img
          width="100"
          max-height="100"
          max-width="100"
          src="/svgs/manage-cookbooks.svg"
        />
      </template>
      <template #title>
        {{ $t('recipe-finder.recipe-finder') }}
      </template>

      <template #content>
        {{ $t('recipe-finder.recipe-finder-description') }}
      </template>
    </BasePageTitle>
    <v-container
      v-if="state.ready"
      class="recipe-finder-content ma-0 pa-0"
    >
      <v-row
        dense
        class="recipe-finder-layout"
      >
        <v-col
          cols="12"
          md="4"
          lg="3"
        >
          <v-sheet
            border
            rounded
            class="recipe-finder-filter-card pa-3"
          >
            <v-container class="ma-0 pa-0">
              <v-row no-gutters>
                <v-col
                  cols="12"
                  no-gutters
                  :class="attrs.searchFilter.colClass"
                >
                  <SearchFilter
                    v-if="foods"
                    v-model="selectedFoods"
                    :items="foods"
                    :class="attrs.searchFilter.filterClass"
                  >
                    <v-icon start>
                      {{ $globals.icons.foods }}
                    </v-icon>
                    {{ $t("general.foods") }}
                  </SearchFilter>
                  <SearchFilter
                    v-if="tools"
                    v-model="selectedTools"
                    :items="tools"
                    :class="attrs.searchFilter.filterClass"
                  >
                    <v-icon start>
                      {{ $globals.icons.potSteam }}
                    </v-icon>
                    {{ $t("tool.tools") }}
                  </SearchFilter>
                  <div :class="attrs.searchFilter.filterClass">
                    <v-badge
                      :model-value="!!state.queryFilterJSON.parts && state.queryFilterJSON.parts.length > 0"
                      size="small"
                      color="primary"
                      :content="(state.queryFilterJSON.parts || []).length"
                    >
                      <v-btn
                        size="small"
                        color="accent"
                        dark
                        @click="state.queryFilterMenu = !state.queryFilterMenu"
                      >
                        <v-icon start>
                          {{ $globals.icons.filter }}
                        </v-icon>
                        {{ $t("recipe-finder.other-filters") }}
                        <BaseDialog
                          v-model="state.queryFilterMenu"
                          :title="$t('recipe-finder.other-filters')"
                          :icon="$globals.icons.filter"
                          width="100%"
                          max-width="1100px"
                          :submit-disabled="!state.queryFilterEditorValue"
                          can-confirm
                          @confirm="saveQueryFilter"
                        >
                          <v-card-text>
                            <QueryFilterBuilder
                              :key="state.queryFilterMenuKey"
                              :initial-query-filter="state.queryFilterJSON"
                              :field-defs="queryFilterBuilderFields"
                              @input="(value) => state.queryFilterEditorValue = value"
                              @input-j-s-o-n="(value) => state.queryFilterEditorValueJSON = value"
                            />
                          </v-card-text>
                          <template #custom-card-action>
                            <BaseButton
                              color="error"
                              type="submit"
                              @click="clearQueryFilter"
                            >
                              <template #icon>
                                {{ $globals.icons.close }}
                              </template>
                              {{ $t("search.clear-selection") }}
                            </BaseButton>
                          </template>
                        </BaseDialog>
                      </v-btn>
                    </v-badge>
                  </div>
                </v-col>
              </v-row>
              <!-- Settings Menu -->
              <v-row
                no-gutters
                class="mb-2"
              >
                <v-col
                  cols="12"
                  :class="attrs.settings.colClass"
                >
                  <v-menu
                    v-model="state.settingsMenu"
                    offset-y
                    nudge-bottom="3"
                    :close-on-content-click="false"
                  >
                    <template #activator="{ props: menuProps }">
                      <v-btn
                        size="small"
                        color="primary"
                        dark
                        v-bind="menuProps"
                      >
                        <v-icon start>
                          {{ $globals.icons.cog }}
                        </v-icon>
                        {{ $t("general.settings") }}
                      </v-btn>
                    </template>
                    <v-card>
                      <v-card-text>
                        <div>
                          <v-number-input
                            v-model="state.settings.maxMissingFoods"
                            :precision="null"
                            :min="0"
                            control-variant="stacked"
                            inset
                            hide-details
                            :label="$t('recipe-finder.max-missing-ingredients')"
                          />
                          <v-number-input
                            v-model="state.settings.maxMissingTools"
                            :precision="null"
                            :min="0"
                            control-variant="stacked"
                            inset
                            hide-details
                            :label="$t('recipe-finder.max-missing-tools')"
                            class="mt-4"
                          />
                        </div>
                        <div class="mt-1">
                          <v-checkbox
                            v-if="isOwnGroup"
                            v-model="state.settings.includeFoodsOnHand"
                            density="compact"
                            size="small"
                            hide-details
                            class="my-auto"
                            :label="$t('recipe-finder.include-ingredients-on-hand')"
                          />
                          <v-checkbox
                            v-if="isOwnGroup"
                            v-model="state.settings.includeToolsOnHand"
                            density="compact"
                            size="small"
                            hide-details
                            class="my-auto"
                            :label="$t('recipe-finder.include-tools-on-hand')"
                          />
                        </div>
                      </v-card-text>
                    </v-card>
                  </v-menu>
                </v-col>
              </v-row>
              <v-row
                no-gutters
                class="my-2"
              >
                <v-col cols="12">
                  <v-divider />
                </v-col>
              </v-row>
              <v-row
                no-gutters
                class="mt-5"
              >
                <v-card-title class="ma-0 pa-0">
                  {{ $t("recipe-finder.selected-ingredients") }}
                </v-card-title>
                <v-container
                  class="ma-0 pa-0"
                  style="max-height: 60vh; overflow-y: auto;"
                >
                  <v-card-text
                    v-if="!selectedFoods.length"
                    class="ma-0 pa-0"
                  >
                    {{ $t("recipe-finder.no-ingredients-selected") }}
                  </v-card-text>
                  <div v-if="useMobile">
                    <v-row no-gutters>
                      <v-col
                        cols="12"
                        class="d-flex flex-wrap justify-end"
                      >
                        <v-chip
                          v-for="food in selectedFoods"
                          :key="food.id"
                          label
                          class="ma-1"
                          color="accent custom-transparent"
                          closable
                          variant="flat"
                          @click:close="removeFood(food)"
                        >
                          <span class="text-hide-overflow">{{ food.pluralName || food.name }}</span>
                        </v-chip>
                      </v-col>
                    </v-row>
                  </div>
                  <div v-else>
                    <v-row
                      v-for="food in selectedFoods"
                      :key="food.id"
                      no-gutters
                      class="mb-1"
                    >
                      <v-col cols="12">
                        <v-chip
                          label
                          color="accent custom-transparent"
                          variant="flat"
                          closable
                          @click:close="removeFood(food)"
                        >
                          <span class="text-hide-overflow">{{ food.pluralName || food.name }}</span>
                        </v-chip>
                      </v-col>
                    </v-row>
                  </div>
                </v-container>
              </v-row>
              <v-row
                v-if="selectedTools.length"
                no-gutters
                class="mt-5"
              >
                <v-card-title class="ma-0 pa-0">
                  {{ $t("recipe-finder.selected-tools") }}
                </v-card-title>
                <v-container class="ma-0 pa-0">
                  <div v-if="useMobile">
                    <v-row no-gutters>
                      <v-col
                        cols="12"
                        class="d-flex flex-wrap justify-end"
                      >
                        <v-chip
                          v-for="tool in selectedTools"
                          :key="tool.id"
                          label
                          class="ma-1"
                          color="accent custom-transparent"
                          closeable
                          variant="flat"
                          @click:close="removeTool(tool)"
                        >
                          <span class="text-hide-overflow">{{ tool.name }}</span>
                        </v-chip>
                      </v-col>
                    </v-row>
                  </div>
                  <div v-else>
                    <v-row
                      v-for="tool in selectedTools"
                      :key="tool.id"
                      no-gutters
                      class="mb-1"
                    >
                      <v-col cols="12">
                        <v-chip
                          label
                          color="accent custom-transparent"
                          closable
                          variant="flat"
                          @click:close="removeTool(tool)"
                        >
                          <span class="text-hide-overflow">{{ tool.name }}</span>
                        </v-chip>
                      </v-col>
                    </v-row>
                  </div>
                </v-container>
              </v-row>
            </v-container>
          </v-sheet>
        </v-col>
        <v-col
          cols="12"
          md="8"
          lg="9"
          :style="resultsColumnStyle"
        >
          <v-form
            v-if="isOwnGroup"
            class="mb-4"
            @submit.prevent="runAISearch"
          >
            <v-sheet
              border
              rounded
              class="recipe-finder-ai-card pa-3"
            >
              <div class="d-flex align-center mb-3">
                <v-icon start>
                  {{ $globals.icons.robot }}
                </v-icon>
                <span class="text-subtitle-1 font-weight-medium">
                  {{ $t("recipe-finder.ai-search") }}
                </span>
              </div>
              <v-row dense>
                <v-col
                  cols="12"
                  md="8"
                >
                  <v-textarea
                    v-model="aiSearch.query"
                    :label="$t('recipe-finder.ai-search-placeholder')"
                    rows="2"
                    auto-grow
                    clearable
                    density="compact"
                    variant="outlined"
                    hide-details
                  />
                </v-col>
                <v-col
                  cols="12"
                  sm="5"
                  md="2"
                >
                  <v-select
                    v-model="aiSearch.limit"
                    :items="aiSearchLimitOptions"
                    :label="$t('search.max-results')"
                    density="compact"
                    variant="outlined"
                    hide-details
                  />
                </v-col>
                <v-col
                  cols="12"
                  sm="7"
                  md="2"
                  class="d-flex align-start ga-2"
                >
                  <v-btn
                    color="primary"
                    type="submit"
                    :loading="aiSearch.loading"
                    :disabled="aiSearchDisabled"
                  >
                    <v-icon start>
                      {{ $globals.icons.search }}
                    </v-icon>
                    {{ $t("recipe-finder.ai-search-action") }}
                  </v-btn>
                  <v-btn
                    type="button"
                    variant="text"
                    :disabled="aiSearch.loading || !aiSearch.active"
                    @click="clearAISearch"
                  >
                    {{ $t("search.clear-selection") }}
                  </v-btn>
                </v-col>
              </v-row>
              <v-alert
                v-if="aiSearch.error"
                type="error"
                variant="tonal"
                density="compact"
                class="mt-3"
              >
                {{ aiSearch.error }}
              </v-alert>
            </v-sheet>
          </v-form>
          <v-container
            v-if="aiSearch.active"
            class="ma-0 pa-0"
          >
            <v-row v-if="aiSearch.loading">
              <v-col
                cols="12"
                class="d-flex justify-center"
              >
                <AppLoader waiting-text="" />
              </v-col>
            </v-row>
            <v-row
              v-else-if="aiSearchResults.length"
              density="compact"
            >
              <v-col cols="12">
                <v-card-title class="ma-0 pa-0">
                  {{ $t("recipe-finder.ai-search-results") }}
                </v-card-title>
                <v-card-subtitle class="ma-0 pa-0">
                  {{ $t("recipe-finder.ai-search-results-summary", {
                    count: aiSearchResults.length,
                    recipeCount: aiSearch.recipeCount,
                  }) }}
                </v-card-subtitle>
              </v-col>
              <v-col
                v-for="item in aiSearchResults"
                :key="item.recipe.slug"
                cols="12"
              >
                <v-lazy>
                  <v-container class="elevation-3">
                    <RecipeCardMobile
                      :name="item.recipe.name"
                      :description="item.recipe.description"
                      :slug="item.recipe.slug"
                      :rating="item.recipe.rating"
                      :image="item.recipe.image"
                      :recipe-id="item.recipe.id"
                    />
                    <v-alert
                      v-if="item.reason"
                      color="primary"
                      variant="tonal"
                      density="compact"
                      class="mt-2"
                    >
                      {{ item.reason }}
                    </v-alert>
                  </v-container>
                </v-lazy>
              </v-col>
            </v-row>
            <v-row v-else>
              <v-col
                cols="12"
                class="d-flex flex-column justify-center align-center ga-1"
              >
                <v-card-title class="ma-0 pa-0">
                  {{ $t("recipe-finder.ai-no-recipes-found") }}
                </v-card-title>
                <v-card-text class="ma-0 pa-0 text-center">
                  {{ $t("recipe-finder.ai-no-recipes-found-description") }}
                </v-card-text>
              </v-col>
            </v-row>
          </v-container>
          <v-container
            v-else-if="recipeSuggestions.readyToMake.length || recipeSuggestions.missingItems.length"
            class="ma-0 pa-0"
          >
            <v-row
              v-if="recipeSuggestions.readyToMake.length"
              density="compact"
            >
              <v-col cols="12">
                <v-card-title :class="attrs.title.class.readyToMake">
                  {{ $t("recipe-finder.ready-to-make") }}
                </v-card-title>
              </v-col>
              <v-col
                v-for="(item, idx) in recipeSuggestions.readyToMake"
                :key="`${idx}-ready`"
                cols="12"
              >
                <v-lazy>
                  <RecipeSuggestion
                    :recipe="item.recipe"
                    :missing-foods="item.missingFoods"
                    :missing-tools="item.missingTools"
                    :disable-checkbox="state.loading"
                    @add-food="addFood"
                    @remove-food="removeFood"
                    @add-tool="addTool"
                    @remove-tool="removeTool"
                  />
                </v-lazy>
              </v-col>
            </v-row>
            <v-row
              v-if="recipeSuggestions.missingItems.length"
              density="compact"
            >
              <v-col cols="12">
                <v-card-title :class="attrs.title.class.missingItems">
                  {{ $t("recipe-finder.almost-ready-to-make") }}
                </v-card-title>
              </v-col>
              <v-col
                v-for="(item, idx) in recipeSuggestions.missingItems"
                :key="`${idx}-missing`"
                cols="12"
              >
                <v-lazy>
                  <RecipeSuggestion
                    :recipe="item.recipe"
                    :missing-foods="item.missingFoods"
                    :missing-tools="item.missingTools"
                    :disable-checkbox="state.loading"
                    @add-food="addFood"
                    @remove-food="removeFood"
                    @add-tool="addTool"
                    @remove-tool="removeTool"
                  />
                </v-lazy>
              </v-col>
            </v-row>
          </v-container>
          <v-container v-else-if="!state.recipesReady">
            <v-row>
              <v-col
                cols="12"
                class="d-flex justify-center"
              >
                <div class="text-center">
                  <AppLoader waiting-text="" />
                </div>
              </v-col>
            </v-row>
          </v-container>
          <v-container v-else>
            <v-row>
              <v-col
                cols="12"
                class="d-flex flex-column justify-center align-center ga-1"
              >
                <v-card-title class="ma-0 pa-0">
                  {{ $t("recipe-finder.no-recipes-found") }}
                </v-card-title>
                <v-card-text class="ma-0 pa-0 text-center">
                  {{ $t("recipe-finder.no-recipes-found-description") }}
                </v-card-text>
              </v-col>
            </v-row>
          </v-container>
        </v-col>
      </v-row>
    </v-container>
    <v-container v-else>
      <v-row>
        <v-col
          cols="12"
          class="d-flex justify-center"
        >
          <div class="text-center">
            <AppLoader waiting-text="" />
          </div>
        </v-col>
      </v-row>
    </v-container>
  </v-container>
</template>

<script setup lang="ts">
import { watchDebounced } from "@vueuse/core";
import { usePublicExploreApi, useUserApi } from "~/composables/api/api-client";
import { useLoggedInState } from "~/composables/use-logged-in-state";
import { useFoodStore, usePublicFoodStore, useToolStore, usePublicToolStore } from "~/composables/store";
import type { IngredientFood, RecipeAISearchResult, RecipeSuggestionQuery, RecipeSuggestionResponseItem, RecipeTool } from "~/lib/api/types/recipe";
import { Organizer } from "~/lib/api/types/non-generated";
import QueryFilterBuilder from "~/components/Domain/QueryFilterBuilder.vue";
import RecipeCardMobile from "~/components/Domain/Recipe/RecipeCardMobile.vue";
import RecipeSuggestion from "~/components/Domain/Recipe/RecipeSuggestion.vue";
import SearchFilter from "~/components/Domain/SearchFilter.vue";
import type { QueryFilterJSON } from "~/lib/api/types/non-generated";
import type { FieldDefinition } from "~/composables/use-query-filter-builder";
import { useRecipeFinderPreferences } from "~/composables/use-users/preferences";

interface RecipeSuggestions {
  readyToMake: RecipeSuggestionResponseItem[];
  missingItems: RecipeSuggestionResponseItem[];
}

const props = withDefaults(defineProps<{
  showTitle?: boolean;
  scrollResults?: boolean;
}>(), {
  showTitle: false,
  scrollResults: true,
});

const display = useDisplay();
const i18n = useI18n();
const auth = useMealieAuth();
const route = useRoute();

const useMobile = computed(() => display.smAndDown.value);
const resultsColumnStyle = computed(() => {
  return useMobile.value || !props.scrollResults ? "" : "max-height: 70vh; overflow-y: auto";
});

const groupSlug = computed(() => route.params.groupSlug as string || auth.user.value?.groupSlug || "");
const { isOwnGroup } = useLoggedInState();
const userApi = useUserApi();
const api = isOwnGroup.value ? userApi : usePublicExploreApi(groupSlug.value).explore;

const preferences = useRecipeFinderPreferences();
const state = reactive({
  ready: false,
  loading: false,
  recipesReady: false,
  settingsMenu: false,
  queryFilterMenu: false,
  queryFilterMenuKey: 0,
  queryFilterEditorValue: "",
  queryFilterEditorValueJSON: {},
  queryFilterJSON: preferences.value.queryFilterJSON,
  settings: {
    maxMissingFoods: preferences.value.maxMissingFoods,
    maxMissingTools: preferences.value.maxMissingTools,
    includeFoodsOnHand: preferences.value.includeFoodsOnHand,
    includeToolsOnHand: preferences.value.includeToolsOnHand,
    queryFilter: preferences.value.queryFilter,
    limit: 20,
  },
});

onMounted(() => {
  if (!isOwnGroup.value) {
    state.settings.includeFoodsOnHand = false;
    state.settings.includeToolsOnHand = false;
  }
});

watch(
  () => state,
  (newState) => {
    preferences.value.queryFilter = newState.settings.queryFilter;
    preferences.value.queryFilterJSON = newState.queryFilterJSON;
    preferences.value.maxMissingFoods = newState.settings.maxMissingFoods;
    preferences.value.maxMissingTools = newState.settings.maxMissingTools;
    preferences.value.includeFoodsOnHand = newState.settings.includeFoodsOnHand;
    preferences.value.includeToolsOnHand = newState.settings.includeToolsOnHand;
  },
  {
    deep: true,
  },
);

const attrs = computed(() => {
  return {
    title: {
      class: {
        readyToMake: "ma-0 pa-0",
        missingItems: recipeSuggestions.value.readyToMake.length ? "ma-0 pa-0 mt-5" : "ma-0 pa-0",
      },
    },
    searchFilter: {
      colClass: useMobile.value ? "d-flex flex-wrap justify-end" : "d-flex flex-wrap justify-start",
      filterClass: useMobile.value ? "ml-4 mb-2" : "mr-4 mb-2",
    },
    settings: {
      colClass: useMobile.value ? "d-flex flex-wrap justify-end" : "d-flex flex-wrap justify-start",
    },
  };
});

const aiSearchLimitOptions = [5, 10, 20, 30, 50];
const aiSearch = reactive({
  query: "",
  limit: 10,
  loading: false,
  active: false,
  error: "",
  recipeCount: 0,
});
const aiSearchResults = ref<RecipeAISearchResult[]>([]);
let aiSearchRun = 0;
const aiSearchDisabled = computed(() => aiSearch.loading || aiSearch.query.trim().length < 2);

function apiErrorMessage(error: unknown, fallback: string) {
  const responseData = (error as { response?: { data?: { detail?: unknown } } })?.response?.data;
  const detail = responseData?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (detail && typeof detail === "object") {
    const detailObject = detail as { message?: string; exception?: string };
    return detailObject.exception || detailObject.message || fallback;
  }

  if (error instanceof Error) {
    return error.message || fallback;
  }

  return fallback;
}

async function runAISearch() {
  const query = aiSearch.query.trim();
  if (!query || aiSearchDisabled.value || !isOwnGroup.value) {
    return;
  }

  const run = ++aiSearchRun;
  aiSearch.loading = true;
  aiSearch.active = true;
  aiSearch.error = "";
  const { data, error } = await userApi.recipes.aiSearch({ query, limit: aiSearch.limit }).finally(() => {
    if (run === aiSearchRun) {
      aiSearch.loading = false;
    }
  });

  if (run !== aiSearchRun) {
    return;
  }

  if (error || !data) {
    aiSearchResults.value = [];
    aiSearch.recipeCount = 0;
    aiSearch.error = apiErrorMessage(error, i18n.t("recipe-finder.ai-search-error"));
    return;
  }

  aiSearchResults.value = data.items;
  aiSearch.recipeCount = data.recipeCount;
}

function clearAISearch() {
  aiSearchRun++;
  aiSearch.active = false;
  aiSearch.loading = false;
  aiSearch.error = "";
  aiSearchResults.value = [];
  aiSearch.recipeCount = 0;
}

const foodStore = isOwnGroup.value ? useFoodStore() : usePublicFoodStore(groupSlug.value);
const foods = foodStore.store.value;
const selectedFoods = ref<IngredientFood[]>([]);
function addFood(food: IngredientFood) {
  selectedFoods.value = [...selectedFoods.value, food];
  handleFoodUpdates();
}
function removeFood(food: IngredientFood) {
  selectedFoods.value = selectedFoods.value.filter(f => f.id !== food.id);
  handleFoodUpdates();
}
function handleFoodUpdates() {
  selectedFoods.value.sort((a, b) => (a.pluralName || a.name).localeCompare(b.pluralName || b.name));
  preferences.value.foodIds = selectedFoods.value.map(food => food.id);
}
watch(
  () => selectedFoods.value,
  () => {
    handleFoodUpdates();
  },
);

const toolStore = isOwnGroup.value ? useToolStore() : usePublicToolStore(groupSlug.value);
const tools = toolStore.store.value;
const selectedTools = ref<RecipeTool[]>([]);
function addTool(tool: RecipeTool) {
  selectedTools.value = [...selectedTools.value, tool];
  handleToolUpdates();
}
function removeTool(tool: RecipeTool) {
  selectedTools.value = selectedTools.value.filter(t => t.id !== tool.id);
  handleToolUpdates();
}
function handleToolUpdates() {
  selectedTools.value.sort((a, b) => a.name.localeCompare(b.name));
  preferences.value.toolIds = selectedTools.value.map(tool => tool.id);
}
watch(
  () => selectedTools.value,
  () => {
    handleToolUpdates();
  },
);

async function hydrateFoods() {
  if (!preferences.value.foodIds.length) {
    return;
  }
  if (!foodStore.store.value.length) {
    await foodStore.actions.refresh();
  }

  const foods = preferences.value.foodIds
    .map(foodId => foodStore.store.value.find(food => food.id === foodId))
    .filter(food => !!food);

  selectedFoods.value = foods;
}

async function hydrateTools() {
  if (!preferences.value.toolIds.length) {
    return;
  }
  if (!toolStore.store.value.length) {
    await toolStore.actions.refresh();
  }

  const tools = preferences.value.toolIds
    .map(toolId => toolStore.store.value.find(tool => tool.id === toolId))
    .filter(tool => !!tool);

  selectedTools.value = tools;
}

onMounted(async () => {
  await Promise.all([hydrateFoods(), hydrateTools()]);
  state.ready = true;
  if (!selectedFoods.value.length) {
    state.recipesReady = true;
  };
});

const recipeResponseItems = ref<RecipeSuggestionResponseItem[]>([]);
const recipeSuggestions = computed<RecipeSuggestions>(() => {
  const readyToMake: RecipeSuggestionResponseItem[] = [];
  const missingItems: RecipeSuggestionResponseItem[] = [];
  recipeResponseItems.value.forEach((responseItem) => {
    if (responseItem.missingFoods.length === 0 && responseItem.missingTools.length === 0) {
      readyToMake.push(responseItem);
    }
    else {
      missingItems.push(responseItem);
    };
  });

  return {
    readyToMake,
    missingItems,
  };
});

watchDebounced(
  [selectedFoods, selectedTools, state.settings], async () => {
    // don't search for suggestions if no foods are selected
    if (!selectedFoods.value.length) {
      recipeResponseItems.value = [];
      state.recipesReady = true;
      return;
    }

    state.loading = true;
    const { data } = await api.recipes.getSuggestions(
      {
        limit: state.settings.limit,
        queryFilter: state.settings.queryFilter,
        maxMissingFoods: state.settings.maxMissingFoods,
        maxMissingTools: state.settings.maxMissingTools,
        includeFoodsOnHand: state.settings.includeFoodsOnHand,
        includeToolsOnHand: state.settings.includeToolsOnHand,
      } as RecipeSuggestionQuery,
      selectedFoods.value.map(food => food.id),
      selectedTools.value.map(tool => tool.id),
    );
    state.loading = false;
    if (!data) {
      return;
    }
    recipeResponseItems.value = data.items;
    state.recipesReady = true;
  },
  {
    debounce: 500,
  },
);

const queryFilterBuilderFields: FieldDefinition[] = [
  {
    name: "recipe_category.id",
    label: i18n.t("category.categories"),
    type: Organizer.Category,
  },
  {
    name: "tags.id",
    label: i18n.t("tag.tags"),
    type: Organizer.Tag,
  },
  {
    name: "household_id",
    label: i18n.t("household.households"),
    type: Organizer.Household,
  },
  {
    name: "user_id",
    label: i18n.t("user.users"),
    type: Organizer.User,
  },
  {
    name: "last_made",
    label: i18n.t("general.last-made"),
    type: "relativeDate",
  },
];

function clearQueryFilter() {
  state.queryFilterEditorValue = "";
  state.queryFilterEditorValueJSON = { parts: [] } as QueryFilterJSON;
  state.settings.queryFilter = "";
  state.queryFilterJSON = { parts: [] } as QueryFilterJSON;
  state.queryFilterMenu = false;
  state.queryFilterMenuKey += 1;
}

function saveQueryFilter() {
  state.settings.queryFilter = state.queryFilterEditorValue || "";
  state.queryFilterJSON = state.queryFilterEditorValueJSON || { parts: [] } as QueryFilterJSON;
  state.queryFilterMenu = false;
}
</script>

<style scoped>
.recipe-finder-panel {
  --finder-gap: 12px;
}

.recipe-finder-content {
  max-width: 100%;
}

.recipe-finder-layout {
  row-gap: var(--finder-gap);
}

.recipe-finder-filter-card,
.recipe-finder-ai-card {
  background: rgb(var(--v-theme-surface));
}

.recipe-finder-filter-card {
  height: 100%;
}

.recipe-finder-filter-card :deep(.v-card-title) {
  font-size: 0.95rem;
  font-weight: 700;
  line-height: 1.3;
  padding-block: 4px !important;
}

.recipe-finder-filter-card :deep(.v-chip) {
  max-width: 100%;
}

.recipe-finder-ai-card {
  border-color: rgba(var(--v-theme-primary), 0.35);
}

.recipe-finder-ai-card :deep(.v-field) {
  background: rgb(var(--v-theme-surface));
}

@media (max-width: 960px) {
  .recipe-finder-filter-card {
    height: auto;
  }
}
</style>
