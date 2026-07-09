<template>
  <v-container
    v-if="shoppingListChoices && ready"
    class="narrow-container"
  >
    <BaseDialog
      v-model="state.createDialog"
      :title="$t('shopping-list.create-shopping-list')"
      :icon="$globals.icons.formatListCheck"
      can-submit
      @submit="createOne"
    >
      <v-card-text>
        <v-text-field
          v-model="state.createName"
          autofocus
          :label="$t('shopping-list.new-list')"
        />
      </v-card-text>
    </BaseDialog>

    <!-- Settings -->
    <BaseDialog
      v-model="state.ownerDialog"
      :icon="$globals.icons.admin"
      :title="$t('user.edit-user')"
      can-confirm
      @confirm="updateOwner"
    >
      <v-container>
        <v-form>
          <v-select
            v-model="updateUserId"
            :items="allUsers"
            item-title="fullName"
            item-value="id"
            :label="$t('general.owner')"
            :prepend-icon="$globals.icons.user"
          />
        </v-form>
      </v-container>
    </BaseDialog>

    <BaseDialog
      v-model="state.deleteDialog"
      :title="$t('general.confirm')"
      :icon="$globals.icons.alertCircle"
      color="error"
      can-confirm
      @confirm="deleteOne"
    >
      <v-card-text>{{ $t('shopping-list.are-you-sure-you-want-to-delete-this-item') }}</v-card-text>
    </BaseDialog>

    <BaseDialog
      v-model="state.renameDialog"
      :title="$t('shopping-list.rename-shopping-list')"
      :icon="$globals.icons.edit"
      can-submit
      @submit="renameOne"
    >
      <v-card-text>
        <v-text-field
          v-model="state.renameName"
          autofocus
          :label="$t('shopping-list.list-name')"
          @keyup.enter="renameOne"
        />
      </v-card-text>
    </BaseDialog>

    <BasePageTitle divider>
      <template #header>
        <v-img
          width="100%"
          max-height="100"
          max-width="100"
          src="/svgs/shopping-cart.svg"
        />
      </template>
      <template #title>
        {{ $t('shopping-list.shopping-lists') }}
      </template>
    </BasePageTitle>

    <v-container class="d-flex align-center justify-end px-0 pt-0 pb-4">
      <v-switch
        v-model="preferences.openListsInline"
        hide-details
        color="primary"
        density="compact"
        :label="$t('shopping-list.open-lists-inline')"
        class="my-0 mr-4"
      />
      <v-checkbox
        v-model="preferences.viewAllLists"
        hide-details
        :label="$t('general.show-all')"
        class="my-0 mr-4"
      />
      <BaseButton
        create
        class="my-0"
        @click="state.createDialog = true"
      />
    </v-container>

    <v-container v-if="!shoppingListChoices.length">
      <BasePageTitle>
        <template #title>
          {{ $t('shopping-list.no-shopping-lists-found') }}
        </template>
      </BasePageTitle>
    </v-container>

    <section>
      <v-card
        v-for="list in shoppingListChoices"
        :key="list.id"
        class="my-2 left-border"
        :class="{ 'shopping-list-card--expanded': isExpandedShoppingList(list.id) }"
        :to="preferences.openListsInline ? undefined : `/shopping-lists/${list.id}`"
        @click="openShoppingListCard(list)"
      >
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">
            {{ $globals.icons.cartCheck }}
          </v-icon>
          <span class="flex-grow-1">
            {{ list.name }}
          </span>
          <v-chip
            v-if="isShoppingListGroceriesReady(list)"
            size="small"
            color="success"
            variant="tonal"
            class="shopping-list-ready-chip"
          >
            <v-icon start size="small">
              {{ $globals.icons.cartCheck }}
            </v-icon>
            {{ $t("shopping-list.all-groceries-ready-short") }}
          </v-chip>
          <v-btn
            icon
            variant="plain"
            :title="$t('shopping-list.rename-shopping-list')"
            :aria-label="$t('shopping-list.rename-shopping-list')"
            @click.prevent.stop="openRename(list)"
          >
            <v-icon>
              {{ $globals.icons.edit }}
            </v-icon>
          </v-btn>
          <v-chip
            size="small"
            :color="isShoppingListAiOrganized(list) ? 'success' : 'grey'"
            :variant="isShoppingListAiOrganized(list) ? 'tonal' : 'outlined'"
            class="shopping-list-ai-chip"
            :title="isShoppingListAiOrganized(list) ? $t('shopping-list.ai-organized') : $t('shopping-list.ai-not-organized')"
          >
            <v-icon start size="small">
              {{ $globals.icons.robot }}
            </v-icon>
            AI
          </v-chip>
          <v-btn
            icon
            variant="plain"
            color="success"
            :title="$t('shopping-list.organize-with-ai')"
            :aria-label="$t('shopping-list.organize-with-ai')"
            :loading="isOrganizingShoppingList(list.id)"
            @click.prevent.stop="organizeShoppingListById(list.id)"
          >
            <v-icon>
              {{ $globals.icons.robot }}
            </v-icon>
          </v-btn>
          <v-btn
            icon
            variant="plain"
            :title="$t('general.copy')"
            :aria-label="$t('general.copy')"
            :loading="isCopyingShoppingList(list.id)"
            @click.prevent.stop="copyShoppingListById(list.id)"
          >
            <v-icon>
              {{ $globals.icons.contentCopy }}
            </v-icon>
          </v-btn>
          <v-btn
            icon
            variant="plain"
            @click.prevent.stop="toggleOwnerDialog(list)"
          >
            <v-icon>
              {{ $globals.icons.user }}
            </v-icon>
          </v-btn>
          <v-btn
            icon
            variant="plain"
            @click.prevent.stop="openDelete(list.id)"
          >
            <v-icon>
              {{ $globals.icons.delete }}
            </v-icon>
          </v-btn>
        </v-card-title>
        <v-expand-transition>
          <div
            v-if="preferences.openListsInline && isExpandedShoppingList(list.id)"
            class="shopping-list-inline-panel"
            @click.stop
          >
            <v-progress-linear
              v-if="isLoadingExpandedShoppingList(list.id)"
              indeterminate
              color="primary"
              class="my-2"
            />
            <template v-else-if="expandedShoppingLists[list.id]">
              <div class="shopping-list-inline-toolbar">
                <v-btn
                  size="small"
                  variant="text"
                  :to="`/shopping-lists/${list.id}`"
                >
                  {{ $t("shopping-list.open-full-list") }}
                </v-btn>
                <v-btn
                  size="small"
                  class="shopping-list-ready-action"
                  :class="{ 'shopping-list-ready-action--active': isShoppingListGroceriesReady(expandedShoppingLists[list.id]) }"
                  :color="isShoppingListGroceriesReady(expandedShoppingLists[list.id]) ? 'success' : 'grey'"
                  :variant="isShoppingListGroceriesReady(expandedShoppingLists[list.id]) ? 'tonal' : 'outlined'"
                  :prepend-icon="$globals.icons.cartCheck"
                  :loading="isUpdatingShoppingListReady(list.id)"
                  :disabled="!expandedShoppingLists[list.id].listItems?.length"
                  @click.stop.prevent="setShoppingListGroceriesReady(expandedShoppingLists[list.id], true)"
                >
                  {{ isShoppingListGroceriesReady(expandedShoppingLists[list.id]) ? $t("shopping-list.all-groceries-ready") : $t("shopping-list.mark-all-groceries-ready") }}
                </v-btn>
                <v-btn
                  v-if="isShoppingListGroceriesReady(expandedShoppingLists[list.id])"
                  size="small"
                  class="shopping-list-ready-action shopping-list-ready-action--reset"
                  color="warning"
                  variant="outlined"
                  :prepend-icon="$globals.icons.refresh"
                  :loading="isUpdatingShoppingListReady(list.id)"
                  :disabled="!expandedShoppingLists[list.id].listItems?.length"
                  @click.stop.prevent="setShoppingListGroceriesReady(expandedShoppingLists[list.id], false)"
                >
                  {{ $t("shopping-list.reset-groceries-ready") }}
                </v-btn>
              </div>
              <template v-if="!expandedShoppingLists[list.id].listItems?.length">
                <div
                  class="text-medium-emphasis py-4 text-center"
                >
                  {{ $t("shopping-list.no-items-in-list") }}
                </div>
              </template>
              <template v-else>
                <div
                  v-for="group in inlineShoppingListGroups(expandedShoppingLists[list.id])"
                  :key="group.label"
                  class="shopping-list-inline-group"
                >
                  <div class="shopping-list-inline-group-title">
                    {{ group.label }}
                  </div>
                  <div
                    v-for="item in group.items"
                    :key="item.id"
                    class="shopping-list-inline-item"
                    :class="{ 'shopping-list-inline-item--checked': item.checked }"
                  >
                    <v-checkbox-btn
                      :model-value="item.checked"
                      density="compact"
                      class="shopping-list-inline-checkbox"
                      @click.stop.prevent="toggleInlineShoppingListItem(list.id, item)"
                    />
                    <template v-if="isEditingInlineShoppingListItem(item.id)">
                      <v-text-field
                        v-model="inlineShoppingListItemDrafts[item.id]"
                        density="compact"
                        hide-details
                        class="shopping-list-inline-edit-input"
                        autofocus
                        @keydown.enter.stop.prevent="saveInlineShoppingListItemName(list.id, item)"
                        @keydown.esc.stop.prevent="cancelInlineShoppingListItemEdit(item.id)"
                      />
                      <v-btn
                        icon
                        size="x-small"
                        variant="text"
                        color="success"
                        class="shopping-list-inline-action"
                        :loading="isUpdatingInlineShoppingListItem(item.id)"
                        @click.stop.prevent="saveInlineShoppingListItemName(list.id, item)"
                      >
                        <v-icon>{{ $globals.icons.save }}</v-icon>
                      </v-btn>
                      <v-btn
                        icon
                        size="x-small"
                        variant="text"
                        class="shopping-list-inline-action"
                        :disabled="isUpdatingInlineShoppingListItem(item.id)"
                        @click.stop.prevent="cancelInlineShoppingListItemEdit(item.id)"
                      >
                        <v-icon>{{ $globals.icons.close }}</v-icon>
                      </v-btn>
                    </template>
                    <template v-else>
                      <span class="shopping-list-inline-item-text">{{ formatInlineShoppingListItem(item) }}</span>
                      <v-spacer />
                      <v-btn
                        icon
                        size="x-small"
                        variant="text"
                        class="shopping-list-inline-action"
                        :title="$t('general.edit')"
                        :aria-label="$t('general.edit')"
                        @click.stop.prevent="startInlineShoppingListItemEdit(item)"
                      >
                        <v-icon>{{ $globals.icons.edit }}</v-icon>
                      </v-btn>
                      <v-btn
                        icon
                        size="x-small"
                        variant="text"
                        color="error"
                        class="shopping-list-inline-action"
                        :loading="isUpdatingInlineShoppingListItem(item.id)"
                        :title="$t('general.delete')"
                        :aria-label="$t('general.delete')"
                        @click.stop.prevent="deleteInlineShoppingListItem(list.id, item)"
                      >
                        <v-icon>{{ $globals.icons.delete }}</v-icon>
                      </v-btn>
                    </template>
                  </div>
                </div>
              </template>
            </template>
          </div>
        </v-expand-transition>
      </v-card>
    </section>
  </v-container>
