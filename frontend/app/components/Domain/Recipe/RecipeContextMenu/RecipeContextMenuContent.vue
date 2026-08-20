<template>
  <RecipeDialogShare
    v-model="shareDialog"
    :recipe-id="recipeId"
    :name="name"
    :recipe="recipeRef"
    :recipe-scale="recipeScale"
  />
  <RecipeDialogPrintPreferences v-model="printPreferencesDialog" :recipe="recipeRef" />
  <ShoppingWebsiteLinksDialog
    v-model="shoppingWebsiteLinksDialog"
    entity-type="recipe"
    :entity-id="recipeId"
  />
  <BaseDialog
    v-model="recipeDeleteDialog"
    :title="$t('recipe.delete-recipe')"
    color="error"
    :icon="$globals.icons.alertCircle"
    can-confirm
    @confirm="deleteRecipe()"
  >
    <v-card-text>
      <template v-if="isAdminAndNotOwner">
        {{ $t("recipe.admin-delete-confirmation") }}
      </template>
      <template v-else>
        {{ $t("recipe.delete-confirmation") }}
      </template>
      <v-progress-linear v-if="deletePreviewLoading" indeterminate color="primary" class="mt-4" />
      <template v-else>
        <v-divider v-if="deleteShoppingListOptions.length || deleteWebsiteOptions.length" class="my-4" />
        <p v-if="deleteShoppingListOptions.length" class="font-weight-medium mb-2">
          {{ $t("recipe.delete-linked-shopping-lists") }}
        </p>
        <v-checkbox
          v-for="item in deleteShoppingListOptions"
          :key="item.id"
          v-model="selectedDeleteShoppingListIds"
          :value="item.id"
          :label="item.name"
          density="compact"
          hide-details
        />
        <p v-if="deleteWebsiteOptions.length" class="font-weight-medium mt-4 mb-2">
          {{ $t("recipe.delete-linked-websites") }}
        </p>
        <v-checkbox
          v-for="item in deleteWebsiteOptions"
          :key="item.id"
          v-model="selectedDeleteWebsiteIds"
          :value="item.id"
          :label="item.name"
          density="compact"
          hide-details
        />
        <v-alert
          v-if="deleteShoppingListOptions.length || deleteWebsiteOptions.length"
          type="info"
          variant="tonal"
          density="compact"
          class="mt-4"
        >
          {{ $t("recipe.linked-items-remain-by-default") }}
        </v-alert>
      </template>
    </v-card-text>
  </BaseDialog>
  <BaseDialog
    v-model="recipeDuplicateDialog"
    :title="$t('recipe.duplicate')"
    color="primary"
    :icon="$globals.icons.duplicate"
    can-confirm
    @confirm="duplicateRecipe()"
  >
    <v-card-text>
      <v-text-field v-model="recipeName" density="compact" :label="$t('recipe.recipe-name')" autofocus />
    </v-card-text>
  </BaseDialog>
  <BaseDialog
    v-model="recipeRenameDialog"
    :title="$t('recipe.rename-recipe')"
    color="primary"
    :icon="$globals.icons.edit"
    :submit-disabled="!recipeRenameName.trim()"
    :submit-text="$t('general.save')"
    can-submit
    @submit="renameRecipe()"
  >
    <v-card-text>
      <v-text-field v-model="recipeRenameName" density="compact" :label="$t('recipe.recipe-name')" autofocus />
    </v-card-text>
  </BaseDialog>
  <BaseDialog
    v-model="recipeSectionDialog"
    :title="$t('recipe.show-in-sections')"
    :icon="$globals.icons.folderOutline"
    :submit-text="$t('general.save')"
    :submit-icon="$globals.icons.save"
    :loading="recipeSectionLoading"
    can-submit
    @submit="moveRecipeToSection()"
  >
    <v-card-text>
      <p class="mb-2 text-medium-emphasis">
        {{ $t("recipe.show-in-sections-description") }}
      </p>
      <v-checkbox
        v-model="selectedRecipeSections"
        :label="$t('recipe.section-recipes')"
        value="recipes"
        density="compact"
        hide-details
      />
      <v-checkbox
        v-model="selectedRecipeSections"
        :label="$t('recipe.section-book')"
        value="book"
        density="compact"
        hide-details
      />
      <v-checkbox
        v-model="selectedRecipeSections"
        :label="$t('recipe.section-sauce')"
        value="sauce"
        density="compact"
        hide-details
      />
      <v-divider class="my-4" />
      <v-text-field
        v-model="recipeGroupLocationSearch"
        class="mb-3"
        density="compact"
        variant="outlined"
        hide-details
        clearable
        :prepend-inner-icon="$globals.icons.search"
        :label="$t('search.search')"
      />
      <div class="recipe-group-location-picker">
        <v-chip-group v-if="selectedRecipeGroupLocationOptions.length" class="mb-2" column>
          <v-chip
            v-for="option in selectedRecipeGroupLocationOptions"
            :key="option.value"
            closable
            size="small"
            @click:close="removeRecipeGroupId(option.value)"
          >
            {{ option.title }}
          </v-chip>
        </v-chip-group>
        <div class="recipe-group-location-results" role="listbox" :aria-label="$t('recipe.recipe-categories-and-subcategories')">
          <v-checkbox
            v-for="option in filteredRecipeGroupLocationOptions"
            :key="option.value"
            v-model="selectedRecipeGroupIds"
            class="recipe-group-location-option"
            :value="option.value"
            :label="option.title"
            density="compact"
            hide-details
          />
          <p v-if="!filteredRecipeGroupLocationOptions.length" class="recipe-group-location-empty text-medium-emphasis">
            {{ $t("search.no-results") }}
          </p>
        </div>
      </div>
      <v-checkbox
        v-model="keepExistingRecipeGroups"
        :label="$t('recipe.keep-existing-recipe-locations')"
        :hint="$t('recipe.keep-existing-recipe-locations-hint')"
        persistent-hint
        density="compact"
      />
      <v-alert
        v-if="!selectedRecipeSections.length"
        type="warning"
        variant="tonal"
        density="compact"
        class="mt-3"
      >
        {{ $t("recipe.select-at-least-one-section") }}
      </v-alert>
    </v-card-text>
  </BaseDialog>
  <BaseDialog
    v-model="aiEditDialog"
    :title="$t('recipe.ai-edit')"
    :icon="$globals.icons.robot"
    width="1050"
    max-width="96vw"
    :loading="aiEditLoading || aiEditSaving"
    :submit-disabled="aiEditDraft ? !aiEditDraft.name?.trim() : !aiEditInstruction.trim()"
    :submit-text="aiEditDraft ? $t('general.save') : $t('recipe.create-ai-draft')"
    :submit-icon="aiEditDraft ? $globals.icons.save : $globals.icons.robot"
    can-submit
    @submit="aiEditDraft ? saveAIEdit() : generateAIEdit()"
    @cancel="resetAIEdit()"
  >
    <v-card-text>
      <v-textarea
        v-if="!aiEditDraft"
        v-model="aiEditInstruction"
        :label="$t('recipe.ai-edit-instruction')"
        :hint="$t('recipe.ai-edit-instruction-hint')"
        persistent-hint
        rows="5"
        autofocus
      />
      <template v-else>
        <v-alert type="info" variant="tonal" density="compact" class="mb-4">
          {{ $t('recipe.ai-edit-review') }}
        </v-alert>
        <RecipeQuickEditForm v-model="aiEditDraft" />
      </template>
    </v-card-text>
  </BaseDialog>
  <BaseDialog
    v-model="aiImageDialog"
    :title="$t('recipe.change-image-with-ai')"
    :icon="$globals.icons.fileImage"
    :loading="aiImageLoading"
    :submit-text="$t('recipe.find-new-image')"
    :submit-icon="$globals.icons.fileImage"
    can-submit
    @submit="createAIImage()"
  >
    <v-card-text>
      <v-textarea
        v-model="aiImagePrompt"
        :label="$t('recipe.ai-image-instruction')"
        :hint="$t('recipe.ai-image-instruction-hint')"
        persistent-hint
        rows="4"
        autofocus
      />
    </v-card-text>
  </BaseDialog>
  <BaseDialog
    v-model="imageUploadDialog"
    :title="$t('recipe.upload-recipe-image')"
    :icon="$globals.icons.fileImage"
    :loading="imageUploadLoading"
    :submit-disabled="!canSubmitImageUpload"
    :submit-text="$t('general.upload')"
    :submit-icon="$globals.icons.upload"
    can-submit
    @submit="uploadRecipeImage()"
    @cancel="resetImageUpload()"
  >
    <v-card-text>
      <v-btn-toggle
        v-model="imageUploadMode"
        mandatory
        divided
        color="primary"
        class="mb-4"
      >
        <v-btn value="file" :prepend-icon="$globals.icons.fileImage">
          {{ $t("asset.file") }}
        </v-btn>
        <v-btn value="url" :prepend-icon="$globals.icons.link">
          {{ $t("general.url") }}
        </v-btn>
      </v-btn-toggle>
      <v-file-input
        v-if="imageUploadMode === 'file'"
        v-model="imageUploadFile"
        accept="image/*"
        :label="$t('recipe.upload-recipe-image')"
        :prepend-icon="$globals.icons.fileImage"
        show-size
        clearable
      />
      <v-text-field
        v-else
        v-model="imageUploadUrl"
        type="url"
        :label="$t('recipe.image-url')"
        :hint="$t('recipe.image-url-download-hint')"
        persistent-hint
        :prepend-inner-icon="$globals.icons.link"
        autofocus
      />
      <v-checkbox
        v-if="imageUploadMode === 'url'"
        v-model="imageUploadViaExtension"
        class="mt-2"
        color="primary"
        density="compact"
        hide-details
        :label="$t('recipe.image-url-use-browser-extension')"
      />
      <p
        v-if="imageUploadMode === 'url' && imageUploadViaExtension"
        class="text-caption text-medium-emphasis mt-1 mb-0"
      >
        {{ $t("recipe.image-url-use-browser-extension-hint") }}
      </p>
    </v-card-text>
  </BaseDialog>
  <BaseDialog
    v-model="mealplannerDialog"
    :title="$t('recipe.add-recipe-to-mealplan')"
    color="primary"
    :icon="$globals.icons.calendar"
    can-confirm
    @confirm="addRecipeToPlan()"
  >
    <v-card-text>
      <v-date-picker
        v-model="newMealdate"
        class="mx-auto mb-3"
        hide-header
        show-adjacent-months
        color="primary"
        :first-day-of-week="firstDayOfWeek"
        :local="$i18n.locale"
      />
      <v-select
        v-model="newMealType"
        :return-object="false"
        :items="planTypeOptions"
        :label="$t('recipe.entry-type')"
        item-title="text"
        item-value="value"
      />
    </v-card-text>
  </BaseDialog>
  <RecipeDialogAddToShoppingList
    v-if="shoppingLists && recipeRefWithScale"
    v-model="shoppingListDialog"
    :recipes="[recipeRefWithScale]"
    :shopping-lists="shoppingLists"
    :default-create-new-list="true"
    :default-list-name="name"
  />

  <v-list
    density="compact"
    class="recipe-context-menu-list"
  >
    <v-list-item v-for="(item, index) in menuItems" :key="index" @click.stop="contextMenuEventHandler(item.event)">
      <template #prepend>
        <v-icon :color="item.color">
          {{ item.icon }}
        </v-icon>
      </template>
      <v-list-item-title>{{ item.title }}</v-list-item-title>
    </v-list-item>
    <div v-if="useItems.recipeActions && recipeActions && recipeActions.length">
      <v-divider />
      <v-list-item v-for="(action, index) in recipeActions" :key="index" @click.stop="executeRecipeAction(action)">
        <template #prepend>
          <v-icon color="undefined">
            {{ $globals.icons.linkVariantPlus }}
          </v-icon>
        </template>
        <v-list-item-title>
          {{ action.title }}
        </v-list-item-title>
      </v-list-item>
    </div>
    <template v-if="useItems.rating && isOwnGroup">
      <v-divider />
      <v-list-item class="recipe-menu-rating-item" @click.stop>
        <template #prepend>
          <v-icon color="undefined">
            {{ $globals.icons.star }}
          </v-icon>
        </template>
        <v-list-item-title>{{ $t("general.rating") }}</v-list-item-title>
        <template #append>
          <RecipeRating v-model="ratingModel" :recipe-id="recipeId" :slug="slug" small @click.stop />
        </template>
      </v-list-item>
    </template>
  </v-list>
