<template>
  <BaseDialog
    v-model="dialog"
    :title="$t('cookbook.delete-book-recipes')"
    :icon="$globals.icons.broom"
    color="error"
    width="820"
    max-width="920"
    can-submit
    keep-open
    :loading="loading"
    :submit-disabled="loading || selectedRecipeIds.length === 0 || (!deleteRecipes && !deleteShoppingLists)"
    :submit-icon="$globals.icons.delete"
    :submit-text="deleteSubmitText"
    disable-submit-on-enter
    @submit="deleteSelectedRecipes"
    @close="resetDialog"
  >
    <v-card-text>
      <div v-if="book" class="text-h6 mb-3">
        {{ book.name }}
      </div>
      <v-alert type="warning" variant="tonal" density="compact" class="mb-4">
        {{ $t("cookbook.delete-book-recipes-warning") }}
      </v-alert>

      <div class="d-flex flex-wrap ga-4 mb-4">
        <v-checkbox
          v-model="deleteRecipes"
          :label="`${$t('general.delete')} ${$t('general.recipes')}`"
          color="error"
          density="compact"
          hide-details
        />
        <v-checkbox
          v-model="deleteShoppingLists"
          :label="`${$t('general.delete')} ${$t('shopping-list.shopping-lists')}`"
          color="error"
          density="compact"
          hide-details
        />
      </div>

      <div class="d-flex flex-wrap align-center ga-2 mb-3">
        <v-btn
          variant="tonal"
          color="error"
          size="small"
          :prepend-icon="$globals.icons.check"
          :disabled="loading || recipes.length === selectedRecipeIds.length"
          @click="selectAllRecipes"
        >
          {{ $t("cookbook.select-all-recipes") }}
        </v-btn>
        <v-btn
          variant="text"
          size="small"
          :prepend-icon="$globals.icons.close"
          :disabled="loading || selectedRecipeIds.length === 0"
          @click="selectedRecipeIds = []"
        >
          {{ $t("search.clear-selection") }}
        </v-btn>
        <v-spacer />
        <span class="text-body-2 font-weight-medium text-error">
          {{ $t("cookbook.recipes-selected-for-deletion", { count: selectedRecipeIds.length }) }}
        </span>
        <span class="text-body-2 text-medium-emphasis">
          {{ $t("cookbook.recipes-will-remain", { count: remainingCount }) }}
        </span>
      </div>

      <v-text-field
        v-model="search"
        :label="$t('cookbook.search-extracted-recipes')"
        :prepend-inner-icon="$globals.icons.search"
        variant="outlined"
        density="comfortable"
        clearable
        hide-details
        class="mb-3"
      />

      <v-progress-linear v-if="loadingRecipes" indeterminate color="primary" />
      <v-alert v-else-if="loadError" type="error" variant="tonal">
        {{ loadError }}
      </v-alert>
      <v-alert v-else-if="recipes.length === 0" type="info" variant="tonal">
        {{ $t("cookbook.no-extracted-recipes") }}
      </v-alert>
      <div v-else class="book-recipe-delete-list">
        <v-checkbox
          v-for="recipe in filteredRecipes"
          :key="recipe.id"
          v-model="selectedRecipeIds"
          :value="recipe.id"
          color="error"
          density="compact"
          hide-details
          class="book-recipe-delete-list__item"
        >
          <template #label>
            <div class="min-width-0 py-1">
              <div class="font-weight-medium text-wrap">
                {{ recipe.name }}
              </div>
              <div v-if="recipe.source" class="text-caption text-medium-emphasis text-wrap">
                {{ recipe.source }}
              </div>
            </div>
          </template>
        </v-checkbox>
      </div>
    </v-card-text>
  </BaseDialog>
</template>

<script setup lang="ts">
import type { UploadedBookRecipeSummary } from "~/lib/api/types/uploaded-book";
import { useUserApi } from "~/composables/api";
import { alert } from "~/composables/use-toast";

interface Props {
  modelValue: boolean;
  book: { id: string; name: string } | null;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  "update:modelValue": [value: boolean];
  "deleted": [bookId: string, deletedCount: number, remainingCount: number];
}>();

