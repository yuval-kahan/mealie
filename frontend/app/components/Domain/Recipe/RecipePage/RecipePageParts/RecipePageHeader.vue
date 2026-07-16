<template>
  <div>
    <RecipePageInfoCard
      :recipe="recipe"
      :recipe-scale="recipeScale"
      :landscape="landscape"
    >
      <template #actions>
        <RecipeActionMenu
          :recipe="recipe"
          :slug="recipe.slug"
          :recipe-scale="recipeScale"
          :can-edit="canEditRecipe"
          :name="recipe.name"
          :logged-in="isOwnGroup"
          :open="isEditMode"
          :quick-editing="quickEditing"
          :recipe-id="recipe.id"
          inline
          @close="$emit('close')"
          @json="toggleEditMode()"
          @edit="setMode(PageMode.EDIT)"
          @quick-edit="$emit('quick-edit')"
          @quick-save="$emit('quick-save')"
          @quick-close="$emit('quick-close')"
          @save="$emit('save')"
          @delete="$emit('delete', $event)"
          @print="printRecipe"
          @renamed="$emit('renamed', $event)"
        />
      </template>
    </RecipePageInfoCard>
  </div>
</template>

<script setup lang="ts">
import { useLoggedInState } from "~/composables/use-logged-in-state";
import { useRecipePermissions } from "~/composables/recipes";
import RecipePageInfoCard from "~/components/Domain/Recipe/RecipePage/RecipePageParts/RecipePageInfoCard.vue";
import RecipeActionMenu from "~/components/Domain/Recipe/RecipeActionMenu.vue";
import { useStaticRoutes } from "~/composables/api";
import { useUserApi } from "~/composables/api/api-client";
import type { HouseholdSummary } from "~/lib/api/types/household";
import type { Recipe } from "~/lib/api/types/recipe";
import type { NoUndefinedField } from "~/lib/api/types/non-generated";
import { usePageState, usePageUser, PageMode } from "~/composables/recipe-page/shared-state";

interface Props {
  recipe: NoUndefinedField<Recipe>;
  recipeScale?: number;
  landscape?: boolean;
  quickEditing?: boolean;
}
const props = withDefaults(defineProps<Props>(), {
  recipeScale: 1,
  landscape: false,
  quickEditing: false,
});

defineEmits(["save", "delete", "print", "close", "renamed", "quick-edit", "quick-save", "quick-close"]);

const { recipeImage } = useStaticRoutes();
const { imageKey, setMode, toggleEditMode, isEditMode } = usePageState(props.recipe.slug);
const { user } = usePageUser();
const { isOwnGroup } = useLoggedInState();

const recipeHousehold = ref<HouseholdSummary>();
if (user) {
  const userApi = useUserApi();
  userApi.households.getOne(props.recipe.householdId).then(({ data }) => {
    recipeHousehold.value = data || undefined;
  });
}
const { canEditRecipe } = useRecipePermissions(props.recipe, recipeHousehold, user);

function printRecipe() {
  window.print();
}

const hideImage = ref(false);

const recipeImageUrl = computed(() => {
  return recipeImage(props.recipe.id, props.recipe.image, imageKey.value);
});

watch(
  () => recipeImageUrl.value,
  () => {
    hideImage.value = false;
  },
);
</script>