</template>

<script setup lang="ts">
import RecipeDialogAddToShoppingList from "~/components/Domain/Recipe/RecipeDialogAddToShoppingList.vue";
import RecipeDialogPrintPreferences from "~/components/Domain/Recipe/RecipeDialogPrintPreferences.vue";
import RecipeDialogShare from "~/components/Domain/Recipe/RecipeDialogShare.vue";
import RecipeRating from "~/components/Domain/Recipe/RecipeRating.vue";
import RecipeQuickEditForm from "~/components/Domain/Recipe/RecipeQuickEditForm.vue";
import { useLoggedInState } from "~/composables/use-logged-in-state";
import { useUserApi } from "~/composables/api/api-client";
import { useGroupRecipeActions } from "~/composables/use-group-recipe-actions";
import { useHouseholdSelf } from "~/composables/use-households";
import { alert } from "~/composables/use-toast";
import { usePlanTypeOptions } from "~/composables/use-group-mealplan";
import { useRecipeCopy } from "~/composables/recipes/use-recipe-copy";
import type { Recipe, RecipeCategory } from "~/lib/api/types/recipe";
import type { GroupRecipeActionOut, ShoppingListSummary } from "~/lib/api/types/household";
import type { RecipeDeletePreview } from "~/lib/api/user/recipes/recipe";
import type { PlanEntryType } from "~/lib/api/types/meal-plan";
import { useDownloader } from "~/composables/api/use-downloader";
import { useCategoryStore } from "~/composables/store/use-category-store";
import { normalizeFilter } from "~/composables/use-utils";

