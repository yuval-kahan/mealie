<template>
  <div
    v-if="recipe.image && !hideImage"
    class="recipe-page-hero d-print-none"
  >
    <v-img
      :key="imageKey"
      :src="recipeImageUrl"
      :alt="recipe.name"
      class="recipe-page-hero__image"
      cover
      @error="hideImage = true"
    />
  </div>
</template>

<script setup lang="ts">
import { useStaticRoutes } from "~/composables/api";
import { usePageState } from "~/composables/recipe-page/shared-state";
import type { NoUndefinedField } from "~/lib/api/types/non-generated";
import type { Recipe } from "~/lib/api/types/recipe";

const props = defineProps<{
  recipe: NoUndefinedField<Recipe>;
}>();

const display = useDisplay();
const { recipeImage, recipeSmallImage } = useStaticRoutes();
const { imageKey } = usePageState(props.recipe.slug);
const hideImage = ref(false);

const recipeImageUrl = computed(() => {
  if (typeof props.recipe.image === "string" && props.recipe.image.toLowerCase().startsWith("http")) {
    return props.recipe.image;
  }

  return display.smAndDown.value
    ? recipeSmallImage(props.recipe.id, props.recipe.image, imageKey.value)
    : recipeImage(props.recipe.id, props.recipe.image, imageKey.value);
});

watch(recipeImageUrl, () => {
  hideImage.value = false;
});
</script>

<style scoped>
.recipe-page-hero {
  width: 100%;
  overflow: hidden;
  background: rgb(var(--v-theme-surface-variant));
}

.recipe-page-hero__image {
  width: 100%;
  height: clamp(260px, 42vw, 620px);
}

@media (max-width: 600px) {
  .recipe-page-hero__image {
    height: 240px;
  }
}
</style>
