<template>
  <v-container class="product-knowledge-page">
    <BaseDialog
      v-model="editorOpen"
      :title="editingItem ? $t('product-knowledge.edit') : $t('product-knowledge.create')"
      :icon="$globals.icons.informationOutline"
      width="860"
      max-width="96vw"
      can-submit
      keep-open
      :loading="saving"
      :submit-disabled="!canSubmit"
      @submit="submitItem"
      @close="resetEditor"
    >
      <v-card-text class="pt-4">
        <v-tabs
          v-if="!editingItem"
          v-model="createMode"
          color="primary"
          density="comfortable"
        >
          <v-tab value="manual">
            {{ $t("product-knowledge.manual") }}
          </v-tab>
          <v-tab value="ai">
            {{ $t("product-knowledge.ai-explanation") }}
          </v-tab>
        </v-tabs>

        <v-window
          v-model="createMode"
          class="mt-4"
        >
          <v-window-item value="manual">
            <v-text-field
              v-model="form.title"
              :label="$t('product-knowledge.title')"
              variant="outlined"
              density="comfortable"
              autofocus
            />
            <v-text-field
              v-model="form.source"
              :label="$t('product-knowledge.source')"
              variant="outlined"
              density="comfortable"
            />
            <v-file-input
              v-model="imageFile"
              accept="image/*"
              :label="$t('product-knowledge.upload-image')"
              :prepend-inner-icon="$globals.icons.fileImage"
              prepend-icon=""
              clearable
              variant="outlined"
              density="comfortable"
            />
            <v-text-field
              v-model="imageUrl"
              :label="$t('product-knowledge.image-url')"
              :prepend-inner-icon="$globals.icons.link"
              type="url"
              variant="outlined"
              density="comfortable"
            />
            <div v-if="editingItem" class="d-flex flex-wrap ga-2 mb-4">
              <v-btn
                variant="tonal"
                color="primary"
                :prepend-icon="$globals.icons.robot"
                :loading="imageSaving"
                @click="findProductImage(editingItem)"
              >
                {{ $t("product-knowledge.find-image-with-ai") }}
              </v-btn>
              <v-btn
                v-if="editingItem.hasImage"
                variant="text"
                color="error"
                :prepend-icon="$globals.icons.delete"
                :loading="imageSaving"
                @click="deleteProductImage(editingItem)"
              >
                {{ $t("product-knowledge.delete-image") }}
              </v-btn>
            </div>
            <v-textarea
              v-model="form.summary"
              :label="$t('product-knowledge.summary')"
              variant="outlined"
              rows="3"
            />
            <v-textarea
              v-model="form.content"
              :label="$t('product-knowledge.content')"
              variant="outlined"
              rows="12"
            />
            <ArticleOrganizerInputs
              v-model:categories="form.categories"
              v-model:tags="form.tags"
              :category-items="categoryOptions"
              :tag-items="tagOptions"
            />
          </v-window-item>

          <v-window-item value="ai">
            <v-textarea
              v-model="aiTopic"
              :label="$t('product-knowledge.ai-topic')"
              :hint="$t('product-knowledge.ai-topic-hint')"
              persistent-hint
              variant="outlined"
              rows="8"
              autofocus
            />
            <v-text-field
              :model-value="targetLanguage"
              :label="$t('product-knowledge.target-language')"
              variant="outlined"
              density="comfortable"
              readonly
              class="mt-4"
            />
          </v-window-item>
        </v-window>
      </v-card-text>
    </BaseDialog>

    <BaseDialog
      v-model="detailsOpen"
      :title="selectedItem?.title || $t('product-knowledge.products-and-explanations')"
      :icon="$globals.icons.informationOutline"
      width="900"
      max-width="96vw"
    >
      <v-card-text v-if="selectedItem" class="product-details">
        <v-img
          v-if="selectedItem.hasImage && !imageErrors.has(selectedItem.id)"
          :src="api.productKnowledge.imageUrl(selectedItem)"
          :alt="selectedItem.title"
          class="product-details__image mb-5"
          cover
          @error="imageErrors.add(selectedItem.id)"
        />
        <p v-if="selectedItem.summary" class="text-subtitle-1 mb-4">
          {{ selectedItem.summary }}
        </p>
        <SafeMarkdown :source="selectedItem.content" />
        <a
          v-if="selectedItem.source"
          :href="isWebUrl(selectedItem.source) ? selectedItem.source : undefined"
          :target="isWebUrl(selectedItem.source) ? '_blank' : undefined"
          :rel="isWebUrl(selectedItem.source) ? 'noopener noreferrer' : undefined"
          class="d-block mt-5"
        >
          {{ selectedItem.source }}
        </a>
        <div class="d-flex flex-wrap ga-1 mt-4">
          <v-chip
            v-for="category in selectedItem.categories"
            :key="`detail-category-${category}`"
            size="small"
            color="primary"
            variant="tonal"
          >
            {{ category }}
          </v-chip>
          <v-chip
            v-for="tag in selectedItem.tags"
            :key="`detail-tag-${tag}`"
            size="small"
            color="accent"
            variant="tonal"
          >
            {{ tag }}
          </v-chip>
        </div>
      </v-card-text>
      <template #custom-card-action>
        <v-btn
          v-if="selectedItem"
          color="primary"
          variant="text"
          :prepend-icon="$globals.icons.edit"
          @click="editSelectedItem"
        >
          {{ $t("general.edit") }}
        </v-btn>
      </template>
    </BaseDialog>

    <BaseDialog
      v-model="deleteOpen"
      :title="$t('general.confirm')"
      :icon="$globals.icons.delete"
      color="error"
      can-confirm
      :loading="deleting"
      @confirm="deleteItem"
    >
      <v-card-text>
        {{ $t("product-knowledge.delete-confirm", { title: deletingItem?.title || "" }) }}
      </v-card-text>
    </BaseDialog>

    <BasePageTitle divider>
      <template #header>
        <v-icon size="72" color="primary">
          {{ $globals.icons.informationOutline }}
        </v-icon>
      </template>
      <template #title>
        {{ $t("product-knowledge.products-and-explanations") }}
      </template>
      <template #subTitle>
        {{ $t("product-knowledge.page-description") }}
      </template>
    </BasePageTitle>

    <div class="product-toolbar">
      <v-text-field
        v-model="search"
        :label="$t('search.search')"
        variant="outlined"
        density="comfortable"
        hide-details
        clearable
        :prepend-inner-icon="$globals.icons.search"
      />
      <v-combobox
        v-model="selectedCategories"
        :items="categoryOptions"
        :label="$t('category.categories')"
        variant="outlined"
        density="comfortable"
        hide-details
        multiple
        chips
        clearable
      />
      <v-combobox
        v-model="selectedTags"
        :items="tagOptions"
        :label="$t('tag.tags')"
        variant="outlined"
        density="comfortable"
        hide-details
        multiple
        chips
        clearable
      />
      <BaseButton create @click="openCreate" />
    </div>
    <BaseListSortControls
      v-model:sort-by="productSortBy"
      v-model:sort-direction="productSortDirection"
      :options="productSortOptions"
      class="mt-4"
    />

    <BaseListPagination
      v-if="filteredItems.length"
      v-model:page="productPage"
      v-model:items-per-page="productsPerPage"
      :total-items="productTotal"
    />

    <v-row class="mt-3">
      <v-col
        v-for="item in paginatedProducts"
        :key="item.id"
        cols="12"
        md="6"
        lg="4"
      >
        <v-card class="product-card" @click="openDetails(item)">
          <v-img
            v-if="item.hasImage && !imageErrors.has(item.id)"
            :src="api.productKnowledge.imageUrl(item)"
            :alt="item.title"
            height="190"
            cover
            @error="imageErrors.add(item.id)"
          />
          <div v-else class="product-card__image-placeholder">
            <v-icon size="64" color="primary">
              {{ $globals.icons.informationOutline }}
            </v-icon>
          </div>
          <v-card-title class="product-card__title">
            {{ item.title }}
          </v-card-title>
          <v-card-text>
            <p class="product-card__summary">
              {{ item.summary || item.content }}
            </p>
            <div class="d-flex flex-wrap ga-1">
              <v-chip
                v-for="category in item.categories.slice(0, 3)"
                :key="`${item.id}-category-${category}`"
                size="small"
                color="primary"
                variant="tonal"
              >
                {{ category }}
              </v-chip>
              <v-chip
                v-for="tag in item.tags.slice(0, 4)"
                :key="`${item.id}-tag-${tag}`"
                size="small"
                color="accent"
                variant="tonal"
              >
                {{ tag }}
              </v-chip>
            </div>
          </v-card-text>
          <v-card-actions @click.stop>
            <v-btn
              icon
              variant="text"
              :title="$t('product-knowledge.find-image-with-ai')"
              :loading="imageSaving && imageSavingId === item.id"
              @click="findProductImage(item)"
            >
              <v-icon>{{ $globals.icons.fileImage }}</v-icon>
            </v-btn>
            <v-spacer />
            <v-btn
              icon
              variant="text"
              :title="$t('general.edit')"
              @click="openEdit(item)"
            >
              <v-icon>{{ $globals.icons.edit }}</v-icon>
            </v-btn>
            <v-btn
              icon
              variant="text"
              color="error"
              :title="$t('general.delete')"
              @click="openDelete(item)"
            >
              <v-icon>{{ $globals.icons.delete }}</v-icon>
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <v-alert
      v-if="ready && !filteredItems.length"
      type="info"
      variant="tonal"
      class="mt-4"
    >
      {{ $t("product-knowledge.no-items") }}
    </v-alert>
  </v-container>