export interface ContextMenuIncludes {
  delete: boolean;
  edit: boolean;
  rename: boolean;
  copy: boolean;
  rating: boolean;
  download: boolean;
  duplicate: boolean;
  mealplanner: boolean;
  shoppingList: boolean;
  aiShoppingList: boolean;
  aiImage: boolean;
  imageUpload?: boolean;
  aiEdit: boolean;
  print: boolean;
  printPreferences: boolean;
  share: boolean;
  recipeActions: boolean;
  shoppingWebsites?: boolean;
  section?: boolean;
  markDone?: boolean;
}

export interface ContextMenuItem {
  title: string;
  icon: string;
  color: string | undefined;
  event: string;
  isPublic: boolean;
}

interface Props {
  useItems?: ContextMenuIncludes;
  appendItems?: ContextMenuItem[];
  leadingItems?: ContextMenuItem[];
  menuTop?: boolean;
  fab?: boolean;
  color?: string;
  slug: string;
  menuIcon?: string | null;
  name: string;
  recipe?: Recipe;
  recipeId: string;
  rating?: number;
  recipeScale?: number;
  redirectOnDelete?: boolean;
  recipeSection?: string;
  showInRecipes?: boolean;
  showInBook?: boolean;
  showInSauce?: boolean;
  lastMade?: string | null;
  bulkDelete?: boolean;
}
const props = withDefaults(defineProps<Props>(), {
  useItems: () => ({
    delete: true,
    edit: true,
    rename: true,
    copy: true,
    rating: true,
    download: true,
    duplicate: false,
    mealplanner: true,
    shoppingList: true,
    aiShoppingList: true,
    aiImage: true,
    imageUpload: true,
    aiEdit: true,
    print: true,
    printPreferences: true,
    share: true,
    recipeActions: true,
    shoppingWebsites: true,
    section: true,
    markDone: true,
  }),
  appendItems: () => [],
  leadingItems: () => [],
  menuTop: true,
  fab: false,
  color: "primary",
  menuIcon: null,
  recipe: undefined,
  rating: 0,
  recipeScale: 1,
  redirectOnDelete: true,
  recipeSection: "recipes",
  showInRecipes: undefined,
  showInBook: undefined,
  showInSauce: undefined,
  lastMade: null,
  bulkDelete: false,
});

const emit = defineEmits<{
  [key: string]: any;
  deleted: [slug: string];
  deleteRequested: [slug: string];
  renamed: [{ slug: string; name: string; recipe?: Recipe }];
  imageUpdated: [{ slug: string; image: string }];
  sectionUpdated: [{ slug: string; recipeSection: string }];
  made: [{ slug: string; lastMade: string | null }];
  print: [];
}>();

const api = useUserApi();
const { copyRecipeText } = useRecipeCopy();

const printPreferencesDialog = ref(false);
const shareDialog = ref(false);
const recipeDeleteDialog = ref(false);
const deletePreviewLoading = ref(false);
const deletePreview = ref<RecipeDeletePreview>();
const selectedDeleteShoppingListIds = ref<string[]>([]);
const selectedDeleteWebsiteIds = ref<string[]>([]);
const mealplannerDialog = ref(false);
const shoppingListDialog = ref(false);
const shoppingWebsiteLinksDialog = ref(false);
const recipeDuplicateDialog = ref(false);
const recipeRenameDialog = ref(false);
const recipeSectionDialog = ref(false);
const selectedRecipeSections = ref<Array<"recipes" | "book" | "sauce">>([]);
const selectedRecipeGroupIds = ref<string[]>([]);
const initialRecipeGroupIds = ref<string[]>([]);
const recipeGroupLocationSearch = ref("");
const recipeLocationCategories = ref<RecipeCategory[]>([]);
const keepExistingRecipeGroups = ref(false);
const recipeSectionLoading = ref(false);
const KEEP_EXISTING_RECIPE_GROUPS_STORAGE_KEY = "mealie.recipe.keep-existing-recipe-groups";

function loadKeepExistingRecipeGroupsPreference() {
  if (!import.meta.client) return false;
  try {
    return window.localStorage.getItem(KEEP_EXISTING_RECIPE_GROUPS_STORAGE_KEY) === "true";
  }
  catch {
    return false;
  }
}

function saveKeepExistingRecipeGroupsPreference(value: boolean) {
  if (!import.meta.client) return;
  try {
    window.localStorage.setItem(KEEP_EXISTING_RECIPE_GROUPS_STORAGE_KEY, String(value));
  }
  catch {
    // Ignore storage restrictions; the transfer itself should still succeed.
  }
}
const aiEditDialog = ref(false);
const aiEditInstruction = ref("");
const aiEditDraft = ref<Recipe | null>(null);
const aiEditLoading = ref(false);
const aiEditSaving = ref(false);
const aiImageDialog = ref(false);
const aiImagePrompt = ref("");
const aiImageLoading = ref(false);
const imageUploadDialog = ref(false);
const imageUploadMode = ref<"file" | "url">("file");
const imageUploadFile = ref<File | File[] | null>(null);
const imageUploadUrl = ref("");
const imageUploadViaExtension = ref(true);
const imageUploadLoading = ref(false);
const pendingImageExtensionRequests = new Set<() => void>();
const recipeName = ref(props.name);
const recipeRenameName = ref(props.name);
const ratingModel = ref(props.rating ?? 0);
const loading = ref(false);
const menuItems = ref<ContextMenuItem[]>([]);
const menuLastMade = ref<string | null>(props.lastMade ?? props.recipe?.lastMade ?? null);
const newMealdate = ref(new Date());
const newMealType = ref<PlanEntryType>("dinner");

