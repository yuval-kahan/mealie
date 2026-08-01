<template>
  <RecipeExplorerPage
    section="sauce"
    title-key="recipe.sauces"
    :icon="$globals.icons.potSteam"
  />
</template>

<script setup lang="ts">
import RecipeExplorerPage from "~/components/Domain/Recipe/RecipeExplorerPage/RecipeExplorerPage.vue";

const { $globals } = useNuxtApp();
</script>
