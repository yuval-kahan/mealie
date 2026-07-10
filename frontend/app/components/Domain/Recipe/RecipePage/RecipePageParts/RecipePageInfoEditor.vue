<template>
  <div class="recipe-info-editor py-4">
    <section class="recipe-info-editor__section">
      <div class="text-subtitle-1 font-weight-medium mb-3">
        {{ $t("recipe.manual-basic-details") }}
      </div>
      <div class="recipe-info-editor__grid recipe-info-editor__grid--details">
        <v-text-field
          v-model="recipe.name"
          class="recipe-info-editor__wide"
          :label="$t('recipe.recipe-name')"
          :rules="[validators.required]"
          density="comfortable"
          variant="outlined"
          autofocus
        />
        <v-number-input
          :model-value="recipe.recipeServings"
          :min="0"
          :precision="null"
          density="comfortable"
          :label="$t('recipe.servings')"
          variant="outlined"
          control-variant="stacked"
          @update:model-value="recipe.recipeServings = $event"
        />
        <v-number-input
          :model-value="recipe.recipeYieldQuantity"
          :min="0"
          :precision="null"
          density="comfortable"
          :label="$t('recipe.yield')"
          variant="outlined"
          control-variant="stacked"
          @update:model-value="recipe.recipeYieldQuantity = $event"
        />
        <v-text-field
          v-model="recipe.recipeYield"
          density="comfortable"
          :label="$t('recipe.yield-text')"
          variant="outlined"
        />
      </div>
    </section>

    <section class="recipe-info-editor__section">
      <div class="text-subtitle-1 font-weight-medium mb-3">
        {{ $t("recipe.manual-time-details") }}
      </div>
      <div class="recipe-info-editor__grid recipe-info-editor__grid--times">
        <v-text-field v-model="recipe.totalTime" :label="$t('recipe.total-time')" density="comfortable" variant="outlined" />
        <v-text-field v-model="recipe.prepTime" :label="$t('recipe.prep-time')" density="comfortable" variant="outlined" />
        <v-text-field v-model="recipe.performTime" :label="$t('recipe.perform-time')" density="comfortable" variant="outlined" />
      </div>
    </section>

    <section class="recipe-info-editor__section">
      <v-textarea
        v-model="recipe.description"
        auto-grow
        min-height="120"
        :label="$t('recipe.description')"
        density="comfortable"
        variant="outlined"
      />
      <div class="recipe-info-editor__grid recipe-info-editor__grid--source">
        <v-text-field v-model="recipe.createdBy" density="comfortable" :label="$t('recipe.created-by')" variant="outlined" />
        <v-text-field v-model="recipe.source" density="comfortable" :label="$t('recipe.source')" variant="outlined" />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { validators } from "~/composables/use-validators";
import type { NoUndefinedField } from "~/lib/api/types/non-generated";
import type { Recipe } from "~/lib/api/types/recipe";

const recipe = defineModel<NoUndefinedField<Recipe>>({ required: true });
</script>

<style scoped>
.recipe-info-editor__section {
  padding-block: 16px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.recipe-info-editor__grid {
  display: grid;
  gap: 12px;
}

.recipe-info-editor__grid--details {
  grid-template-columns: minmax(120px, 0.7fr) minmax(120px, 0.7fr) minmax(220px, 1.6fr);
}

.recipe-info-editor__wide {
  grid-column: 1 / -1;
}

.recipe-info-editor__grid--times {
  grid-template-columns: repeat(3, minmax(160px, 1fr));
}

.recipe-info-editor__grid--source {
  grid-template-columns: repeat(2, minmax(220px, 1fr));
}

@media (max-width: 720px) {
  .recipe-info-editor__grid--details,
  .recipe-info-editor__grid--times,
  .recipe-info-editor__grid--source {
    grid-template-columns: 1fr;
  }
}
</style>
