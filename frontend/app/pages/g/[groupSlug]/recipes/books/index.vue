<template>
  <RecipeExplorerPage
    section="book"
    title-key="recipe.book-recipes"
    :icon="$globals.icons.book"
    group-by-book
  />
</template>

<script setup lang="ts">
import RecipeExplorerPage from "~/components/Domain/Recipe/RecipeExplorerPage/RecipeExplorerPage.vue";

const { $globals } = useNuxtApp();
</script>
