<template>
  <v-container class="narrow-container">
    <EquipmentCreateDialog
      v-model="createDialogOpen"
      :categories="categoryOptions"
      @saved="handleCreated"
    />

    <BaseDialog
      v-model="editDialogOpen"
      :title="$t('equipment.edit-equipment')"
      :icon="$globals.icons.tools"
      width="680"
      max-width="96vw"
      can-submit
      keep-open
      :loading="saving"
      :submit-text="$t('general.save')"
      @submit="saveEquipment"
      @close="closeEditDialog"
    >
      <v-card-text v-if="editingEquipment" class="pt-4">
        <v-text-field
          :model-value="editingEquipment.name"
          :label="$t('equipment.name')"
          variant="outlined"
          density="comfortable"
          readonly
        />
        <v-combobox
          v-model="editCategory"
          :items="categoryOptions"
          :label="$t('equipment.category')"
          variant="outlined"
          density="comfortable"
        />
        <v-textarea
          v-model="editDescription"
          :label="$t('equipment.description')"
          rows="4"
          auto-grow
          variant="outlined"
        />
        <v-file-input
          v-model="editImage"
          accept="image/*"
          :label="$t('equipment.upload-image')"
          :prepend-inner-icon="$globals.icons.fileImage"
          prepend-icon=""
          clearable
          variant="outlined"
          density="comfortable"
        />
        <v-text-field
          v-model="editImageUrl"
          :label="$t('equipment.image-url')"
          :prepend-inner-icon="$globals.icons.link"
          type="url"
          variant="outlined"
          density="comfortable"
        />
        <div class="d-flex flex-wrap ga-2">
          <v-btn
            variant="tonal"
            color="primary"
            :prepend-icon="$globals.icons.robot"
            :loading="enrichingIds.has(editingEquipment.id)"
            @click="enrichOne(editingEquipment)"
          >
            {{ $t("equipment.enrich-with-ai") }}
          </v-btn>
          <v-btn
            variant="tonal"
            color="primary"
            :prepend-icon="$globals.icons.fileImage"
            @click="findEquipmentImage(editingEquipment)"
          >
            {{ $t("equipment.find-image-with-ai") }}
          </v-btn>
          <v-btn
            v-if="editingEquipment.hasImage"
            variant="text"
            color="error"
            :prepend-icon="$globals.icons.delete"
            @click="deleteEquipmentImage(editingEquipment)"
          >
            {{ $t("equipment.delete-image") }}
          </v-btn>
        </div>
      </v-card-text>
    </BaseDialog>

    <BasePageTitle divider>
      <template #title>
        {{ $t("equipment.equipment") }}
      </template>
      <template #subtitle>
        {{ $t("equipment.equipment-description") }}
      </template>
    </BasePageTitle>

    <div class="equipment-toolbar mb-6">
      <v-text-field
        v-model="search"
        :label="$t('search.search')"
        :prepend-inner-icon="$globals.icons.search"
        density="compact"
        clearable
        hide-details
      />
      <v-select
        v-model="selectedCategory"
        :items="categoryOptions"
        :label="$t('equipment.category')"
        density="compact"
        clearable
        hide-details
      />
      <v-btn
        color="primary"
        :prepend-icon="$globals.icons.create"
        @click="createDialogOpen = true"
      >
        {{ $t("equipment.quick-add") }}
      </v-btn>
      <v-btn
        color="primary"
        variant="tonal"
        :prepend-icon="$globals.icons.robot"
        :loading="bulkEnriching"
        @click="enrichMissing"
      >
        {{ $t("equipment.organize-missing-with-ai") }}
      </v-btn>
    </div>
    <div class="equipment-filters mb-6">
      <v-select
        v-model="aiStatusFilter"
        :items="aiStatusOptions"
        item-title="title"
        item-value="value"
        :label="$t('catalog.ai-status')"
        density="compact"
        hide-details
      />
      <v-select
        v-model="imageStatusFilter"
        :items="imageStatusOptions"
        item-title="title"
        item-value="value"
        :label="$t('catalog.image-status')"
        density="compact"
        hide-details
      />
      <BaseListSortControls
        v-model:sort-by="equipmentSortBy"
        v-model:sort-direction="equipmentSortDirection"
        :options="equipmentSortOptions"
      />
    </div>

    <v-alert type="info" variant="tonal" density="compact" class="mb-5">
      {{ $t("equipment.automatic-catalog-help") }}
    </v-alert>

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />
    <template v-else-if="filteredEquipment.length">
      <BaseListPagination
        v-model:page="equipmentPage"
        v-model:items-per-page="equipmentPerPage"
        :total-items="equipmentTotal"
      />
      <section v-for="section in equipmentSections" :key="section.category" class="mb-8">
        <div class="d-flex align-center ga-2 mb-3">
          <h2 class="text-h6">
            {{ section.category }}
          </h2>
          <v-chip size="small" color="primary" variant="tonal">
            {{ section.items.length }}
          </v-chip>
        </div>
        <div class="equipment-grid">
          <v-card
            v-for="item in section.items"
            :key="item.id"
            class="equipment-card"
            variant="outlined"
          >
            <div class="equipment-image">
              <v-img
                v-if="item.hasImage && !imageErrors.has(item.id)"
                :src="api.equipment.imageUrl(item)"
                :alt="item.name"
                cover
                height="180"
                @error="imageErrors.add(item.id)"
              />
              <div v-else class="equipment-image-placeholder">
                <v-icon size="64" color="primary">
                  {{ $globals.icons.tools }}
                </v-icon>
              </div>
            </div>
            <v-card-title class="equipment-title">
              <span>{{ item.name }}</span>
              <v-spacer />
              <v-btn
                icon
                size="small"
                variant="text"
                :title="$t('general.edit')"
                @click="openEditDialog(item)"
              >
                <v-icon>{{ $globals.icons.edit }}</v-icon>
              </v-btn>
            </v-card-title>
            <v-card-text class="equipment-content">
              <p v-if="item.description" class="mb-3">
                {{ item.description }}
              </p>
              <div class="text-body-2 font-weight-bold mb-2">
                {{ $t("equipment.used-in-recipes", { count: item.recipeCount }) }}
              </div>
              <div class="d-flex flex-wrap ga-1">
                <NuxtLink
                  v-for="recipe in item.recipes.slice(0, 8)"
                  :key="recipe.slug"
                  :to="`/g/${groupSlug}/r/${recipe.slug}`"
                  class="text-decoration-none"
                >
                  <v-chip size="small" variant="tonal">
                    {{ recipe.name }}
                  </v-chip>
                </NuxtLink>
                <v-chip v-if="item.recipes.length > 8" size="small" variant="outlined">
                  +{{ item.recipes.length - 8 }}
                </v-chip>
              </div>
            </v-card-text>
            <v-card-actions>
              <v-chip
                size="small"
                :color="item.aiEnriched ? 'success' : undefined"
                variant="tonal"
              >
                {{ item.aiEnriched ? $t("equipment.ai-organized") : $t("equipment.not-ai-organized") }}
              </v-chip>
              <v-spacer />
              <v-btn
                v-if="!item.aiEnriched || !item.hasImage"
                icon
                size="small"
                variant="text"
                :title="$t('equipment.enrich-with-ai')"
                :loading="enrichingIds.has(item.id)"
                @click="enrichOne(item)"
              >
                <v-icon>{{ $globals.icons.robot }}</v-icon>
              </v-btn>
            </v-card-actions>
          </v-card>
        </div>
      </section>
    </template>
    <v-alert v-else type="info" variant="tonal">
      {{ $t("equipment.no-equipment") }}
    </v-alert>
  </v-container>
