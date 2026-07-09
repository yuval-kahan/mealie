<template>
  <div class="d-flex align-center flex-wrap ga-3">
    <AppButtonUpload
      :post="false"
      :text="$t('recipe.upload-video')"
      :icon="$globals.icons.play"
      accept="video/*,.mp4,.webm,.mov,.m4v,.ogv,.avi,.mkv,.flv,.f4v,.wmv,.mpg,.mpeg,.mpe,.m1v,.m2v,.3gp,.3g2,.ts,.mts,.m2ts"
      :disabled="disabled"
      @uploaded="setVideoFile"
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

function setVideoFile(file: File | File[] | unknown | null) {
  if (file instanceof File) {
    model.value = file;
  }
}
</script>