</template>

<script setup lang="ts">
import type { ShoppingListItemOut, ShoppingListOut } from "~/lib/api/types/household";
import { useUserApi } from "~/composables/api/api-client";
import { useAsyncKey } from "~/composables/use-utils";
import { useShoppingListPreferences } from "~/composables/use-users/preferences";
import { alert } from "~/composables/use-toast";
import { useShoppingListCopy } from "~/composables/shopping-list-page/sub-composables/use-shopping-list-copy";
import {
  buildShoppingListReadyExtras,
  isShoppingListGroceriesReady,
  useShoppingListAvailability,
} from "~/composables/shopping-list-page/use-shopping-list-availability";
import type { UserOut } from "~/lib/api/types/user";

const auth = useMealieAuth();
const i18n = useI18n();
const ready = ref(false);
const userApi = useUserApi();
const route = useRoute();
const { copyShoppingList } = useShoppingListCopy();
const copyingShoppingListIds = ref<Set<string>>(new Set());
const organizingShoppingListIds = ref<Set<string>>(new Set());
const expandedShoppingListIds = ref<Set<string>>(new Set());
const loadingExpandedShoppingListIds = ref<Set<string>>(new Set());
const updatingReadyShoppingListIds = ref<Set<string>>(new Set());
const editingInlineShoppingListItemIds = ref<Set<string>>(new Set());
const updatingInlineShoppingListItemIds = ref<Set<string>>(new Set());
const inlineShoppingListItemDrafts = ref<Record<string, string>>({});
const expandedShoppingLists = ref<Record<string, ShoppingListOut>>({});
const { updateAvailabilityForListName } = useShoppingListAvailability();

