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
        <v-select
          v-if="formMode === 'ai' && !editingWebsite"
          v-model="aiWebsiteType"
          :items="aiWebsiteTypeOptions"
          item-title="title"
          item-value="value"
          :label="$t('shopping-website.website-types')"
          variant="outlined"
          class="mb-3"
        />
        <div v-else class="website-type-options mb-3">
          <strong>{{ $t("shopping-website.website-types") }}</strong>
          <v-checkbox
            v-model="form.isRecipeSite"
            :label="$t('shopping-website.recipe-site')"
            hide-details
            density="compact"
          />
          <v-checkbox
            v-model="form.isShoppingSite"
            :label="$t('shopping-website.shopping-site')"
            hide-details
            density="compact"
          />
          <small>{{ $t("shopping-website.website-types-help") }}</small>
        </div>
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

    <BaseDialog
      v-model="imageDialogOpen"
      :title="$t('shopping-website.website-image')"
      :icon="$globals.icons.fileImage"
      :loading="imageSaving"
      @close="resetImageDialog"
    >
      <v-card-text>
        <v-btn-toggle
          v-model="imageMode"
          mandatory
          divided
          density="comfortable"
          class="mb-4"
        >
          <v-btn value="upload" :prepend-icon="$globals.icons.upload">
            {{ $t("shopping-website.upload-image") }}
          </v-btn>
          <v-btn value="url" :prepend-icon="$globals.icons.link">
            {{ $t("shopping-website.image-address") }}
          </v-btn>
          <v-btn value="auto" :prepend-icon="$globals.icons.robot">
            {{ $t("shopping-website.find-image") }}
          </v-btn>
        </v-btn-toggle>
        <v-file-input
          v-if="imageMode === 'upload'"
          v-model="imageFile"
          accept="image/*"
          :label="$t('shopping-website.choose-image')"
          :prepend-icon="$globals.icons.fileImage"
          show-size
        />
        <v-text-field
          v-else-if="imageMode === 'url'"
          v-model="imageAddress"
          :label="$t('shopping-website.image-address')"
          :prepend-inner-icon="$globals.icons.link"
          type="url"
        />
        <v-alert v-else type="info" variant="tonal" density="compact">
          {{ $t("shopping-website.find-image-help") }}
        </v-alert>
      </v-card-text>
      <template #custom-card-action>
        <v-btn
          color="primary"
          :prepend-icon="$globals.icons.save"
          :disabled="!canSaveImage"
          :loading="imageSaving"
          @click="saveWebsiteImage"
        >
          {{ $t("general.save") }}
        </v-btn>
      </template>
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
    <template v-else-if="filteredWebsites.length">
      <v-checkbox
        v-model="groupByType"
        :label="$t('shopping-website.group-by-type')"
        density="compact"
        hide-details
        class="mb-4"
      />
      <section
        v-for="section in websiteSections"
        :key="section.key"
        class="shopping-website-section mb-7"
      >
        <div v-if="groupByType" class="shopping-website-section__header">
          <v-icon>{{ section.icon }}</v-icon>
          <h2 class="text-h6">
            {{ section.title }}
          </h2>
          <v-chip size="small" variant="tonal">
            {{ section.websites.length }}
          </v-chip>
        </div>
        <div class="shopping-websites-grid">
          <v-card v-for="website in section.websites" :key="`${section.key}-${website.id}`" class="shopping-website-card" variant="outlined">
            <div class="shopping-website-image">
              <v-img
                v-if="website.hasImage"
                :src="api.shoppingWebsites.imageUrl(website.id, website.imageVersion)"
                height="180"
                cover
              />
              <div v-else class="shopping-website-image-placeholder">
                <v-icon size="72" color="primary">
                  {{ $globals.icons.web }}
                </v-icon>
              </div>
              <v-btn
                class="shopping-website-image-action"
                icon
                size="small"
                color="primary"
                :title="$t('shopping-website.change-image')"
                @click="openImageDialog(website)"
              >
                <v-icon>{{ website.hasImage ? $globals.icons.edit : $globals.icons.fileImage }}</v-icon>
              </v-btn>
            </div>
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
              <div class="d-flex flex-wrap ga-1 mb-3">
                <v-chip v-if="website.isRecipeSite" size="small" color="primary" variant="tonal">
                  {{ $t("shopping-website.recipe-site") }}
                </v-chip>
                <v-chip v-if="website.isShoppingSite" size="small" color="success" variant="tonal">
                  {{ $t("shopping-website.shopping-site") }}
                </v-chip>
              </div>
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
      </section>
    </template>
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
const imageDialogOpen = ref(false);
const imageSaving = ref(false);
const imageWebsite = ref<ShoppingWebsite | null>(null);
const imageMode = ref<"upload" | "url" | "auto">("upload");
const imageFile = ref<File | null>(null);
const imageAddress = ref("");
const formMode = ref<"manual" | "ai">("manual");
const aiWebsiteType = ref<"auto" | "recipe" | "shopping" | "both">("auto");
const groupByType = ref(true);
const form = reactive<ShoppingWebsiteCreate>({
  name: "",
  url: "",
  pageFood: "",
  offeredFoods: [],
  isRecipeSite: true,
  isShoppingSite: true,
});

