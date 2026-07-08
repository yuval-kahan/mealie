<template>
  <div v-if="dialog">
    <BaseDialog
      v-if="ready"
      v-model="dialog"
      :title="$t('recipe.add-to-list')"
      :icon="$globals.icons.cartCheck"
      width="780"
      max-width="96vw"
      :loading="shoppingListSelectionLoading"
      :submit-text="$t('recipe.add-to-list')"
      :submit-disabled="!canSubmitShoppingListDialog"
      can-submit
      keep-open
      @submit="addRecipesToList"
    >
      <v-card-text
        v-if="shoppingListDialog"
        class="shopping-list-target pb-0"
      >
        <v-radio-group
          v-model="shoppingListTarget"
          hide-details
        >
          <v-radio
            value="new"
            color="primary"
            :label="$t('shopping-list.new-list')"
          />
          <v-text-field
            v-if="shoppingListTarget === 'new'"
            v-model="newShoppingListName"
            class="mb-4 ms-8"
            density="compact"
            variant="outlined"
            :label="$t('shopping-list.list-name')"
            :placeholder="defaultShoppingListName"
          />

          <v-divider
            v-if="filteredShoppingLists.length"
            class="my-2"
          />

          <v-radio
            v-for="list in filteredShoppingLists"
            :key="list.id"
            color="primary"
            :value="list.id"
            :label="list.name || $t('shopping-list.shopping-list')"
          />
        </v-radio-group>

        <v-alert
          v-if="!filteredShoppingLists.length"
          type="info"
          variant="tonal"
          class="mt-4"
        >
          {{ $t('shopping-list.no-shopping-lists-found') }}
        </v-alert>

        <v-alert
          v-if="duplicateShoppingList"
          type="warning"
          variant="tonal"
          class="mt-4"
        >
          <div class="font-weight-bold mb-2">
            {{ $t("shopping-list.list-name-already-exists") }}
          </div>
          <div class="mb-3">
            {{ $t("shopping-list.choose-existing-list-behavior", { name: duplicateShoppingList.name }) }}
          </div>
          <v-radio-group
            v-model="duplicateConflictAction"
            hide-details
          >
            <v-radio
              color="primary"
              value="append"
              :label="$t('shopping-list.add-to-existing-list')"
            />
            <v-radio
              color="primary"
              value="overwrite"
              :label="$t('shopping-list.replace-existing-list')"
            />
          </v-radio-group>
        </v-alert>
      </v-card-text>
      <v-card-text
        v-if="shoppingListIngredientDialog"
        class="shopping-list-preview"
      >
        <v-divider class="mb-4" />
        <div class="d-flex flex-wrap align-center justify-space-between ga-2 mb-3">
          <div>
            <div class="text-caption text-medium-emphasis">
              {{ $t("shopping-list.selected-shopping-list") }}
            </div>
            <div class="text-h6">
              {{ selectedShoppingListName }}
            </div>
          </div>
        </div>

        <v-alert
          v-if="overwriteExistingList"
          type="warning"
          variant="tonal"
          class="mb-4"
        >
          {{ $t("shopping-list.replace-existing-list-warning") }}
        </v-alert>

        <div class="shopping-list-preview-scroll">
          <v-card
            v-for="(recipeSection, recipeSectionIndex) in recipeIngredientSections"
            :key="recipeSection.recipeId + recipeSectionIndex"
            elevation="0"
            height="fit-content"
            width="100%"
          >
            <v-divider
              v-if="recipeSectionIndex > 0"
              class="mt-3"
            />
            <v-card-title
              v-if="recipeIngredientSections.length > 1"
              class="justify-center text-h5"
              width="100%"
            >
              <v-container style="width: 100%;">
                <v-row
                  no-gutters
                  class="ma-0 pa-0"
                >
                  <v-col
                    cols="12"
                    align-self="center"
                    class="text-center"
                  >
                    {{ recipeSection.recipeName }}
                    <v-tooltip v-if="recipeSection.parentRecipe?.name" location="top">
                      <template #activator="{ props: tooltipProps }">
                        <v-icon
                          v-bind="tooltipProps"
                          size="tiny"
                          class="mb-2 ml-2"
                          style="cursor: pointer"
                        >
                          {{ $globals.icons.potSteam }}
                        </v-icon>
                      </template>
                      <span>{{ $t("shopping-list.ingredient-of-recipe", { recipe: recipeSection.parentRecipe.name }) }}</span>
                    </v-tooltip>
                  </v-col>
                </v-row>
                <v-row
                  v-if="recipeSection.recipeScale > 1"
                  no-gutters
                  class="ma-0 pa-0"
                >
                  <!-- TODO: make this editable in the dialog and visible on single-recipe lists -->
                  <v-col
                    cols="12"
                    align-self="center"
                    class="text-center"
                  >
                    ({{ $t("recipe.quantity") }}: {{ recipeSection.recipeScale }})
                  </v-col>
                </v-row>
              </v-container>
            </v-card-title>
            <div>
              <div
                v-for="(ingredientSection, ingredientSectionIndex) in recipeSection.ingredientSections"
                :key="recipeSection.recipeId + recipeSectionIndex + ingredientSectionIndex"
              >
                <v-card-title
                  v-if="ingredientSection.sectionName"
                  class="ingredient-title mt-2 pb-0 text-h6"
                >
                  {{ ingredientSection.sectionName }}
                </v-card-title>
                <div class="shopping-ingredient-list">
                  <v-list-item
                    v-for="(ingredientData, i) in ingredientSection.ingredients"
                    :key="recipeSection.recipeId + recipeSectionIndex + ingredientSectionIndex + i"
                    class="shopping-ingredient-row"
                    density="compact"
                    @click="toggleIngredientChecked(recipeSectionIndex, ingredientSectionIndex, i)"
                  >
                    <template #prepend>
                      <v-checkbox
                        hide-details
                        :model-value="ingredientData.checked"
                        class="shopping-ingredient-checkbox"
                        color="secondary"
                        density="compact"
                        @click.stop="toggleIngredientChecked(recipeSectionIndex, ingredientSectionIndex, i)"
                      />
                    </template>
                    <v-text-field
                      v-if="isEditingIngredient(ingredientKey(recipeSectionIndex, ingredientSectionIndex, i))"
                      v-model="editingIngredientText"
                      class="shopping-ingredient-edit"
                      density="compact"
                      variant="underlined"
                      hide-details
                      autofocus
                      @click.stop
                      @keydown.enter.stop.prevent="saveIngredientEdit(recipeSectionIndex, ingredientSectionIndex, i)"
                      @keydown.esc.stop.prevent="cancelIngredientEdit"
                    />
                    <div
                      v-else
                      class="shopping-ingredient-text"
                    >
                      <div :key="`${ingredientData.ingredient?.quantity || 'no-qty'}-${i}`" class="pa-auto my-auto">
                        <RecipeIngredientListItem
                          :ingredient="ingredientData.ingredient"
                          :scale="recipeSection.recipeScale"
                        />
                      </div>
                    </div>
                    <template #append>
                      <div class="shopping-ingredient-actions">
                        <template v-if="isEditingIngredient(ingredientKey(recipeSectionIndex, ingredientSectionIndex, i))">
                          <v-btn
                            icon
                            size="x-small"
                            variant="text"
                            color="primary"
                            :title="$t('general.save')"
                            @click.stop="saveIngredientEdit(recipeSectionIndex, ingredientSectionIndex, i)"
                          >
                            <v-icon>{{ $globals.icons.save }}</v-icon>
                          </v-btn>
                          <v-btn
                            icon
                            size="x-small"
                            variant="text"
                            :title="$t('general.cancel')"
                            @click.stop="cancelIngredientEdit"
                          >
                            <v-icon>{{ $globals.icons.close }}</v-icon>
                          </v-btn>
                        </template>
                        <template v-else>
                          <v-btn
                            icon
                            size="x-small"
                            variant="text"
                            :title="$t('general.edit')"
                            @click.stop="startIngredientEdit(ingredientData.ingredient, ingredientKey(recipeSectionIndex, ingredientSectionIndex, i))"
                          >
                            <v-icon>{{ $globals.icons.edit }}</v-icon>
                          </v-btn>
                          <v-btn
                            icon
                            size="x-small"
                            variant="text"
                            color="error"
                            :title="$t('general.delete')"
                            @click.stop="removeIngredient(recipeSectionIndex, ingredientSectionIndex, i)"
                          >
                            <v-icon>{{ $globals.icons.delete }}</v-icon>
                          </v-btn>
                        </template>
                      </div>
                    </template>
                  </v-list-item>
                </div>
              </div>
            </div>
          </v-card>

          <div class="d-flex justify-end mb-4 mt-2">
            <BaseButtonGroup
              :buttons="[
                {
                  icon: $globals.icons.checkboxBlankOutline,
                  text: $t('shopping-list.uncheck-all-items'),
                  event: 'uncheck',
                },
                {
                  icon: $globals.icons.checkboxOutline,
                  text: $t('shopping-list.check-all-items'),
                  event: 'check',
                },
              ]"
              @uncheck="bulkCheckIngredients(false)"
              @check="bulkCheckIngredients(true)"
            />
          </div>

          <v-divider class="my-4" />
          <div class="text-h6 mb-2">
            {{ $t("shopping-list.additional-items") }}
          </div>
          <ShoppingListItemEditor
            v-model="manualListItem"
            class="mb-3"
            :labels="allLabels || []"
            :units="allUnits || []"
            :foods="allFoods || []"
            :allow-delete="false"
            @cancel="resetManualListItem"
            @save="addManualListItem"
          />
          <v-list
            v-if="manualShoppingListItems.length"
            density="compact"
            class="manual-shopping-list-items"
          >
            <v-list-item
              v-for="item in manualShoppingListItems"
              :key="item.id"
              :title="formatManualListItem(item)"
            >
              <template #prepend>
                <v-icon>{{ $globals.icons.createAlt }}</v-icon>
              </template>
              <template #append>
                <v-btn
                  icon
                  size="small"
                  variant="text"
                  color="error"
                  @click="removeManualListItem(item.id || '')"
                >
                  <v-icon>{{ $globals.icons.delete }}</v-icon>
                </v-btn>
              </template>
            </v-list-item>
          </v-list>
        </div>
      </v-card-text>
      <template #custom-card-action>
        <v-checkbox
          v-if="shoppingListDialog"
          v-model="preferences.viewAllLists"
          hide-details
          :label="$t('general.show-all')"
          class="my-auto mr-4"
          @click="setShowAllToggled()"
        />
      </template>
    </BaseDialog>
  </div>
