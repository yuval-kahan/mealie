<template>
  <div v-if="providerSettings">
    <BaseCardSectionTitle v-if="!hideHeader" :title="$t('group.ai-provider-settings.ai-provider-settings')">
      <template v-if="noDefaultProviderWarning" #append-title>
        <v-tooltip location="bottom" color="warning">
          <template #activator="{ props: tooltipProps }">
            <v-icon v-bind="tooltipProps" size="small" color="warning" class="ms-2">
              {{ $globals.icons.alert }}
            </v-icon>
          </template>
          <span>{{ $t('group.ai-provider-settings.no-default-provider-warning') }}</span>
        </v-tooltip>
      </template>
    </BaseCardSectionTitle>
    <v-card-text v-if="!hideHeader" class="pt-0 pb-10 px-0">
      {{ $t("group.ai-provider-settings.ai-provider-settings-description") }}
    </v-card-text>

    <v-row class="mb-4">
      <v-col cols="12">
        <v-autocomplete
          v-model="local.defaultProviderId"
          :label="$t('group.ai-provider-settings.default-provider')"
          :items="local.providers"
          :item-title="providerDisplayName"
          item-value="id"
          clearable
          hide-details
          density="compact"
          variant="outlined"
        />
        <v-card-subtitle class="mt-1">
          {{ $t("group.ai-provider-settings.default-provider-description") }}
        </v-card-subtitle>
      </v-col>
      <v-col cols="12">
        <v-autocomplete
          v-model="local.audioProviderId"
          :label="$t('group.ai-provider-settings.audio-provider')"
          :items="local.providers"
          :item-title="providerDisplayName"
          item-value="id"
          clearable
          hide-details
          density="compact"
          variant="outlined"
        />
        <v-card-subtitle class="mt-1">
          {{ $t("group.ai-provider-settings.audio-provider-description") }}
        </v-card-subtitle>
      </v-col>
      <v-col cols="12">
        <v-autocomplete
          v-model="local.imageProviderId"
          :label="$t('group.ai-provider-settings.image-provider')"
          :items="local.providers"
          :item-title="providerDisplayName"
          item-value="id"
          clearable
          hide-details
          density="compact"
          variant="outlined"
        />
        <v-card-subtitle class="mt-1">
          {{ $t("group.ai-provider-settings.image-provider-description") }}
        </v-card-subtitle>
      </v-col>
    </v-row>

    <GroupAIProviderDialog
      v-model="dialogOpen"
      :provider-id="editingProviderId ?? undefined"
      :default-provider-id="local.defaultProviderId ?? undefined"
      @create="(data) => $emit('create', data)"
      @update="(id, data) => $emit('update', id, data)"
    />

    <BaseCardSectionTitle
      :title="$t('group.ai-provider-settings.providers')"
      size="medium"
      class="pt-2"
    >
      <template #append-title>
        <BaseButton
          :text="$t('group.ai-provider-settings.create-provider')"
          class="ms-auto my-2"
          create
          small
          @click="openCreate"
        />
      </template>
    </BaseCardSectionTitle>

    <v-card
      v-for="provider in local.providers"
      :key="provider.id"
      variant="tonal"
      class="pa-0 mb-4"
    >
      <v-row no-gutters>
        <v-col :cols="9">
          <v-card-text class="d-flex align-center ga-3 py-3">
            <v-avatar size="36" color="surface-variant">
              <v-icon :icon="providerPresentation(provider).icon" />
            </v-avatar>
            <div class="min-width-0">
              <div class="d-flex align-center flex-wrap ga-2">
                <strong class="text-body-1">{{ provider.name }}</strong>
                <v-chip
                  v-if="provider.id === local.defaultProviderId"
                  size="x-small"
                  color="primary"
                  variant="tonal"
                >
                  {{ $t("group.ai-provider-settings.default-badge") }}
                </v-chip>
              </div>
              <div class="text-caption text-medium-emphasis provider-model-line">
                {{ providerPresentation(provider).label }} · {{ provider.model || $t("group.ai-provider-settings.model-unknown") }}
              </div>
            </div>
          </v-card-text>
        </v-col>

        <v-col :cols="3" class="d-flex align-center justify-end">
          <BaseButtonGroup
            :buttons="[
              {
                icon: $globals.icons.edit,
                text: $t('general.edit'),
                event: 'edit',
              },
              {
                icon: $globals.icons.delete,
                text: $t('general.delete'),
                event: 'delete',
              },
            ]"
            @edit="openEdit(provider.id)"
            @delete="$emit('delete', provider.id)"
          />
        </v-col>
      </v-row>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import type { AIProviderCreate, AIProviderUpdate } from "~/lib/api/types/group";
import type { AIProviderSettingsOut, AIProviderSummary } from "~/lib/api/types/user";

const providerSettings = defineModel<AIProviderSettingsOut>({ required: true });

const props = withDefaults(defineProps<{
  hideHeader?: boolean;
}>(), {
  hideHeader: false,
});

const { hideHeader } = toRefs(props);

const local = reactive({ ...providerSettings.value });
watch(local, (newVal) => { providerSettings.value = { ...newVal }; });
// Sync back when the parent refreshes after create/update/delete
watch(providerSettings, (newVal) => { if (newVal) Object.assign(local, newVal); });

const noDefaultProviderWarning = computed(
  () => local.providers.length > 0 && !local.defaultProviderId,
);

defineEmits<{
  (e: "create", data: AIProviderCreate): void;
  (e: "update", id: string, data: AIProviderUpdate): void;
  (e: "delete", id: string): void;
}>();

const dialogOpen = ref(false);
const editingProviderId = ref<string | null>(null);

function openCreate() {
  editingProviderId.value = null;
  dialogOpen.value = true;
}

function openEdit(id: string) {
  editingProviderId.value = id;
  dialogOpen.value = true;
}

function providerDisplayName(provider: AIProviderSummary) {
  return provider.model ? `${provider.name} · ${provider.model}` : provider.name;
}

function providerPresentation(provider: AIProviderSummary) {
  const value = `${provider.name} ${provider.model ?? ""} ${provider.baseUrl ?? ""}`.toLowerCase();
  if (value.includes("gemini") || value.includes("generativelanguage.googleapis.com")) {
    return { label: "Google Gemini", icon: "mdi-google" };
  }
  if (value.includes("anthropic") || value.includes("claude")) {
    return { label: "Anthropic Claude", icon: "mdi-head-snowflake" };
  }
  if (value.includes("openai") || value.includes("gpt")) {
    return { label: "OpenAI", icon: "mdi-creation" };
  }
  return { label: i18n.t("group.ai-provider-settings.custom-provider"), icon: "mdi-robot-outline" };
}
</script>

<style scoped>
.min-width-0 {
  min-width: 0;
}

.provider-model-line {
  overflow-wrap: anywhere;
}
</style>
