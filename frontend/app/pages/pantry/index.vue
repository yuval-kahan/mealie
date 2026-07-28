<template>
  <v-container class="narrow-container">
    <BaseDialog
      v-model="itemDialogOpen"
      :title="editingItem ? $t('pantry.edit-item') : $t('pantry.add-item')"
      :icon="$globals.icons.foods"
      can-submit
      keep-open
      :loading="saving"
      :submit-disabled="!form.name.trim()"
      @submit="saveItem"
      @close="resetForm"
    >
      <v-card-text>
        <v-text-field
          v-model="form.name"
          variant="outlined"
          :label="$t('pantry.item-name')"
          autofocus
        />
        <v-checkbox
          v-model="trackQuantity"
          :label="$t('pantry.track-quantity')"
          hide-details
          class="mb-3"
        />
        <v-row v-if="trackQuantity" dense>
          <v-col cols="12" sm="6">
            <v-number-input
              v-model="form.quantity"
              :min="0"
              variant="outlined"
              control-variant="stacked"
              :label="$t('pantry.quantity')"
            />
          </v-col>
          <v-col cols="12" sm="6">
            <v-text-field v-model="form.unit" variant="outlined" :label="$t('pantry.unit')" />
          </v-col>
        </v-row>
        <v-text-field v-model="form.category" variant="outlined" :label="$t('pantry.category')" />
        <v-textarea v-model="form.note" variant="outlined" rows="2" auto-grow :label="$t('pantry.note')" />
      </v-card-text>
    </BaseDialog>

    <BaseDialog
      v-model="deleteDialogOpen"
      :title="$t('general.confirm')"
      :icon="$globals.icons.delete"
      color="error"
      can-confirm
      @confirm="deleteItem"
    >
      <v-card-text>
        {{ $t("pantry.delete-confirm", { name: deletingItem?.name || "" }) }}
      </v-card-text>
    </BaseDialog>

    <BaseDialog
      v-model="historyDialogOpen"
      :title="$t('pantry.search-history')"
      :icon="$globals.icons.clockOutline"
    >
      <v-card-text>
        <v-text-field
          v-model="historySearch"
          :label="$t('pantry.search-history')"
          :prepend-inner-icon="$globals.icons.search"
          clearable
          hide-details
          density="compact"
          class="mb-3"
        />
        <v-progress-linear v-if="historyLoading" indeterminate color="primary" class="mb-3" />
        <div v-else-if="historyItems.length" class="pantry-history-dialog">
          <button
            v-for="entry in historyItems"
            :key="entry.id"
            type="button"
            class="pantry-history-row"
            @click="restoreHistory(entry)"
          >
            <v-icon size="small">
              {{ entry.useAi ? $globals.icons.robot : $globals.icons.search }}
            </v-icon>
            <span class="pantry-history-row__text">
              <strong>{{ entry.query }}</strong>
              <small>{{ formatHistoryDate(entry.createdAt) }}</small>
            </span>
            <v-btn
              icon
              size="x-small"
              variant="text"
              color="error"
              :title="$t('general.delete')"
              @click.stop="deleteHistoryEntry(entry.id)"
            >
              <v-icon>{{ $globals.icons.delete }}</v-icon>
            </v-btn>
          </button>
        </div>
        <v-alert v-else type="info" variant="tonal">
          {{ $t("pantry.no-search-history") }}
        </v-alert>
      </v-card-text>
    </BaseDialog>

    <BasePageTitle divider>
      <template #title>
        {{ $t("pantry.food-i-have") }}
      </template>
      <template #subtitle>
        {{ $t("pantry.description") }}
      </template>
    </BasePageTitle>

    <div class="pantry-toolbar mb-5">
      <v-text-field
        v-model="search"
        :label="$t('search.search')"
        :prepend-inner-icon="$globals.icons.search"
        clearable
        hide-details
        density="compact"
      />
      <v-btn color="primary" :prepend-icon="$globals.icons.create" @click="openCreateDialog">
        {{ $t("pantry.add-item") }}
      </v-btn>
    </div>

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />
    <div v-else-if="filteredItems.length" class="pantry-items mb-8">
      <v-card
        v-for="item in filteredItems"
        :key="item.id"
        variant="outlined"
        class="pantry-item"
      >
        <v-card-text class="pantry-item__content">
          <v-icon color="primary">
            {{ $globals.icons.foods }}
          </v-icon>
          <div class="pantry-item__text">
            <strong>{{ item.name }}</strong>
            <span v-if="item.quantity != null">
              {{ item.quantity }} {{ item.unit || "" }}
            </span>
            <small v-if="item.note">{{ item.note }}</small>
          </div>
          <v-chip v-if="item.category" size="small" variant="tonal" color="primary">
            {{ item.category }}
          </v-chip>
          <v-btn icon size="small" variant="text" :title="$t('general.edit')" @click="openEditDialog(item)">
            <v-icon>{{ $globals.icons.edit }}</v-icon>
          </v-btn>
          <v-btn
            icon
            size="small"
            variant="text"
            color="error"
            :title="$t('general.delete')"
            @click="openDeleteDialog(item)"
          >
            <v-icon>{{ $globals.icons.delete }}</v-icon>
          </v-btn>
        </v-card-text>
      </v-card>
    </div>
    <v-alert v-else type="info" variant="tonal" class="mb-8">
      {{ $t("pantry.no-items") }}
    </v-alert>

    <section class="pantry-suggestions">
      <div class="d-flex align-center ga-2 mb-3">
        <v-icon color="primary">
          {{ $globals.icons.robot }}
        </v-icon>
        <h2 class="text-h6">
          {{ $t("pantry.find-recipes") }}
        </h2>
      </div>
      <v-btn-toggle v-model="suggestionMode" mandatory divided class="mb-4">
        <v-btn value="normal" :prepend-icon="$globals.icons.filter">
          {{ $t("pantry.normal-match") }}
        </v-btn>
        <v-btn value="ai" :prepend-icon="$globals.icons.robot">
          {{ $t("pantry.ai-match") }}
        </v-btn>
      </v-btn-toggle>
      <v-textarea
        v-model="availableText"
        variant="outlined"
        rows="3"
        auto-grow
        :label="$t('pantry.additional-food-or-request')"
        :hint="$t('pantry.additional-food-hint')"
        persistent-hint
      />
      <div v-if="recentHistory.length" class="pantry-recent mb-4">
        <div class="pantry-recent__title">
          <strong>{{ $t("pantry.recent-searches") }}</strong>
          <v-btn
            v-if="historyTotal > recentHistory.length"
            size="small"
            variant="text"
            :prepend-icon="$globals.icons.clockOutline"
            @click="openHistoryDialog"
          >
            {{ $t("pantry.all-searches", { count: historyTotal }) }}
          </v-btn>
        </div>
        <div class="d-flex flex-wrap ga-2">
          <v-chip
            v-for="entry in recentHistory"
            :key="entry.id"
            :prepend-icon="entry.useAi ? $globals.icons.robot : $globals.icons.search"
            color="primary"
            variant="tonal"
            class="pantry-recent__chip"
            @click="restoreHistory(entry)"
          >
            {{ entry.query }}
          </v-chip>
        </div>
      </div>
      <v-btn
        color="primary"
        :prepend-icon="suggestionMode === 'ai' ? $globals.icons.robot : $globals.icons.search"
        :loading="suggesting"
        :disabled="!items.length && !availableText.trim()"
        @click="loadSuggestions"
      >
        {{ $t("pantry.find-recipes") }}
      </v-btn>

      <div v-if="suggestionsLoaded" class="mt-6">
        <h3 class="text-subtitle-1 font-weight-bold mb-3">
          {{ $t("pantry.suggestions") }}
        </h3>
        <div v-if="suggestions.length" class="pantry-results">
          <v-card
            v-for="suggestion in suggestions"
            :key="suggestion.recipe.id || suggestion.recipe.slug"
            :to="suggestion.recipe.slug ? `/g/${groupSlug}/r/${suggestion.recipe.slug}` : undefined"
            variant="outlined"
            class="pantry-result"
          >
            <v-img
              v-if="suggestion.recipe.image"
              :src="recipeImageUrl(suggestion.recipe.id || '')"
              width="120"
              cover
            />
            <v-card-text>
              <div class="d-flex align-center justify-space-between ga-3">
                <strong>{{ suggestion.recipe.name }}</strong>
                <v-chip size="small" color="success" variant="tonal">
                  {{ $t("pantry.match-score", { score: suggestion.score }) }}
                </v-chip>
              </div>
              <p v-if="suggestion.reason" class="mt-2 mb-0">
                {{ suggestion.reason }}
              </p>
              <p v-if="suggestion.matchedItems.length" class="mt-2 mb-0">
                <strong>{{ $t("pantry.matched-items") }}:</strong>
                {{ suggestion.matchedItems.join(", ") }}
              </p>
              <p v-if="suggestion.missingIngredients.length" class="mt-1 mb-0 text-medium-emphasis">
                <strong>{{ $t("pantry.missing-items") }}:</strong>
                {{ suggestion.missingIngredients.join(", ") }}
              </p>
            </v-card-text>
          </v-card>
        </div>
        <v-alert v-else type="info" variant="tonal">
          {{ $t("pantry.no-suggestions") }}
        </v-alert>
      </div>
    </section>
  </v-container>
