<template>
  <v-img
    v-if="imageSource && !fallBackImage"
    :height="height"
    cover
    min-height="125"
    max-height="fill-height"
    :src="imageSource"
    @click="$emit('click')"
    @load="handleImageLoad"
    @error="handleImageError"
  >
    <slot />
  </v-img>
  <div
    v-else
    class="icon-slot"
    @click="$emit('click')"
  >
    <v-icon
      color="primary"
      class="icon-position"
      :size="iconSize"
    >
      {{ $globals.icons.primary }}
    </v-icon>
    <slot />
  </div>
</template>

<script setup lang="ts">
import { useStaticRoutes } from "~/composables/api";

interface Props {
  tiny?: boolean | null;
  small?: boolean | null;
  large?: boolean | null;
  iconSize?: number | string;
  slug?: string | null;
  recipeId: string;
  imageVersion?: string | null;
  height?: number | string;
}
const props = withDefaults(defineProps<Props>(), {
  tiny: null,
  small: null,
  large: null,
  iconSize: 100,
  slug: null,
  imageVersion: null,
  height: "100%",
});

const emit = defineEmits<{
  click: [];
  imageStatus: [hasImage: boolean];
}>();

const { recipeImage, recipeSmallImage, recipeTinyImage } = useStaticRoutes();

const fallBackImage = ref(false);
const isExternalImage = computed(() => {
  return typeof props.imageVersion === "string" && props.imageVersion.toLowerCase().startsWith("http");
});
const imageSource = computed(() => {
  if (!props.imageVersion) {
    return "";
  }

  return isExternalImage.value ? props.imageVersion : getImage(props.recipeId);
});
const imageSize = computed(() => {
  if (props.tiny) return "tiny";
  if (props.small) return "small";
  if (props.large) return "large";
  return "large";
});

watch(
  () => [props.recipeId, props.imageVersion],
  () => {
    fallBackImage.value = false;
  },
);

function handleImageLoad() {
  fallBackImage.value = false;
  emit("imageStatus", true);
}

function handleImageError() {
  fallBackImage.value = true;
  emit("imageStatus", false);
}

function getImage(recipeId: string) {
  switch (imageSize.value) {
    case "tiny":
      return recipeTinyImage(recipeId, props.imageVersion);
    case "small":
      return recipeSmallImage(recipeId, props.imageVersion);
    case "large":
      return recipeImage(recipeId, props.imageVersion);
  }
}
</script>

<style scoped>
.icon-slot {
  position: relative;
}

.icon-slot > div {
  top: 0;
  position: absolute;
  z-index: 1;
}

.icon-position {
  opacity: 0.8;
  display: flex !important;
  position: relative;
  margin-left: auto !important;
  margin-right: auto !important;
}
</style>