</template>

<script setup lang="ts">
import { toRefs } from "@vueuse/core";
import RecipeIngredientListItem from "./RecipeIngredientListItem.vue";
import ShoppingListItemEditor from "~/components/Domain/ShoppingList/ShoppingListItemEditor.vue";
import { useUserApi } from "~/composables/api";
import { useFoodStore, useLabelStore, useUnitStore } from "~/composables/store";
import { alert } from "~/composables/use-toast";
import { useShoppingListPreferences } from "~/composables/use-users/preferences";
import { uuid4 } from "~/composables/use-utils";
import type { RecipeIngredient, ShoppingListAddRecipeParamsBulk, ShoppingListItemCreate, ShoppingListOut, ShoppingListSummary } from "~/lib/api/types/household";
import type { Recipe } from "~/lib/api/types/recipe";

export interface RecipeWithScale extends Recipe {
  scale: number;
}

export interface ShoppingListIngredient {
  checked: boolean;
  ingredient: RecipeIngredient;
}

export interface ShoppingListIngredientSection {
  sectionName: string;
  ingredients: ShoppingListIngredient[];
}

export interface ShoppingListRecipeIngredientSection {
  recipeId: string;
  recipeName: string;
  recipeScale: number;
  ingredientSections: ShoppingListIngredientSection[];
  parentRecipe?: Recipe;
}

