<template>
  <BaseDialog
    v-model="dialog"
    :title="$t('recipe.open-or-create-shopping-list')"
    :icon="$globals.icons.cartCheck"
    width="780"
    max-width="95vw"
    :loading="loading"
  >
    <v-card-text class="recipe-shopping-list-dialog">
      <template v-if="shoppingList">
        <div v-if="dialogMode === 'view'" class="recipe-shopping-list-view">
          <div class="recipe-shopping-list-view-header">
            <div class="min-width-0">
              <div class="text-h5 font-weight-bold recipe-shopping-list-name">
                {{ shoppingList.name }}
              </div>
              <div v-if="totalItems" class="recipe-shopping-list-progress mt-3">
                <v-progress-linear
                  :model-value="completionPercentage"
                  color="success"
                  height="6"
                  rounded
                />
                <span class="text-caption text-medium-emphasis" dir="ltr">
                  {{ checkedItems }} / {{ totalItems }}
                </span>
              </div>
            </div>
            <v-icon color="primary" size="40">
              {{ $globals.icons.cartCheck }}
            </v-icon>
          </div>

          <div v-if="groupedItems.length" class="recipe-shopping-list-view-groups">
            <section v-for="group in groupedItems" :key="group.label" class="recipe-shopping-list-view-group">
              <div class="recipe-shopping-list-view-group-title">
                <span>{{ group.label }}</span>
                <span class="text-caption">{{ group.items.length }}</span>
              </div>
              <div
                v-for="item in group.items"
                :key="item.id"
                class="recipe-shopping-list-view-item"
                :class="{ 'recipe-shopping-list-view-item--checked': item.checked }"
              >
                <v-checkbox-btn
                  :model-value="Boolean(item.checked)"
                  density="compact"
                  color="success"
                  class="recipe-shopping-list-view-checkbox"
                  :disabled="busyItemIds.has(item.id)"
                  :aria-label="formatItem(item)"
                  @update:model-value="toggleItem(item)"
                />
                <span class="recipe-shopping-list-view-item-text">{{ formatItem(item) }}</span>
              </div>
            </section>
          </div>
          <v-alert v-else type="info" variant="tonal">
            {{ $t("shopping-list.no-items-in-list") }}
          </v-alert>
        </div>

        <div v-else class="recipe-shopping-list-edit">
          <div class="d-flex align-center ga-2 mb-4">
            <v-text-field
              v-model="listName"
              density="compact"
              hide-details
              :label="$t('shopping-list.list-name')"
              @keydown.enter.prevent="saveListName"
            />
            <v-btn
              icon
              size="small"
              color="primary"
              :loading="savingName"
              :disabled="!canSaveName"
              :title="$t('general.save')"
              @click="saveListName"
            >
              <v-icon>{{ $globals.icons.save }}</v-icon>
            </v-btn>
          </div>

          <div v-if="groupedItems.length" class="recipe-shopping-list-items">
            <section v-for="group in groupedItems" :key="group.label" class="mb-3">
              <div class="text-subtitle-2 font-weight-bold mb-1">
                {{ group.label }}
              </div>
              <div v-for="item in group.items" :key="item.id" class="recipe-shopping-list-item">
                <v-checkbox-btn
                  :model-value="Boolean(item.checked)"
                  :aria-label="formatItem(item)"
                  @update:model-value="toggleItem(item)"
                />
                <v-text-field
                  v-model="itemDrafts[item.id]"
                  density="compact"
                  hide-details
                  variant="underlined"
                  @keydown.enter.prevent="saveItem(item)"
                />
                <v-btn
                  icon
                  variant="text"
                  size="x-small"
                  color="primary"
                  :loading="busyItemIds.has(item.id)"
                  :disabled="!itemChanged(item)"
                  :title="$t('general.save')"
                  @click="saveItem(item)"
                >
                  <v-icon>{{ $globals.icons.save }}</v-icon>
                </v-btn>
                <v-btn
                  icon
                  variant="text"
                  size="x-small"
                  color="error"
                  :loading="busyItemIds.has(item.id)"
                  :title="$t('general.delete')"
                  @click="deleteItem(item)"
                >
                  <v-icon>{{ $globals.icons.delete }}</v-icon>
                </v-btn>
              </div>
            </section>
          </div>
          <v-alert v-else type="info" variant="tonal" class="mb-3">
            {{ $t("shopping-list.no-items-in-list") }}
          </v-alert>

          <div class="d-flex align-center ga-2 mt-4">
            <v-text-field
              v-model="newItem"
              density="compact"
              hide-details
              :label="$t('shopping-list.add-item')"
              @keydown.enter.prevent="addItem"
            />
            <v-btn
              icon
              size="small"
              color="success"
              :loading="addingItem"
              :disabled="!newItem.trim()"
              :title="$t('shopping-list.add-item')"
              @click="addItem"
            >
              <v-icon>{{ $globals.icons.createAlt }}</v-icon>
            </v-btn>
          </div>
        </div>
      </template>
    </v-card-text>

    <template #custom-card-action>
      <div v-if="shoppingList" class="d-flex align-center ga-2">
        <v-btn
          color="success"
          variant="tonal"
          :prepend-icon="$globals.icons.robot"
          @click="aiAdjustDialog = true"
        >
          {{ $t("shopping-list.adjust-quantities-with-ai") }}
        </v-btn>
        <v-btn
          color="primary"
          variant="tonal"
          :prepend-icon="$globals.icons.contentCopy"
          @click="copyCurrentList"
        >
          {{ $t("general.copy") }}
        </v-btn>
        <v-btn
          color="primary"
          variant="tonal"
          :prepend-icon="dialogMode === 'view' ? $globals.icons.edit : $globals.icons.eye"
          @click="toggleDialogMode"
        >
          {{ $t(dialogMode === "view" ? "general.edit" : "general.view") }}
        </v-btn>
      </div>
    </template>
  </BaseDialog>
  <BaseDialog
    v-model="aiAdjustDialog"
    :title="$t('shopping-list.adjust-quantities-with-ai')"
    :icon="$globals.icons.robot"
    :submit-text="$t('general.apply')"
    :loading="aiAdjusting"
    :submit-disabled="aiAdjustmentRequest.trim().length < 2"
    can-submit
    @submit="adjustQuantitiesWithAI"
    @close="aiAdjustmentRequest = ''"
  >
    <v-card-text>
      <p class="text-body-2 text-medium-emphasis mb-3">
        {{ $t("shopping-list.adjust-quantities-with-ai-description") }}
      </p>
      <v-textarea
        v-model="aiAdjustmentRequest"
        :label="$t('shopping-list.quantity-change')"
        :placeholder="$t('shopping-list.adjust-quantities-with-ai-placeholder')"
        rows="4"
        maxlength="2000"
        counter
        autofocus
      />
    </v-card-text>
  </BaseDialog>