useSeoMeta({
  title: i18n.t("shopping-list.shopping-list"),
});

const overrideDisableRedirect = ref(false);
const disableRedirect = computed(() => route.query.disableRedirect === "true" || overrideDisableRedirect.value);
const preferences = useShoppingListPreferences();

const state = reactive({
  createName: "",
  createDialog: false,
  deleteDialog: false,
  deleteTarget: "",
  renameDialog: false,
  renameName: "",
  renameTarget: null as ShoppingListOut | null,
  ownerDialog: false,
  ownerTarget: ref<ShoppingListOut | null>(null),
});

const { data: shoppingLists } = useAsyncData(useAsyncKey(), async () => {
  return await fetchShoppingLists();
});

const shoppingListChoices = computed(() => {
  if (!shoppingLists.value) {
    return [];
  }

  return shoppingLists.value.filter(list => preferences.value.viewAllLists || list.userId === auth.user.value?.id);
});

// This has to appear before the shoppingListChoices watcher, otherwise that runs first and the redirect is not disabled
watch(
  () => preferences.value.viewAllLists,
  () => {
    overrideDisableRedirect.value = true;
  },
);

watch(
  () => preferences.value.openListsInline,
  () => {
    overrideDisableRedirect.value = true;
    if (!preferences.value.openListsInline) {
      clearExpandedShoppingLists();
    }
  },
);