</template>

<script setup lang="ts">
import ArticleOrganizerInputs from "~/components/Domain/Article/ArticleOrganizerInputs.vue";
import SafeMarkdown from "~/components/global/SafeMarkdown.vue";
import { useUserApi } from "~/composables/api/api-client";
import { alert } from "~/composables/use-toast";
import type {
  ProductKnowledge,
  ProductKnowledgeCreate,
} from "~/lib/api/types/product-knowledge";

const i18n = useI18n();
const { $globals } = useNuxtApp();
const api = useUserApi();

useSeoMeta({
  title: i18n.t("product-knowledge.products-and-explanations"),
});

const ready = ref(false);
const items = ref<ProductKnowledge[]>([]);
const editorOpen = ref(false);
const detailsOpen = ref(false);
const deleteOpen = ref(false);
const saving = ref(false);
const deleting = ref(false);
const imageSaving = ref(false);
const imageSavingId = ref<string | null>(null);
const imageFile = ref<File | File[] | null>(null);
const imageUrl = ref("");
const imageErrors = reactive(new Set<string>());
const editingItem = ref<ProductKnowledge | null>(null);
const selectedItem = ref<ProductKnowledge | null>(null);
const deletingItem = ref<ProductKnowledge | null>(null);
const createMode = ref<"manual" | "ai">("manual");
const aiTopic = ref("");
const search = ref("");
const selectedCategories = ref<string[]>([]);
const selectedTags = ref<string[]>([]);
const PRODUCT_SORT_KEYS = ["title", "created", "updated", "categoryCount"] as const;
type ProductSortKey = typeof PRODUCT_SORT_KEYS[number];
const {
  sortBy: productSortBy,
  sortDirection: productSortDirection,
} = usePersistedListSort(PRODUCT_SORT_KEYS, "title", "asc", "product-knowledge");
const productSortOptions = computed<{ title: string; value: ProductSortKey }[]>(() => [
  { title: i18n.t("product-knowledge.title"), value: "title" },
  { title: i18n.t("catalog.created-at"), value: "created" },
  { title: i18n.t("catalog.updated-at"), value: "updated" },
  { title: i18n.t("catalog.category-count"), value: "categoryCount" },
]);