</template>

<script setup lang="ts">
import type { Equipment } from "~/lib/api/types/equipment";
import { useUserApi } from "~/composables/api/api-client";
import { alert } from "~/composables/use-toast";

const i18n = useI18n();
const api = useUserApi();
const auth = useMealieAuth();
const groupSlug = computed(() => auth.user.value?.groupSlug || "home");
const equipment = ref<Equipment[]>([]);
const loading = ref(true);
const saving = ref(false);
const bulkEnriching = ref(false);
const search = ref("");
const selectedCategory = ref<string | null>(null);
const aiStatusFilter = ref<"all" | "organized" | "not-organized">("all");
const imageStatusFilter = ref<"all" | "with-image" | "without-image">("all");
const createDialogOpen = ref(false);
const editDialogOpen = ref(false);
const editingEquipment = ref<Equipment | null>(null);
const editCategory = ref("");
const editDescription = ref("");
const editImage = ref<File | File[] | null>(null);
const editImageUrl = ref("");
const enrichingIds = reactive(new Set<string>());
const imageErrors = reactive(new Set<string>());

useSeoMeta({ title: i18n.t("equipment.equipment") });

const categoryOptions = computed(() => [...new Set(equipment.value
  .map(item => item.category || i18n.t("equipment.uncategorized")))]
  .sort((left, right) => left.localeCompare(right, i18n.locale.value)));

