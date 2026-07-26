<template>
  <div>
    <RecipeIngredients
      :value="recipe.recipeIngredient"
      :scale="scale"
      :is-cook-mode="isCookMode"
      :group-id="recipe.groupId"
      :recipe-slug="recipe.slug"
      :item-images-ensured="recipeItemImagesEnsured(recipe.extras)"
      :ai-ingredients-adjusted="Boolean(recipe.extras?.aiIngredientAdjustment)"
      :can-reset-ai-ingredients-adjustment="Boolean(aiIngredientAdjustmentOriginal)"
      @item-images-ensured="markItemImagesEnsured"
      @update:scale="$emit('update:scale', $event)"
      @ingredients-adjusted="applyAiIngredientAdjustment"
      @reset-ai-ingredients-adjustment="resetAiIngredientAdjustment"
    />
    <div v-if="!isEditMode && recipe.tools && recipe.tools.length > 0">
      <h2 class="mt-4 text-h5 font-weight-medium opacity-80">
        {{ $t('tool.required-tools') }}
      </h2>
      <v-list density="compact">
        <v-list-item
          v-for="(tool, index) in recipe.tools"
          :key="index"
          density="compact"
          class="px-1"
        >
          <template #prepend>
            <v-checkbox
              v-model="recipeTools[index].onHand"
              hide-details
              class="pt-0 py-auto"
              color="secondary"
              density="compact"
              @change="updateTool(index)"
            />
          </template>
          <v-list-item-title class="d-flex align-center ga-2">
            <ItemImageThumb
              v-if="userExperiencePreferences.showRecipeItemImages"
              :src="itemImage(recipe.groupId, 'tool', tool.name)"
              :alt="tool.name"
            />
            <span>{{ tool.name }}</span>
          </v-list-item-title>
        </v-list-item>
      </v-list>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useLoggedInState } from "~/composables/use-logged-in-state";
import { useUserApi } from "~/composables/api/api-client";
import { useStaticRoutes } from "~/composables/api";
import { usePageState, usePageUser } from "~/composables/recipe-page/shared-state";
import { useToolStore } from "~/composables/store";
import { useUserExperiencePreferences } from "~/composables/use-users/preferences";
import { markRecipeItemImagesEnsured, recipeItemImagesEnsured } from "~/composables/recipes/use-recipe-item-images";
import type { NoUndefinedField } from "~/lib/api/types/non-generated";
import type { Recipe, RecipeIngredient, RecipeTool } from "~/lib/api/types/recipe";
import ItemImageThumb from "~/components/Domain/ItemImages/ItemImageThumb.vue";
import RecipeIngredients from "~/components/Domain/Recipe/RecipeIngredients.vue";
import { alert } from "~/composables/use-toast";

interface RecipeToolWithOnHand extends RecipeTool {
  onHand: boolean;
}

interface Props {
  recipe: NoUndefinedField<Recipe>;
  scale: number;
  isCookMode?: boolean;
}
const props = withDefaults(defineProps<Props>(), {
  isCookMode: false,
});

const emit = defineEmits<{
  "update:scale": [scale: number];
}>();

const { isOwnGroup } = useLoggedInState();
const api = useUserApi();
const i18n = useI18n();

const toolStore = isOwnGroup.value ? useToolStore() : null;
const { user } = usePageUser();
const { isEditMode } = usePageState(props.recipe.slug);
const userExperiencePreferences = useUserExperiencePreferences();
const { itemImage } = useStaticRoutes();

const recipeTools = ref<RecipeToolWithOnHand[]>([]);
const aiIngredientAdjustmentOriginal = ref<RecipeIngredient[] | null>(null);
watch(() => props.recipe.tools, () => {
  if (!(user.householdSlug && toolStore)) {
    recipeTools.value = props.recipe.tools.map(tool => ({ ...tool, onHand: false }) as RecipeToolWithOnHand);
  }
  else {
    recipeTools.value = props.recipe.tools.map((tool) => {
      const onHand = tool.householdsWithTool?.includes(user.householdSlug) || false;
      return { ...tool, onHand } as RecipeToolWithOnHand;
    });
  }
}, { immediate: true });

function updateTool(index: number) {
  if (user.id && user.householdSlug && toolStore) {
    const tool = recipeTools.value[index];
    if (tool.onHand && !tool.householdsWithTool?.includes(user.householdSlug)) {
      if (!tool.householdsWithTool) {
        tool.householdsWithTool = [user.householdSlug];
      }
      else {
        tool.householdsWithTool.push(user.householdSlug);
      }
    }
    else if (!tool.onHand && tool.householdsWithTool?.includes(user.householdSlug)) {
      tool.householdsWithTool = tool.householdsWithTool.filter(household => household !== user.householdSlug);
    }

    toolStore.actions.updateOne(tool);
  }
  else {
    console.log("no user, skipping server update");
  }
}

function markItemImagesEnsured() {
  markRecipeItemImagesEnsured(props.recipe);
}

function cloneIngredients(ingredients: RecipeIngredient[]) {
  return JSON.parse(JSON.stringify(ingredients)) as RecipeIngredient[];
}

async function persistRecipeIngredients(
  ingredients: RecipeIngredient[],
  extras: Record<string, unknown>,
) {
  const previousIngredients = cloneIngredients(props.recipe.recipeIngredient || []);
  const previousExtras = { ...(props.recipe.extras || {}) };
  // The recipe page deliberately shares one editable recipe model between its child sections.
  // eslint-disable-next-line vue/no-mutating-props
  props.recipe.recipeIngredient = ingredients;
  // eslint-disable-next-line vue/no-mutating-props
  props.recipe.extras = extras;

  const { data, error } = await api.recipes.updateOne(props.recipe.slug, props.recipe);
  if (error || !data) {
    // eslint-disable-next-line vue/no-mutating-props
    props.recipe.recipeIngredient = previousIngredients;
    // eslint-disable-next-line vue/no-mutating-props
    props.recipe.extras = previousExtras;
    alert.error(i18n.t("events.something-went-wrong"));
    return false;
  }

  // eslint-disable-next-line vue/no-mutating-props
  props.recipe.recipeIngredient = data.recipeIngredient || ingredients;
  // eslint-disable-next-line vue/no-mutating-props
  props.recipe.extras = data.extras || extras;
  return true;
}

async function applyAiIngredientAdjustment(payload: { ingredients: RecipeIngredient[]; adjustmentNote: string }) {
  if (!aiIngredientAdjustmentOriginal.value) {
    aiIngredientAdjustmentOriginal.value = cloneIngredients(props.recipe.recipeIngredient || []);
  }

  const saved = await persistRecipeIngredients(payload.ingredients, {
    ...(props.recipe.extras || {}),
    aiIngredientAdjustment: {
      appliedAt: new Date().toISOString(),
      note: payload.adjustmentNote,
    },
  });
  if (!saved) {
    aiIngredientAdjustmentOriginal.value = null;
    return;
  }
  emit("update:scale", 1);
}

async function resetAiIngredientAdjustment() {
  if (!aiIngredientAdjustmentOriginal.value) {
    return;
  }

  const extras = { ...(props.recipe.extras || {}) };
  delete extras.aiIngredientAdjustment;
  const original = cloneIngredients(aiIngredientAdjustmentOriginal.value);
  if (!(await persistRecipeIngredients(original, extras))) {
    return;
  }
  aiIngredientAdjustmentOriginal.value = null;
  emit("update:scale", 1);
}
</script>
