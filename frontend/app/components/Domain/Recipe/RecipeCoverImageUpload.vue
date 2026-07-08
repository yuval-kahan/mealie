<template>
  <div class="d-flex align-center flex-wrap ga-3">
    <AppButtonUpload
      :post="false"
      :text="$t('recipe.upload-recipe-image')"
      :icon="$globals.icons.fileImage"
      accept="image/*"
      :disabled="disabled"
      @uploaded="setImageFile"
    />
    <v-chip
      v-if="model"
      closable
      color="primary"
      variant="tonal"
      @click:close="model = null"
    >
      {{ model.name }}
    </v-chip>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  disabled?: boolean;
}>();

const model = defineModel<File | null>({ default: null });

function setImageFile(file: File | File[] | unknown | null) {
  if (file instanceof File) {
    model.value = file;
  }
}
</script>
