<template>
  <BaseDialog
    v-model="dialog"
    :title="isEdit ? $t('group.ai-provider-settings.edit-provider') : $t('group.ai-provider-settings.create-provider')"
    :icon="$globals.icons.robot"
    :loading="loading"
    can-submit
    :submit-icon="isEdit ? $globals.icons.save : $globals.icons.createAlt"
    :submit-text="isEdit ? $t('general.update') : $t('general.create')"
    :submit-disabled="submitDisabled"
    @submit="handleSubmit"
    @close="resetForm"
  >
    <v-card-text v-if="init" style="max-height: 70vh; overflow-y: auto;">
      <v-form ref="form" v-no-autofill>
        <v-alert
          v-if="isEdit"
          :type="isDefaultProvider ? 'success' : 'info'"
          variant="tonal"
          density="compact"
          class="mb-4"
        >
          {{
            isDefaultProvider
              ? $t('group.ai-provider-settings.default-provider-selected')
              : $t('group.ai-provider-settings.not-default-provider-selected')
          }}
        </v-alert>
        <v-text-field
          v-model="formData.name"
          :label="$t('group.ai-provider-settings.provider-name')"
          :rules="[validators.required]"
          density="compact"
          variant="outlined"
          class="mb-4"
        />
        <v-select
          v-model="providerPreset"
          :label="$t('group.ai-provider-settings.provider-preset')"
          :items="providerPresetItems"
          item-title="label"
          item-value="value"
          density="compact"
          variant="outlined"
          class="mb-4"
        />
        <v-alert
          v-if="selectedProviderHint"
          type="info"
          variant="tonal"
          density="compact"
          class="mb-4"
        >
          {{ selectedProviderHint }}
        </v-alert>
        <v-combobox
          v-model="formData.model"
          :items="modelOptions"
          :label="$t('group.ai-provider-settings.model')"
          :hint="$t('group.ai-provider-settings.model-description')"
          :rules="[validators.required]"
          item-title="title"
          item-value="value"
          :return-object="false"
          clearable
          density="compact"
          variant="outlined"
          class="mb-4"
        />
        <v-textarea
          v-if="isGeminiProvider"
          v-model="formData.apiKey"
          :label="$t('group.ai-provider-settings.api-keys')"
          :hint="$t('group.ai-provider-settings.gemini-api-keys-description')"
          :persistent-hint="isEdit || !!formData.apiKey"
          :rules="isEdit ? [] : [validators.required]"
          auto-grow
          rows="3"
          density="compact"
          variant="outlined"
          class="mb-2"
        />
        <v-text-field
          v-else
          v-model="formData.apiKey"
          :label="$t('group.ai-provider-settings.api-key')"
          :hint="$t(
            isEdit
              ? 'group.ai-provider-settings.api-key-description-edit'
              : 'group.ai-provider-settings.api-key-description-create',
          )"
          :persistent-hint="isEdit"
          :rules="isEdit ? [] : [validators.required]"
          density="compact"
          variant="outlined"
          type="password"
          class="mb-2"
        />
        <v-alert
          v-if="apiValidation.message"
          :type="apiValidationStatusColor"
          variant="tonal"
          density="compact"
          class="mb-4"
        >
          {{ apiValidation.message }}
        </v-alert>
        <v-alert
          v-if="isGeminiProvider && geminiKeyCount > 0"
          type="info"
          variant="tonal"
          density="compact"
          class="mb-2"
        >
          {{ $t('group.ai-provider-settings.gemini-default-key-description', { count: geminiKeyCount }) }}
        </v-alert>
        <v-alert
          v-if="hasDuplicateGeminiKeys"
          type="warning"
          variant="tonal"
          density="compact"
          class="mb-4"
        >
          {{ $t('group.ai-provider-settings.gemini-duplicate-api-keys', { count: geminiDuplicateKeyCount }) }}
        </v-alert>
        <v-text-field
          v-model="formData.baseUrl"
          :label="$t('group.ai-provider-settings.base-url')"
          :hint="$t('group.ai-provider-settings.base-url-description')"
          density="compact"
          variant="outlined"
          class="mb-4"
        />
        <v-number-input
          v-model.number="formData.timeout"
          :label="$t('group.ai-provider-settings.request-timeout-seconds')"
          type="number"
          :min="0"
          hide-details
          control-variant="stacked"
          density="compact"
          variant="outlined"
          class="mb-4"
        />
        <v-expansion-panels v-model="advancedPanel" variant="accordion">
          <v-expansion-panel>
            <v-expansion-panel-title class="text-subtitle-2" expand-icon="$expand" collapse-icon="$expand">
              {{ $t('search.advanced') }}
            </v-expansion-panel-title>
            <v-expansion-panel-text class="px-0">
              <div class="mb-2 text-subtitle-2">
                {{ $t('group.ai-provider-settings.request-headers') }}
              </div>
              <BaseKeyValueEditor
                v-model="formData.requestHeaders"
                class="mb-4"
              />
              <v-divider class="mb-4" />
              <div class="mb-2 text-subtitle-2">
                {{ $t('group.ai-provider-settings.request-params') }}
              </div>
              <BaseKeyValueEditor
                v-model="formData.requestParams"
              />
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-form>
    </v-card-text>
    <AppLoader v-else waiting-text="" />
  </BaseDialog>
