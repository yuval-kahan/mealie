import type { ShoppingListItemOut, ShoppingListOut } from "~/lib/api/types/household";
import { useCopyList } from "~/composables/use-copy";

type CopyTypes = "plain" | "markdown";

/**
 * Composable for managing shopping list copy functionality
 */
export function useShoppingListCopy() {
  const copy = useCopyList();
  const i18n = useI18n();

  function copyListItems(itemsByLabel: { [key: string]: ShoppingListItemOut[] }, copyType: CopyTypes) {
    const text: string[] = [];
    Object.entries(itemsByLabel).forEach(([label, items], idx) => {
      if (idx) {
        text.push("");
      }

      text.push(formatCopiedLabelHeading(copyType, label));
      items.forEach(item => text.push(formatCopiedListItem(copyType, item)));
    });

    copy.copyPlain(text);
  }

  function copyShoppingList(shoppingList: ShoppingListOut, copyType: CopyTypes = "plain") {
    copyListItems(buildItemsByLabel(shoppingList), copyType);
  }

  function buildItemsByLabel(shoppingList: ShoppingListOut) {
    const items: Record<string, ShoppingListItemOut[]> = {};
    const noLabelText = i18n.t("shopping-list.no-label");
    const noLabel: ShoppingListItemOut[] = [];
    const labelOrder = shoppingList.labelSettings?.map(labelSetting => labelSetting.label.name) || [];

    const sortedItems = [...(shoppingList.listItems || [])].sort(sortItems);
    sortedItems.forEach((item) => {
      if (item.checked) {
        return;
      }

      if (item.label?.name) {
        (items[item.label.name] ||= []).push(item);
      }
      else {
        noLabel.push(item);
      }
    });

    const sorted: Record<string, ShoppingListItemOut[]> = {};
    if (noLabel.length) {
      sorted[noLabelText] = noLabel;
    }

    labelOrder.forEach((labelName) => {
      if (items[labelName]) {
        sorted[labelName] = items[labelName];
      }
    });

    Object.keys(items)
      .filter(labelName => !(labelName in sorted))
      .sort((a, b) => a.localeCompare(b))
      .forEach((labelName) => {
        sorted[labelName] = items[labelName];
      });

    return sorted;
  }

  function sortItems(a: ShoppingListItemOut, b: ShoppingListItemOut) {
    const posA = a.position ?? 0;
    const posB = b.position ?? 0;
    if (posA !== posB) {
      return posA - posB;
    }

    const createdA = a.createdAt ?? "";
    const createdB = b.createdAt ?? "";
    if (createdA !== createdB) {
      return createdA < createdB ? -1 : 1;
    }

    return (a.display || "").localeCompare(b.display || "");
  }

  function formatCopiedListItem(copyType: CopyTypes, item: ShoppingListItemOut): string {
    const display = item.display || "";
    switch (copyType) {
      case "markdown":
        return `- [ ] ${display}`;
      default:
        return display;
    }
  }

  function formatCopiedLabelHeading(copyType: CopyTypes, label: string): string {
    switch (copyType) {
      case "markdown":
        return `# ${label}`;
      default:
        return `[${label}]`;
    }
  }

  return {
    copyListItems,
    copyShoppingList,
    buildItemsByLabel,
    formatCopiedListItem,
    formatCopiedLabelHeading,
  };
}
