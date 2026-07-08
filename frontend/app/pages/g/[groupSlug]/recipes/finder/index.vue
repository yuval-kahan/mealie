<template>
  <v-container class="d-flex justify-center py-8">
    <AppLoader waiting-text="" />
  </v-container>
</template>

<script setup lang="ts">
const route = useRoute();
const groupSlug = computed(() => route.params.groupSlug as string);

onMounted(() => {
  navigateTo({
    path: `/g/${groupSlug.value}`,
    query: {
      ...route.query,
      finder: "true",
    },
  }, { replace: true });
});
</script>