</template>

<script setup lang="ts">
import type { ShoppingListItemOut, ShoppingListOut } from "~/lib/api/types/household";
import { useUserApi } from "~/composables/api/api-client";
import { useShoppingListCopy } from "~/composables/shopping-list-page/sub-composables/use-shopping-list-copy";
import { alert } from "~/composables/use-toast";

interface Props {
  modelValue: boolean;
  recipeSlug: string;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  "update:modelValue": [value: boolean];
  "resolved": [payload: { shoppingListId: string; created: boolean }];
  "failed": [];
}>();

const dialog = computed({
  get: () => props.modelValue,
  set: value => emit("update:modelValue", value),
});
const api = useUserApi();
const i18n = useI18n();
const { copyShoppingList } = useShoppingListCopy();
const shoppingList = ref<ShoppingListOut | null>(null);
const dialogMode = ref<"view" | "edit">("view");
const listName = ref("");
const itemDrafts = ref<Record<string, string>>({});
const loading = ref(false);
const savingName = ref(false);
const addingItem = ref(false);
const newItem = ref("");
const busyItemIds = ref<Set<string>>(new Set());
const aiAdjustDialog = ref(false);
const aiAdjusting = ref(false);
const aiAdjustmentRequest = ref("");
let loadVersion = 0;

const canSaveName = computed(() => {
  return Boolean(
    shoppingList.value
    && listName.value.trim()
    && listName.value.trim() !== (shoppingList.value.name || "").trim(),
  );
});

const groupedItems = computed(() => {
  const groups = new Map<string, ShoppingListItemOut[]>();
  const noLabel = i18n.t("shopping-list.no-label");
  for (const item of shoppingList.value?.listItems || []) {
    const label = item.label?.name || noLabel;
    const group = groups.get(label);
    if (group) group.push(item);
    else groups.set(label, [item]);
  }

  const orderedLabels: string[] = [];
  if (groups.has(noLabel)) orderedLabels.push(noLabel);
  for (const setting of shoppingList.value?.labelSettings || []) {
    const label = setting.label.name;
    if (groups.has(label) && !orderedLabels.includes(label)) orderedLabels.push(label);
  }
  for (const label of groups.keys()) {
    if (!orderedLabels.includes(label)) orderedLabels.push(label);
  }

  return orderedLabels.map(label => ({
    label,
    items: [...(groups.get(label) || [])].sort(sortItemsWithinCategory),
  }));
});

