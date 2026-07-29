<template>
  <div v-if="value && value.length > 0">
    <BaseDialog
      v-model="aiIngredientsDialog"
      :title="$t('recipe.adjust-ingredients-with-ai')"
      :icon="$globals.icons.robot"
      width="720"
      max-width="96vw"
      can-submit
      keep-open
      :submit-text="aiIngredientPreview ? $t('recipe.apply-ai-ingredient-adjustment') : $t('recipe.create-ai-ingredient-preview')"
      :submit-disabled="aiIngredientSubmitDisabled"
      :loading="aiIngredientsLoading"
      @submit="adjustIngredientsWithAI"
      @close="resetAiIngredientDialog"
    >
      <v-card-text class="pt-4">
        <p class="mb-4">
          {{ $t("recipe.adjust-ingredients-with-ai-description") }}
        </p>
        <v-textarea
          v-model="aiIngredientRequest"
          autofocus
          auto-grow
          rows="4"
          variant="outlined"
          :label="$t('recipe.adjust-ingredients-with-ai')"
          :placeholder="$t('recipe.adjust-ingredients-with-ai-placeholder')"
          :disabled="aiIngredientsLoading"
        />
        <template v-if="aiIngredientPreview">
          <v-alert
            type="info"
            variant="tonal"
            density="compact"
            class="mb-3"
          >
            {{ $t("recipe.ai-ingredient-preview-only") }}
            <div
              v-if="aiIngredientPreview.adjustmentNote"
              class="mt-1"
            >
              {{ aiIngredientPreview.adjustmentNote }}
            </div>
          </v-alert>
          <v-list
            density="compact"
            class="ai-ingredient-preview-list mb-3"
          >
            <template
              v-for="(ingredient, index) in aiIngredientPreview.ingredients"
              :key="`ai-preview-${index}`"
            >
              <v-list-subheader v-if="ingredient.title">
                {{ ingredient.title }}
              </v-list-subheader>
              <v-list-item v-else>
                {{ parseIngredientText(ingredient, 1, false) }}
              </v-list-item>
            </template>
          </v-list>
          <v-checkbox
            v-model="applyAiIngredientPermanently"
            color="primary"
            hide-details
            :label="$t('recipe.apply-ai-ingredient-adjustment-permanently')"
          />
          <v-checkbox
            v-model="syncAiIngredientShoppingLists"
            class="ms-6"
            color="primary"
            hide-details
            :disabled="!applyAiIngredientPermanently"
            :label="$t('recipe.sync-linked-shopping-lists')"
          />
        </template>

        <v-expansion-panels
          v-if="aiIngredientHistory.length"
          class="mt-4"
          variant="accordion"
        >
          <v-expansion-panel>
            <v-expansion-panel-title>
              {{ $t("recipe.ai-ingredient-adjustment-history") }}
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-list
                density="compact"
                class="ai-ingredient-history-list"
              >
                <v-list-item
                  v-for="entry in aiIngredientHistory"
                  :key="entry.id"
                  :title="entry.request"
                  :subtitle="formatHistoryDate(entry.createdAt)"
                  @click="restoreAiIngredientHistory(entry)"
                >
                  <template #append>
                    <v-icon>{{ $globals.icons.timelineText }}</v-icon>
                  </template>
                </v-list-item>
              </v-list>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card-text>
    </BaseDialog>
    <BaseDialog
      v-model="quantityScaleDialog"
      :title="$t('recipe.scale-from-ingredient')"
      :icon="$globals.icons.edit"
      width="460"
      max-width="96vw"
      can-submit
      :submit-disabled="!validTargetQuantity"
      @submit="applyQuantityScale"
    >
      <v-card-text class="pt-4">
        <div class="text-subtitle-1 font-weight-medium mb-3">
          {{ quantityScaleIngredientName }}
        </div>
        <v-text-field
          v-model.number="targetQuantity"
          type="number"
          min="0.001"
          step="any"
          variant="outlined"
          autofocus
          :label="$t('recipe.new-ingredient-quantity')"
          :hint="$t('recipe.scale-from-ingredient-description')"
          persistent-hint
        />
      </v-card-text>
    </BaseDialog>
    <div
      v-if="!isCookMode"
      class="d-flex flex-wrap align-center justify-start ga-1"
    >
      <h2 class="mt-1 text-h5 font-weight-medium opacity-80">
        {{ $t("recipe.ingredients") }}
      </h2>
      <v-btn
        v-if="showAiIngredientAdjustment"
        size="small"
        variant="tonal"
        color="success"
        class="ms-2"
        :prepend-icon="$globals.icons.robot"
        @click="aiIngredientsDialog = true"
      >
        AI
      </v-btn>
      <v-btn
        icon
        size="small"
        variant="text"
        class="ml-2"
        :color="userExperiencePreferences.showRecipeItemImages ? 'primary' : undefined"
        :title="$t('recipe.toggle-item-images')"
        :aria-label="$t('recipe.toggle-item-images')"
        @click.stop="toggleItemImages"
      >
        <v-icon>{{ $globals.icons.fileImage }}</v-icon>
      </v-btn>
      <v-btn
        v-if="showEnsureItemImagesButton"
        icon
        size="small"
        variant="text"
        color="success"
        class="ml-1"
        :loading="itemImagesLoading"
        :title="$t('recipe.create-item-images')"
        :aria-label="$t('recipe.create-item-images')"
        @click.stop="ensureItemImages"
      >
        <v-icon>{{ $globals.icons.robot }}</v-icon>
      </v-btn>
      <AppButtonCopy
        btn-class="ml-auto"
        :copy-text="ingredientCopyText"
      />
    </div>
    <v-alert
      v-if="aiIngredientsAdjusted"
      type="success"
      variant="tonal"
      density="compact"
      class="mb-3"
    >
      <div class="d-flex flex-wrap align-center ga-2">
        <span>{{ $t("recipe.ai-ingredients-adjusted") }}</span>
        <v-spacer />
        <v-btn
          v-if="canResetAiIngredientsAdjustment"
          size="small"
          variant="text"
          :prepend-icon="$globals.icons.refresh"
          @click="$emit('resetAiIngredientsAdjustment')"
        >
          {{ $t("general.reset") }}
        </v-btn>
      </div>
    </v-alert>
    <div>
      <div
        v-for="(ingredient, index) in value"
        :key="'ingredient' + index"
      >
        <h3
          v-if="showTitleEditor[index]"
          class="mt-4 mb-0"
        >
          {{ ingredient.title }}
        </h3>
        <v-divider v-if="showTitleEditor[index]" class="my-2" />
        <v-list-item
          density="compact"
          class="pa-0"
          @click.stop="toggleChecked(index)"
        >
          <template #prepend>
            <v-checkbox
              v-model="checked[index]"
              hide-details
              class="pt-0 my-auto py-auto"
              color="secondary"
              density="comfortable"
            />
          </template>
          <v-list-item-title
            :class="{ 'recipe-completed-item': checked[index] && userExperiencePreferences.strikeCompletedRecipeItems }"
          >
            <RecipeIngredientListItem
              :ingredient="ingredient"
              :scale="scale"
              :show-image="userExperiencePreferences.showRecipeItemImages"
              :image-url="ingredientImageUrl(ingredient)"
            />
          </v-list-item-title>
          <template v-if="scalableQuantity(ingredient)" #append>
            <v-btn
              icon
              size="x-small"
              variant="text"
              :title="$t('recipe.scale-from-this-ingredient')"
              :aria-label="$t('recipe.scale-from-this-ingredient')"
              @click.stop="openQuantityScale(ingredient)"
            >
              <v-icon :icon="$globals.icons.edit" />
            </v-btn>
          </template>
        </v-list-item>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useLocalStorage } from "@vueuse/core";