interface Props {
  recipes?: RecipeWithScale[];
  shoppingLists?: ShoppingListSummary[];
  defaultCreateNewList?: boolean;
  defaultListName?: string | null;
}
const props = withDefaults(defineProps<Props>(), {
  recipes: undefined,
  shoppingLists: () => [],
  defaultCreateNewList: false,
  defaultListName: null,
});

const dialog = defineModel<boolean>({ default: false });

const i18n = useI18n();
const auth = useMealieAuth();
const api = useUserApi();
const preferences = useShoppingListPreferences();
const { store: allLabels } = useLabelStore();
const { store: allUnits } = useUnitStore();
const { store: allFoods } = useFoodStore();
const ready = ref(false);
const shoppingListSelectionLoading = ref(false);

// Capture values at initialization to avoid reactive updates
const currentHouseholdSlug = ref("");
const filteredShoppingLists = ref<ShoppingListSummary[]>([]);
const shoppingListTarget = ref("new");
const newShoppingListName = ref("");
const pendingNewShoppingListName = ref("");
const duplicateConflictAction = ref<"append" | "overwrite" | null>(null);
const overwriteExistingList = ref(false);
const manualShoppingListItems = ref<ShoppingListItemCreate[]>([]);
const editingIngredientKey = ref("");
const editingIngredientText = ref("");

