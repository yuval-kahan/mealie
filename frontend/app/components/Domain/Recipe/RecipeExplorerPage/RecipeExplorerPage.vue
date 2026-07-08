<template>
  <v-container
    fluid
    class="px-0"
  >
    <RecipeExplorerPageSearch
      ref="searchComponent"
      v-model:finder-open="finderOpen"
      @ready="onSearchReady"
    />
    <v-expand-transition>
      <v-container
        v-if="finderOpen"
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
    <v-divider />
    <v-container class="mt-6 px-md-6">
      <RecipeCardSection
        v-if="ready"
        class="mt-n5"
        :icon="$globals.icons.silverwareForkKnife"
        :title="$t('general.recipes')"
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
  </v-container>
</template>

<script setup lang="ts">
import RecipeExplorerPageSearch from "./RecipeExplorerPageParts/RecipeExplorerPageSearch.vue";
import { useLoggedInState } from "~/composables/use-logged-in-state";
import RecipeFinderPanel from "~/components/Domain/Recipe/RecipeFinderPanel.vue";
import RecipeCardSection from "~/components/Domain/Recipe/RecipeCardSection.vue";
import { useLazyRecipes } from "~/composables/recipes";

const auth = useMealieAuth();
const route = useRoute();

const { isOwnGroup } = useLoggedInState();
const groupSlug = computed(() => route.params.groupSlug as string || auth.user.value?.groupSlug || "");

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