import RecipeIngredientListItem from "./RecipeIngredientListItem.vue";
import { useStaticRoutes, useUserApi } from "~/composables/api";
import { useIngredientTextParser } from "~/composables/recipes";
import { recipeItemImagesEnsured, useRecipeItemImages } from "~/composables/recipes/use-recipe-item-images";
import { useLoggedInState } from "~/composables/use-logged-in-state";
import { alert } from "~/composables/use-toast";
import { useUserExperiencePreferences } from "~/composables/use-users/preferences";
import type { RecipeIngredient } from "~/lib/api/types/recipe";

interface Props {
  value?: RecipeIngredient[];
  scale?: number;
  isCookMode?: boolean;
  groupId?: string | null;
  recipeSlug?: string | null;
  itemImagesEnsured?: boolean;
  aiIngredientsAdjusted?: boolean;
  canResetAiIngredientsAdjustment?: boolean;
}
const props = withDefaults(defineProps<Props>(), {
  value: () => [],
  scale: 1,
  isCookMode: false,
  groupId: null,
  recipeSlug: null,
  itemImagesEnsured: false,
  aiIngredientsAdjusted: false,
  canResetAiIngredientsAdjustment: false,
});

const emit = defineEmits<{
  "itemImagesEnsured": [];
  "update:scale": [scale: number];
  "ingredientsAdjusted": [payload: {
    ingredients: RecipeIngredient[];
    adjustmentNote: string;
    syncShoppingLists: boolean;
  }];
  "resetAiIngredientsAdjustment": [];
}>();