watch(
  () => shoppingListChoices,
  () => {
    if (!preferences.value.openListsInline && !disableRedirect.value && shoppingListChoices.value.length === 1) {
      navigateTo(`/shopping-lists/${shoppingListChoices.value[0].id}`);
    }
    else {
      ready.value = true;
    }
  },
  {
    deep: true,
  },
);

async function fetchShoppingLists() {
  const { data } = await userApi.shopping.lists.getAll(1, -1, { orderBy: "name", orderDirection: "asc" });

  if (!data) {
    return [];
  }

  return data.items;
}

async function refresh() {
  shoppingLists.value = await fetchShoppingLists();
  pruneExpandedShoppingLists();
}

function setShoppingListCopying(id: string, copying: boolean) {
  const next = new Set(copyingShoppingListIds.value);
  if (copying) {
    next.add(id);
  }
  else {
    next.delete(id);
  }
  copyingShoppingListIds.value = next;
}

function isCopyingShoppingList(id: string) {
  return copyingShoppingListIds.value.has(id);
}

function setShoppingListOrganizing(id: string, organizing: boolean) {
  const next = new Set(organizingShoppingListIds.value);
  if (organizing) {
    next.add(id);
  }
  else {
    next.delete(id);
  }
  organizingShoppingListIds.value = next;
}

function isOrganizingShoppingList(id: string) {
  return organizingShoppingListIds.value.has(id);
}

function isShoppingListAiOrganized(list: ShoppingListOut) {
  const value = list.extras?.aiOrganized;
  return value === true || value === "true";
}

function replaceShoppingList(updatedList: ShoppingListOut) {
  if (shoppingLists.value) {
    shoppingLists.value = shoppingLists.value.map(list => list.id === updatedList.id ? { ...list, ...updatedList } : list);
  }

  if (expandedShoppingLists.value[updatedList.id]) {
    expandedShoppingLists.value = {
      ...expandedShoppingLists.value,
      [updatedList.id]: updatedList,
    };
  }
}

function setExpandedShoppingListLoading(id: string, loading: boolean) {
  const next = new Set(loadingExpandedShoppingListIds.value);
  if (loading) {
    next.add(id);
  }
  else {
    next.delete(id);
  }
  loadingExpandedShoppingListIds.value = next;
}

function setShoppingListReadyUpdating(id: string, updating: boolean) {
  const next = new Set(updatingReadyShoppingListIds.value);
  if (updating) {
    next.add(id);
  }
  else {
    next.delete(id);
  }
  updatingReadyShoppingListIds.value = next;
}

function isExpandedShoppingList(id: string) {
  return expandedShoppingListIds.value.has(id);
}

function isLoadingExpandedShoppingList(id: string) {
  return loadingExpandedShoppingListIds.value.has(id);
}

