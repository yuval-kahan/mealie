<template>
  <div class="base-list-sort-controls">
    <v-select
      :model-value="sortBy"
      :items="options"
      item-title="title"
      item-value="value"
      :label="$t('general.sort')"
      density="compact"
      variant="outlined"
      hide-details
      @update:model-value="$emit('update:sortBy', $event)"
    />
    <v-select
      :model-value="sortDirection"
      :items="directionOptions"
      item-title="title"
      item-value="value"
      :label="$t('catalog.sort-direction')"
      density="compact"
      variant="outlined"
      hide-details
      @update:model-value="$emit('update:sortDirection', $event)"
    />
  </div>
</template>

<script setup lang="ts">
import type { ListSortDirection } from "~/composables/use-list-sort";

interface SortOption {
  title: string;
  value: string;
}

defineProps<{
  sortBy: string;
  sortDirection: ListSortDirection;
  options: SortOption[];
}>();

defineEmits<{
  "update:sortBy": [value: string];
  "update:sortDirection": [value: ListSortDirection];
}>();

const i18n = useI18n();
const directionOptions = computed(() => [
  { title: i18n.t("general.sort-ascending"), value: "asc" },
  { title: i18n.t("general.sort-descending"), value: "desc" },
]);
</script>

<style scoped>
.base-list-sort-controls {
  display: grid;
  gap: 10px;
  grid-template-columns: minmax(150px, 1fr) minmax(150px, 1fr);
  min-width: min(100%, 320px);
}

@media (max-width: 600px) {
  .base-list-sort-controls {
    grid-template-columns: 1fr;
    width: 100%;
  }
}
</style>