const { parseIngredientText } = useIngredientTextParser();
const api = useUserApi();
const auth = useMealieAuth();
const i18n = useI18n();
const { isOwnGroup } = useLoggedInState();
const userExperiencePreferences = useUserExperiencePreferences();
const { ensureRecipeItemImages } = useRecipeItemImages();
const { itemImage } = useStaticRoutes();
const itemImagesLoading = ref(false);
const localItemImagesEnsured = ref(props.itemImagesEnsured);
const quantityScaleDialog = ref(false);
const quantityScaleIngredient = ref<RecipeIngredient | null>(null);
const targetQuantity = ref<number | null>(null);
const aiIngredientsDialog = ref(false);
const aiIngredientRequest = ref("");
const aiIngredientsLoading = ref(false);
const aiIngredientPreview = ref<{
  ingredients: RecipeIngredient[];
  adjustmentNote: string;
} | null>(null);
const applyAiIngredientPermanently = ref(false);
const syncAiIngredientShoppingLists = ref(false);

interface AiIngredientAdjustmentHistoryEntry {
  id: string;
  createdAt: string;
  request: string;
  adjustmentNote: string;
  ingredients: RecipeIngredient[];
}

const aiIngredientHistoryStorage = useLocalStorage<Record<string, AiIngredientAdjustmentHistoryEntry[]>>(
  "mealie-ai-ingredient-adjustment-history-v1",
  {},
  { deep: true },
);
const aiIngredientHistoryKey = computed(() => {
  return `${auth.user.value?.id || "anonymous"}:${props.recipeSlug || "unknown"}`;
});
const aiIngredientHistory = computed(() => {
  return aiIngredientHistoryStorage.value[aiIngredientHistoryKey.value] || [];
});
const aiIngredientSubmitDisabled = computed(() => {
  if (aiIngredientsLoading.value) return true;
  if (!aiIngredientPreview.value) return aiIngredientRequest.value.trim().length < 2;
  return !applyAiIngredientPermanently.value;
});

const validTargetQuantity = computed(() => Number.isFinite(Number(targetQuantity.value)) && Number(targetQuantity.value) > 0);
const quantityScaleIngredientName = computed(() => {
  const ingredient = quantityScaleIngredient.value;
  return ingredient?.food?.name || ingredient?.display || ingredient?.note || "";
});

function validateTitle(title?: string | null) {
  return !(title === undefined || title === "" || title === null);
}

const checked = ref(props.value.map(() => false));
const showTitleEditor = computed(() => props.value.map(x => validateTitle(x.title)));
const showEnsureItemImagesButton = computed(() => {
  return !props.isCookMode && !!props.recipeSlug && !localItemImagesEnsured.value;
});
const showAiIngredientAdjustment = computed(() => {
  return !props.isCookMode
    && isOwnGroup.value
    && !!props.recipeSlug
    && props.value.some(ingredient => !ingredient.title || ingredient.display || ingredient.note || ingredient.food);
});

watch(
  () => props.itemImagesEnsured,
  (value) => {
    localItemImagesEnsured.value = recipeItemImagesEnsured({ itemImagesEnsured: value });
  },
);

watch(aiIngredientRequest, () => {
  aiIngredientPreview.value = null;
  applyAiIngredientPermanently.value = false;
  syncAiIngredientShoppingLists.value = false;
});

watch(applyAiIngredientPermanently, (enabled) => {
  if (!enabled) syncAiIngredientShoppingLists.value = false;
});

const ingredientCopyText = computed(() => {
  const components: string[] = [];
  props.value.forEach((ingredient) => {
    if (ingredient.title) {
      if (components.length) {
        components.push("");
      }

      components.push(`[${ingredient.title}]`);
    }

    components.push(parseIngredientText(ingredient, props.scale, false));
  });

  return components.join("\n");
});

function toggleItemImages() {
  userExperiencePreferences.value.showRecipeItemImages = !userExperiencePreferences.value.showRecipeItemImages;
}

async function ensureItemImages() {
  if (!props.recipeSlug || itemImagesLoading.value) {
    return;
  }

  itemImagesLoading.value = true;
  try {
    const result = await ensureRecipeItemImages(props.recipeSlug);
    if (result) {
      localItemImagesEnsured.value = true;
      emit("itemImagesEnsured");
    }
  }
  finally {
    itemImagesLoading.value = false;
  }
}

function ingredientImageName(ingredient: RecipeIngredient) {
  if (ingredient.title) {
    return "";
  }

  return ingredient.food?.name || ingredient.display || ingredient.note || "";
}

function ingredientImageUrl(ingredient: RecipeIngredient) {
  return itemImage(props.groupId, "food", ingredientImageName(ingredient));
}