const state = reactive({
  shoppingListDialog: false,
  shoppingListIngredientDialog: false,
  shoppingListShowAllToggled: false,
});

const { shoppingListDialog, shoppingListIngredientDialog, shoppingListShowAllToggled: _shoppingListShowAllToggled } = toRefs(state);

const recipeIngredientSections = ref<ShoppingListRecipeIngredientSection[]>([]);
const selectedShoppingList = ref<ShoppingListSummary | ShoppingListOut | null>(null);
const manualListItem = ref<ShoppingListItemCreate>(manualListItemFactory());

const defaultShoppingListName = computed(() => {
  return props.defaultListName?.trim()
    || props.recipes?.[0]?.name?.trim()
    || i18n.t("shopping-list.shopping-list");
});

const normalizedNewShoppingListName = computed(() => newShoppingListName.value.trim() || defaultShoppingListName.value);

const duplicateShoppingList = computed(() => {
  if (shoppingListTarget.value !== "new") {
    return null;
  }

  return findShoppingListByName(normalizedNewShoppingListName.value);
});

const selectedShoppingListFromTarget = computed(() => {
  if (shoppingListTarget.value === "new") {
    return duplicateShoppingList.value;
  }

  return filteredShoppingLists.value.find(list => list.id === shoppingListTarget.value)
    || props.shoppingLists.find(list => list.id === shoppingListTarget.value)
    || null;
});

const selectedShoppingListName = computed(() => {
  return selectedShoppingList.value?.name
    || selectedShoppingListFromTarget.value?.name
    || pendingNewShoppingListName.value
    || normalizedNewShoppingListName.value;
});

const hasSelectedRecipeIngredients = computed(() => {
  return recipeIngredientSections.value.some(recipeSection =>
    recipeSection.ingredientSections.some(ingredientSection =>
      ingredientSection.ingredients.some(ingredient => ingredient.checked),
    ),
  );
});

const manualListItemHasData = computed(() => {
  return Boolean(manualListItem.value.foodId || manualListItem.value.food?.name || manualListItem.value.note?.trim());
});

const hasValidShoppingListSelection = computed(() => {
  if (shoppingListTarget.value === "new") {
    if (!normalizedNewShoppingListName.value.trim()) {
      return false;
    }

    return duplicateShoppingList.value ? Boolean(duplicateConflictAction.value) : true;
  }

  return Boolean(selectedShoppingListFromTarget.value);
});

const canSubmitShoppingListDialog = computed(() => {
  return hasValidShoppingListSelection.value
    && (hasSelectedRecipeIngredients.value || manualShoppingListItems.value.length > 0 || manualListItemHasData.value);
});

watch([dialog, () => preferences.value.viewAllLists], () => {
  if (dialog.value) {
    void initializeShoppingListDialog();
  }
  else if (!dialog.value) {
    initState();
  }
});