const newMealdateString = computed(() => {
  // Format the date to YYYY-MM-DD in the same timezone as newMealdate
  const year = newMealdate.value.getFullYear();
  const month = String(newMealdate.value.getMonth() + 1).padStart(2, "0");
  const day = String(newMealdate.value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
});

const i18n = useI18n();
const auth = useMealieAuth();
const { $globals } = useNuxtApp();
const { household } = useHouseholdSelf();
const { isOwnGroup } = useLoggedInState();
const categoryStore = useCategoryStore();

type RecipeLibrarySection = "recipes" | "book" | "sauce";

function recipeGroupSection(category: { recipeGroupSection?: string | null }): RecipeLibrarySection {
  if (category.recipeGroupSection === "book" || category.recipeGroupSection === "sauce") {
    return category.recipeGroupSection;
  }
  return "recipes";
}

function recipeSectionLabel(section: RecipeLibrarySection) {
  if (section === "book") return i18n.t("recipe.section-book");
  if (section === "sauce") return i18n.t("recipe.section-sauce");
  return i18n.t("recipe.section-recipes");
}

const RECIPE_UNCATEGORIZED_PREFIX = "__mealie_recipe_uncategorized__:";
type RecipeLocationOption = {
  title: string;
  value: string;
  section: RecipeLibrarySection;
  isUncategorized?: boolean;
};

function recipeUncategorizedValue(section: RecipeLibrarySection) {
  return `${RECIPE_UNCATEGORIZED_PREFIX}${section}`;
}

const availableRecipeLocationCategories = computed(() => {
  return recipeLocationCategories.value.length
    ? recipeLocationCategories.value
    : categoryStore.store.value;
});

function recipeGroupPath(category: RecipeCategory, groupsById: Map<string, RecipeCategory>) {
  const names = [category.name];
  const visited = new Set<string>();
  let parentId = category.parentCategoryId;
  while (parentId && !visited.has(parentId)) {
    visited.add(parentId);
    const parent = groupsById.get(parentId);
    if (!parent) break;
    names.unshift(parent.name);
    parentId = parent.parentCategoryId;
  }
  return names.join(" / ");
}

const recipeGroupLocationOptions = computed(() => {
  const categoriesById = new Map<string, RecipeCategory>();
  for (const category of [
    ...availableRecipeLocationCategories.value,
    ...(recipeRef.value?.recipeCategory || []),
  ]) {
    if (category.id && category.isRecipeGroup) categoriesById.set(category.id, category);
  }
  const groups = [...categoriesById.values()];
  const groupsById = new Map(groups.map(category => [category.id!, category]));
  const groupOptions: RecipeLocationOption[] = groups
    .map((category) => {
      const section = recipeGroupSection(category);
      return {
        title: `${recipeSectionLabel(section)}: ${recipeGroupPath(category, groupsById)}`,
        value: category.id!,
        section,
      };
    });
  const uncategorizedOptions: RecipeLocationOption[] = (["recipes", "book", "sauce"] as const).map(section => ({
    title: `${recipeSectionLabel(section)}: ${i18n.t("recipe.no-category")}`,
    value: recipeUncategorizedValue(section),
    section,
    isUncategorized: true,
  }));
  return [...uncategorizedOptions, ...groupOptions]
    .sort((left, right) => left.title.localeCompare(right.title, i18n.locale.value));
});

const filteredRecipeGroupLocationOptions = computed(() => {
  const query = recipeGroupLocationSearch.value.trim();
  return recipeGroupLocationOptions.value.filter((option) => {
    if (!selectedRecipeSections.value.includes(option.section)) return false;
    return !query || normalizeFilter(option.title, query);
  });
});

const selectedRecipeGroupLocationOptions = computed(() => {
  const selectedIds = new Set(selectedRecipeGroupIds.value);
  return recipeGroupLocationOptions.value.filter(
    option => selectedIds.has(option.value) && selectedRecipeSections.value.includes(option.section),
  );
});

function removeRecipeGroupId(id: string) {
  selectedRecipeGroupIds.value = selectedRecipeGroupIds.value.filter(selectedId => selectedId !== id);
}

function haveSameValues(left: string[], right: string[]) {
  return left.length === right.length && left.every(value => right.includes(value));
}

watch(selectedRecipeGroupIds, (ids) => {
  const requiredSections = recipeGroupLocationOptions.value
    .filter(option => ids.includes(option.value))
    .map(option => option.section);
  const nextSections = [...new Set([...selectedRecipeSections.value, ...requiredSections])];
  if (!haveSameValues(selectedRecipeSections.value, nextSections)) {
    selectedRecipeSections.value = nextSections;
  }
});

watch(selectedRecipeSections, (sections) => {
  const visibleSections = new Set(sections);
  const nextGroupIds = selectedRecipeGroupIds.value.filter((id) => {
    const option = recipeGroupLocationOptions.value.find(item => item.value === id);
    return option ? visibleSections.has(option.section) : false;
  });
  if (!haveSameValues(selectedRecipeGroupIds.value, nextGroupIds)) {
    selectedRecipeGroupIds.value = nextGroupIds;
  }
});

const route = useRoute();
const groupSlug = computed(() => route.params.groupSlug || auth.user.value?.groupSlug || "");

watch(
  () => props.rating,
  (rating) => {
    ratingModel.value = rating ?? 0;
  },
);

watch(
  () => props.name,
  (name) => {
    recipeName.value = name;
    recipeRenameName.value = name;
  },
);

const firstDayOfWeek = computed(() => {
  return household.value?.preferences?.firstDayOfWeek || 0;
});

onBeforeUnmount(() => {
  for (const cancel of [...pendingImageExtensionRequests]) {
    cancel();
  }
  pendingImageExtensionRequests.clear();
});

// ===========================================================================
// Context Menu Setup

const defaultItems: { [key: string]: ContextMenuItem } = {
  edit: {
    title: i18n.t("general.edit"),
    icon: $globals.icons.edit,
    color: undefined,
    event: "edit",
    isPublic: false,
  },
  rename: {
    title: i18n.t("recipe.rename-recipe"),
    icon: $globals.icons.edit,
    color: undefined,
    event: "rename",
    isPublic: false,
  },
  copy: {
    title: i18n.t("recipe.copy-recipe"),
    icon: $globals.icons.contentCopy,
    color: undefined,
    event: "copy",
    isPublic: true,
  },
  delete: {
    title: i18n.t("general.delete"),
    icon: $globals.icons.delete,
    color: "error",
    event: "delete",
    isPublic: false,
  },
  download: {
    title: i18n.t("general.download"),
    icon: $globals.icons.download,
    color: undefined,
    event: "download",
    isPublic: false,
  },
  duplicate: {
    title: i18n.t("general.duplicate"),
    icon: $globals.icons.duplicate,
    color: undefined,
    event: "duplicate",
    isPublic: false,
  },
  mealplanner: {
    title: i18n.t("recipe.add-to-plan"),
    icon: $globals.icons.calendar,
    color: undefined,
    event: "mealplanner",
    isPublic: false,
  },
  shoppingList: {
    title: i18n.t("recipe.add-to-list"),
    icon: $globals.icons.cartCheck,
    color: undefined,
    event: "shoppingList",
    isPublic: false,
  },
  aiShoppingList: {
    title: i18n.t("recipe.create-ai-shopping-list"),
    icon: $globals.icons.robot,
    color: undefined,
    event: "aiShoppingList",
    isPublic: false,
  },
  aiImage: {
    title: i18n.t("recipe.change-image-with-ai"),
    icon: $globals.icons.fileImage,
    color: undefined,
    event: "aiImage",
    isPublic: false,
  },
  imageUpload: {
    title: i18n.t("recipe.upload-recipe-image"),
    icon: $globals.icons.upload,
    color: undefined,
    event: "imageUpload",
    isPublic: false,
  },
  aiEdit: {
    title: i18n.t("recipe.ai-edit"),
    icon: $globals.icons.robot,
    color: undefined,
    event: "aiEdit",
    isPublic: false,
  },
  print: {
    title: i18n.t("general.print"),
    icon: $globals.icons.printer,
    color: undefined,
    event: "print",
    isPublic: true,
  },
  printPreferences: {
    title: i18n.t("general.print-preferences"),
    icon: $globals.icons.printerSettings,
    color: undefined,
    event: "printPreferences",
    isPublic: true,
  },
  share: {
    title: i18n.t("general.share"),
    icon: $globals.icons.shareVariant,
    color: undefined,
    event: "share",
    isPublic: false,
  },
  shoppingWebsites: {
    title: i18n.t("shopping-website.link-websites"),
    icon: $globals.icons.web,
    color: undefined,
    event: "shoppingWebsites",
    isPublic: false,
  },
  section: {
    title: i18n.t("recipe.move-to-section"),
    icon: $globals.icons.folderOutline,
    color: undefined,
    event: "section",
    isPublic: false,
  },
  markDone: {
    title: i18n.t(menuLastMade.value ? "recipe.mark-as-not-done" : "recipe.mark-as-done"),
    icon: menuLastMade.value ? $globals.icons.undo : $globals.icons.checkBold,
    color: menuLastMade.value ? undefined : "success",
    event: "markDone",
    isPublic: false,
  },
};

// Add leading and Appending Items
menuItems.value = [...menuItems.value, ...props.leadingItems, ...props.appendItems];

// ===========================================================================
// Context Menu Event Handler

const shoppingLists = ref<ShoppingListSummary[]>();
const recipeRef = ref<Recipe | undefined>(props.recipe);
const recipeRefWithScale = computed(() =>
  recipeRef.value ? { scale: props.recipeScale, ...recipeRef.value } : undefined,
);
const isAdminAndNotOwner = computed(() => {
  return !!recipeRef.value && auth.user.value?.admin && auth.user.value?.id !== recipeRef.value?.userId;
});
const canDelete = computed(() => {
  const user = auth.user.value;
  const recipe = recipeRef.value;
  if (!user) {
    return false;
  }

  if (!recipe) {
    return isOwnGroup.value;
  }

  return user.admin || user.id === recipe.userId;
});
const deleteShoppingListOptions = computed(() => (deletePreview.value?.shoppingListIds || []).map((id, index) => ({
  id,
  name: deletePreview.value?.shoppingListNames[index] || id,
})));
const deleteWebsiteOptions = computed(() => (deletePreview.value?.websiteIds || []).map((id, index) => ({
  id,
  name: deletePreview.value?.websiteNames[index] || id,
})));

// Get Default Menu Items Specified in Props
for (const [key, value] of Object.entries(props.useItems)) {
  if (!value) continue;

  // Skip delete if not allowed
  if (key === "delete" && !canDelete.value) continue;

  const item = defaultItems[key];
  if (item && (item.isPublic || isOwnGroup.value)) {
    menuItems.value.push(item);
  }
}

function syncMarkDoneMenuItem() {
  const item = menuItems.value.find(menuItem => menuItem.event === "markDone");
  if (!item) return;

  item.title = i18n.t(menuLastMade.value ? "recipe.mark-as-not-done" : "recipe.mark-as-done");
  item.icon = menuLastMade.value ? $globals.icons.undo : $globals.icons.checkBold;
  item.color = menuLastMade.value ? undefined : "success";
}

watch(
  () => props.lastMade,
  (lastMade) => {
    menuLastMade.value = lastMade ?? null;
    syncMarkDoneMenuItem();
  },
);

async function getShoppingLists() {
  const { data } = await api.shopping.lists.getAll(1, -1, { orderBy: "name", orderDirection: "asc" });
  if (data) {
    shoppingLists.value = data.items ?? [];
  }
}

async function refreshRecipe() {
  const { data } = await api.recipes.getOne(props.slug);
  if (data) {
    recipeRef.value = data;
  }
}

const router = useRouter();
const groupRecipeActionsStore = useGroupRecipeActions();

async function executeRecipeAction(action: GroupRecipeActionOut) {
  if (!props.recipe) return;
  const response = await groupRecipeActionsStore.execute(action, props.recipe, props.recipeScale);

  if (action.actionType === "post") {
    if (!response?.error) {
      alert.success(i18n.t("events.message-sent"));
    }
    else {
      alert.error(i18n.t("events.something-went-wrong"));
    }
  }
}

async function deleteRecipe() {
  const { data, error } = await api.recipes.deleteWithLinks(
    props.slug,
    selectedDeleteShoppingListIds.value,
    selectedDeleteWebsiteIds.value,
  );
  if (error) {
    alert.error(i18n.t("recipe.unable-to-delete-recipe") as string);
    return;
  }

  if (data?.slug) {
    alert.success(i18n.t("events.recipe-deleted") as string);
    window.dispatchEvent(new CustomEvent("mealie:organizers-updated"));
    emit("deleted", props.slug);
    if (props.redirectOnDelete) {
      router.push(`/g/${groupSlug.value}`);
    }
  }
}

async function openDeleteDialog() {
  selectedDeleteShoppingListIds.value = [];
  selectedDeleteWebsiteIds.value = [];
  deletePreview.value = undefined;
  recipeDeleteDialog.value = true;
  deletePreviewLoading.value = true;
  try {
    const { data } = await api.recipes.getDeletePreview(props.slug);
    if (data) deletePreview.value = data;
  }
  finally {
    deletePreviewLoading.value = false;
  }
}

const download = useDownloader();

async function handleDownloadEvent() {
  const { data: shareToken } = await api.recipes.share.createOne({ recipeId: props.recipeId });
  if (!shareToken) {
    console.error("No share token received");
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }

  download(api.recipes.share.getZipRedirectUrl(shareToken.id), `${props.slug}.zip`);
}

async function addRecipeToPlan() {
  const { response } = await api.mealplans.createOne({
    date: newMealdateString.value,
    entryType: newMealType.value,
    title: "",
    text: "",
    recipeId: props.recipeId,
  });

  if (response?.status === 201) {
    alert.success(i18n.t("recipe.recipe-added-to-mealplan") as string);
  }
  else {
    alert.error(i18n.t("recipe.failed-to-add-recipe-to-mealplan") as string);
  }
}

async function duplicateRecipe() {
  const { data } = await api.recipes.duplicateOne(props.slug, recipeName.value);
  if (data && data.slug) {
    router.push(`/g/${groupSlug.value}/r/${data.slug}`);
  }
}

async function renameRecipe() {
  const name = recipeRenameName.value.trim();
  if (!name) {
    return;
  }

  if (!recipeRef.value) {
    await refreshRecipe();
  }

  if (!recipeRef.value) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }

  const { data, error } = await api.recipes.updateOne(props.slug, { ...recipeRef.value, name });
  if (error || !data) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }

  recipeRef.value = data;
  recipeName.value = data.name || name;
  recipeRenameName.value = data.name || name;
  alert.success(i18n.t("events.updated"));
  emit("renamed", { slug: props.slug, name: data.name || name, recipe: data });
}