const form = reactive<ProductKnowledgeCreate>({
  title: "",
  summary: "",
  content: "",
  source: "",
  categories: [],
  tags: [],
});

const targetLanguage = computed(() => {
  const locale = String(i18n.locale.value || "").toLocaleLowerCase();
  return locale.startsWith("he")
    ? i18n.t("cookbook.language-hebrew")
    : i18n.t("cookbook.language-english");
});
const categoryOptions = computed(() => sortedUnique(items.value.flatMap(item => item.categories)));
const tagOptions = computed(() => sortedUnique(items.value.flatMap(item => item.tags)));
const canSubmit = computed(() => {
  if (editingItem.value || createMode.value === "manual") {
    return Boolean(form.title.trim() && form.content.trim());
  }
  return Boolean(aiTopic.value.trim());
});
const filteredItems = computed(() => {
  const query = search.value.trim().toLocaleLowerCase();
  const categories = new Set(selectedCategories.value.map(value => value.toLocaleLowerCase()));
  const tags = new Set(selectedTags.value.map(value => value.toLocaleLowerCase()));
  return items.value.filter((item) => {
    const haystack = [
      item.title,
      item.summary,
      item.content,
      item.source,
      item.categories.join(" "),
      item.tags.join(" "),
    ].join(" ").toLocaleLowerCase();
    const itemCategories = item.categories.map(value => value.toLocaleLowerCase());
    const itemTags = item.tags.map(value => value.toLocaleLowerCase());
    return (!query || haystack.includes(query))
      && (!categories.size || itemCategories.some(value => categories.has(value)))
      && (!tags.size || itemTags.some(value => tags.has(value)));
  });
});
const sortedItems = sortListItems(
  filteredItems,
  item => ({
    title: item.title,
    created: item.createdAt,
    updated: item.updatedAt,
    categoryCount: item.categories.length,
  })[productSortBy.value],
  productSortDirection,
  i18n.locale,
);
const {
  page: productPage,
  itemsPerPage: productsPerPage,
  totalItems: productTotal,
  paginatedItems: paginatedProducts,
} = useListPagination(sortedItems);

