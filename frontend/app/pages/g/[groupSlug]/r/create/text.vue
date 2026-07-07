<template>
  <RecipeCreateFromTextForm :return-to="`/g/${groupSlug}/r/create/text`" />
</template>

<script setup lang="ts">
const auth = useMealieAuth();
const route = useRoute();
const groupSlug = computed(() => route.params.groupSlug as string || auth.user.value?.groupSlug || "");
</script>