</template>

<script setup lang="ts">
import type {
  PantryItem,
  PantryItemCreate,
  PantryRecipeSuggestion,
  PantrySearchHistory,
} from "~/lib/api/types/pantry-item";
import { useUserApi } from "~/composables/api/api-client";
import { alert } from "~/composables/use-toast";

const i18n = useI18n();
const api = useUserApi();
const auth = useMealieAuth();
const { $globals } = useNuxtApp();
const groupSlug = computed(() => auth.user.value?.groupSlug || "home");

const items = ref<PantryItem[]>([]);
const loading = ref(false);
const saving = ref(false);
const search = ref("");
const itemDialogOpen = ref(false);
const editingItem = ref<PantryItem | null>(null);
const deletingItem = ref<PantryItem | null>(null);
const deleteDialogOpen = ref(false);
const trackQuantity = ref(false);
const form = reactive<PantryItemCreate>({
  name: "",
  quantity: null,
  unit: "",
  category: "",
  note: "",
});
const suggestionMode = ref<"normal" | "ai">("normal");
const availableText = ref("");
const suggesting = ref(false);
const suggestionsLoaded = ref(false);
const suggestions = ref<PantryRecipeSuggestion[]>([]);
const historyDialogOpen = ref(false);
const historyLoading = ref(false);
const historySearch = ref("");
const historyItems = ref<PantrySearchHistory[]>([]);
const historyTotal = ref(0);
const RECENT_HISTORY_LIMIT = 6;
let historySearchTimer: ReturnType<typeof setTimeout> | undefined;