function sortItemsWithinCategory(a: ShoppingListItemOut, b: ShoppingListItemOut) {
  if (Boolean(a.checked) !== Boolean(b.checked)) return a.checked ? 1 : -1;
  const positionDifference = (a.position ?? 0) - (b.position ?? 0);
  if (positionDifference !== 0) return positionDifference;
  return (a.createdAt || "").localeCompare(b.createdAt || "");
}

const totalItems = computed(() => shoppingList.value?.listItems?.length || 0);
const checkedItems = computed(() => shoppingList.value?.listItems?.filter(item => item.checked).length || 0);
const completionPercentage = computed(() => totalItems.value ? (checkedItems.value / totalItems.value) * 100 : 0);

watch(
  () => props.modelValue,
  (open) => {
    if (open) void openList();
    else clearLoadedList();
  },
);

onBeforeUnmount(clearLoadedList);

function clearLoadedList() {
  loadVersion += 1;
  shoppingList.value = null;
  dialogMode.value = "view";
  listName.value = "";
  itemDrafts.value = {};
  newItem.value = "";
  busyItemIds.value = new Set();
}

function formatItem(item: ShoppingListItemOut) {
  if (item.display) return item.display;
  const quantity = item.quantity ? String(item.quantity) : "";
  return [quantity, item.unit?.name, item.food?.name, item.note].filter(Boolean).join(" ");
}

function initializeDrafts(list: ShoppingListOut) {
  listName.value = list.name || "";
  itemDrafts.value = Object.fromEntries((list.listItems || []).map(item => [item.id, formatItem(item)]));
}

async function openList() {
  const version = ++loadVersion;
  shoppingList.value = null;
  dialogMode.value = "view";
  loading.value = true;
  try {
    const { data: link, error: linkError } = await api.recipes.openOrCreateShoppingList(props.recipeSlug);
    const listId = link?.shoppingListId || link?.shopping_list_id;
    if (linkError || !listId || version !== loadVersion) {
      if (version === loadVersion) {
        alert.error(i18n.t("recipe.shopping-list-open-failed"));
        emit("failed");
      }
      return;
    }

    const { data, error } = await api.shopping.lists.getOne(listId);
    if (error || !data || version !== loadVersion) {
      if (version === loadVersion) {
        alert.error(i18n.t("recipe.shopping-list-open-failed"));
        emit("failed");
      }
      return;
    }
    shoppingList.value = data;
    initializeDrafts(data);
    const created = Boolean(link?.shoppingListCreated ?? link?.shopping_list_created);
    const shoppingListError = link?.shoppingListError ?? link?.shopping_list_error;
    if (created) {
      if (shoppingListError) {
        alert.error(i18n.t("recipe.ai-shopping-list-organize-failed"));
      }
      else {
        alert.success(i18n.t("recipe.ai-shopping-list-created"));
      }
    }
    emit("resolved", { shoppingListId: String(listId), created });
  }
  finally {
    if (version === loadVersion) loading.value = false;
  }
}

function toggleDialogMode() {
  dialogMode.value = dialogMode.value === "view" ? "edit" : "view";
}

function copyCurrentList() {
  if (shoppingList.value) {
    copyShoppingList(shoppingList.value);
  }
}

async function adjustQuantitiesWithAI() {
  if (!shoppingList.value || aiAdjusting.value || aiAdjustmentRequest.value.trim().length < 2) return;
  aiAdjusting.value = true;
  try {
    const { data, error } = await api.shopping.lists.adjustQuantitiesWithAi(
      shoppingList.value.id,
      aiAdjustmentRequest.value.trim(),
    );
    if (error || !data) {
      alert.error(i18n.t("shopping-list.ai-quantity-adjustment-failed"));
      return;
    }
    shoppingList.value = data;
    initializeDrafts(data);
    aiAdjustmentRequest.value = "";
    aiAdjustDialog.value = false;
    alert.success(i18n.t("shopping-list.ai-quantities-adjusted"));
  }
  finally {
    aiAdjusting.value = false;
  }
}

async function reloadList() {
  if (!shoppingList.value) return;
  const { data, error } = await api.shopping.lists.getOne(shoppingList.value.id);
  if (error || !data) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }
  shoppingList.value = data;
  initializeDrafts(data);
}

async function saveListName() {
  if (!shoppingList.value || savingName.value || !canSaveName.value) return;
  savingName.value = true;
  const nextName = listName.value.trim();
  try {
    const { data, error } = await api.shopping.lists.updateOne(shoppingList.value.id, {
      ...shoppingList.value,
      name: nextName,
    });
    if (error || !data) {
      alert.error(i18n.t("shopping-list.list-name-already-exists"));
      listName.value = shoppingList.value.name || "";
      return;
    }
    shoppingList.value = data;
    initializeDrafts(data);
  }
  finally {
    savingName.value = false;
  }
}

