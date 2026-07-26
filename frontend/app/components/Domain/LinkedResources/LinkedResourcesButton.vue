<template>
  <div v-if="visible" class="d-inline-flex">
    <v-btn
      icon
      variant="text"
      size="x-small"
      color="primary"
      class="linked-resources-button"
      :loading="loading && !resources"
      :title="$t('linked-resources.title')"
      :aria-label="$t('linked-resources.title')"
      @click.stop.prevent="openDialog"
    >
      <v-badge :content="resolvedCount" :model-value="resolvedCount > 1" color="primary" floating>
        <v-icon>{{ $globals.icons.externalLink }}</v-icon>
      </v-badge>
    </v-btn>

    <BaseDialog
      v-model="dialog"
      :title="$t('linked-resources.title')"
      :icon="$globals.icons.externalLink"
      width="620"
      max-width="94vw"
    >
      <v-card-text>
        <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-3" />
        <template v-for="group in groups" :key="group.key">
          <section v-if="group.items.length" class="linked-resource-group mb-4">
            <div class="d-flex align-center ga-2 mb-1">
              <v-icon size="small" color="primary">
                {{ group.icon }}
              </v-icon>
              <strong>{{ group.title }}</strong>
              <v-chip size="x-small" variant="tonal">
                {{ group.items.length }}
              </v-chip>
            </div>
            <v-list density="compact" lines="one" class="pa-0">
              <v-list-item
                v-for="item in group.items"
                :key="item.id"
                :to="group.to?.(item)"
                :href="group.href?.(item)"
                :target="group.href?.(item) ? '_blank' : undefined"
                @click="dialog = false"
              >
                <v-list-item-title>{{ item.name }}</v-list-item-title>
                <template #append>
                  <v-icon size="small">
                    {{ group.href?.(item) ? $globals.icons.openInNew : $globals.icons.chevronRight }}
                  </v-icon>
                </template>
              </v-list-item>
            </v-list>
          </section>
        </template>
        <v-alert v-if="!loading && resolvedCount === 0" type="info" variant="tonal" density="compact">
          {{ $t('linked-resources.none') }}
        </v-alert>
      </v-card-text>
    </BaseDialog>
  </div>
</template>

<script setup lang="ts">
import type {
  LinkedResourceEntityType,
  LinkedResourceItem,
  LinkedResources,
} from "~/lib/api/types/linked-resources";
import { useUserApi } from "~/composables/api/api-client";
import { useLoggedInState } from "~/composables/use-logged-in-state";

interface Props {
  entityType: LinkedResourceEntityType;
  entityId: string;
  count?: number;
  probe?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  count: undefined,
  probe: false,
});
const api = useUserApi();
const { groupSlug } = useLoggedInState();
const { $globals } = useNuxtApp();
const i18n = useI18n();
const dialog = ref(false);
const loading = ref(false);
const resources = ref<LinkedResources | null>(null);
let requestVersion = 0;

const resolvedCount = computed(() => {
  if (resources.value) {
    return resources.value.recipes.length
      + resources.value.shoppingLists.length
      + resources.value.videos.length
      + resources.value.websites.length;
  }
  return props.count ?? 0;
});
const visible = computed(() => resolvedCount.value > 0 || (props.probe && loading.value));
const groups = computed(() => {
  const value = resources.value || { recipes: [], shoppingLists: [], videos: [], websites: [] };
  return [
    {
      key: "recipes",
      title: i18n.t("linked-resources.recipes"),
      icon: $globals.icons.silverwareForkKnife,
      items: value.recipes,
      to: (item: LinkedResourceItem) => `/g/${groupSlug.value}/r/${item.slug}`,
    },
    {
      key: "shopping-lists",
      title: i18n.t("linked-resources.shopping-lists"),
      icon: $globals.icons.formatListCheck,
      items: value.shoppingLists,
      to: (item: LinkedResourceItem) => `/shopping-lists/${item.id}`,
    },
    {
      key: "videos",
      title: i18n.t("linked-resources.videos"),
      icon: $globals.icons.video,
      items: value.videos,
      href: (item: LinkedResourceItem) => item.url || `/videos?video=${item.id}`,
    },
    {
      key: "websites",
      title: i18n.t("linked-resources.websites"),
      icon: $globals.icons.web,
      items: value.websites,
      href: (item: LinkedResourceItem) => item.url || "",
    },
  ];
});

watch(() => [props.entityType, props.entityId], () => {
  requestVersion += 1;
  resources.value = null;
  if (props.probe) void load();
});

onMounted(() => {
  if (props.probe) void load();
});

onBeforeUnmount(() => {
  requestVersion += 1;
});

async function load() {
  if (loading.value || resources.value) return;
  const version = ++requestVersion;
  loading.value = true;
  try {
    const { data } = await api.linkedResources.getOne(props.entityType, props.entityId);
    if (version === requestVersion && data) resources.value = data;
  }
  finally {
    if (version === requestVersion) loading.value = false;
  }
}

async function openDialog() {
  dialog.value = true;
  await load();
}
</script>

<style scoped>
.linked-resources-button:hover,
.linked-resources-button:focus-visible {
  background: rgba(var(--v-theme-primary), 0.12);
}

.linked-resource-group {
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