const api = useUserApi();
const i18n = useI18n();
const recipes = ref<UploadedBookRecipeSummary[]>([]);
const selectedRecipeIds = ref<string[]>([]);
const search = ref("");
const loadingRecipes = ref(false);
const deletingRecipes = ref(false);
const deleteRecipes = ref(true);
const deleteShoppingLists = ref(true);
const loadError = ref("");
let loadRequestId = 0;

const dialog = computed({
  get: () => props.modelValue,
  set: value => emit("update:modelValue", value),
});
const loading = computed(() => loadingRecipes.value || deletingRecipes.value);
const deleteSubmitText = computed(() => {
  const targets: string[] = [];
  if (deleteRecipes.value) {
    targets.push(i18n.t("general.recipes"));
  }
  if (deleteShoppingLists.value) {
    targets.push(i18n.t("shopping-list.shopping-lists"));
  }
  return `${i18n.t("general.delete")} ${selectedRecipeIds.value.length} ${targets.join(" + ")}`;
});
const remainingCount = computed(() => Math.max(0, recipes.value.length - selectedRecipeIds.value.length));
const filteredRecipes = computed(() => {
  const query = search.value.trim().toLocaleLowerCase();
  if (!query) {
    return recipes.value;
  }
  return recipes.value.filter((recipe) => {
    return recipe.name.toLocaleLowerCase().includes(query)
      || (recipe.source || "").toLocaleLowerCase().includes(query);
  });
});

watch(
  () => [props.modelValue, props.book?.id] as const,
  ([isOpen]) => {
    if (isOpen) {
      void loadRecipes();
    }
  },
);

async function loadRecipes() {
  if (!props.book) {
    return;
  }
  const requestId = ++loadRequestId;
  loadingRecipes.value = true;
  loadError.value = "";
  try {
    const { data, error } = await api.uploadedBooks.getRecipes(props.book.id);
    if (requestId !== loadRequestId) {
      return;
    }
    if (error || !data) {
      loadError.value = i18n.t("cookbook.load-book-recipes-failed");
      return;
    }
    recipes.value = data;
    selectAllRecipes();
  }
  finally {
    if (requestId === loadRequestId) {
      loadingRecipes.value = false;
    }
  }
}

function selectAllRecipes() {
  selectedRecipeIds.value = recipes.value.map(recipe => recipe.id);
}

async function deleteSelectedRecipes() {
  if (!props.book || selectedRecipeIds.value.length === 0 || deletingRecipes.value) {
    return;
  }
  deletingRecipes.value = true;
  const bookId = props.book.id;
  const { data, error } = await api.uploadedBooks.deleteRecipes(bookId, {
    recipeIds: selectedRecipeIds.value,
    deleteRecipes: deleteRecipes.value,
    deleteShoppingLists: deleteShoppingLists.value,
  }).finally(() => {
    deletingRecipes.value = false;
  });
  if (error || !data) {
    alert.error(i18n.t("cookbook.delete-book-recipes-failed"));
    return;
  }

  alert.success([
    `${data.deletedCount} ${i18n.t("general.recipes")}`,
    `${data.deletedShoppingListCount} ${i18n.t("shopping-list.shopping-lists")}`,
  ].join(" / "));
  emit("deleted", bookId, data.deletedCount, data.remainingCount);
  dialog.value = false;
}

function resetDialog() {
  loadRequestId++;
  loadingRecipes.value = false;
  recipes.value = [];
  selectedRecipeIds.value = [];
  search.value = "";
  loadError.value = "";
  deleteRecipes.value = true;
  deleteShoppingLists.value = true;
}
</script>

<style scoped>
.book-recipe-delete-list {
  max-height: min(55vh, 560px);
  overflow-y: auto;
  border-block: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  scrollbar-gutter: stable;
}

.book-recipe-delete-list__item {
  min-height: 54px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.book-recipe-delete-list__item:last-child {
  border-bottom: 0;
}
</style>