const recentHistory = computed(() => historyItems.value.slice(0, RECENT_HISTORY_LIMIT));

const filteredItems = computed(() => {
  const query = search.value.trim().toLocaleLowerCase();
  if (!query) return items.value;
  return items.value.filter(item =>
    `${item.name} ${item.category || ""} ${item.note || ""}`.toLocaleLowerCase().includes(query),
  );
});

function recipeImageUrl(id: string) {
  return id ? `/api/media/recipes/${id}/images/original.webp` : "";
}

function resetForm() {
  editingItem.value = null;
  trackQuantity.value = false;
  Object.assign(form, { name: "", quantity: null, unit: "", category: "", note: "" });
}

function openCreateDialog() {
  resetForm();
  itemDialogOpen.value = true;
}

function openEditDialog(item: PantryItem) {
  editingItem.value = item;
  trackQuantity.value = item.quantity != null;
  Object.assign(form, {
    name: item.name,
    quantity: item.quantity ?? null,
    unit: item.unit || "",
    category: item.category || "",
    note: item.note || "",
  });
  itemDialogOpen.value = true;
}

function openDeleteDialog(item: PantryItem) {
  deletingItem.value = item;
  deleteDialogOpen.value = true;
}

async function loadItems() {
  loading.value = true;
  try {
    const { data } = await api.pantryItems.getAll();
    items.value = data || [];
  }
  finally {
    loading.value = false;
  }
}

async function saveItem() {
  if (!form.name.trim() || saving.value) return;
  saving.value = true;
  try {
    const payload: PantryItemCreate = {
      name: form.name.trim(),
      quantity: trackQuantity.value ? form.quantity : null,
      unit: trackQuantity.value ? form.unit?.trim() || null : null,
      category: form.category?.trim() || null,
      note: form.note?.trim() || null,
    };
    const response = editingItem.value
      ? await api.pantryItems.updateOne(editingItem.value.id, payload)
      : await api.pantryItems.createOne(payload);
    if (response.error || !response.data) {
      alert.error(i18n.t("pantry.item-save-failed"));
      return;
    }
    itemDialogOpen.value = false;
    resetForm();
    await loadItems();
    alert.success(i18n.t("pantry.item-saved"));
  }
  finally {
    saving.value = false;
  }
}