async function moveRecipeToSection() {
  if (recipeSectionLoading.value) return;
  recipeSectionLoading.value = true;
  try {
    // Cards contain a summary that can be stale. Always submit from a fresh
    // recipe so an older category list cannot overwrite the user's choice.
    await refreshRecipe();
    if (!recipeRef.value) {
      alert.error(i18n.t("events.something-went-wrong"));
      return;
    }

    // The checked locations are the final selection. When the keep-existing
    // option is off, this replaces all previous recipe groups; when it is on,
    // the previous groups are preserved in addition to the new selection.
    const selectedLocationIds = [...new Set(selectedRecipeGroupIds.value.filter(Boolean))];
    const selectedLocationOptions = recipeGroupLocationOptions.value.filter(option => selectedLocationIds.includes(option.value));
    const selectedActualGroupIds = selectedLocationOptions
      .filter(option => !option.isUncategorized)
      .map(option => option.value);
    const initialGroupIds = new Set(initialRecipeGroupIds.value);
    const targetGroupIds = keepExistingRecipeGroups.value
      ? [...new Set([...initialRecipeGroupIds.value, ...selectedActualGroupIds])]
      : [];
    if (!keepExistingRecipeGroups.value) {
      const selectedSections = new Set(selectedLocationOptions.map(option => option.section));
      const targetIds = new Set<string>();
      for (const section of selectedSections) {
        const sectionOptions = selectedLocationOptions.filter(option => option.section === section);
        if (sectionOptions.some(option => option.isUncategorized)) continue;
        const newlySelected = sectionOptions.filter(option => !option.isUncategorized && !initialGroupIds.has(option.value));
        for (const option of (newlySelected.length ? newlySelected : sectionOptions)) {
          if (!option.isUncategorized) targetIds.add(option.value);
        }
      }
      targetGroupIds.push(...targetIds);
    }
    const selectedGroups = availableRecipeLocationCategories.value.filter(category => targetGroupIds.includes(category.id || ""));
    const selectedLocationSections = recipeGroupLocationOptions.value
      .filter(option => selectedLocationIds.includes(option.value))
      .map(option => option.section);
    const effectiveSections = [...new Set([
      ...selectedRecipeSections.value,
      ...selectedLocationSections,
      ...selectedGroups.map(recipeGroupSection),
    ])];
    if (!effectiveSections.length) return;

    const currentPrimary = recipeRef.value.recipeSection || props.recipeSection || "recipes";
    const primarySection = effectiveSections.includes(currentPrimary as RecipeLibrarySection)
      ? currentPrimary
      : effectiveSections[0];
    const { data, error } = await api.recipes.updateLibraryLocation(props.slug, {
      sections: effectiveSections,
      recipeGroupIds: targetGroupIds,
      keepExistingRecipeGroups: keepExistingRecipeGroups.value,
    });
    if (error || !data) {
      alert.error(i18n.t("events.something-went-wrong"));
      return;
    }

    recipeRef.value = data;
    saveKeepExistingRecipeGroupsPreference(keepExistingRecipeGroups.value);
    recipeSectionDialog.value = false;
    alert.success(i18n.t("recipe.recipe-moved"));
    emit("sectionUpdated", { slug: props.slug, recipeSection: primarySection });
    window.dispatchEvent(new CustomEvent("mealie:recipes-updated"));
    window.dispatchEvent(new CustomEvent("mealie:organizers-updated"));
  }
  finally {
    recipeSectionLoading.value = false;
  }
}