function isUpdatingShoppingListReady(id: string) {
  return updatingReadyShoppingListIds.value.has(id);
}

function setInlineShoppingListItemUpdating(id: string, updating: boolean) {
  const next = new Set(updatingInlineShoppingListItemIds.value);
  if (updating) {
    next.add(id);
  }
  else {
    next.delete(id);
  }
  updatingInlineShoppingListItemIds.value = next;
}

function isUpdatingInlineShoppingListItem(id: string) {
  return updatingInlineShoppingListItemIds.value.has(id);
}

function isEditingInlineShoppingListItem(id: string) {
  return editingInlineShoppingListItemIds.value.has(id);
}

function startInlineShoppingListItemEdit(item: ShoppingListItemOut) {
  const next = new Set(editingInlineShoppingListItemIds.value);
  next.add(item.id);
  editingInlineShoppingListItemIds.value = next;
  inlineShoppingListItemDrafts.value = {
    ...inlineShoppingListItemDrafts.value,
    [item.id]: formatInlineShoppingListItem(item),
  };
}

function cancelInlineShoppingListItemEdit(id: string) {
  const next = new Set(editingInlineShoppingListItemIds.value);
  next.delete(id);
  editingInlineShoppingListItemIds.value = next;
  inlineShoppingListItemDrafts.value = Object.fromEntries(
    Object.entries(inlineShoppingListItemDrafts.value).filter(([itemId]) => itemId !== id),
  );
}

function removeExpandedShoppingList(id: string) {
  const nextExpanded = new Set(expandedShoppingListIds.value);
  nextExpanded.delete(id);
  expandedShoppingListIds.value = nextExpanded;

  if (expandedShoppingLists.value[id]) {
    expandedShoppingLists.value = Object.fromEntries(
      Object.entries(expandedShoppingLists.value).filter(([listId]) => listId !== id),
    );
  }
}

function clearExpandedShoppingLists() {
  expandedShoppingListIds.value = new Set();
  loadingExpandedShoppingListIds.value = new Set();
  expandedShoppingLists.value = {};
}

function pruneExpandedShoppingLists() {
  const currentIds = new Set(shoppingLists.value?.map(list => list.id) || []);
  expandedShoppingListIds.value.forEach((id) => {
    if (!currentIds.has(id)) {
      removeExpandedShoppingList(id);
    }
  });
}

async function openShoppingListCard(list: ShoppingListOut) {
  if (!preferences.value.openListsInline) {
    return;
  }

  const nextExpanded = new Set(expandedShoppingListIds.value);
  if (nextExpanded.has(list.id)) {
    removeExpandedShoppingList(list.id);
    return;
  }

  nextExpanded.add(list.id);
  expandedShoppingListIds.value = nextExpanded;

  if (!expandedShoppingLists.value[list.id]) {
    await loadExpandedShoppingList(list.id);
  }
}

async function loadExpandedShoppingList(id: string) {
  if (isLoadingExpandedShoppingList(id)) {
    return;
  }

  setExpandedShoppingListLoading(id, true);
  try {
    const { data } = await userApi.shopping.lists.getOne(id);
    if (data) {
      expandedShoppingLists.value = {
        ...expandedShoppingLists.value,
        [id]: data,
      };
      replaceShoppingList(data);
    }
    else {
      alert.error(i18n.t("events.something-went-wrong"));
    }
  }
  finally {
    setExpandedShoppingListLoading(id, false);
  }
}

function inlineShoppingListGroups(list?: ShoppingListOut) {
  const noLabelText = i18n.t("shopping-list.no-label");
  const items = [...(list?.listItems || [])].sort(sortInlineShoppingListItems);
  const labelOrder = list?.labelSettings?.map(labelSetting => labelSetting.label.name).filter(Boolean) || [];
  const grouped = new Map<string, ShoppingListItemOut[]>();

  items.forEach((item) => {
    const label = item.label?.name || noLabelText;
    const labelItems = grouped.get(label) || [];
    labelItems.push(item);
    grouped.set(label, labelItems);
  });

  const groups: Array<{ label: string; items: ShoppingListItemOut[] }> = [];
  if (grouped.has(noLabelText)) {
    groups.push({ label: noLabelText, items: grouped.get(noLabelText)! });
    grouped.delete(noLabelText);
  }

  labelOrder.forEach((label) => {
    if (grouped.has(label)) {
      groups.push({ label, items: grouped.get(label)! });
      grouped.delete(label);
    }
  });

  Array.from(grouped.keys())
    .sort((a, b) => a.localeCompare(b))
    .forEach((label) => {
      groups.push({ label, items: grouped.get(label)! });
    });

  return groups;
}