</template>

<script setup lang="ts">
import { useAIProviders } from "~/composables/use-ai-providers";
import { validators } from "~/composables/use-validators";
import type { AIProviderCreate, AIProviderUpdate } from "~/lib/api/types/group";

const props = withDefaults(defineProps<{
  providerId?: string;
  defaultProviderId?: string;
}>(), {
  providerId: undefined,
  defaultProviderId: undefined,
});

const emit = defineEmits<{
  (e: "create", data: AIProviderCreate): void;
  (e: "update", id: string, data: AIProviderUpdate): void;
}>();

const dialog = defineModel<boolean>({ default: false });

const { $globals } = useNuxtApp();
const i18n = useI18n();
const { loading, getOne, validateOne } = useAIProviders();
const init = ref(false);

const form = ref();
const advancedPanel = ref<number | undefined>(undefined);

const isEdit = computed(() => !!props.providerId);

interface AIModelOption {
  title: string;
  value: string;
}

interface ProviderPreset {
  value: string;
  label: string;
  defaultName: string;
  baseUrl: string;
  hint: string;
  models: AIModelOption[];
}

const providerPresets: ProviderPreset[] = [
  {
    value: "openai",
    label: "OpenAI",
    defaultName: "OpenAI",
    baseUrl: "https://api.openai.com/v1",
    hint: "Works directly with an OpenAI API key using the official OpenAI API endpoint.",
    models: [
      { title: "GPT-5.5 - strongest", value: "gpt-5.5" },
      { title: "GPT-5.5 Pro", value: "gpt-5.5-pro" },
      { title: "GPT-5.4 - balanced", value: "gpt-5.4" },
      { title: "GPT-5.4 Pro", value: "gpt-5.4-pro" },
      { title: "GPT-5.4 mini - recommended for cost/speed", value: "gpt-5.4-mini" },
      { title: "GPT-5.4 nano - cheapest", value: "gpt-5.4-nano" },
      { title: "GPT-5.2", value: "gpt-5.2" },
      { title: "GPT-5.1", value: "gpt-5.1" },
      { title: "GPT-5", value: "gpt-5" },
      { title: "GPT-5 mini", value: "gpt-5-mini" },
      { title: "GPT-5 nano", value: "gpt-5-nano" },
      { title: "GPT-4.1", value: "gpt-4.1" },
      { title: "GPT-4.1 mini", value: "gpt-4.1-mini" },
      { title: "GPT-4o", value: "gpt-4o" },
      { title: "GPT-4o mini", value: "gpt-4o-mini" },
      { title: "o3-pro", value: "o3-pro" },
      { title: "o3", value: "o3" },
      { title: "o4-mini", value: "o4-mini" },
    ],
  },
  {
    value: "gemini",
    label: "Google Gemini",
    defaultName: "Google Gemini",
    baseUrl: "https://generativelanguage.googleapis.com/v1beta/openai/",
    hint: "Uses Google's OpenAI-compatible Gemini endpoint with a Gemini API key.",
    models: [
      { title: "Gemini 3.5 Flash - חינם + בתשלום ($1.50 קלט / $9 פלט) - מומלץ", value: "gemini-3.5-flash" },
      { title: "Gemini Flash Latest - חינם + בתשלום (המודל Flash הנוכחי)", value: "gemini-flash-latest" },
      { title: "Gemini 3.1 Pro Preview - בתשלום בלבד ($2 קלט / $12 פלט)", value: "gemini-3.1-pro-preview" },
      { title: "Gemini 3.1 Flash-Lite - חינם + בתשלום ($0.25 קלט / $1.50 פלט)", value: "gemini-3.1-flash-lite" },
      { title: "Gemini 3 Flash Preview - חינם + בתשלום ($0.50 קלט / $3 פלט)", value: "gemini-3-flash-preview" },
      { title: "Gemini 2.5 Pro - חינם + בתשלום ($1.25 קלט / $10 פלט)", value: "gemini-2.5-pro" },
      { title: "Gemini 2.5 Flash - חינם + בתשלום ($0.30 קלט / $2.50 פלט)", value: "gemini-2.5-flash" },
      { title: "Gemini 2.5 Flash-Lite - חינם + בתשלום ($0.10 קלט / $0.40 פלט)", value: "gemini-2.5-flash-lite" },
      { title: "Gemini 2.5 Flash-Lite Preview - חינם + בתשלום ($0.10 קלט / $0.40 פלט)", value: "gemini-2.5-flash-lite-preview-09-2025" },
    ],
  },
  {
    value: "anthropic",
    label: "Anthropic Claude",
    defaultName: "Anthropic Claude",
    baseUrl: "https://api.anthropic.com/v1",
    hint: "Works for text AI features through Anthropic's Messages API. Do not use it as the image or audio provider.",
    models: [
      { title: "Claude Fable 5 - strongest widely released", value: "claude-fable-5" },
      { title: "Claude Opus 4.8", value: "claude-opus-4-8" },
      { title: "Claude Sonnet 5 - recommended", value: "claude-sonnet-5" },
      { title: "Claude Haiku 4.5", value: "claude-haiku-4-5" },
      { title: "Claude Haiku 4.5 dated", value: "claude-haiku-4-5-20251001" },
      { title: "Claude Mythos 5 - invitation only", value: "claude-mythos-5" },
      { title: "Claude Mythos Preview - invitation only", value: "claude-mythos-preview" },
    ],
  },
  {
    value: "custom",
    label: "Custom / Local OpenAI-compatible",
    defaultName: "",
    baseUrl: "",
    hint: "Use this for Ollama, LM Studio, LiteLLM, OpenRouter, or another compatible endpoint.",
    models: [],
  },
];

