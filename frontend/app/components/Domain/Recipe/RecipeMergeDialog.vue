<template>
  <BaseDialog
    v-model="dialog"
    :title="$t('recipe.merge-recipes')"
    :icon="$globals.icons.merge"
    width="760"
    max-width="96vw"
    can-submit
    :submit-text="$t('recipe.create-merged-recipe')"
    :submit-icon="$globals.icons.merge"
    :submit-disabled="selectedSlugs.length < 2 || saving"
    :loading="saving"
    @submit="mergeRecipes"
    @cancel="close"
  >
    <v-card-text class="pt-4">
      <p class="mb-4">
        {{ $t("recipe.merge-recipes-description") }}
      </p>
      <v-autocomplete
        v-model="selectedSlugs"
        v-model:search="recipeSearch"
        :items="recipeOptions"
        item-title="name"
        item-value="slug"
        :label="$t('recipe.choose-recipes')"
        :loading="loadingRecipes"
        multiple
        chips
        closable-chips
        clearable
        variant="outlined"
        hide-details="auto"
        :no-data-text="$t('recipe.no-recipes-found')"
      />
      <v-text-field
        v-model="mergedName"
        class="mt-4"
        variant="outlined"
        clearable
        :label="$t('recipe.merged-recipe-name')"
        :hint="$t('recipe.merged-recipe-name-hint')"
        persistent-hint
        maxlength="255"
      />
      <v-checkbox
        v-model="keepOriginals"
        class="mt-2"
        color="primary"
        hide-details
        :label="$t('recipe.keep-original-recipes')"
      />
      <p class="text-body-small text-medium-emphasis ms-8">
        {{ $t("recipe.keep-original-recipes-description") }}
      </p>

      <template v-if="mergedRecipes.length">
        <v-divider class="my-5" />
        <h3 class="text-title-medium mb-2">
          {{ $t("recipe.existing-recipe-merges") }}
        </h3>
        <v-list density="compact" class="recipe-merge-list">
          <v-list-item
            v-for="recipe in mergedRecipes"
            :key="recipe.slug"
            :title="recipe.name || recipe.slug"
          >
            <template #append>
              <v-btn
                icon
                size="small"
                variant="text"
                color="error"
                :title="$t('recipe.undo-recipe-merge')"
                :aria-label="$t('recipe.undo-recipe-merge')"
                @click="confirmUndo(recipe)"
              >
                <v-icon>{{ $globals.icons.undo }}</v-icon>
              </v-btn>
            </template>
          </v-list-item>
        </v-list>
      </template>
    </v-card-text>
  </BaseDialog>

  <BaseDialog
    v-model="undoDialog"
    :title="$t('recipe.undo-recipe-merge')"
    :icon="$globals.icons.undo"
    color="error"
    can-submit
    :submit-text="$t('recipe.undo-recipe-merge')"
    :loading="undoing"
    @submit="undoMerge"
  >
    <v-card-text>
      {{ $t("recipe.undo-recipe-merge-description", { name: undoTarget?.name || "" }) }}
    </v-card-text>
  </BaseDialog>
</template>

<script setup lang="ts">
import { watchDebounced } from "@vueuse/core";
import type { Recipe } from "~/lib/api/types/recipe";
import { useUserApi } from "~/composables/api/api-client";
import { alert } from "~/composables/use-toast";

interface Props {
  modelValue: boolean;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  "update:modelValue": [value: boolean];
  "updated": [];
}>();

const api = useUserApi();
const i18n = useI18n();
const selectedSlugs = ref<string[]>([]);
const recipeSearch = ref("");
const recipeOptions = ref<Recipe[]>([]);
const mergedRecipes = ref<Recipe[]>([]);
const mergedName = ref("");
const keepOriginals = ref(true);
const loadingRecipes = ref(false);
const saving = ref(false);
const undoing = ref(false);
const undoDialog = ref(false);
const undoTarget = ref<Recipe | null>(null);
let searchVersion = 0;

const dialog = computed({
  get: () => props.modelValue,
  set: value => emit("update:modelValue", value),
});

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      void Promise.all([loadRecipes(), loadMerges()]);
    }
    else {
      reset();
    }
  },
);

watchDebounced(
  recipeSearch,
  () => {
    if (props.modelValue) void loadRecipes();
  },
  { debounce: 250, maxWait: 700 },
);

onBeforeUnmount(() => {
  searchVersion += 1;
});

function reset() {
  searchVersion += 1;
  selectedSlugs.value = [];
  recipeSearch.value = "";
  recipeOptions.value = [];
  mergedName.value = "";
  keepOriginals.value = true;
  undoTarget.value = null;
  undoDialog.value = false;
}

function close() {
  dialog.value = false;
}

async function loadRecipes() {
  const version = ++searchVersion;
  loadingRecipes.value = true;
  try {
    const { data, error } = await api.recipes.search({
      search: recipeSearch.value.trim() || undefined,
      page: 1,
      perPage: 100,
      orderBy: "name",
      orderDirection: "asc",
    });
    if (version !== searchVersion) return;
    if (error || !data) {
      recipeOptions.value = [];
      return;
    }

    const selected = recipeOptions.value.filter(recipe => selectedSlugs.value.includes(recipe.slug || ""));
    const bySlug = new Map<string, Recipe>();
    for (const recipe of [...selected, ...data.items]) {
      if (recipe.slug && !recipe.isMergedRecipe) bySlug.set(recipe.slug, recipe);
    }
    recipeOptions.value = Array.from(bySlug.values());
  }
  finally {
    if (version === searchVersion) loadingRecipes.value = false;
  }
}

async function loadMerges() {
  const { data } = await api.recipes.getMerges();
  mergedRecipes.value = data || [];
}

async function mergeRecipes() {
  if (selectedSlugs.value.length < 2 || saving.value) return;
  saving.value = true;
  try {
    const { data, error } = await api.recipes.merge({
      sourceSlugs: selectedSlugs.value,
      name: mergedName.value.trim() || null,
      keepOriginals: keepOriginals.value,
    });
    if (error || !data?.recipe) {
      alert.error(i18n.t("recipe.recipe-merge-failed"));
      return;
    }
    alert.success(i18n.t("recipe.recipe-merge-complete"));
    selectedSlugs.value = [];
    mergedName.value = "";
    keepOriginals.value = true;
    await Promise.all([loadRecipes(), loadMerges()]);
    emit("updated");
  }
  finally {
    saving.value = false;
  }
}

function confirmUndo(recipe: Recipe) {
  undoTarget.value = recipe;
  undoDialog.value = true;
}

async function undoMerge() {
  if (!undoTarget.value?.slug || undoing.value) return;
  undoing.value = true;
  try {
    const { data, error } = await api.recipes.undoMerge(undoTarget.value.slug);
    if (error || !data) {
      alert.error(i18n.t("recipe.undo-recipe-merge-failed"));
      return;
    }
    alert.success(i18n.t("recipe.undo-recipe-merge-complete"));
    undoDialog.value = false;
    undoTarget.value = null;
    await Promise.all([loadRecipes(), loadMerges()]);
    emit("updated");
  }
  finally {
    undoing.value = false;
  }
}
</script>

<style scoped>
.recipe-merge-list {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  max-height: 220px;
  overflow-y: auto;
}
</style>