function sortInlineShoppingListItems(a: ShoppingListItemOut, b: ShoppingListItemOut) {
  if (Boolean(a.checked) !== Boolean(b.checked)) {
    return a.checked ? 1 : -1;
  }

  const posA = a.position ?? 0;
  const posB = b.position ?? 0;
  if (posA !== posB) {
    return posA - posB;
  }

  return formatInlineShoppingListItem(a).localeCompare(formatInlineShoppingListItem(b));
}

function formatInlineShoppingListItem(item: ShoppingListItemOut) {
  if (item.display) {
    return item.display;
  }

  const amount = item.quantity ? String(item.quantity) : "";
  return [amount, item.unit?.name, item.food?.name, item.note].filter(Boolean).join(" ");
}

function replaceInlineShoppingListItem(listId: string, item: ShoppingListItemOut) {
  const list = expandedShoppingLists.value[listId];
  if (!list?.listItems) {
    return;
  }

  const nextList = {
    ...list,
    listItems: list.listItems.map(existingItem => existingItem.id === item.id ? item : existingItem),
  };
  expandedShoppingLists.value = {
    ...expandedShoppingLists.value,
    [listId]: nextList,
  };
}

function removeInlineShoppingListItem(listId: string, itemId: string) {
  const list = expandedShoppingLists.value[listId];
  if (!list?.listItems) {
    return;
  }

  const nextList = {
    ...list,
    listItems: list.listItems.filter(existingItem => existingItem.id !== itemId),
  };
  expandedShoppingLists.value = {
    ...expandedShoppingLists.value,
    [listId]: nextList,
  };
}

async function saveInlineShoppingListItemName(listId: string, item: ShoppingListItemOut) {
  if (isUpdatingInlineShoppingListItem(item.id)) {
    return;
  }

  const draft = (inlineShoppingListItemDrafts.value[item.id] || "").trim();
  if (!draft) {
    return;
  }

  const originalItem = { ...item };
  const optimisticItem = {
    ...item,
    display: draft,
    updatedAt: new Date().toISOString(),
  };

  setInlineShoppingListItemUpdating(item.id, true);
  replaceInlineShoppingListItem(listId, optimisticItem);
  try {
    const { data, error } = await userApi.shopping.items.updateOne(item.id, optimisticItem);
    if (error || !data) {
      replaceInlineShoppingListItem(listId, originalItem);
      alert.error(i18n.t("events.something-went-wrong"));
      return;
    }

    replaceInlineShoppingListItem(listId, data);
    cancelInlineShoppingListItemEdit(item.id);
  }
  finally {
    setInlineShoppingListItemUpdating(item.id, false);
  }
}

async function deleteInlineShoppingListItem(listId: string, item: ShoppingListItemOut) {
  if (isUpdatingInlineShoppingListItem(item.id)) {
    return;
  }

  const list = expandedShoppingLists.value[listId];
  const originalItems = [...(list?.listItems || [])];
  setInlineShoppingListItemUpdating(item.id, true);
  removeInlineShoppingListItem(listId, item.id);
  cancelInlineShoppingListItemEdit(item.id);
  try {
    const { error } = await userApi.shopping.items.deleteOne(item.id);
    if (error) {
      if (list) {
        expandedShoppingLists.value = {
          ...expandedShoppingLists.value,
          [listId]: { ...list, listItems: originalItems },
        };
      }
      alert.error(i18n.t("events.something-went-wrong"));
    }
  }
  finally {
    setInlineShoppingListItemUpdating(item.id, false);
  }
}

async function toggleInlineShoppingListItem(listId: string, item: ShoppingListItemOut) {
  const originalItem = { ...item };
  const optimisticItem = {
    ...item,
    checked: !item.checked,
    updatedAt: new Date().toISOString(),
  };

  replaceInlineShoppingListItem(listId, optimisticItem);
  const { data, error } = await userApi.shopping.items.updateOne(item.id, optimisticItem);
  if (error || !data) {
    replaceInlineShoppingListItem(listId, originalItem);
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }

  replaceInlineShoppingListItem(listId, data);
}