const aiStatusOptions = computed(() => [
  { title: i18n.t("catalog.all"), value: "all" },
  { title: i18n.t("equipment.ai-organized"), value: "organized" },
  { title: i18n.t("equipment.not-ai-organized"), value: "not-organized" },
]);
const imageStatusOptions = computed(() => [
  { title: i18n.t("catalog.all"), value: "all" },
  { title: i18n.t("catalog.with-image"), value: "with-image" },
  { title: i18n.t("catalog.without-image"), value: "without-image" },
]);
const EQUIPMENT_SORT_KEYS = ["name", "category", "recipeCount", "aiStatus"] as const;
type EquipmentSortKey = typeof EQUIPMENT_SORT_KEYS[number];
const {
  sortBy: equipmentSortBy,
  sortDirection: equipmentSortDirection,
} = usePersistedListSort(EQUIPMENT_SORT_KEYS, "name", "asc", "equipment");
const equipmentSortOptions = computed<{ title: string; value: EquipmentSortKey }[]>(() => [
  { title: i18n.t("general.name"), value: "name" },
  { title: i18n.t("equipment.category"), value: "category" },
  { title: i18n.t("catalog.recipe-count"), value: "recipeCount" },
  { title: i18n.t("catalog.ai-status"), value: "aiStatus" },
]);

const filteredEquipment = computed(() => {
  const query = search.value.trim().toLocaleLowerCase();
  return equipment.value.filter((item) => {
    const category = item.category || i18n.t("equipment.uncategorized");
    if (selectedCategory.value && category !== selectedCategory.value) return false;
    if (aiStatusFilter.value === "organized" && !item.aiEnriched) return false;
    if (aiStatusFilter.value === "not-organized" && item.aiEnriched) return false;
    if (imageStatusFilter.value === "with-image" && !item.hasImage) return false;
    if (imageStatusFilter.value === "without-image" && item.hasImage) return false;
    if (!query) return true;
    return [
      item.name,
      item.category || "",
      item.description || "",
      ...item.recipes.map(recipe => recipe.name),
    ].join(" ").toLocaleLowerCase().includes(query);
  });
});
const sortedEquipment = sortListItems(
  filteredEquipment,
  item => ({
    name: item.name,
    category: item.category || i18n.t("equipment.uncategorized"),
    recipeCount: item.recipeCount,
    aiStatus: item.aiEnriched ? 1 : 0,
  })[equipmentSortBy.value],
  equipmentSortDirection,
  i18n.locale,
);
const {
  page: equipmentPage,
  itemsPerPage: equipmentPerPage,
  totalItems: equipmentTotal,
  paginatedItems: paginatedEquipment,
} = useListPagination(sortedEquipment);

const equipmentSections = computed(() => {
  const sections = new Map<string, Equipment[]>();
  for (const item of paginatedEquipment.value) {
    const category = item.category || i18n.t("equipment.uncategorized");
    const items = sections.get(category) || [];
    items.push(item);
    sections.set(category, items);
  }
  return [...sections.entries()]
    .sort(([left], [right]) => left.localeCompare(right, i18n.locale.value))
    .map(([category, items]) => ({ category, items }));
});

onMounted(loadEquipment);

async function handleCreated() {
  imageErrors.clear();
  await loadEquipment();
}

