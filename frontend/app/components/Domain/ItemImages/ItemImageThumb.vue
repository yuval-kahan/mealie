<template>
  <span
    v-if="visible && src"
    class="item-image-thumb"
    :title="alt"
  >
    <img
      :src="src"
      :alt="alt"
      loading="lazy"
      decoding="async"
      @error="visible = false"
    >
  </span>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  src?: string;
  alt?: string;
}>(), {
  src: "",
  alt: "",
});

const visible = ref(Boolean(props.src));

watch(() => props.src, (src) => {
  visible.value = Boolean(src);
});
</script>

<style scoped>
.item-image-thumb {
  align-items: center;
  border-radius: 6px;
  display: inline-flex;
  flex: 0 0 auto;
  height: 36px;
  justify-content: center;
  overflow: hidden;
  width: 36px;
}

.item-image-thumb img {
  display: block;
  height: 100%;
  object-fit: cover;
  width: 100%;
}
</style>