watch(newShoppingListName, () => {
  duplicateConflictAction.value = null;
});

function normalizeShoppingListName(name?: string | null) {
  return (name || "").trim().toLocaleLowerCase();
}

function findShoppingListByName(name: string) {
  const normalizedName = normalizeShoppingListName(name);
  if (!normalizedName) {
    return null;
  }

  return props.shoppingLists.find(list => normalizeShoppingListName(list.name) === normalizedName) || null;
}

function manualListItemFactory(): ShoppingListItemCreate {
  return {
    id: uuid4(),
    shoppingListId: selectedShoppingList.value?.id || "",
    checked: false,
    position: manualShoppingListItems.value.length,
    quantity: 0,
    note: "",
    labelId: undefined,
    unitId: undefined,
    foodId: undefined,
  };
}

function buildIngredientSections(ingredients: ShoppingListIngredient[]): ShoppingListIngredientSection[] {
  let currentTitle = "";
  const onHandIngs: ShoppingListIngredient[] = [];
  const sections = ingredients.reduce((acc, ing) => {
    if (ing.ingredient.title) {
      currentTitle = ing.ingredient.title;
    }

    if (!acc.length || currentTitle !== acc[acc.length - 1].sectionName) {
      if (acc.length) {
        acc[acc.length - 1].ingredients.push(...onHandIngs);
        onHandIngs.length = 0;
      }
      acc.push({ sectionName: currentTitle, ingredients: [] });
    }

    const householdsWithFood = ing.ingredient?.food?.householdsWithIngredientFood || [];
    if (householdsWithFood.includes(currentHouseholdSlug.value)) {
      onHandIngs.push(ing);
      return acc;
    }

    acc[acc.length - 1].ingredients.push(ing);
    return acc;
  }, [] as ShoppingListIngredientSection[]);

  if (sections.length) {
    sections[sections.length - 1].ingredients.push(...onHandIngs);
  }
  return sections;
}

async function consolidateRecipesIntoSections(recipes: RecipeWithScale[]) {
  const recipeSectionMap = new Map<string, ShoppingListRecipeIngredientSection>();

  function addSubRecipeToMap(ing: RecipeIngredient, parentQuantity: number, parentScale: number, parentRecipe: Recipe) {
    const ref = ing.referencedRecipe!;
    const key = ref.id || ref.slug || "";
    const ownIngs: ShoppingListIngredient[] = [];
    const subRefIngs: RecipeIngredient[] = [];

    for (const subIng of ref.recipeIngredient ?? []) {
      if (subIng.referencedRecipe) {
        subRefIngs.push(subIng);
      }
      else {
        const householdsWithFood = subIng.food?.householdsWithIngredientFood || [];
        ownIngs.push({
          checked: !householdsWithFood.includes(currentHouseholdSlug.value),
          ingredient: subIng,
        });
      }
    }

    recipeSectionMap.set(key, {
      recipeId: ref.id || "",
      recipeName: ref.name || "",
      recipeScale: parentQuantity * parentScale,
      ingredientSections: buildIngredientSections(ownIngs),
      parentRecipe,
    });

    subRefIngs.forEach(subIng => addSubRecipeToMap(subIng, (ing.quantity || 1) * (subIng.quantity || 1), parentScale, ref));
  }

  for (const recipe of recipes) {
    if (!recipe.slug) {
      continue;
    }

    if (recipeSectionMap.has(recipe.slug)) {
      const existingSection = recipeSectionMap.get(recipe.slug);
      if (existingSection) {
        existingSection.recipeScale += recipe.scale;
      }
      continue;
    }

    // Create a local copy to avoid mutating props
    let recipeData = { ...recipe };
    if (!(recipeData.id && recipeData.name && recipeData.recipeIngredient)) {
      const { data } = await api.recipes.getOne(recipeData.slug);
      if (!data?.recipeIngredient?.length) {
        continue;
      }
      recipeData = {
        ...recipeData,
        id: data.id || "",
        name: data.name || "",
        recipeIngredient: data.recipeIngredient,
      };
    }
    else if (!recipeData.recipeIngredient.length) {
      continue;
    }

    const ownIngs: ShoppingListIngredient[] = [];
    const subRefIngs: RecipeIngredient[] = [];
    recipeData.recipeIngredient.forEach((ing) => {
      if (ing.referencedRecipe) {
        subRefIngs.push(ing);
      }
      else {
        const householdsWithFood = ing.food?.householdsWithIngredientFood || [];
        ownIngs.push({
          checked: !householdsWithFood.includes(currentHouseholdSlug.value),
          ingredient: ing,
        });
      }
    });

    recipeSectionMap.set(recipe.slug, {
      recipeId: recipeData.id,
      recipeName: recipeData.name,
      recipeScale: recipeData.scale,
      ingredientSections: buildIngredientSections(ownIngs),
    });

    subRefIngs.forEach(ing => addSubRecipeToMap(ing, ing.quantity || 1, recipeData.scale, recipeData));
  }

  recipeIngredientSections.value = Array.from(recipeSectionMap.values());
}