onMounted(refreshItems);

function sortedUnique(values: string[]) {
  return Array.from(new Set(values.map(value => value.trim()).filter(Boolean)))
    .sort((a, b) => a.localeCompare(b));
}

function isWebUrl(value: string | null | undefined) {
  return /^https?:\/\//i.test(String(value || "").trim());
}

async function refreshItems() {
  const { data, error } = await api.productKnowledge.getAll();
  if (error || !data) {
    alert.error(i18n.t("events.something-went-wrong"));
  }
  else {
    items.value = data;
  }
  ready.value = true;
}

function resetEditor() {
  editingItem.value = null;
  createMode.value = "manual";
  aiTopic.value = "";
  form.title = "";
  form.summary = "";
  form.content = "";
  form.source = "";
  form.categories = [];
  form.tags = [];
  imageFile.value = null;
  imageUrl.value = "";
}

function openCreate() {
  resetEditor();
  editorOpen.value = true;
}

function openEdit(item: ProductKnowledge) {
  resetEditor();
  editingItem.value = item;
  form.title = item.title;
  form.summary = item.summary || "";
  form.content = item.content;
  form.source = item.source || "";
  form.categories = [...item.categories];
  form.tags = [...item.tags];
  imageFile.value = null;
  imageUrl.value = "";
  editorOpen.value = true;
}

function openDetails(item: ProductKnowledge) {
  selectedItem.value = item;
  detailsOpen.value = true;
}

function editSelectedItem() {
  if (!selectedItem.value) return;
  const item = selectedItem.value;
  detailsOpen.value = false;
  openEdit(item);
}

function openDelete(item: ProductKnowledge) {
  deletingItem.value = item;
  deleteOpen.value = true;
}

