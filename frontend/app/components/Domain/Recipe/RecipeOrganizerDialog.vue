<template>
  <div>
    <BaseDialog
      v-model="dialog"
      width="500"
      :title="properties.title"
      :icon="properties.icon"
      can-submit
      :submit-disabled="!name"
      @submit="select"
    >
      <v-form>
        <v-card-text>
          <v-text-field
            v-model="name"
            :label="properties.label"
            :rules="[rules.required]"
            autofocus
          />
          <v-autocomplete
            v-if="itemType === Organizer.Category && recipeGroup"
            v-model="selectedParentCategoryId"
            :items="parentCategoryOptions"
            :label="$t('recipe.parent-recipe-category')"
            clearable
            density="comfortable"
            variant="outlined"
            :custom-filter="normalizeFilter"
          />
          <v-checkbox
            v-if="itemType === Organizer.Tool"
            v-model="onHand"
            :label="$t('tool.on-hand')"
          />
        </v-card-text>
      </v-form>
    </BaseDialog>
  </div>
</template>

<script setup lang="ts">
import { useUserApi } from "~/composables/api";
import { useCategoryStore, useTagStore, useToolStore } from "~/composables/store";
import type { RecipeCategory } from "~/lib/api/types/recipe";
import { type RecipeOrganizer, Organizer } from "~/lib/api/types/non-generated";
import { normalizeFilter } from "~/composables/use-utils";

const { $globals } = useNuxtApp();

const CREATED_ITEM_EVENT = "created-item";

interface Props {
  color?: string | null;
  tagDialog?: boolean;
  itemType?: RecipeOrganizer;
  recipeGroup?: boolean;
  recipeGroupSection?: string;
  parentCategoryId?: string | null;
  editCategory?: {
    id?: string | null;
    name: string;
    isRecipeGroup?: boolean | null;
    recipeGroupSection?: string | null;
    parentCategoryId?: string | null;
  } | null;
}
const props = withDefaults(defineProps<Props>(), {
  color: null,
  tagDialog: true,
  itemType: Organizer.Category as RecipeOrganizer,
  recipeGroup: false,
  recipeGroupSection: "recipes",
  parentCategoryId: null,
  editCategory: null,
});

const emit = defineEmits<{
  "created-item": [item: any];
}>();

const dialog = defineModel<boolean>({ default: false });

const i18n = useI18n();

const name = ref("");
const onHand = ref(false);
const selectedParentCategoryId = ref<string | null>(null);
const allRecipeGroupCategories = ref<RecipeCategory[]>([]);

watch(
  dialog,
  async (val: boolean) => {
    if (val) {
      name.value = props.editCategory?.name || "";
      selectedParentCategoryId.value = props.editCategory?.parentCategoryId || props.parentCategoryId || null;
      if (props.itemType === Organizer.Category && props.recipeGroup) {
        const { data, error } = await userApi.categories.getRecipeGroups();
        allRecipeGroupCategories.value = !error && data ? data : [...categoryStore.store.value];
      }
    }
    else {
      name.value = "";
      selectedParentCategoryId.value = null;
    }
  },
);

const userApi = useUserApi();
const categoryStore = useCategoryStore();
const effectiveRecipeGroupSection = computed(() => props.editCategory?.recipeGroupSection || props.recipeGroupSection || "recipes");
const availableRecipeGroupCategories = computed(() => allRecipeGroupCategories.value.length
  ? allRecipeGroupCategories.value
  : categoryStore.store.value);
const parentCategoryOptions = computed(() => availableRecipeGroupCategories.value
  .filter(item => item.isRecipeGroup
    && (item.recipeGroupSection || "recipes") === effectiveRecipeGroupSection.value
    && item.id
    && item.id !== props.editCategory?.id
    && !item.parentCategoryId)
  .map(item => ({ title: item.name, value: item.id! }))
  .sort((left, right) => left.title.localeCompare(right.title, i18n.locale.value, { numeric: true, sensitivity: "base" })));

const store = (() => {
  switch (props.itemType) {
    case Organizer.Tag:
      return useTagStore();
    case Organizer.Tool:
      return useToolStore();
    default:
      return categoryStore;
  }
})();

const properties = computed(() => {
  switch (props.itemType) {
    case Organizer.Tag:
      return {
        title: i18n.t("tag.create-a-tag"),
        label: i18n.t("tag.tag-name"),
        icon: $globals.icons.tags,
        api: userApi.tags,
      };
    case Organizer.Tool:
      return {
        title: i18n.t("tool.create-a-tool"),
        label: i18n.t("tool.tool-name"),
        icon: $globals.icons.potSteam,
        api: userApi.tools,
      };
    default:
      return {
        title: props.editCategory
          ? i18n.t("recipe.rename-recipe-category")
          : props.recipeGroup ? i18n.t("recipe.create-recipe-category") : i18n.t("category.create-a-category"),
        label: i18n.t("category.category-name"),
        icon: $globals.icons.categories,
        api: userApi.categories,
      };
  }
});

const rules = {
  required: (val: string) => !!val || (i18n.t("general.a-name-is-required") as string),
};

async function select() {
  if (store) {
    const normalizedName = name.value.trim();
    if (props.itemType === Organizer.Category && props.recipeGroup && props.editCategory?.id) {
      const updatedItem = await categoryStore.actions.updateOne({
        ...props.editCategory,
        name: normalizedName,
        isRecipeGroup: true,
        recipeGroupSection: effectiveRecipeGroupSection.value,
        parentCategoryId: selectedParentCategoryId.value,
      });
      const { data } = await userApi.categories.getRecipeGroups();
      if (data) allRecipeGroupCategories.value = data;
      emit(CREATED_ITEM_EVENT, updatedItem || props.editCategory);
      dialog.value = false;
      return;
    }
    const existing = props.itemType === Organizer.Category && props.recipeGroup
      ? availableRecipeGroupCategories.value.find(item => item.name.trim().toLocaleLowerCase() === normalizedName.toLocaleLowerCase()
        && (item.recipeGroupSection || "recipes") === effectiveRecipeGroupSection.value
        && (item.parentCategoryId || null) === selectedParentCategoryId.value)
      : null;
    if (existing) {
      const updatedItem = existing.isRecipeGroup
        ? existing
        : await categoryStore.actions.updateOne({
            ...existing,
            isRecipeGroup: true,
            recipeGroupSection: effectiveRecipeGroupSection.value,
            parentCategoryId: selectedParentCategoryId.value,
          });
      emit(CREATED_ITEM_EVENT, updatedItem || existing);
      dialog.value = false;
      return;
    }

    // @ts-expect-error the same state is used for different organizer types, which have different requirements
    const newItem = await store.actions.createOne({
      name: normalizedName,
      onHand: onHand.value,
      isRecipeGroup: props.itemType === Organizer.Category && props.recipeGroup,
      recipeGroupSection: effectiveRecipeGroupSection.value,
      parentCategoryId: selectedParentCategoryId.value,
    });
    if (props.itemType === Organizer.Category && props.recipeGroup) {
      const { data } = await userApi.categories.getRecipeGroups();
      if (data) allRecipeGroupCategories.value = data;
    }
    emit(CREATED_ITEM_EVENT, newItem);
  }
  dialog.value = false;
}
</script>

<style></style>