function itemChanged(item: ShoppingListItemOut) {
  return Boolean(itemDrafts.value[item.id]?.trim() && itemDrafts.value[item.id].trim() !== formatItem(item));
}

function setItemBusy(id: string, busy: boolean) {
  const next = new Set(busyItemIds.value);
  if (busy) next.add(id);
  else next.delete(id);
  busyItemIds.value = next;
}

async function saveItem(item: ShoppingListItemOut) {
  if (busyItemIds.value.has(item.id) || !itemChanged(item)) return;
  setItemBusy(item.id, true);
  try {
    const { error } = await api.shopping.items.updateOne(item.id, {
      ...item,
      display: "",
      food: null,
      foodId: null,
      note: itemDrafts.value[item.id].trim(),
      quantity: 0,
      unit: null,
      unitId: null,
    });
    if (error) alert.error(i18n.t("events.something-went-wrong"));
    else await reloadList();
  }
  finally {
    setItemBusy(item.id, false);
  }
}

async function toggleItem(item: ShoppingListItemOut) {
  if (busyItemIds.value.has(item.id)) return;
  setItemBusy(item.id, true);
  try {
    const { error } = await api.shopping.items.updateOne(item.id, { ...item, checked: !item.checked });
    if (error) alert.error(i18n.t("events.something-went-wrong"));
    else await reloadList();
  }
  finally {
    setItemBusy(item.id, false);
  }
}

async function deleteItem(item: ShoppingListItemOut) {
  if (busyItemIds.value.has(item.id)) return;
  setItemBusy(item.id, true);
  try {
    const { error } = await api.shopping.items.deleteOne(item.id);
    if (error) alert.error(i18n.t("events.something-went-wrong"));
    else await reloadList();
  }
  finally {
    setItemBusy(item.id, false);
  }
}

async function addItem() {
  if (!shoppingList.value || addingItem.value || !newItem.value.trim()) return;
  addingItem.value = true;
  try {
    const { error } = await api.shopping.items.createOne({
      shoppingListId: shoppingList.value.id,
      note: newItem.value.trim(),
      quantity: 0,
    });
    if (error) alert.error(i18n.t("events.something-went-wrong"));
    else {
      newItem.value = "";
      await reloadList();
    }
  }
  finally {
    addingItem.value = false;
  }
}
</script>

<style scoped>
.recipe-shopping-list-dialog {
  min-height: 180px;
}
.recipe-shopping-list-view {
  padding-block: 4px 12px;
}
.recipe-shopping-list-view-header {
  align-items: center;
  display: grid;
  gap: 20px;
  grid-template-columns: minmax(0, 1fr) auto;
  margin-bottom: 24px;
}
.recipe-shopping-list-name {
  overflow-wrap: anywhere;
}
.recipe-shopping-list-progress {
  align-items: center;
  display: grid;
  gap: 10px;
  grid-template-columns: minmax(0, 1fr) auto;
  max-width: 360px;
}
.recipe-shopping-list-view-groups {
  display: grid;
  gap: 14px;
  max-height: min(56vh, 560px);
  overflow-y: auto;
  padding-inline-end: 4px;
}
.recipe-shopping-list-view-group {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 6px;
  overflow: hidden;
}
.recipe-shopping-list-view-group-title {
  align-items: center;
  background: rgba(var(--v-theme-primary), 0.09);
  display: flex;
  font-weight: 700;
  justify-content: space-between;
  min-height: 38px;
  padding: 8px 14px;
}
.recipe-shopping-list-view-item {
  align-items: center;
  display: flex;
  gap: 10px;
  min-height: 44px;
  padding: 8px 14px;
}
.recipe-shopping-list-view-item + .recipe-shopping-list-view-item {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.recipe-shopping-list-view-checkbox {
  flex: 0 0 40px;
  max-width: 40px;
}
.recipe-shopping-list-view-item-text {
  flex: 1 1 auto;
  min-width: 0;
  overflow-wrap: anywhere;
}
.recipe-shopping-list-view-item--checked .recipe-shopping-list-view-item-text {
  opacity: 0.62;
  text-decoration: line-through;
}
.recipe-shopping-list-items {
  max-height: min(52vh, 520px);
  overflow-y: auto;
  padding-inline-end: 4px;
}
.recipe-shopping-list-item {
  align-items: center;
  display: flex;
  gap: 4px;
  min-height: 42px;
}
.recipe-shopping-list-item :deep(.v-input) {
  flex: 1 1 auto;
  min-width: 0;
  width: 100%;
}
.recipe-shopping-list-item :deep(.v-checkbox-btn) {
  flex: 0 0 40px;
}
@media (max-width: 600px) {
  .recipe-shopping-list-view-header {
    gap: 12px;
  }
  .recipe-shopping-list-view-header > .v-icon {
    display: none;
  }
}
</style>