async function markRecipeDone() {
  const timestamp = menuLastMade.value ? null : new Date().toISOString();
  const { data, error } = await api.recipes.updateLastMade(props.slug, timestamp);
  if (error || !data) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }

  menuLastMade.value = timestamp;
  if (recipeRef.value) {
    recipeRef.value.lastMade = timestamp;
  }
  syncMarkDoneMenuItem();
  alert.success(i18n.t(timestamp ? "recipe.marked-as-done" : "recipe.marked-as-not-done"));
  emit("made", { slug: props.slug, lastMade: timestamp });
}

async function copyRecipe() {
  if (!recipeRef.value) {
    await refreshRecipe();
  }

  if (!recipeRef.value) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }

  copyRecipeText(recipeRef.value, props.name, props.recipeScale);
}

async function createAIShoppingList() {
  const { data, error } = await api.recipes.createAIShoppingList(props.slug, {
    includeAiTips: true,
    organizeShoppingListWithAi: true,
  });

  if (error || !data) {
    alert.error(i18n.t("recipe.ai-shopping-list-create-failed"));
    return;
  }

  const shoppingListError = data.shoppingListError || data.shopping_list_error;
  if (shoppingListError) {
    alert.error(shoppingListError);
    return;
  }

  alert.success(i18n.t("recipe.ai-shopping-list-created"));
  window.dispatchEvent(new CustomEvent("mealie:shopping-lists-updated"));
}

