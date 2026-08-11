<template>
  <v-container
    fluid
    class="px-0"
  >
    <RecipeExplorerPageSearch
      v-if="canLoadRecipes"
      ref="searchComponent"
      v-model:finder-open="finderOpen"
      @ready="onSearchReady"
    />
    <v-expand-transition>
      <v-container
        v-if="canLoadRecipes && finderOpen"
        class="recipe-explorer-finder-panel px-md-6 pb-5"
      >
        <v-sheet
          border
          rounded
          class="pa-3 pa-md-4"
        >
          <RecipeFinderPanel :scroll-results="false" />
        </v-sheet>
      </v-container>
    </v-expand-transition>
    <v-divider v-if="canLoadRecipes" />
    <v-container v-if="canLoadRecipes" class="mt-6 px-md-6">
      <RecipeCardSection
        v-if="ready"
        class="mt-n5"
        :icon="displayIcon"
        :title="$t(titleKey)"
        :section="section"
        :group-by-book="groupByBook"
        :group-by-category="['recipes', 'sauce'].includes(section) && isOwnGroup"
        :recipes="recipes"
        :query="searchQuery"
        disable-sort
        @item-selected="onItemSelected"
        @replace-recipes="replaceRecipes"
        @append-recipes="appendRecipes"
        @delete="removeRecipe"
        @renamed="renameRecipe"
      />
    </v-container>
    <v-container v-else class="py-12 text-center">
      <v-btn
        color="primary"
        to="/login"
      >
        {{ $t("user.login") }}
      </v-btn>
    </v-container>
  </v-container>
</template>

<script setup lang="ts">
import RecipeExplorerPageSearch from "./RecipeExplorerPageParts/RecipeExplorerPageSearch.vue";
import { useLoggedInState } from "~/composables/use-logged-in-state";
import RecipeFinderPanel from "~/components/Domain/Recipe/RecipeFinderPanel.vue";
import RecipeCardSection from "~/components/Domain/Recipe/RecipeCardSection.vue";
import { useLazyRecipes } from "~/composables/recipes";

interface Props {
  section?: string;
  titleKey?: string;
  icon?: string | null;
  groupByBook?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  section: "recipes",
  titleKey: "general.recipes",
  icon: null,
  groupByBook: false,
});

const { $globals } = useNuxtApp();
const section = computed(() => props.section);
const titleKey = computed(() => props.titleKey);
const groupByBook = computed(() => props.groupByBook);
const displayIcon = computed(() => props.icon || $globals.icons.silverwareForkKnife);

const route = useRoute();

const { loggedIn, isOwnGroup, groupSlug, isHomeRoute } = useLoggedInState();
const canLoadRecipes = computed(() => loggedIn.value || (!isHomeRoute.value && Boolean(groupSlug.value)));

const { recipes, appendRecipes, removeRecipe, renameRecipe, replaceRecipes } = useLazyRecipes(isOwnGroup.value ? null : groupSlug.value);

const ready = ref(false);
const finderOpen = ref(route.query.finder === "true");
const searchComponent = ref<InstanceType<typeof RecipeExplorerPageSearch>>();

const searchQuery = computed(() => {
  return searchComponent.value?.passedQueryWithSeed || {};
});

function onSearchReady() {
  ready.value = true;
}

function onItemSelected(item: any, urlPrefix: string) {
  searchComponent.value?.filterItems(item, urlPrefix);
}

watch(
  () => route.query.finder,
  (value) => {
    if (value === "true") {
      finderOpen.value = true;
    }
  },
);
</script>

<style scoped>
.recipe-explorer-finder-panel {
  margin-top: -1rem;
  max-width: 1120px;
}
</style>