function toggleChecked(index: number) {
  // TODO Find a better way to do this - $set is not available, and
  // direct array modifications are not propagated for some reason
  checked.value.splice(index, 1, !checked.value[index]);
}

function scalableQuantity(ingredient: RecipeIngredient) {
  const quantity = Number(ingredient.quantity);
  return Number.isFinite(quantity) && quantity > 0 && !ingredient.title;
}

function openQuantityScale(ingredient: RecipeIngredient) {
  if (!scalableQuantity(ingredient)) {
    return;
  }

  quantityScaleIngredient.value = ingredient;
  targetQuantity.value = Number(ingredient.quantity) * props.scale;
  quantityScaleDialog.value = true;
}

function applyQuantityScale() {
  const baseQuantity = Number(quantityScaleIngredient.value?.quantity);
  const desiredQuantity = Number(targetQuantity.value);
  if (!Number.isFinite(baseQuantity) || baseQuantity <= 0 || !Number.isFinite(desiredQuantity) || desiredQuantity <= 0) {
    return;
  }

  emit("update:scale", desiredQuantity / baseQuantity);
  quantityScaleDialog.value = false;
}

async function adjustIngredientsWithAI() {
  const request = aiIngredientRequest.value.trim();
  if (!props.recipeSlug || aiIngredientsLoading.value) {
    return;
  }

  if (aiIngredientPreview.value) {
    if (!applyAiIngredientPermanently.value) return;
    emit("ingredientsAdjusted", {
      ingredients: aiIngredientPreview.value.ingredients,
      adjustmentNote: aiIngredientPreview.value.adjustmentNote,
      syncShoppingLists: syncAiIngredientShoppingLists.value,
    });
    aiIngredientsDialog.value = false;
    return;
  }

  if (request.length < 2) return;
  aiIngredientsLoading.value = true;
  try {
    const { data, error } = await api.recipes.adjustIngredientsWithAI(props.recipeSlug, request);
    if (error || !data?.ingredients?.length) {
      alert.error(i18n.t("events.something-went-wrong"));
      return;
    }

    aiIngredientPreview.value = {
      ingredients: data.ingredients,
      adjustmentNote: data.adjustmentNote || "",
    };
    saveAiIngredientHistory(request, aiIngredientPreview.value);
  }
  finally {
    aiIngredientsLoading.value = false;
  }
}

function saveAiIngredientHistory(
  request: string,
  preview: { ingredients: RecipeIngredient[]; adjustmentNote: string },
) {
  const entry: AiIngredientAdjustmentHistoryEntry = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    createdAt: new Date().toISOString(),
    request,
    adjustmentNote: preview.adjustmentNote,
    ingredients: JSON.parse(JSON.stringify(preview.ingredients)) as RecipeIngredient[],
  };
  const nextStorage = {
    ...aiIngredientHistoryStorage.value,
    [aiIngredientHistoryKey.value]: [
      entry,
      ...aiIngredientHistory.value,
    ].slice(0, 20),
  };
  const keys = Object.keys(nextStorage);
  if (keys.length > 100) {
    const staleKeys = new Set(
      keys
        .sort((a, b) => {
          const aDate = nextStorage[a]?.[0]?.createdAt || "";
          const bDate = nextStorage[b]?.[0]?.createdAt || "";
          return aDate.localeCompare(bDate);
        })
        .slice(0, keys.length - 100),
    );
    aiIngredientHistoryStorage.value = Object.fromEntries(
      Object.entries(nextStorage).filter(([key]) => !staleKeys.has(key)),
    );
    return;
  }
  aiIngredientHistoryStorage.value = nextStorage;
}

async function restoreAiIngredientHistory(entry: AiIngredientAdjustmentHistoryEntry) {
  aiIngredientRequest.value = entry.request;
  await nextTick();
  aiIngredientPreview.value = {
    ingredients: JSON.parse(JSON.stringify(entry.ingredients)) as RecipeIngredient[],
    adjustmentNote: entry.adjustmentNote,
  };
}

function formatHistoryDate(value: string) {
  return new Intl.DateTimeFormat(i18n.locale.value, {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function resetAiIngredientDialog() {
  aiIngredientRequest.value = "";
  aiIngredientPreview.value = null;
  applyAiIngredientPermanently.value = false;
  syncAiIngredientShoppingLists.value = false;
}
</script>

<style>
.dense-markdown p {
  margin: auto !important;
}

.recipe-completed-item,
.recipe-completed-item * {
  text-decoration: line-through;
}

.ai-ingredient-preview-list,
.ai-ingredient-history-list {
  max-height: 260px;
  overflow-y: auto;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