async function createAIImage() {
  if (aiImageLoading.value) return;
  aiImageLoading.value = true;
  try {
    const { data, error } = await api.recipes.createAIImage(props.slug, aiImagePrompt.value.trim());
    if (error || !data?.image) {
      alert.error(i18n.t("recipe.ai-image-create-failed"));
      return;
    }

    if (recipeRef.value) {
      recipeRef.value.image = data.image;
    }

    alert.success(i18n.t("recipe.recipe-image-updated"));
    emit("imageUpdated", { slug: props.slug, image: data.image });
    aiImageDialog.value = false;
    aiImagePrompt.value = "";
  }
  finally {
    aiImageLoading.value = false;
  }
}

const selectedImageFile = computed(() => {
  const value = imageUploadFile.value;
  return Array.isArray(value) ? value[0] || null : value;
});

const validImageUrl = computed(() => {
  const value = imageUploadUrl.value.trim();
  if (!value) return false;
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  }
  catch {
    return false;
  }
});

const canSubmitImageUpload = computed(() => imageUploadMode.value === "file"
  ? Boolean(selectedImageFile.value)
  : validImageUrl.value);

function resetImageUpload() {
  imageUploadMode.value = "file";
  imageUploadFile.value = null;
  imageUploadUrl.value = "";
  imageUploadViaExtension.value = true;
  imageUploadLoading.value = false;
}

type ExtensionImageUpdateResponse = {
  ok?: boolean;
  image?: string;
  error?: string;
};

function apiErrorMessage(error: unknown) {
  const detail = (error as {
    response?: { data?: { detail?: string | { message?: string } } };
  } | null)?.response?.data?.detail;
  return typeof detail === "string" ? detail : detail?.message || "";
}