const providerPresetItems = providerPresets.map(({ value, label }) => ({ value, label }));
const providerPreset = ref("openai");
const loadingExistingProvider = ref(false);

const defaultForm = () => ({
  name: "",
  model: "",
  apiKey: "",
  baseUrl: "",
  timeout: 300,
  requestHeaders: {} as Record<string, string>,
  requestParams: {} as Record<string, string>,
});

const formData = reactive(defaultForm());
const selectedProvider = computed(() => providerPresets.find(provider => provider.value === providerPreset.value));
const selectedProviderHint = computed(() => selectedProvider.value?.hint ?? "");
const modelOptions = computed(() => selectedProvider.value?.models ?? []);
const isGeminiProvider = computed(() => providerPreset.value === "gemini");
const isDefaultProvider = computed(() => !!props.providerId && props.providerId === props.defaultProviderId);
const geminiKeys = computed(() => formData.apiKey.replaceAll(",", "\n").split("\n").map(key => key.trim()).filter(Boolean));
const geminiKeyCount = computed(() => geminiKeys.value.length);
const uniqueGeminiKeys = computed(() => uniqueApiKeys(geminiKeys.value));
const geminiDuplicateKeyCount = computed(() => geminiKeyCount.value - uniqueGeminiKeys.value.length);
const hasDuplicateGeminiKeys = computed(() => isGeminiProvider.value && geminiDuplicateKeyCount.value > 0);
const apiValidation = reactive({
  status: "idle" as "idle" | "checking" | "valid" | "invalid",
  message: "",
  fingerprint: "",
});
let validationTimer: ReturnType<typeof setTimeout> | undefined;
let validationRun = 0;

function uniqueApiKeys(keys: string[]) {
  const seen = new Set<string>();
  return keys.filter((key) => {
    if (seen.has(key)) {
      return false;
    }

    seen.add(key);
    return true;
  });
}

function normalizedFormApiKey() {
  return isGeminiProvider.value ? uniqueGeminiKeys.value.join("\n") : formData.apiKey.trim();
}

function normalizeApiKeysForSave() {
  formData.apiKey = normalizedFormApiKey();
}

