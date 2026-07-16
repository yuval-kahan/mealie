<template>
  <v-container class="narrow-container">
    <BaseDialog
      v-model="dialogOpen"
      :title="editingWebsite ? $t('shopping-website.edit-website') : $t('shopping-website.save-website')"
      :icon="$globals.icons.web"
      can-submit
      keep-open
      :loading="saving"
      :submit-disabled="!canSubmit"
      @submit="submitWebsite"
      @close="resetForm"
    >
      <v-card-text>
        <v-btn-toggle
          v-if="!editingWebsite"
          v-model="formMode"
          mandatory
          divided
          density="comfortable"
          class="mb-4"
        >
          <v-btn value="manual" :prepend-icon="$globals.icons.edit">
            {{ $t("shopping-website.manual") }}
          </v-btn>
          <v-btn value="ai" :prepend-icon="$globals.icons.robot">
            {{ $t("shopping-website.analyze-with-ai") }}
          </v-btn>
        </v-btn-toggle>

        <v-text-field
          v-if="formMode === 'manual'"
          v-model="form.name"
          :label="$t('shopping-website.website-name')"
          autofocus
        />
        <v-text-field
          v-model="form.url"
          :label="$t('shopping-website.website-address')"
          type="url"
          :prepend-inner-icon="$globals.icons.link"
        />
        <template v-if="formMode === 'manual'">
          <v-textarea
            v-model="form.pageFood"
            :label="$t('shopping-website.saved-page-food')"
            rows="3"
            auto-grow
          />
          <v-combobox
            v-model="form.offeredFoods"
            :label="$t('shopping-website.other-offered-foods')"
            multiple
            chips
            closable-chips
            clearable
          />
        </template>
        <v-alert
          v-else
          type="info"
          variant="tonal"
          density="compact"
        >
          {{ $t("shopping-website.ai-url-help") }}
        </v-alert>
      </v-card-text>
    </BaseDialog>

    <BaseDialog
      v-model="deleteDialogOpen"
      :title="$t('general.confirm')"
      :icon="$globals.icons.delete"
      color="error"
      can-confirm
      @confirm="deleteWebsite"
    >
      <v-card-text>
        {{ $t("shopping-website.delete-confirm") }}
        <v-progress-linear v-if="deletePreviewLoading" indeterminate color="primary" class="mt-4" />
        <template v-else-if="deletePreview">
          <v-checkbox
            v-if="deletePreview.recipeIds.length"
            v-model="deleteLinkedRecipes"
            :label="$t('shopping-website.delete-linked-recipes', { names: deletePreview.recipeNames.join(', ') })"
            density="compact"
            hide-details
            class="mt-4"
          />
          <v-checkbox
            v-if="deletePreview.shoppingListIds.length"
            v-model="deleteLinkedShoppingLists"
            :label="$t('shopping-website.delete-linked-shopping-lists', { names: deletePreview.shoppingListNames.join(', ') })"
            density="compact"
            hide-details
          />
          <v-alert
            v-if="deletePreview.recipeIds.length || deletePreview.shoppingListIds.length"
            type="info"
            variant="tonal"
            density="compact"
            class="mt-4"
          >
            {{ $t("shopping-website.linked-items-remain-by-default") }}
          </v-alert>
        </template>
      </v-card-text>
    </BaseDialog>

    <BasePageTitle divider>
      <template #title>
        {{ $t("shopping-website.websites") }}
      </template>
      <template #subtitle>
        {{ $t("shopping-website.websites-description") }}
      </template>
    </BasePageTitle>

    <div class="shopping-websites-toolbar mb-6">
      <v-text-field
        v-model="search"
        :label="$t('search.search')"
        :prepend-inner-icon="$globals.icons.search"
        density="compact"
        clearable
        hide-details
      />
      <v-btn color="primary" :prepend-icon="$globals.icons.create" @click="openCreateDialog">
        {{ $t("shopping-website.save-website") }}
      </v-btn>
    </div>

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />
    <div v-else-if="filteredWebsites.length" class="shopping-websites-grid">
      <v-card v-for="website in filteredWebsites" :key="website.id" class="shopping-website-card" variant="outlined">
        <v-card-title class="d-flex align-center ga-2">
          <v-icon color="primary">
            {{ $globals.icons.web }}
          </v-icon>
          <span class="text-truncate">{{ website.name }}</span>
        </v-card-title>
        <v-card-subtitle>
          <a :href="website.url" target="_blank" rel="noopener" class="shopping-website-link">
            {{ website.url }}
            <v-icon size="x-small">{{ $globals.icons.openInNew }}</v-icon>
          </a>
        </v-card-subtitle>
        <v-card-text>
          <div v-if="website.pageFood" class="mb-3">
            <strong>{{ $t("shopping-website.saved-page-food") }}:</strong>
            <div>{{ website.pageFood }}</div>
          </div>
          <div v-if="website.offeredFoods.length">
            <strong>{{ $t("shopping-website.other-offered-foods") }}:</strong>
            <div class="d-flex flex-wrap ga-1 mt-1">
              <v-chip v-for="food in website.offeredFoods" :key="food" size="small" color="primary" variant="tonal">
                {{ food }}
              </v-chip>
            </div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn icon variant="text" :title="$t('general.edit')" @click="openEditDialog(website)">
            <v-icon>{{ $globals.icons.edit }}</v-icon>
          </v-btn>
          <v-btn icon variant="text" color="error" :title="$t('general.delete')" @click="openDeleteDialog(website)">
            <v-icon>{{ $globals.icons.delete }}</v-icon>
          </v-btn>
        </v-card-actions>
      </v-card>
    </div>
    <v-alert v-else type="info" variant="tonal">
      {{ $t("shopping-website.no-websites") }}
    </v-alert>
  </v-container>
