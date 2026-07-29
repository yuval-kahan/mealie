<template>
  <BaseDialog
    v-model="dialogOpen"
    :title="$t('restaurant.ai-discovery')"
    :icon="$globals.icons.robot"
    :loading="searching || saving"
    @close="reset"
  >
    <v-card-text>
      <v-textarea
        v-model="prompt"
        :label="$t('restaurant.ai-discovery-prompt')"
        :placeholder="$t('restaurant.ai-discovery-example')"
        rows="3"
        auto-grow
        autofocus
      />
      <v-select
        v-model="limit"
        :items="[5, 8, 10, 15, 20]"
        :label="$t('restaurant.maximum-results')"
        variant="outlined"
        density="comfortable"
      />
      <v-alert
        v-if="searched && !results.length"
        type="info"
        variant="tonal"
        density="compact"
      >
        {{ $t("restaurant.no-ai-results") }}
      </v-alert>
      <v-list v-else-if="results.length" class="discovery-results" lines="three">
        <v-list-item
          v-for="(restaurant, index) in results"
          :key="`${restaurant.websiteUrl || restaurant.name}-${index}`"
          :title="restaurant.name"
          :subtitle="[restaurant.cuisineTypes.join(', '), restaurant.addresses[0]].filter(Boolean).join(' · ')"
        >
          <template #prepend>
            <v-checkbox-btn v-model="selectedIndexes" :value="index" />
          </template>
          <template #append>
            <v-chip v-if="restaurant.michelinStarCount" size="small" color="warning" variant="tonal">
              {{ restaurant.michelinStarCount }} ★
            </v-chip>
          </template>
        </v-list-item>
      </v-list>
    </v-card-text>
    <template #custom-card-action>
      <v-btn
        variant="text"
        :prepend-icon="$globals.icons.search"
        :disabled="!prompt.trim() || searching || saving"
        :loading="searching"
        @click="discover"
      >
        {{ $t("restaurant.find-with-ai") }}
      </v-btn>
      <v-btn
        color="primary"
        :prepend-icon="$globals.icons.save"
        :disabled="!selectedIndexes.length || searching || saving"
        :loading="saving"
        @click="saveSelected"
      >
        {{ $t("restaurant.save-selected", { count: selectedIndexes.length }) }}
      </v-btn>
    </template>
  </BaseDialog>
</template>

<script setup lang="ts">
import type { RestaurantCreate } from "~/lib/api/types/restaurant";
import { useUserApi } from "~/composables/api/api-client";
import { alert } from "~/composables/use-toast";

const emit = defineEmits<{ saved: [] }>();
const dialogOpen = defineModel<boolean>({ default: false });
const api = useUserApi();
const i18n = useI18n();
const prompt = ref("");
const limit = ref(8);
const results = ref<RestaurantCreate[]>([]);
const selectedIndexes = ref<number[]>([]);
const searching = ref(false);
const saving = ref(false);
const searched = ref(false);

function reset() {
  prompt.value = "";
  limit.value = 8;
  results.value = [];
  selectedIndexes.value = [];
  searched.value = false;
}

async function discover() {
  if (!prompt.value.trim() || searching.value) return;
  searching.value = true;
  const { data, error } = await api.restaurants.discoverWithAI({
    prompt: prompt.value.trim(),
    limit: limit.value,
  });
  searching.value = false;
  searched.value = true;
  if (!data || error) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }
  results.value = data;
  selectedIndexes.value = data.map((_, index) => index);
}

async function saveSelected() {
  if (!selectedIndexes.value.length || saving.value) return;
  saving.value = true;
  for (const index of [...selectedIndexes.value].sort((a, b) => a - b)) {
    const restaurant = results.value[index];
    if (!restaurant) continue;
    const { error } = await api.restaurants.createOne(restaurant);
    if (error) {
      saving.value = false;
      alert.error(i18n.t("events.something-went-wrong"));
      return;
    }
  }
  saving.value = false;
  dialogOpen.value = false;
  emit("saved");
  reset();
}
</script>

<style scoped>
.discovery-results {
  max-height: min(48vh, 480px);
  overflow-y: auto;
}
</style>
