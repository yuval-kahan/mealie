<template>
  <BaseDialog
    v-model="dialogOpen"
    :title="$t('equipment.quick-add')"
    :icon="$globals.icons.tools"
    width="720"
    max-width="96vw"
    can-submit
    keep-open
    disable-submit-on-enter
    :loading="saving"
    :submit-disabled="!canSubmit"
    :submit-text="$t('general.save')"
    @submit="submit"
    @close="resetForm"
  >
    <v-card-text class="pt-4">
      <v-btn-toggle
        v-model="mode"
        mandatory
        divided
        density="comfortable"
        class="mb-4"
      >
        <v-btn value="manual" :prepend-icon="$globals.icons.edit">
          {{ $t("equipment.manual") }}
        </v-btn>
        <v-btn value="ai" :prepend-icon="$globals.icons.robot">
          {{ $t("equipment.add-with-ai") }}
        </v-btn>
      </v-btn-toggle>

      <template v-if="mode === 'ai'">
        <v-textarea
          v-model="aiPrompt"
          :label="$t('equipment.ai-request')"
          :hint="$t('equipment.ai-request-hint')"
          persistent-hint
          autofocus
          rows="5"
          auto-grow
          variant="outlined"
        />
        <v-text-field
          v-model="aiName"
          :label="$t('equipment.optional-name')"
          variant="outlined"
          density="comfortable"
        />
        <v-alert type="info" variant="tonal" density="compact">
          {{ $t("equipment.quantity-cleanup-help") }}
        </v-alert>
      </template>

      <template v-else>
        <v-text-field
          v-model="form.name"
          :label="$t('equipment.name')"
          autofocus
          variant="outlined"
          density="comfortable"
        />
        <v-combobox
          v-model="form.category"
          :items="categories"
          :label="$t('equipment.category')"
          clearable
          variant="outlined"
          density="comfortable"
        />
        <v-textarea
          v-model="form.description"
          :label="$t('equipment.description')"
          rows="4"
          auto-grow
          variant="outlined"
        />
        <v-alert type="info" variant="tonal" density="compact">
          {{ $t("equipment.quantity-cleanup-help") }}
        </v-alert>
      </template>
    </v-card-text>
  </BaseDialog>
</template>

<script setup lang="ts">
import type { Equipment, EquipmentCreate } from "~/lib/api/types/equipment";
import { useUserApi } from "~/composables/api/api-client";
import { alert } from "~/composables/use-toast";

withDefaults(defineProps<{
  categories?: string[];
}>(), {
  categories: () => [],
});

const emit = defineEmits<{
  saved: [equipment: Equipment];
}>();

const dialogOpen = defineModel<boolean>({ default: false });
const i18n = useI18n();
const api = useUserApi();
const saving = ref(false);
const mode = ref<"manual" | "ai">("manual");
const aiPrompt = ref("");
const aiName = ref("");
const form = reactive<EquipmentCreate>({
  name: "",
  category: "",
  description: "",
});

const canSubmit = computed(() => mode.value === "ai"
  ? Boolean(aiPrompt.value.trim() || aiName.value.trim())
  : Boolean(form.name.trim()));

function resetForm() {
  mode.value = "manual";
  aiPrompt.value = "";
  aiName.value = "";
  form.name = "";
  form.category = "";
  form.description = "";
}

async function submit() {
  saving.value = true;
  const response = mode.value === "ai"
    ? await api.equipment.createWithAI({
        prompt: aiPrompt.value.trim() || aiName.value.trim(),
        name: aiName.value.trim() || null,
      })
    : await api.equipment.createOne({
        name: form.name.trim(),
        category: form.category?.trim() || null,
        description: form.description?.trim() || null,
      });
  saving.value = false;

  if (!response.data || response.error) {
    const detail = response.error?.response?.data?.detail;
    const message = typeof detail?.message === "string"
      ? detail.message
      : typeof detail === "string"
        ? detail
        : i18n.t("events.something-went-wrong");
    alert.error(message);
    return;
  }

  emit("saved", response.data);
  dialogOpen.value = false;
  resetForm();
}
</script>
