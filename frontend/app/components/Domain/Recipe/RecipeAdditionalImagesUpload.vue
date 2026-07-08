<template>
  <div class="d-flex align-center flex-wrap ga-3">
    <AppButtonUpload
      :post="false"
      :text="$t('recipe.upload-additional-recipe-images')"
      :icon="$globals.icons.fileImage"
      accept="image/*"
      multiple
      :disabled="disabled"
      @uploaded="addImageFiles"
    />
    <v-chip
      v-for="(file, index) in model"
      :key="`${file.name}-${file.size}-${index}`"
      closable
      color="primary"
      variant="tonal"
      @click:close="removeImageFile(index)"
    >
      {{ file.name }}
    </v-chip>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  disabled?: boolean;
}>();

const model = defineModel<File[]>({ default: () => [] });

function addImageFiles(files: File | File[] | unknown | null) {
  if (files instanceof File) {
    model.value = [...model.value, files];
    return;
  }

  if (Array.isArray(files)) {
    model.value = [
      ...model.value,
      ...files.filter((file): file is File => file instanceof File),
    ];
  }
}

function removeImageFile(index: number) {
  model.value = model.value.filter((_, currentIndex) => currentIndex !== index);
}
</script>