function initState() {
  state.shoppingListDialog = false;
  state.shoppingListIngredientDialog = false;
  state.shoppingListShowAllToggled = false;
  recipeIngredientSections.value = [];
  selectedShoppingList.value = null;
  shoppingListTarget.value = "new";
  newShoppingListName.value = "";
  pendingNewShoppingListName.value = "";
  duplicateConflictAction.value = null;
  overwriteExistingList.value = false;
  manualShoppingListItems.value = [];
  manualListItem.value = manualListItemFactory();
  shoppingListSelectionLoading.value = false;
}

initState();

async function initializeShoppingListDialog() {
  if (!props.recipes?.length) {
    return;
  }

  currentHouseholdSlug.value = auth.user.value?.householdSlug || "";
  filteredShoppingLists.value = props.shoppingLists.filter(
    list => preferences.value.viewAllLists || list.userId === auth.user.value?.id,
  );

  newShoppingListName.value = defaultShoppingListName.value;
  duplicateConflictAction.value = null;
  selectedShoppingList.value = null;
  pendingNewShoppingListName.value = "";
  overwriteExistingList.value = false;

  if (props.defaultCreateNewList) {
    shoppingListTarget.value = "new";
  }
  else if (filteredShoppingLists.value.length === 1 && !state.shoppingListShowAllToggled) {
    shoppingListTarget.value = filteredShoppingLists.value[0].id;
  }
  else {
    shoppingListTarget.value = filteredShoppingLists.value[0]?.id || "new";
  }

  ready.value = false;
  await consolidateRecipesIntoSections(props.recipes);
  state.shoppingListDialog = true;
  state.shoppingListIngredientDialog = true;
  ready.value = true;
  manualListItem.value = manualListItemFactory();
}

async function createPendingShoppingList() {
  const name = pendingNewShoppingListName.value.trim() || normalizedNewShoppingListName.value;
  const { data, error } = await api.shopping.lists.createOne({ name });

  if (error || !data) {
    alert.error(i18n.t("events.something-went-wrong"));
    return null;
  }

  return data;
}

async function ensureSelectedShoppingList() {
  if (selectedShoppingList.value?.id) {
    return selectedShoppingList.value;
  }

  const createdList = await createPendingShoppingList();
  if (createdList) {
    selectedShoppingList.value = createdList;
  }

  return createdList;
}

async function prepareShoppingListSelection() {
  shoppingListSelectionLoading.value = true;

  try {
    if (shoppingListTarget.value === "new") {
      const duplicateList = duplicateShoppingList.value;
      if (duplicateList) {
        if (!duplicateConflictAction.value) {
          return false;
        }
        selectedShoppingList.value = duplicateList;
        pendingNewShoppingListName.value = "";
        overwriteExistingList.value = duplicateConflictAction.value === "overwrite";
      }
      else {
        selectedShoppingList.value = null;
        pendingNewShoppingListName.value = normalizedNewShoppingListName.value;
        overwriteExistingList.value = false;
      }

      return true;
    }

    const selectedList = selectedShoppingListFromTarget.value;

    if (selectedList) {
      selectedShoppingList.value = selectedList;
      pendingNewShoppingListName.value = "";
      overwriteExistingList.value = false;
      return true;
    }

    return false;
  }
  finally {
    shoppingListSelectionLoading.value = false;
  }
}