</template>

<script setup lang="ts">
import type { ShoppingWebsite, ShoppingWebsiteCreate, ShoppingWebsiteDeletePreview } from "~/lib/api/types/shopping-website";
import { useUserApi } from "~/composables/api/api-client";
import { alert } from "~/composables/use-toast";

const i18n = useI18n();
const api = useUserApi();
const websites = ref<ShoppingWebsite[]>([]);
const loading = ref(true);
const saving = ref(false);
const search = ref("");
const dialogOpen = ref(false);
const deleteDialogOpen = ref(false);
const editingWebsite = ref<ShoppingWebsite | null>(null);
const deletingWebsite = ref<ShoppingWebsite | null>(null);
const deletePreview = ref<ShoppingWebsiteDeletePreview>();
const deletePreviewLoading = ref(false);
const deleteLinkedRecipes = ref(false);
const deleteLinkedShoppingLists = ref(false);
const formMode = ref<"manual" | "ai">("manual");
const form = reactive<ShoppingWebsiteCreate>({ name: "", url: "", pageFood: "", offeredFoods: [] });

useSeoMeta({ title: i18n.t("shopping-website.websites") });

const canSubmit = computed(() => Boolean(form.url.trim() && (formMode.value === "ai" || form.name.trim())));
const filteredWebsites = computed(() => {
  const query = search.value.trim().toLocaleLowerCase();
  if (!query) return websites.value;
  return websites.value.filter(website => [
    website.name,
    website.url,
    website.pageFood || "",
    ...website.offeredFoods,
  ].join(" ").toLocaleLowerCase().includes(query));
});

onMounted(loadWebsites);

async function loadWebsites() {
  loading.value = true;
  const { data, error } = await api.shoppingWebsites.getAll();
  websites.value = data || [];
  if (error) alert.error(i18n.t("events.something-went-wrong"));
  loading.value = false;
}

function resetForm() {
  editingWebsite.value = null;
  formMode.value = "manual";
  Object.assign(form, { name: "", url: "", pageFood: "", offeredFoods: [] });
}

function openCreateDialog() {
  resetForm();
  dialogOpen.value = true;
}

function openEditDialog(website: ShoppingWebsite) {
  editingWebsite.value = website;
  formMode.value = "manual";
  Object.assign(form, {
    name: website.name,
    url: website.url,
    pageFood: website.pageFood || "",
    offeredFoods: [...website.offeredFoods],
  });
  dialogOpen.value = true;
}

async function submitWebsite() {
  saving.value = true;
  const response = editingWebsite.value
    ? await api.shoppingWebsites.updateOne(editingWebsite.value.id, form)
    : formMode.value === "ai"
      ? await api.shoppingWebsites.createWithAI({ url: form.url })
      : await api.shoppingWebsites.createOne(form);
  saving.value = false;
  if (!response.data || response.error) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }
  dialogOpen.value = false;
  resetForm();
  await loadWebsites();
}

async function openDeleteDialog(website: ShoppingWebsite) {
  deletingWebsite.value = website;
  deletePreview.value = undefined;
  deleteLinkedRecipes.value = false;
  deleteLinkedShoppingLists.value = false;
  deleteDialogOpen.value = true;
  deletePreviewLoading.value = true;
  try {
    const { data } = await api.shoppingWebsites.deletePreview(website.id);
    if (data) deletePreview.value = data;
  }
  finally {
    deletePreviewLoading.value = false;
  }
}

async function deleteWebsite() {
  if (!deletingWebsite.value) return;
  const { error } = await api.shoppingWebsites.deleteOne(deletingWebsite.value.id, {
    deleteRecipes: deleteLinkedRecipes.value,
    deleteShoppingLists: deleteLinkedShoppingLists.value,
  });
  if (error) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }
  deletingWebsite.value = null;
  await loadWebsites();
}
</script>

<style scoped>
.shopping-websites-toolbar {
  align-items: center;
  display: grid;
  gap: 12px;
  grid-template-columns: minmax(220px, 1fr) auto;
}

.shopping-websites-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 320px), 1fr));
}

.shopping-website-card {
  display: flex;
  flex-direction: column;
  min-height: 260px;
}

.shopping-website-card .v-card-text {
  flex: 1;
}

.shopping-website-link {
  overflow-wrap: anywhere;
}

@media (max-width: 600px) {
  .shopping-websites-toolbar {
    grid-template-columns: 1fr;
  }
}
</style>
