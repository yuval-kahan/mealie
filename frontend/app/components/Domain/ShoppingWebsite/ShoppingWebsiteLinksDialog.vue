<template>
  <BaseDialog
    v-model="dialog"
    :title="$t('shopping-website.link-websites')"
    :icon="$globals.icons.web"
    width="700"
    max-width="95vw"
    can-submit
    keep-open
    :loading="loading || saving"
    :submit-disabled="loading || !changed"
    @submit="saveLinks"
  >
    <v-card-text>
      <v-text-field
        v-model="search"
        density="compact"
        variant="outlined"
        hide-details
        clearable
        :prepend-inner-icon="$globals.icons.search"
        :label="$t('search.search')"
        class="mb-3"
      />

      <v-list v-if="filteredWebsites.length" class="shopping-website-links-list" lines="two">
        <v-list-item v-for="website in filteredWebsites" :key="website.id">
          <template #prepend>
            <v-checkbox-btn
              :model-value="selectedWebsiteIds.has(website.id)"
              :aria-label="website.name"
              @update:model-value="toggleWebsite(website.id, Boolean($event))"
            />
          </template>
          <v-list-item-title>{{ website.name }}</v-list-item-title>
          <v-list-item-subtitle>
            {{ [website.pageFood, ...website.offeredFoods].filter(Boolean).join(" · ") }}
          </v-list-item-subtitle>
          <template #append>
            <v-btn
              icon
              variant="text"
              size="small"
              :href="website.url"
              target="_blank"
              rel="noopener"
              :title="$t('shopping-website.open-website')"
              @click.stop
            >
              <v-icon>{{ $globals.icons.openInNew }}</v-icon>
            </v-btn>
          </template>
        </v-list-item>
      </v-list>

      <v-alert v-else type="info" variant="tonal">
        {{ websites.length ? $t("search.no-results") : $t("shopping-website.no-websites") }}
      </v-alert>

      <div class="d-flex justify-end mt-3">
        <v-btn
          variant="text"
          color="primary"
          :prepend-icon="$globals.icons.create"
          to="/shopping-websites"
        >
          {{ $t("shopping-website.save-website") }}
        </v-btn>
      </div>
    </v-card-text>
  </BaseDialog>
</template>

<script setup lang="ts">
import type { ShoppingWebsite } from "~/lib/api/types/shopping-website";
import { useUserApi } from "~/composables/api/api-client";
import { alert } from "~/composables/use-toast";

interface Props {
  modelValue: boolean;
  entityType: "recipe" | "shopping-list";
  entityId: string;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  "update:modelValue": [value: boolean];
  "saved": [websites: ShoppingWebsite[]];
}>();
const dialog = computed({
  get: () => props.modelValue,
  set: value => emit("update:modelValue", value),
});
const api = useUserApi();
const i18n = useI18n();
const websites = ref<ShoppingWebsite[]>([]);
const selectedWebsiteIds = ref<Set<string>>(new Set());
const initialWebsiteIds = ref<Set<string>>(new Set());
const search = ref("");
const loading = ref(false);
const saving = ref(false);
let loadVersion = 0;

const filteredWebsites = computed(() => {
  const query = search.value.trim().toLocaleLowerCase();
  if (!query) return websites.value;
  return websites.value.filter(website => [
    website.name,
    website.url,
    website.pageFood || "",
    ...website.offeredFoods,
  ].join(" ").toLocaleLowerCase().includes(query));
});
const changed = computed(() => {
  if (selectedWebsiteIds.value.size !== initialWebsiteIds.value.size) return true;
  return [...selectedWebsiteIds.value].some(id => !initialWebsiteIds.value.has(id));
});

watch(
  () => props.modelValue,
  (open) => {
    if (open) void loadWebsites();
    else loadVersion += 1;
  },
);

async function loadWebsites() {
  const version = ++loadVersion;
  loading.value = true;
  try {
    const { data, error } = await api.shoppingWebsites.getAll();
    if (error || !data || version !== loadVersion) {
      if (version === loadVersion) alert.error(i18n.t("events.something-went-wrong"));
      return;
    }
    websites.value = data;
    const linkedIds = data
      .filter(website => props.entityType === "recipe"
        ? website.recipeIds.includes(props.entityId)
        : website.shoppingListIds.includes(props.entityId))
      .map(website => website.id);
    selectedWebsiteIds.value = new Set(linkedIds);
    initialWebsiteIds.value = new Set(linkedIds);
  }
  finally {
    if (version === loadVersion) loading.value = false;
  }
}

function toggleWebsite(id: string, selected: boolean) {
  const next = new Set(selectedWebsiteIds.value);
  if (selected) next.add(id);
  else next.delete(id);
  selectedWebsiteIds.value = next;
}

async function saveLinks() {
  if (saving.value || !changed.value) return;
  saving.value = true;
  try {
    const websiteIds = [...selectedWebsiteIds.value];
    const response = props.entityType === "recipe"
      ? await api.shoppingWebsites.updateRecipeLinks(props.entityId, websiteIds)
      : await api.shoppingWebsites.updateShoppingListLinks(props.entityId, websiteIds);
    if (response.error || !response.data) {
      alert.error(i18n.t("events.something-went-wrong"));
      return;
    }
    initialWebsiteIds.value = new Set(websiteIds);
    emit("saved", response.data);
    alert.success(i18n.t("events.updated"));
    dialog.value = false;
  }
  finally {
    saving.value = false;
  }
}
</script>

<style scoped>
.shopping-website-links-list {
  max-height: min(52vh, 520px);
  overflow-y: auto;
}
</style>