function setShowAllToggled() {
  state.shoppingListShowAllToggled = true;
}

function ingredientKey(recipeSectionIndex: number, ingredientSectionIndex: number, ingredientIndex: number) {
  return `${recipeSectionIndex}-${ingredientSectionIndex}-${ingredientIndex}`;
}

function isEditingIngredient(key: string) {
  return editingIngredientKey.value === key;
}

function toggleIngredientChecked(recipeSectionIndex: number, ingredientSectionIndex: number, ingredientIndex: number) {
  const ingredient = recipeIngredientSections.value[recipeSectionIndex]
    ?.ingredientSections[ingredientSectionIndex]
    ?.ingredients[ingredientIndex];

  if (ingredient) {
    ingredient.checked = !ingredient.checked;
  }
}

function ingredientEditableText(ingredient: RecipeIngredient) {
  return ingredient.note?.trim()
    || ingredient.food?.name?.trim()
    || ingredient.display?.trim()
    || ingredient.originalText?.trim()
    || "";
}

function startIngredientEdit(ingredient: RecipeIngredient, key: string) {
  editingIngredientKey.value = key;
  editingIngredientText.value = ingredientEditableText(ingredient);
}

function cancelIngredientEdit() {
  editingIngredientKey.value = "";
  editingIngredientText.value = "";
}

function saveIngredientEdit(recipeSectionIndex: number, ingredientSectionIndex: number, ingredientIndex: number) {
  const ingredient = recipeIngredientSections.value[recipeSectionIndex]
    ?.ingredientSections[ingredientSectionIndex]
    ?.ingredients[ingredientIndex]
    ?.ingredient;

  if (!ingredient) {
    cancelIngredientEdit();
    return;
  }

  const nextText = editingIngredientText.value.trim();
  ingredient.note = nextText;
  ingredient.food = null;
  ingredient.display = nextText;
  ingredient.originalText = nextText;
  cancelIngredientEdit();
}

function removeIngredient(recipeSectionIndex: number, ingredientSectionIndex: number, ingredientIndex: number) {
  const ingredientSection = recipeIngredientSections.value[recipeSectionIndex]?.ingredientSections[ingredientSectionIndex];
  if (!ingredientSection) {
    return;
  }

  ingredientSection.ingredients.splice(ingredientIndex, 1);
  if (!ingredientSection.ingredients.length) {
    recipeIngredientSections.value[recipeSectionIndex].ingredientSections.splice(ingredientSectionIndex, 1);
  }
  if (!recipeIngredientSections.value[recipeSectionIndex].ingredientSections.length) {
    recipeIngredientSections.value.splice(recipeSectionIndex, 1);
  }
  cancelIngredientEdit();
}

function bulkCheckIngredients(value = true) {
  recipeIngredientSections.value.forEach((recipeSection) => {
    recipeSection.ingredientSections.forEach((ingSection) => {
      ingSection.ingredients.forEach((ing) => {
        ing.checked = value;
      });
    });
  });
}

function resetManualListItem() {
  manualListItem.value = manualListItemFactory();
}

function addManualListItem() {
  if (!manualListItemHasData.value) {
    return;
  }

  manualShoppingListItems.value.push({
    ...manualListItem.value,
    id: manualListItem.value.id || uuid4(),
    checked: false,
    position: manualShoppingListItems.value.length,
  });
  resetManualListItem();
}

function removeManualListItem(id: string) {
  manualShoppingListItems.value = manualShoppingListItems.value.filter(item => item.id !== id);
}