const submitDisabled = computed(() => {
  if (!formData.name?.trim() || !formData.model?.trim()) {
    return true;
  }

  if (!isEdit.value && !formData.apiKey?.trim()) {
    return true;
  }

  if (formData.apiKey?.trim() && apiValidation.status !== "valid") {
    return true;
  }

  return false;
});

const apiValidationStatusColor = computed(() => {
  if (apiValidation.status === "valid") return "success";
  if (apiValidation.status === "invalid") return "error";
  if (apiValidation.status === "checking") return "info";
  return "info";
});

function apiErrorMessage(error: unknown, fallback: string) {
  const responseData = (error as { response?: { data?: { detail?: unknown } } })?.response?.data;
  const detail = responseData?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (detail && typeof detail === "object") {
    const detailObject = detail as { message?: string; exception?: string };
    return detailObject.exception || detailObject.message || fallback;
  }

  return fallback;
}

function validationFingerprint() {
  return JSON.stringify({
    providerPreset: providerPreset.value,
    apiKey: normalizedFormApiKey(),
    baseUrl: formData.baseUrl || null,
    model: formData.model,
    timeout: formData.timeout,
    requestHeaders: formData.requestHeaders,
    requestParams: formData.requestParams,
  });
}

function validationPayload(): AIProviderCreate | null {
  const apiKey = normalizedFormApiKey();
  if (!apiKey || !formData.model?.trim()) {
    return null;
  }

  return {
    name: formData.name?.trim() || selectedProvider.value?.defaultName || "AI Provider",
    model: formData.model,
    apiKey,
    baseUrl: formData.baseUrl || null,
    timeout: formData.timeout,
    requestHeaders: Object.keys(formData.requestHeaders).length ? formData.requestHeaders : undefined,
    requestParams: Object.keys(formData.requestParams).length ? formData.requestParams : undefined,
  };
}

async function validateApiKey(showIdleMessage = false) {
  clearValidationTimer();

  const payload = validationPayload();
  const fingerprint = validationFingerprint();
  const run = ++validationRun;

  if (!payload) {
    apiValidation.status = "idle";
    apiValidation.fingerprint = "";
    apiValidation.message = showIdleMessage ? i18n.t("group.ai-provider-settings.api-key-required") : "";
    return false;
  }

  apiValidation.status = "checking";
  apiValidation.fingerprint = fingerprint;
  apiValidation.message = i18n.t("group.ai-provider-settings.api-key-checking");

  const { error } = await validateOne(payload);
  if (!dialog.value || run !== validationRun || fingerprint !== validationFingerprint()) {
    return false;
  }

  if (error) {
    apiValidation.status = "invalid";
    apiValidation.message = apiErrorMessage(error, i18n.t("group.ai-provider-settings.api-key-invalid"));
    return false;
  }

  apiValidation.status = "valid";
  apiValidation.message = i18n.t("group.ai-provider-settings.api-key-valid");
  return true;
}

function clearValidationTimer() {
  if (validationTimer) {
    clearTimeout(validationTimer);
    validationTimer = undefined;
  }
}

function queueApiKeyValidation() {
  clearValidationTimer();

  if (!formData.apiKey?.trim()) {
    validationRun++;
    apiValidation.status = "idle";
    apiValidation.message = "";
    apiValidation.fingerprint = "";
    return;
  }

  const fingerprint = validationFingerprint();
  if (apiValidation.fingerprint === fingerprint && ["valid", "invalid"].includes(apiValidation.status)) {
    return;
  }

  apiValidation.status = "checking";
  apiValidation.message = i18n.t("group.ai-provider-settings.api-key-checking");
  validationTimer = setTimeout(() => {
    validationTimer = undefined;
    validateApiKey();
  }, 700);
}

function applyProviderPreset(overwriteModel = true, overwriteName = true) {
  const provider = selectedProvider.value;
  if (!provider) {
    return;
  }

  if (overwriteName) {
    formData.name = provider.defaultName;
  }

  formData.baseUrl = provider.baseUrl;

  if (overwriteModel || !formData.model?.trim()) {
    formData.model = provider.models[0]?.value ?? "";
  }
}

