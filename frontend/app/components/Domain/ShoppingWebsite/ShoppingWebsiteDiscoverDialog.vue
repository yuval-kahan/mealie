<template>
  <BaseDialog
    v-model="dialogOpen"
    :title="$t('shopping-website.ai-discovery')"
    :icon="$globals.icons.robot"
    :loading="searching || saving"
    @close="reset"
  >
    <v-card-text>
      <v-textarea
        v-model="prompt"
        :label="$t('shopping-website.ai-discovery-prompt')"
        :placeholder="$t('shopping-website.ai-discovery-example')"
        rows="3"
        auto-grow
        autofocus
      />
      <v-select
        v-model="limit"
        :items="[5, 8, 10, 15, 20]"
        :label="$t('shopping-website.maximum-results')"
        variant="outlined"
        density="comfortable"
      />
      <v-alert
        v-if="searched && !results.length"
        type="info"
        variant="tonal"
        density="compact"
      >
        {{ $t("shopping-website.no-ai-results") }}
      </v-alert>
      <v-list v-else-if="results.length" class="discovery-results" lines="three">
        <v-list-item
          v-for="(website, index) in results"
          :key="`${website.url}-${index}`"
          :title="website.name"
          :subtitle="[website.pageFood, website.url].filter(Boolean).join(' · ')"
        >
          <template #prepend>
            <v-checkbox-btn v-model="selectedIndexes" :value="index" />
          </template>
          <template #append>
            <v-chip v-if="website.isRecipeSite" size="x-small" variant="tonal">
              {{ $t("shopping-website.recipe-site") }}
            </v-chip>
            <v-chip v-if="website.isShoppingSite" size="x-small" variant="tonal" class="ms-1">
              {{ $t("shopping-website.shopping-site") }}
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
        {{ $t("shopping-website.find-with-ai") }}
      </v-btn>
      <v-btn
        color="primary"
        :prepend-icon="$globals.icons.save"
        :disabled="!selectedIndexes.length || searching || saving"
        :loading="saving"
        @click="saveSelected"
      >
        {{ $t("shopping-website.save-selected", { count: selectedIndexes.length }) }}
      </v-btn>
    </template>
  </BaseDialog>
</template>

<script setup lang="ts">
import type { ShoppingWebsiteCreate } from "~/lib/api/types/shopping-website";
import { useUserApi } from "~/composables/api/api-client";
import { alert } from "~/composables/use-toast";

const emit = defineEmits<{ saved: [] }>();
const dialogOpen = defineModel<boolean>({ default: false });
const api = useUserApi();
const i18n = useI18n();
const prompt = ref("");
const limit = ref(8);
const results = ref<ShoppingWebsiteCreate[]>([]);
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
  const { data, error } = await api.shoppingWebsites.discoverWithAI({
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
    const website = results.value[index];
    if (!website) continue;
    const { error } = await api.shoppingWebsites.createOne(website);
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
