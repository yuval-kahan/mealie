<template>
  <div
    v-if="totalItems"
    class="base-list-pagination"
  >
    <v-select
      :model-value="itemsPerPage"
      :items="pageSizeOptions"
      :label="$t('general.items-per-page')"
      density="compact"
      variant="outlined"
      hide-details
      class="base-list-pagination__size"
      @update:model-value="updateItemsPerPage"
    />
    <v-pagination
      v-if="pageCount > 1"
      :model-value="page"
      :length="pageCount"
      :total-visible="$vuetify.display.xs ? 4 : 7"
      density="comfortable"
      class="base-list-pagination__pages"
      @update:model-value="$emit('update:page', $event)"
    />
  </div>
</template>

<script setup lang="ts">
import { LIST_PAGE_SIZE_OPTIONS } from "~/composables/use-list-pagination";

interface Props {
  page: number;
  itemsPerPage: number;
  totalItems: number;
  pageSizeOptions?: number[];
}

const props = withDefaults(defineProps<Props>(), {
  pageSizeOptions: () => [...LIST_PAGE_SIZE_OPTIONS],
});

const emit = defineEmits<{
  "update:page": [value: number];
  "update:itemsPerPage": [value: number];
}>();

const pageCount = computed(() => Math.max(1, Math.ceil(props.totalItems / props.itemsPerPage)));

function updateItemsPerPage(value: number | string | null) {
  const parsed = Number(value);
  if (Number.isFinite(parsed) && parsed > 0) {
    emit("update:itemsPerPage", parsed);
  }
}
</script>

<style scoped>
.base-list-pagination {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: space-between;
  margin-block: 20px;
  min-height: 48px;
}

.base-list-pagination__size {
  flex: 0 0 170px;
  max-width: 170px;
}

.base-list-pagination__pages {
  flex: 1 1 auto;
  min-width: 0;
}

@media (max-width: 600px) {
  .base-list-pagination {
    justify-content: center;
  }

  .base-list-pagination__size {
    flex-basis: 150px;
    max-width: 150px;
  }

  .base-list-pagination__pages {
    flex-basis: 100%;
  }
}
</style>