function inferProviderPreset(baseUrl: string | null | undefined, model: string | null | undefined) {
  const normalizedBaseUrl = (baseUrl || "").toLowerCase();
  const normalizedModel = (model || "").toLowerCase();

  if (normalizedBaseUrl.includes("generativelanguage.googleapis.com") || normalizedModel.startsWith("gemini-")) {
    return "gemini";
  }
  if (normalizedBaseUrl.includes("anthropic.com") || normalizedModel.startsWith("claude-")) {
    return "anthropic";
  }
  if (!normalizedBaseUrl || normalizedBaseUrl.includes("api.openai.com")) {
    return "openai";
  }
  return "custom";
}

watch(providerPreset, () => {
  if (loadingExistingProvider.value) {
    return;
  }
  applyProviderPreset(true, true);
});

watch(
  () => [
    formData.apiKey,
    formData.model,
    formData.baseUrl,
    providerPreset.value,
    formData.timeout,
    JSON.stringify(formData.requestHeaders),
    JSON.stringify(formData.requestParams),
  ],
  () => {
    if (!dialog.value || loadingExistingProvider.value) {
      return;
    }
    queueApiKeyValidation();
  },
);

// Fetch existing provider when editing; reset form for create mode
watch(
  () => [dialog.value, props.providerId] as const,
  async ([open, id]) => {
    if (!open) {
      clearValidationTimer();
      validationRun++;
      return;
    }
    if (!id) {
      // Create mode — just show the empty form
      resetForm();
      init.value = true;
      return;
    }
    init.value = false;
    const { data } = await getOne(id);
    init.value = true;
    if (data) {
      loadingExistingProvider.value = true;
      formData.name = data.name;
      formData.model = data.model;
      formData.apiKey = data.apiKey ?? "";
      formData.baseUrl = data.baseUrl ?? "";
      formData.timeout = data.timeout ?? 300;
      formData.requestHeaders = { ...(data.requestHeaders ?? {}) };
      formData.requestParams = { ...(data.requestParams ?? {}) };
      const inferredPreset = inferProviderPreset(data.baseUrl, data.model);
      providerPreset.value = inferredPreset;
      const inferredProvider = providerPresets.find(provider => provider.value === inferredPreset);
      if (!formData.baseUrl && inferredProvider?.baseUrl) {
        formData.baseUrl = inferredProvider.baseUrl;
      }
      if (formData.apiKey.trim()) {
        apiValidation.status = "valid";
        apiValidation.message = i18n.t("group.ai-provider-settings.api-key-loaded");
        apiValidation.fingerprint = validationFingerprint();
      }
      await nextTick();
      loadingExistingProvider.value = false;
    }
  },
  { immediate: true },
);

async function handleSubmit() {
  const apiKey = normalizedFormApiKey();

  // Required field guard (button is also disabled, but keep as a safeguard)
  if (!formData.name?.trim() || !formData.model?.trim()) return;
  if (!isEdit.value && !apiKey) return;
  if (apiKey && apiValidation.status !== "valid") {
    const valid = await validateApiKey(true);
    if (!valid) return;
  }

  normalizeApiKeysForSave();

  if (isEdit.value && props.providerId) {
    const payload: AIProviderUpdate = {
      name: formData.name,
      model: formData.model,
      baseUrl: formData.baseUrl || null,
      timeout: formData.timeout,
      requestHeaders: Object.keys(formData.requestHeaders).length ? formData.requestHeaders : undefined,
      requestParams: Object.keys(formData.requestParams).length ? formData.requestParams : undefined,
    };
    if (apiKey) {
      payload.apiKey = apiKey;
    }
    emit("update", props.providerId, payload);
  }
  else {
    const createPayload: AIProviderCreate = {
      name: formData.name,
      model: formData.model,
      apiKey,
      baseUrl: formData.baseUrl || null,
      timeout: formData.timeout,
      requestHeaders: Object.keys(formData.requestHeaders).length ? formData.requestHeaders : undefined,
      requestParams: Object.keys(formData.requestParams).length ? formData.requestParams : undefined,
    };
    emit("create", createPayload);
  }
}

function resetForm() {
  clearValidationTimer();
  validationRun++;
  Object.assign(formData, defaultForm());
  providerPreset.value = "openai";
  applyProviderPreset(true, true);
  apiValidation.status = "idle";
  apiValidation.message = "";
  apiValidation.fingerprint = "";
  form.value?.resetValidation?.();
  advancedPanel.value = undefined;
}

onUnmounted(() => {
  clearValidationTimer();
  validationRun++;
});
</script>