function formatManualListItem(item: ShoppingListItemCreate) {
  const quantity = item.quantity ? String(item.quantity) : "";
  const unit = item.unit?.abbreviation || item.unit?.name || "";
  const food = item.food?.name || "";
  const note = item.note || "";
  const mainText = [quantity, unit, food].filter(Boolean).join(" ");

  if (mainText && note && note !== food) {
    return `${mainText} - ${note}`;
  }

  return mainText || note || i18n.t("shopping-list.add-item");
}

function manualItemToCreatePayload(item: ShoppingListItemCreate, shoppingListId: string, position: number): ShoppingListItemCreate {
  const foodId = item.foodId || item.food?.id || null;
  const unitId = item.unitId || item.unit?.id || null;
  const note = item.note || (!foodId ? item.food?.name : "") || "";

  return {
    shoppingListId,
    checked: false,
    position,
    quantity: item.quantity || 0,
    note,
    foodId,
    unitId,
    labelId: item.labelId || item.food?.labelId || null,
  };
}

async function addRecipesToList() {
  const hasShoppingListSelection = await prepareShoppingListSelection();
  if (!hasShoppingListSelection) {
    return;
  }

  if (manualListItemHasData.value) {
    addManualListItem();
  }

  const targetShoppingList = await ensureSelectedShoppingList();
  if (!targetShoppingList) {
    return;
  }

  const recipeData: ShoppingListAddRecipeParamsBulk[] = [];
  recipeIngredientSections.value.forEach((section) => {
    const ingredients: RecipeIngredient[] = [];
    section.ingredientSections.forEach((ingSection) => {
      ingSection.ingredients.forEach((ing) => {
        if (ing.checked) {
          ingredients.push(ing.ingredient);
        }
      });
    });

    if (!ingredients.length) {
      return;
    }

    recipeData.push(
      {
        recipeId: section.recipeId,
        recipeIncrementQuantity: section.recipeScale,
        recipeIngredients: ingredients,
      },
    );
  });

  if (!recipeData.length && !manualShoppingListItems.value.length) {
    return;
  }

  if (overwriteExistingList.value) {
    const { data: existingList } = await api.shopping.lists.getOne(targetShoppingList.id);
    if (existingList?.listItems?.length) {
      await api.shopping.items.deleteMany(existingList.listItems);
    }
  }

  let hasError = false;
  if (recipeData.length) {
    const { error } = await api.shopping.lists.addRecipes(targetShoppingList.id, recipeData);
    hasError = Boolean(error);
  }

  if (!hasError && manualShoppingListItems.value.length) {
    const manualItems = manualShoppingListItems.value.map((item, index) =>
      manualItemToCreatePayload(item, targetShoppingList.id, index),
    );
    const { error } = await api.shopping.items.createMany(manualItems);
    hasError = Boolean(error);
  }

  if (hasError) {
    alert.error(i18n.t("recipe.failed-to-add-recipes-to-list"));
  }
  else {
    alert.success(i18n.t("recipe.successfully-added-to-list"));
    window.dispatchEvent(new CustomEvent("mealie:organizers-updated"));
  }

  state.shoppingListDialog = false;
  state.shoppingListIngredientDialog = false;
  dialog.value = false;
}
</script>

<style scoped lang="css">
.shopping-list-target,
.shopping-list-preview {
  max-width: 760px;
}

.shopping-list-preview-scroll {
  max-height: 52vh;
  overflow-y: auto;
  padding-inline-end: 4px;
}

.shopping-ingredient-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.shopping-ingredient-row {
  border-radius: 6px;
  min-height: 40px;
}

.shopping-ingredient-row :deep(.v-list-item__prepend) {
  align-self: center;
}

.shopping-ingredient-checkbox {
  margin-inline-end: 6px;
}

.shopping-ingredient-text,
.shopping-ingredient-edit {
  min-width: 0;
  width: 100%;
}

.shopping-ingredient-actions {
  align-items: center;
  display: flex;
  gap: 2px;
  opacity: 0.7;
}

.shopping-ingredient-row:hover .shopping-ingredient-actions,
.shopping-ingredient-row:focus-within .shopping-ingredient-actions {
  opacity: 1;
}
</style>
