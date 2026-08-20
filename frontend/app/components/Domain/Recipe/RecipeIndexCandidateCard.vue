<template>
  <v-card
    class="recipe-index-candidate-card"
    border
    variant="tonal"
    aria-disabled="true"
  >
    <v-card-item>
      <template #prepend>
        <v-avatar
          color="primary"
          variant="tonal"
          size="38"
        >
          <v-icon>{{ $globals.icons.formatListBulleted }}</v-icon>
        </v-avatar>
      </template>
      <v-card-title class="text-body-1 font-weight-bold text-wrap">
        {{ candidate.title }}
      </v-card-title>
      <v-card-subtitle v-if="candidate.chapter || candidate.pageStart || candidate.pageEnd || candidate.sourceUrl">
        <span v-if="candidate.chapter">{{ candidate.chapter }} · </span>
        <span v-if="candidate.pageStart || candidate.pageEnd">
          {{ $t("cookbook.pages") }} {{ candidate.pageStart || candidate.pageEnd }}<template v-if="candidate.pageEnd && candidate.pageStart">–{{ candidate.pageEnd }}</template>
        </span>
      </v-card-subtitle>
    </v-card-item>
    <v-card-text class="pt-0">
      <v-chip
        size="small"
        color="primary"
        variant="tonal"
      >
        {{ $t("cookbook.recipe-index-only") }}
      </v-chip>
      <v-chip
        v-if="candidate.source === 'internet'"
        size="small"
        color="info"
        variant="tonal"
      >
        {{ $t("cookbook.recipe-catalog-internet-entry") }}
      </v-chip>
      <a
        v-if="candidate.sourceUrl"
        :href="candidate.sourceUrl"
        target="_blank"
        rel="noopener noreferrer"
        class="recipe-index-candidate-card__source text-primary d-block mt-2"
      >
        {{ candidate.sourceUrl }}
      </a>
      <p v-if="candidate.reason" class="recipe-index-candidate-card__reason mb-0 mt-2">
        {{ candidate.reason }}
      </p>
      <p class="recipe-index-candidate-card__hint mb-0 mt-2">
        {{ $t("cookbook.recipe-index-not-imported-hint") }}
      </p>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import type { UploadedBookRecipeCandidate } from "~/lib/api/types/uploaded-book";

defineProps<{
  candidate: UploadedBookRecipeCandidate;
}>();

const { $globals } = useNuxtApp();
</script>

<style scoped>
.recipe-index-candidate-card {
  height: 100%;
  min-height: 156px;
  cursor: default;
  opacity: 0.9;
}

.recipe-index-candidate-card__reason,
.recipe-index-candidate-card__hint {
  color: rgba(var(--v-theme-on-surface), 0.68);
  font-size: 0.82rem;
  overflow-wrap: anywhere;
}
</style>