async function setShoppingListGroceriesReady(list: ShoppingListOut, nextReady: boolean) {
  if (isUpdatingShoppingListReady(list.id)) {
    return;
  }

  setShoppingListReadyUpdating(list.id, true);
  try {
    const { data: fullList } = await userApi.shopping.lists.getOne(list.id);
    const sourceList = fullList || list;
    if (isShoppingListGroceriesReady(sourceList) === nextReady) {
      return;
    }

    const { data, error } = await userApi.shopping.lists.updateOne(
      list.id,
      {
        ...sourceList,
        extras: buildShoppingListReadyExtras(sourceList, nextReady),
      },
    );

    if (error || !data) {
      alert.error(i18n.t("events.something-went-wrong"));
      return;
    }

    replaceShoppingList(data);
    updateAvailabilityForListName(data.name, nextReady);
    window.dispatchEvent(new CustomEvent("mealie:organizers-updated"));
  }
  finally {
    setShoppingListReadyUpdating(list.id, false);
  }
}

async function copyShoppingListById(id: string) {
  if (isCopyingShoppingList(id)) {
    return;
  }

  setShoppingListCopying(id, true);
  try {
    const { data } = await userApi.shopping.lists.getOne(id);
    if (data) {
      copyShoppingList(data);
    }
    else {
      alert.error(i18n.t("general.clipboard-copy-failure"));
    }
  }
  finally {
    setShoppingListCopying(id, false);
  }
}

async function organizeShoppingListById(id: string) {
  if (isOrganizingShoppingList(id)) {
    return;
  }

  setShoppingListOrganizing(id, true);
  try {
    const { data: shoppingList, error: shoppingListError } = await userApi.shopping.lists.getOne(id);
    if (shoppingListError || !shoppingList) {
      alert.error(i18n.t("shopping-list.ai-organize-failed"));
      return;
    }

    if (!shoppingList.listItems?.length) {
      alert.error(i18n.t("shopping-list.ai-organize-empty"));
      return;
    }

    const { data, error } = await userApi.shopping.lists.organizeWithAi(id);
    if (error || !data) {
      alert.error(i18n.t("shopping-list.ai-organize-failed"));
      return;
    }

    window.dispatchEvent(new CustomEvent("mealie:organizers-updated"));
    replaceShoppingList(data);
    alert.success(i18n.t("shopping-list.ai-organize-complete"));
  }
  catch {
    alert.error(i18n.t("shopping-list.ai-organize-failed"));
  }
  finally {
    setShoppingListOrganizing(id, false);
  }
}

async function createOne() {
  const name = state.createName.trim();
  if (!name) {
    return;
  }

  const existingList = shoppingLists.value?.find(list => (list.name || "").trim().toLocaleLowerCase() === name.toLocaleLowerCase());
  if (existingList) {
    alert.error(i18n.t("shopping-list.list-name-already-exists"));
    return;
  }

  const { data } = await userApi.shopping.lists.createOne({ name });

  if (data) {
    refresh();
    state.createName = "";
  }
}

function openRename(list: ShoppingListOut) {
  state.renameTarget = list;
  state.renameName = list.name || "";
  state.renameDialog = true;
}

async function renameOne() {
  const target = state.renameTarget;
  const name = state.renameName.trim();
  if (!target || !name) {
    return;
  }

  if ((target.name || "").trim() === name) {
    state.renameDialog = false;
    return;
  }

  const existingList = shoppingLists.value?.find(list =>
    list.id !== target.id && (list.name || "").trim().toLocaleLowerCase() === name.toLocaleLowerCase(),
  );
  if (existingList) {
    alert.error(i18n.t("shopping-list.list-name-already-exists"));
    return;
  }

  const { data: fullList } = await userApi.shopping.lists.getOne(target.id);
  if (!fullList) {
    alert.error(i18n.t("shopping-list.rename-shopping-list-failed"));
    return;
  }

  const { data } = await userApi.shopping.lists.updateOne(target.id, { ...fullList, name });
  if (!data) {
    alert.error(i18n.t("shopping-list.rename-shopping-list-failed"));
    return;
  }

  state.renameDialog = false;
  state.renameTarget = null;
  state.renameName = "";
  updateAvailabilityForListName(target.name, false);
  updateAvailabilityForListName(data.name, isShoppingListGroceriesReady(data));
  window.dispatchEvent(new CustomEvent("mealie:organizers-updated"));
  await refresh();
}

