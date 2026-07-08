<template>
  <v-row>
    <v-col
      cols="12"
      md="6"
    >
      <v-combobox
        v-model="categories"
        :items="categoryItems"
        :label="$t('category.categories')"
        variant="outlined"
        density="comfortable"
        multiple
        chips
        clearable
      />
    </v-col>
    <v-col
      cols="12"
      md="6"
    >
      <v-combobox
        v-model="tags"
        :items="tagItems"
        :label="$t('tag.tags')"
        variant="outlined"
        density="comfortable"
        multiple
        chips
        clearable
      />
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
defineProps<{
  categoryItems: string[];
  tagItems: string[];
}>();

const categories = defineModel<string[]>("categories", { required: true });
const tags = defineModel<string[]>("tags", { required: true });
</script>