async function updateRecipeImageViaExtension(url: string): Promise<ExtensionImageUpdateResponse | null> {
  if (!import.meta.client) return null;

  const requestId = `mealie-image-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return await new Promise((resolve) => {
    let acknowledged = false;
    let settled = false;
    let ackTimer: ReturnType<typeof setTimeout> | null = null;
    let finalTimer: ReturnType<typeof setTimeout> | null = null;

    function cleanup() {
      window.removeEventListener("message", onMessage);
      if (ackTimer) clearTimeout(ackTimer);
      if (finalTimer) clearTimeout(finalTimer);
      pendingImageExtensionRequests.delete(cancel);
    }

    function finish(response: ExtensionImageUpdateResponse | null) {
      if (settled) return;
      settled = true;
      cleanup();
      resolve(response);
    }

    function cancel() {
      finish(null);
    }

    function onMessage(event: MessageEvent) {
      if (event.source !== window) return;
      const data = event.data as {
        type?: string;
        requestId?: string;
        response?: ExtensionImageUpdateResponse;
      };
      if (!data || data.requestId !== requestId) return;

      if (data.type === "MEALIE_EXTENSION_IMPORT_RECIPE_IMAGE_URL_ACK") {
        acknowledged = true;
        if (ackTimer) clearTimeout(ackTimer);
        return;
      }
      if (data.type === "MEALIE_EXTENSION_IMPORT_RECIPE_IMAGE_URL_RESULT") {
        finish(data.response || { ok: false });
      }
    }

    pendingImageExtensionRequests.add(cancel);
    window.addEventListener("message", onMessage);
    window.postMessage(
      {
        type: "MEALIE_EXTENSION_IMPORT_RECIPE_IMAGE_URL",
        requestId,
        payload: {
          url,
          recipeSlug: props.slug,
          mealieUrl: window.location.origin,
          interfaceLanguage: i18n.locale.value,
        },
      },
      window.location.origin,
    );

    ackTimer = setTimeout(() => {
      if (!acknowledged) finish(null);
    }, 1500);
    finalTimer = setTimeout(() => finish({
      ok: false,
      error: i18n.t("recipe.recipe-image-upload-failed"),
    }), 90000);
  });
}

async function uploadRecipeImage() {
  if (!canSubmitImageUpload.value || imageUploadLoading.value) return;
  imageUploadLoading.value = true;
  try {
    let image: string | undefined;
    let errorMessage = "";
    if (imageUploadMode.value === "file") {
      const response = await api.recipes.updateImage(props.slug, selectedImageFile.value as File);
      image = response.data?.image;
      errorMessage = apiErrorMessage(response.error);
    }
    else if (imageUploadViaExtension.value) {
      const response = await updateRecipeImageViaExtension(imageUploadUrl.value.trim());
      image = response?.image;
      errorMessage = response?.error || (response ? "" : i18n.t("recipe.image-url-extension-not-available"));
    }
    else {
      const response = await api.recipes.updateImagebyURL(props.slug, imageUploadUrl.value.trim());
      image = response.data?.image;
      errorMessage = apiErrorMessage(response.error);
    }

    if (!image) {
      alert.error(errorMessage || i18n.t("recipe.recipe-image-upload-failed"));
      return;
    }

    if (recipeRef.value) {
      recipeRef.value.image = image;
    }
    emit("imageUpdated", { slug: props.slug, image });
    alert.success(i18n.t("recipe.recipe-image-updated"));
    imageUploadDialog.value = false;
    resetImageUpload();
  }
  finally {
    imageUploadLoading.value = false;
  }
}

function resetAIEdit() {
  aiEditInstruction.value = "";
  aiEditDraft.value = null;
  aiEditLoading.value = false;
  aiEditSaving.value = false;
}

async function generateAIEdit() {
  const instruction = aiEditInstruction.value.trim();
  if (!instruction || aiEditLoading.value) return;
  aiEditLoading.value = true;
  try {
    const { data, error } = await api.recipes.createAIEdit(props.slug, instruction);
    if (error || !data) {
      alert.error(i18n.t("recipe.ai-edit-failed"));
      return;
    }
    aiEditDraft.value = data;
  }
  finally {
    aiEditLoading.value = false;
  }
}

async function saveAIEdit() {
  if (!aiEditDraft.value?.name?.trim() || aiEditSaving.value) return;
  aiEditSaving.value = true;
  try {
    const { data, error } = await api.recipes.updateOne(props.slug, aiEditDraft.value);
    if (error || !data) {
      alert.error(i18n.t("events.something-went-wrong"));
      return;
    }
    recipeRef.value = data;
    recipeName.value = data.name || props.name;
    recipeRenameName.value = data.name || props.name;
    emit("renamed", { slug: props.slug, name: data.name || props.name, recipe: data });
    alert.success(i18n.t("recipe.quick-edit-saved"));
    aiEditDialog.value = false;
    resetAIEdit();
  }
  finally {
    aiEditSaving.value = false;
  }
}

// Note: Print is handled as an event in the parent component
// eslint-disable-next-line @typescript-eslint/no-invalid-void-type
const eventHandlers: { [key: string]: () => void | Promise<any> } = {
  delete: () => {
    if (props.bulkDelete) {
      emit("deleteRequested", props.slug);
      return;
    }
    void openDeleteDialog();
  },
  edit: () => router.push(`/g/${groupSlug.value}/r/${props.slug}` + "?edit=true"),
  rename: () => {
    recipeRenameName.value = recipeRef.value?.name || props.name;
    recipeRenameDialog.value = true;
  },
  copy: copyRecipe,
  download: handleDownloadEvent,
  duplicate: () => {
    recipeDuplicateDialog.value = true;
  },
  mealplanner: openMealplannerDialog,
  printPreferences: async () => {
    if (!recipeRef.value) {
      await refreshRecipe();
    }
    printPreferencesDialog.value = true;
  },
  shoppingList: openShoppingListDialog,
  aiShoppingList: createAIShoppingList,
  aiImage: () => {
    aiImagePrompt.value = recipeName.value || props.name;
    aiImageDialog.value = true;
  },
  imageUpload: () => {
    resetImageUpload();
    imageUploadDialog.value = true;
  },
  section: async () => {
    // Load the complete recipe before opening the picker. Recipe cards only
    // carry a summary and can otherwise show stale section/category state.
    await refreshRecipe();
    const { data: recipeGroups, error: categoryError } = await api.categories.getRecipeGroups();
    if (!categoryError && recipeGroups) {
      recipeLocationCategories.value = recipeGroups;
    }
    else {
      await categoryStore.actions.refresh();
      recipeLocationCategories.value = [...categoryStore.store.value];
    }
    const recipe = recipeRef.value;
    const hasExplicitMembership = recipe?.showInRecipes !== undefined
      || recipe?.showInBook !== undefined
      || recipe?.showInSauce !== undefined
      || props.showInRecipes !== undefined
      || props.showInBook !== undefined
      || props.showInSauce !== undefined;
    selectedRecipeSections.value = hasExplicitMembership
      ? [
          ...((recipe?.showInRecipes ?? props.showInRecipes) ? ["recipes" as const] : []),
          ...((recipe?.showInBook ?? props.showInBook) ? ["book" as const] : []),
          ...((recipe?.showInSauce ?? props.showInSauce) ? ["sauce" as const] : []),
        ]
      : [(recipe?.recipeSection || props.recipeSection || "recipes") as "recipes" | "book" | "sauce"];
    initialRecipeGroupIds.value = (recipe?.recipeCategory || [])
      .filter(category => category.isRecipeGroup && category.id)
      .map(category => category.id!);
    const currentGroupsBySection = new Set(
      (recipe?.recipeCategory || [])
        .filter(category => category.isRecipeGroup && category.id)
        .map(category => recipeGroupSection(category)),
    );
    const defaultUncategorizedLocations = selectedRecipeSections.value
      .filter(section => !currentGroupsBySection.has(section))
      .map(recipeUncategorizedValue);
    selectedRecipeGroupIds.value = [...initialRecipeGroupIds.value, ...defaultUncategorizedLocations];
    recipeGroupLocationSearch.value = "";
    keepExistingRecipeGroups.value = loadKeepExistingRecipeGroupsPreference();
    recipeSectionDialog.value = true;
  },
  markDone: markRecipeDone,
  aiEdit: () => {
    resetAIEdit();
    aiEditDialog.value = true;
  },
  shoppingWebsites: () => {
    shoppingWebsiteLinksDialog.value = true;
  },
  share: async () => {
    if (!recipeRef.value) {
      await refreshRecipe();
    }
    shareDialog.value = true;
  },
};

function openMealplannerDialog() {
  mealplannerDialog.value = true;
}

async function openShoppingListDialog() {
  const promises: Promise<void>[] = [getShoppingLists()];
  if (!recipeRef.value) {
    promises.push(refreshRecipe());
  }

  await Promise.allSettled(promises);
  shoppingListDialog.value = true;
}

defineExpose({
  openMealplannerDialog,
  openShoppingListDialog,
});

function contextMenuEventHandler(eventKey: string) {
  const handler = eventHandlers[eventKey];

  if (handler && typeof handler === "function") {
    handler();
    loading.value = false;
    return;
  }

  emit(eventKey);
  loading.value = false;
}

const planTypeOptions = usePlanTypeOptions();
const recipeActions = groupRecipeActionsStore.recipeActions;
</script>

<style scoped>
.recipe-context-menu-list {
  min-width: 240px;
  overflow-x: hidden;
}

.recipe-menu-rating-item :deep(.v-list-item__append) {
  margin-inline-start: 12px;
}
</style>