async function loadEquipment() {
  loading.value = true;
  const { data, error } = await api.equipment.getAll();
  equipment.value = data || [];
  if (error) alert.error(i18n.t("events.something-went-wrong"));
  loading.value = false;
}

function openEditDialog(item: Equipment) {
  editingEquipment.value = item;
  editCategory.value = item.category || "";
  editDescription.value = item.description || "";
  editImage.value = null;
  editImageUrl.value = "";
  editDialogOpen.value = true;
}

function closeEditDialog() {
  editingEquipment.value = null;
  editCategory.value = "";
  editDescription.value = "";
  editImage.value = null;
  editImageUrl.value = "";
}

function selectedImage(): File | null {
  if (editImage.value instanceof File) return editImage.value;
  return Array.isArray(editImage.value) ? editImage.value[0] || null : null;
}

async function saveEquipment() {
  if (!editingEquipment.value) return;
  saving.value = true;
  const itemId = editingEquipment.value.id;
  let response = await api.equipment.updateOne(itemId, {
    category: editCategory.value || null,
    description: editDescription.value || null,
  });
  const file = selectedImage();
  if (response.data && !response.error && file) {
    response = await api.equipment.uploadImage(itemId, file);
  }
  else if (response.data && !response.error && editImageUrl.value.trim()) {
    response = await api.equipment.saveImageUrl(itemId, editImageUrl.value.trim());
  }
  saving.value = false;
  if (!response.data || response.error) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }
  editDialogOpen.value = false;
  closeEditDialog();
  imageErrors.delete(itemId);
  await loadEquipment();
}

async function enrichOne(item: Equipment) {
  enrichingIds.add(item.id);
  const { data, error } = await api.equipment.enrichWithAI(item.id);
  enrichingIds.delete(item.id);
  if (!data || error) {
    alert.error(i18n.t("equipment.ai-enrichment-failed"));
    return;
  }
  imageErrors.delete(item.id);
  await loadEquipment();
  if (editingEquipment.value?.id === item.id) openEditDialog(data);
}

async function enrichMissing() {
  bulkEnriching.value = true;
  const { error } = await api.equipment.enrichMissing(20);
  bulkEnriching.value = false;
  if (error) alert.warning(i18n.t("equipment.some-items-could-not-be-enriched"));
  imageErrors.clear();
  await loadEquipment();
}

async function findEquipmentImage(item: Equipment) {
  saving.value = true;
  const { data, error } = await api.equipment.findImage(item.id);
  saving.value = false;
  if (!data || error) {
    alert.error(i18n.t("equipment.image-save-failed"));
    return;
  }
  imageErrors.delete(item.id);
  await loadEquipment();
  openEditDialog(data);
}

async function deleteEquipmentImage(item: Equipment) {
  saving.value = true;
  const { error } = await api.equipment.deleteImage(item.id);
  saving.value = false;
  if (error) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }
  imageErrors.delete(item.id);
  await loadEquipment();
  const refreshed = equipment.value.find(candidate => candidate.id === item.id);
  if (refreshed) openEditDialog(refreshed);
}
</script>

<style scoped>
.equipment-toolbar {
  align-items: center;
  display: grid;
  gap: 12px;
  grid-template-columns: minmax(220px, 1fr) minmax(180px, 260px) auto auto;
}

.equipment-filters {
  align-items: start;
  display: grid;
  gap: 12px;
  grid-template-columns: minmax(160px, 0.8fr) minmax(160px, 0.8fr) minmax(280px, 1.6fr);
}

.equipment-grid {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 300px), 1fr));
}

.equipment-card {
  display: flex;
  flex-direction: column;
  min-height: 400px;
}

.equipment-image {
  background: rgb(var(--v-theme-surface-variant));
  height: 180px;
  overflow: hidden;
}

.equipment-image-placeholder {
  align-items: center;
  display: flex;
  height: 100%;
  justify-content: center;
}

.equipment-title {
  align-items: flex-start;
  display: flex;
  font-size: 1.05rem;
  line-height: 1.35;
}

.equipment-content {
  flex: 1;
}

@media (max-width: 980px) {
  .equipment-toolbar {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .equipment-filters {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 620px) {
  .equipment-toolbar {
    grid-template-columns: 1fr;
  }
}
</style>