useSeoMeta({ title: i18n.t("shopping-website.websites") });

const canSubmit = computed(() => Boolean(
  form.url.trim()
  && (formMode.value === "ai" || form.isRecipeSite || form.isShoppingSite)
  && (formMode.value === "ai" || form.name.trim()),
));
const aiWebsiteTypeOptions = computed(() => [
  { title: i18n.t("shopping-website.detect-automatically"), value: "auto" },
  { title: i18n.t("shopping-website.recipe-site"), value: "recipe" },
  { title: i18n.t("shopping-website.shopping-site"), value: "shopping" },
  { title: i18n.t("shopping-website.recipe-and-shopping-site"), value: "both" },
]);
const canSaveImage = computed(() => Boolean(
  imageWebsite.value
  && (imageMode.value === "auto"
    || (imageMode.value === "upload" && imageFile.value)
    || (imageMode.value === "url" && imageAddress.value.trim())),
));
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
const websiteSections = computed(() => {
  if (!groupByType.value) {
    return [{
      key: "all",
      title: i18n.t("shopping-website.websites"),
      icon: $globals.icons.web,
      websites: filteredWebsites.value,
    }];
  }

  return [
    {
      key: "recipes",
      title: i18n.t("shopping-website.recipe-sites"),
      icon: $globals.icons.silverwareForkKnife,
      websites: filteredWebsites.value.filter(website => website.isRecipeSite),
    },
    {
      key: "shopping",
      title: i18n.t("shopping-website.shopping-sites"),
      icon: $globals.icons.cartCheck,
      websites: filteredWebsites.value.filter(website => website.isShoppingSite),
    },
  ].filter(section => section.websites.length);
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
  aiWebsiteType.value = "auto";
  Object.assign(form, {
    name: "",
    url: "",
    pageFood: "",
    offeredFoods: [],
    isRecipeSite: true,
    isShoppingSite: true,
  });
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
    isRecipeSite: website.isRecipeSite,
    isShoppingSite: website.isShoppingSite,
  });
  dialogOpen.value = true;
}

async function submitWebsite() {
  saving.value = true;
  const aiTypeOverrides = aiWebsiteType.value === "auto"
    ? {}
    : {
        isRecipeSite: aiWebsiteType.value === "recipe" || aiWebsiteType.value === "both",
        isShoppingSite: aiWebsiteType.value === "shopping" || aiWebsiteType.value === "both",
      };
  const response = editingWebsite.value
    ? await api.shoppingWebsites.updateOne(editingWebsite.value.id, form)
    : formMode.value === "ai"
      ? await api.shoppingWebsites.createWithAI({
          url: form.url,
          ...aiTypeOverrides,
        })
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

function resetImageDialog() {
  imageWebsite.value = null;
  imageMode.value = "upload";
  imageFile.value = null;
  imageAddress.value = "";
}

function openImageDialog(website: ShoppingWebsite) {
  resetImageDialog();
  imageWebsite.value = website;
  imageDialogOpen.value = true;
}

async function saveWebsiteImage() {
  if (!imageWebsite.value || imageSaving.value || !canSaveImage.value) return;
  imageSaving.value = true;
  try {
    const response = imageMode.value === "upload"
      ? await api.shoppingWebsites.uploadImage(imageWebsite.value.id, imageFile.value!)
      : imageMode.value === "url"
        ? await api.shoppingWebsites.saveImageUrl(imageWebsite.value.id, imageAddress.value.trim())
        : await api.shoppingWebsites.findImage(imageWebsite.value.id);
    if (!response.data || response.error) {
      alert.error(i18n.t("shopping-website.image-save-failed"));
      return;
    }
    const index = websites.value.findIndex(website => website.id === response.data!.id);
    if (index >= 0) websites.value[index] = response.data;
    imageDialogOpen.value = false;
    resetImageDialog();
    alert.success(i18n.t("shopping-website.image-saved"));
  }
  finally {
    imageSaving.value = false;
  }
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

.website-type-options {
  display: grid;
  gap: 2px 12px;
  grid-template-columns: 1fr 1fr;
}

.website-type-options strong,
.website-type-options small {
  grid-column: 1 / -1;
}

.shopping-website-section__header {
  align-items: center;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
  padding-bottom: 8px;
}

.shopping-website-card {
  display: flex;
  flex-direction: column;
  min-height: 260px;
}

.shopping-website-image {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  background: rgb(var(--v-theme-surface-variant));
}

.shopping-website-image-placeholder {
  align-items: center;
  display: flex;
  height: 100%;
  justify-content: center;
}

.shopping-website-image-action {
  position: absolute;
  inset-block-start: 8px;
  inset-inline-end: 8px;
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
