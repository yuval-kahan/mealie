import type { ShoppingListItemOut } from "~/lib/api/types/household";
import { useShoppingListState } from "~/composables/shopping-list-page/sub-composables/use-shopping-list-state";
import { useShoppingListData } from "~/composables/shopping-list-page/sub-composables/use-shopping-list-data";
import { useShoppingListSorting } from "~/composables/shopping-list-page/sub-composables/use-shopping-list-sorting";
import { useShoppingListLabels } from "~/composables/shopping-list-page/sub-composables/use-shopping-list-labels";
import { useShoppingListCopy } from "~/composables/shopping-list-page/sub-composables/use-shopping-list-copy";
import { useShoppingListCrud } from "~/composables/shopping-list-page/sub-composables/use-shopping-list-crud";
import { useShoppingListRecipes } from "~/composables/shopping-list-page/sub-composables/use-shopping-list-recipes";
import { useUserApi } from "~/composables/api/api-client";
import { alert } from "~/composables/use-toast";
import {
  buildShoppingListReadyExtras,
  isShoppingListGroceriesReady,
  useShoppingListAvailability,
} from "~/composables/shopping-list-page/use-shopping-list-availability";

/**
 * Main composable that orchestrates all shopping list page functionality
 */
export function useShoppingListPage(listId: string) {
  const i18n = useI18n();
  const userApi = useUserApi();

  // Initialize state
  const state = useShoppingListState();
  const {
    shoppingList,
    loadingCounter,
    recipeReferenceLoading,
    preserveItemOrder,
    listItems,
    sortCheckedItems,
  } = state;

  // Initialize sorting functionality
  const sorting = useShoppingListSorting();
  const { groupAndSortListItemsByFood, sortListItems, updateItemsByLabel } = sorting;

  // Track items organized by label
  const itemsByLabel = ref<{ [key: string]: ShoppingListItemOut[] }>({});
  const aiOrganizing = ref(false);
  const { updateAvailabilityForListName } = useShoppingListAvailability();
  const shoppingListAiOrganized = computed(() => {
    const value = shoppingList.value?.extras?.aiOrganized;
    return value === true || value === "true";
  });
  const shoppingListGroceriesReady = computed(() => isShoppingListGroceriesReady(shoppingList.value));

  function updateListItemOrder() {
    if (!shoppingList.value) return;

    if (!preserveItemOrder.value) {
      groupAndSortListItemsByFood(shoppingList.value);
    }
    else {
      sortListItems(shoppingList.value);
    }

    const labeledItems = updateItemsByLabel(shoppingList.value);
    if (labeledItems) {
      itemsByLabel.value = labeledItems;
    }
  }

  // Initialize data management
  const dataManager = useShoppingListData(listId, shoppingList, loadingCounter);
  const { isOffline, refresh: baseRefresh, startPolling, stopPolling, shoppingListItemActions } = dataManager;

  const refresh = () => baseRefresh(updateListItemOrder);

  // Initialize shopping list labels
  const labels = useShoppingListLabels(shoppingList);

  // Initialize copy functionality
  const copyManager = useShoppingListCopy();

  // Initialize CRUD operations
  const crud = useShoppingListCrud(
    shoppingList,
    loadingCounter,
    listItems,
    shoppingListItemActions,
    refresh,
    sortCheckedItems,
    updateListItemOrder,
  );

  // Initialize recipe management
  const recipes = useShoppingListRecipes(
    shoppingList,
    loadingCounter,
    recipeReferenceLoading,
    refresh,
  );

  // Handle item reordering by label
  function updateIndexUncheckedByLabel(labelName: string, labeledUncheckedItems: ShoppingListItemOut[]) {
    if (!itemsByLabel.value[labelName]) {
      return;
    }

    const checkedItems = itemsByLabel.value[labelName].filter(item => item.checked);
    const uncheckedItems = labeledUncheckedItems.filter(item => !item.checked);

    // update this label's item order
    itemsByLabel.value[labelName] = [...uncheckedItems, ...checkedItems];

    // reset list order of all items
    const allUncheckedItems: ShoppingListItemOut[] = [];
    for (const labelKey in itemsByLabel.value) {
      allUncheckedItems.push(...itemsByLabel.value[labelKey].filter(item => !item.checked));
    }

    // since the user has manually reordered the list, we should preserve this order
    preserveItemOrder.value = true;

    // save changes
    listItems.unchecked = allUncheckedItems;
    listItems.checked = shoppingList.value?.listItems?.filter(item => item.checked) || [];
    crud.updateUncheckedListItems();
  }

  // Dialog helpers
  function openCheckAll() {
    if (shoppingList.value?.listItems?.some(item => !item.checked)) {
      state.state.checkAllDialog = true;
    }
  }

  function openUncheckAll() {
    if (shoppingList.value?.listItems?.some(item => item.checked)) {
      state.state.uncheckAllDialog = true;
    }
  }

  function openDeleteChecked() {
    if (shoppingList.value?.listItems?.some(item => item.checked)) {
      state.state.deleteCheckedDialog = true;
    }
  }

  function checkAll() {
    state.state.checkAllDialog = false;
    crud.checkAllItems();
  }

  function uncheckAll() {
    state.state.uncheckAllDialog = false;
    crud.uncheckAllItems();
  }

  function deleteChecked() {
    state.state.deleteCheckedDialog = false;
    crud.deleteCheckedItems();
  }

  // Copy functionality wrapper
  function copyListItems(copyType: "plain" | "markdown") {
    copyManager.copyListItems(itemsByLabel.value, copyType);
  }

  async function organizeShoppingListWithAI() {
    if (!shoppingList.value || aiOrganizing.value) {
      return;
    }

    if (!shoppingList.value.listItems?.length) {
      alert.error(i18n.t("shopping-list.ai-organize-empty"));
      return;
    }

    aiOrganizing.value = true;
    loadingCounter.value += 1;
    try {
      await shoppingListItemActions.process();
      const { data, error } = await userApi.shopping.lists.organizeWithAi(shoppingList.value.id);
      if (error || !data) {
        alert.error(i18n.t("shopping-list.ai-organize-failed"));
        return;
      }

      preserveItemOrder.value = false;
      shoppingList.value = data;
      updateListItemOrder();
      const { error: itemImagesError } = await userApi.shopping.lists.ensureItemImages(data.id);
      if (itemImagesError) {
        console.error("Failed to ensure shopping list item images", itemImagesError);
      }
      window.dispatchEvent(new CustomEvent("mealie:organizers-updated"));
      alert.success(i18n.t("shopping-list.ai-organize-complete"));
    }
    catch {
      alert.error(i18n.t("shopping-list.ai-organize-failed"));
    }
    finally {
      loadingCounter.value -= 1;
      aiOrganizing.value = false;
    }
  }

  async function setShoppingListGroceriesReady(nextReady: boolean) {
    if (!shoppingList.value) {
      return;
    }

    if (shoppingListGroceriesReady.value === nextReady) {
      return;
    }

    loadingCounter.value += 1;
    try {
      await shoppingListItemActions.process();
      const payload = {
        ...shoppingList.value,
        extras: buildShoppingListReadyExtras(shoppingList.value, nextReady),
      };
      const { data, error } = await userApi.shopping.lists.updateOne(shoppingList.value.id, payload);
      if (error || !data) {
        alert.error(i18n.t("events.something-went-wrong"));
        return;
      }

      shoppingList.value = data;
      updateAvailabilityForListName(data.name, nextReady);
      window.dispatchEvent(new CustomEvent("mealie:organizers-updated"));
    }
    finally {
      loadingCounter.value -= 1;
    }
  }

  async function toggleShoppingListGroceriesReady() {
    await setShoppingListGroceriesReady(!shoppingListGroceriesReady.value);
  }

  // Label reordering helpers
  function toggleReorderLabelsDialog() {
    crud.toggleReorderLabelsDialog(state.reorderLabelsDialog);
  }

  async function saveLabelOrder() {
    await crud.saveLabelOrder(() => {
      const labeledItems = updateItemsByLabel(shoppingList.value!);
      if (labeledItems) {
        itemsByLabel.value = labeledItems;
      }
    });
  }

  // Lifecycle management
  onMounted(() => {
    startPolling(updateListItemOrder);
  });

  onUnmounted(() => {
    stopPolling();
  });

  return {
    itemsByLabel,
    isOffline,

    // Sub-composables
    ...state,
    ...labels,
    ...crud,
    ...recipes,

    // Specialized functions
    updateIndexUncheckedByLabel,
    copyListItems,
    organizeShoppingListWithAI,
    aiOrganizing,
    shoppingListAiOrganized,
    shoppingListGroceriesReady,
    setShoppingListGroceriesReady,
    toggleShoppingListGroceriesReady,

    // Dialog actions
    openCheckAll,
    openUncheckAll,
    openDeleteChecked,
    checkAll,
    uncheckAll,
    deleteChecked,

    // Label management
    toggleReorderLabelsDialog,
    saveLabelOrder,

    // Data refresh
    refresh,
  };
}