async function toggleOwnerDialog(list: ShoppingListOut) {
  if (!state.ownerDialog) {
    state.ownerTarget = list;
    await fetchAllUsers();
  }
  state.ownerDialog = !state.ownerDialog;
}

// ===============================================================
// Shopping List Edit User/Owner

const allUsers = ref<UserOut[]>([]);
const updateUserId = ref<string | undefined>();
async function fetchAllUsers() {
  const { data } = await userApi.households.fetchMembers();
  if (!data) {
    return;
  }

  // update current user
  allUsers.value = data.items.sort((a, b) => ((a.fullName || "") < (b.fullName || "") ? -1 : 1));
  updateUserId.value = state.ownerTarget?.userId;
}

async function updateOwner() {
  if (!state.ownerTarget || !updateUserId.value) {
    return;
  }
  // user has not changed, so we should not update
  if (state.ownerTarget.userId === updateUserId.value) {
    return;
  }
  // get full list, so the move does not delete shopping list items
  const { data: fullList } = await userApi.shopping.lists.getOne(state.ownerTarget.id);
  if (!fullList) {
    return;
  }
  const { data } = await userApi.shopping.lists.updateOne(
    state.ownerTarget.id,
    { ...fullList, userId: updateUserId.value },
  );

  if (data) {
    window.dispatchEvent(new CustomEvent("mealie:organizers-updated"));
    refresh();
  }
}

function openDelete(id: string) {
  state.deleteDialog = true;
  state.deleteTarget = id;
}

async function deleteOne() {
  const targetList = shoppingLists.value?.find(list => list.id === state.deleteTarget);
  const { data } = await userApi.shopping.lists.deleteOne(state.deleteTarget);
  if (data) {
    updateAvailabilityForListName(targetList?.name, false);
    refresh();
  }
}
</script>

<style scoped>
.shopping-list-ready-chip {
  flex: 0 0 auto;
  font-weight: 700;
  margin-inline: 6px;
}

.shopping-list-card--expanded {
  cursor: default;
}

.shopping-list-inline-panel {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  padding: 8px 20px 16px;
}

.shopping-list-inline-toolbar {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: space-between;
  margin-bottom: 8px;
}

.shopping-list-ready-action {
  transition:
    background-color 0.15s ease,
    box-shadow 0.15s ease,
    transform 0.15s ease;
}

.shopping-list-ready-action:hover,
.shopping-list-ready-action:focus-visible {
  box-shadow: 0 2px 8px rgba(var(--v-theme-on-surface), 0.18);
  transform: translateY(-1px);
}

.shopping-list-ready-action--active {
  box-shadow: inset 0 0 0 1px rgba(var(--v-theme-success), 0.28);
}

.shopping-list-ready-action--reset:hover,
.shopping-list-ready-action--reset:focus-visible {
  background-color: rgba(var(--v-theme-warning), 0.12) !important;
}

.shopping-list-inline-group + .shopping-list-inline-group {
  margin-top: 10px;
}

.shopping-list-inline-group-title {
  color: rgba(var(--v-theme-on-surface), 0.72);
  font-size: 0.85rem;
  font-weight: 700;
  margin: 6px 0;
  text-align: start;
}

.shopping-list-inline-item {
  align-items: center;
  border-bottom: 1px solid rgba(var(--v-border-color), 0.18);
  display: flex;
  gap: 8px;
  min-height: 34px;
}

.shopping-list-inline-item--checked {
  color: rgba(var(--v-theme-on-surface), 0.52);
}

.shopping-list-inline-item--checked .shopping-list-inline-item-text {
  text-decoration: line-through;
}

.shopping-list-inline-checkbox {
  flex: 0 0 auto;
}

.shopping-list-inline-item-text {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.shopping-list-inline-edit-input {
  flex: 1 1 auto;
  min-width: 140px;
}

.shopping-list-inline-action {
  flex: 0 0 auto;
  opacity: 0.68;
  transition:
    background-color 0.15s ease,
    box-shadow 0.15s ease,
    opacity 0.15s ease;
}

.shopping-list-inline-action:hover,
.shopping-list-inline-action:focus-visible {
  background-color: rgba(var(--v-theme-primary), 0.1) !important;
  box-shadow: inset 0 0 0 1px rgba(var(--v-theme-primary), 0.24);
  opacity: 1;
}
</style>