async function deleteItem() {
  if (!deletingItem.value) return;
  const targetId = deletingItem.value.id;
  const { error } = await api.pantryItems.deleteOne(targetId);
  if (!error) items.value = items.value.filter(item => item.id !== targetId);
  deletingItem.value = null;
  deleteDialogOpen.value = false;
}

async function loadSuggestions() {
  suggesting.value = true;
  try {
    const { data, error } = await api.pantryItems.suggestRecipes({
      useAi: suggestionMode.value === "ai",
      availableText: availableText.value.trim() || null,
      limit: 20,
      targetLanguage: i18n.locale.value,
    });
    if (error || !data) {
      alert.error(i18n.t("pantry.suggestion-failed"));
      return;
    }
    suggestions.value = data.items;
    suggestionsLoaded.value = true;
    await loadHistory(undefined, 50);
  }
  finally {
    suggesting.value = false;
  }
}

async function loadHistory(searchValue?: string, limit = 50) {
  historyLoading.value = true;
  try {
    const { data } = await api.pantryItems.getSearchHistory(searchValue, limit);
    historyItems.value = data?.items || [];
    historyTotal.value = data?.total || 0;
  }
  finally {
    historyLoading.value = false;
  }
}

function restoreHistory(entry: PantrySearchHistory) {
  suggestionMode.value = entry.useAi ? "ai" : "normal";
  availableText.value = entry.query;
  suggestions.value = entry.response.items;
  suggestionsLoaded.value = true;
  historyDialogOpen.value = false;
}

function openHistoryDialog() {
  historySearch.value = "";
  historyDialogOpen.value = true;
  void loadHistory(undefined, 200);
}

async function deleteHistoryEntry(id: string) {
  const { error } = await api.pantryItems.deleteSearchHistory(id);
  if (error) return;
  historyItems.value = historyItems.value.filter(entry => entry.id !== id);
  historyTotal.value = Math.max(0, historyTotal.value - 1);
}

function formatHistoryDate(value?: string | null) {
  if (!value) return "";
  return new Intl.DateTimeFormat(i18n.locale.value, {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

watch(historySearch, (value) => {
  if (!historyDialogOpen.value) return;
  if (historySearchTimer) clearTimeout(historySearchTimer);
  historySearchTimer = setTimeout(() => {
    void loadHistory(value, 200);
  }, 250);
});

onBeforeUnmount(() => {
  if (historySearchTimer) clearTimeout(historySearchTimer);
});

onMounted(async () => {
  await Promise.all([loadItems(), loadHistory(undefined, 50)]);
});
</script>

<style scoped>
.pantry-toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
}

.pantry-items,
.pantry-results {
  display: grid;
  gap: 8px;
}

.pantry-item {
  border-radius: 6px;
}

.pantry-item__content {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto auto auto;
  gap: 10px;
  align-items: center;
}

.pantry-item__text {
  display: grid;
  min-width: 0;
}

.pantry-item__text small,
.pantry-item__text span {
  color: rgb(var(--v-theme-on-surface-variant));
}

.pantry-result {
  display: flex;
  min-height: 112px;
  border-radius: 6px;
}

.pantry-recent {
  display: grid;
  gap: 8px;
}

.pantry-recent__title {
  align-items: center;
  display: flex;
  justify-content: space-between;
}

.pantry-recent__chip {
  max-width: min(100%, 320px);
}

.pantry-history-dialog {
  display: grid;
  gap: 4px;
  max-height: min(55vh, 520px);
  overflow-y: auto;
}

.pantry-history-row {
  align-items: center;
  background: transparent;
  border: 0;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  color: inherit;
  cursor: pointer;
  display: grid;
  font: inherit;
  gap: 10px;
  grid-template-columns: auto minmax(0, 1fr) auto;
  padding: 10px 4px;
  text-align: start;
  width: 100%;
}

.pantry-history-row:hover,
.pantry-history-row:focus-visible {
  background: rgba(var(--v-theme-primary), 0.08);
}

.pantry-history-row__text {
  display: grid;
  min-width: 0;
}

.pantry-history-row__text strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pantry-history-row__text small {
  color: rgb(var(--v-theme-on-surface-variant));
}

@media (max-width: 600px) {
  .pantry-toolbar {
    grid-template-columns: 1fr;
  }

  .pantry-item__content {
    grid-template-columns: auto minmax(0, 1fr) auto auto;
  }

  .pantry-item__content .v-chip {
    grid-column: 2 / -1;
    justify-self: start;
  }
}
</style>