async function submitItem() {
  saving.value = true;
  let result = await (async () => {
    if (editingItem.value) {
      return await api.productKnowledge.updateOne(editingItem.value.id, form);
    }
    if (createMode.value === "manual") {
      return await api.productKnowledge.createOne(form);
    }
    return await api.productKnowledge.createWithAI({
      topic: aiTopic.value,
      targetLanguage: targetLanguage.value,
    });
  })().finally(() => {
    // Image persistence below is part of the same save operation.
  });

  if (result.error || !result.data) {
    saving.value = false;
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }
  const file = selectedImage();
  if (file) {
    result = await api.productKnowledge.uploadImage(result.data.id, file);
  }
  else if (imageUrl.value.trim()) {
    result = await api.productKnowledge.saveImageUrl(result.data.id, imageUrl.value.trim());
  }
  saving.value = false;
  if (result.error || !result.data) {
    alert.error(i18n.t("product-knowledge.image-save-failed"));
    return;
  }
  imageErrors.delete(result.data.id);
  editorOpen.value = false;
  resetEditor();
  await refreshItems();
}

function selectedImage(): File | null {
  if (imageFile.value instanceof File) return imageFile.value;
  return Array.isArray(imageFile.value) ? imageFile.value[0] || null : null;
}

async function findProductImage(item: ProductKnowledge) {
  imageSaving.value = true;
  imageSavingId.value = item.id;
  const { data, error } = await api.productKnowledge.findImage(item.id).finally(() => {
    imageSaving.value = false;
    imageSavingId.value = null;
  });
  if (!data || error) {
    alert.error(i18n.t("product-knowledge.image-save-failed"));
    return;
  }
  imageErrors.delete(item.id);
  await refreshItems();
  const refreshed = items.value.find(candidate => candidate.id === item.id);
  if (refreshed && editingItem.value?.id === item.id) {
    openEdit(refreshed);
  }
  if (refreshed && selectedItem.value?.id === item.id) {
    selectedItem.value = refreshed;
  }
}

async function deleteProductImage(item: ProductKnowledge) {
  imageSaving.value = true;
  imageSavingId.value = item.id;
  const { error } = await api.productKnowledge.deleteImage(item.id).finally(() => {
    imageSaving.value = false;
    imageSavingId.value = null;
  });
  if (error) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }
  imageErrors.delete(item.id);
  await refreshItems();
  const refreshed = items.value.find(candidate => candidate.id === item.id);
  if (refreshed) openEdit(refreshed);
}

async function deleteItem() {
  if (!deletingItem.value) return;
  deleting.value = true;
  const { error } = await api.productKnowledge.deleteOne(deletingItem.value.id).finally(() => {
    deleting.value = false;
  });
  if (error) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }
  deleteOpen.value = false;
  deletingItem.value = null;
  await refreshItems();
}
</script>

<style scoped>
.product-knowledge-page {
  max-width: 1180px;
}

.product-toolbar {
  display: grid;
  gap: 12px;
  grid-template-columns: minmax(220px, 1fr) minmax(160px, 240px) minmax(160px, 240px) auto;
  margin-top: 18px;
}

.product-card {
  border-radius: 8px;
  cursor: pointer;
  height: 100%;
}

.product-card__image-placeholder {
  align-items: center;
  background: rgb(var(--v-theme-surface-variant));
  display: flex;
  height: 190px;
  justify-content: center;
}

.product-details__image {
  aspect-ratio: 16 / 8;
  border-radius: 6px;
  max-height: 360px;
}

.product-card__title {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  min-height: 64px;
  overflow: hidden;
  white-space: normal;
}

.product-card__summary {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 5;
  line-clamp: 5;
  min-height: 108px;
  overflow: hidden;
  white-space: pre-wrap;
}

.product-details {
  max-height: min(70vh, 760px);
  overflow-y: auto;
}

@media (max-width: 960px) {
  .product-toolbar {
    grid-template-columns: 1fr;
  }
}
</style>
