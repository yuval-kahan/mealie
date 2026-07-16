<template>
  <v-form ref="domCreateForm" @submit.prevent="createRecipe">
    <div>
      <v-card-title v-if="showTitle" class="headline">
        {{ $t("recipe.create-recipe-from-text") }}
      </v-card-title>
      <v-card-text>
        <p>{{ modeDescription }}</p>
        <v-btn-toggle
          v-model="createMode"
          mandatory
          divided
          class="mb-4"
          color="primary"
          :disabled="state.loading"
        >
          <v-btn value="text">
            <v-icon start>
              {{ $globals.icons.textBoxCheckOutline }}
            </v-icon>
            {{ $t("recipe.ai-create-mode-text") }}
          </v-btn>
          <v-btn value="url">
            <v-icon start>
              {{ $globals.icons.link }}
            </v-icon>
            {{ $t("recipe.ai-create-mode-link") }}
          </v-btn>
          <v-btn value="image">
            <v-icon start>
              {{ $globals.icons.fileImage }}
            </v-icon>
            {{ $t("recipe.ai-create-mode-image") }}
          </v-btn>
        </v-btn-toggle>
        <v-textarea
          v-if="createMode === 'text'"
          v-model="recipeText"
          :label="$t('recipe.recipe-text')"
          :prepend-inner-icon="$globals.icons.textBoxCheckOutline"
          validate-on="blur"
          autofocus
          variant="solo-filled"
          clearable
          rounded
          auto-grow
          :rows="rows"
          :rules="[validators.required]"
        />
        <v-text-field
          v-else-if="createMode === 'url'"
          v-model="recipeUrl"
          :label="$t('new-recipe.recipe-url')"
          :prepend-inner-icon="$globals.icons.link"
          validate-on="blur"
          autofocus
          variant="solo-filled"
          clearable
          rounded
          :rules="[validators.url]"
          :hint="$t('new-recipe.url-form-hint')"
          persistent-hint
        />
        <template v-else>
          <v-file-input
            v-model="uploadedImages"
            accept="image/*"
            variant="solo-filled"
            rounded
            clearable
            multiple
            chips
            show-size
            :prepend-inner-icon="$globals.icons.fileImage"
            prepend-icon=""
            :label="$t('recipe.upload-images')"
            :rules="[uploadedImagesRule]"
            :disabled="state.loading"
          />
          <v-textarea
            v-model="imageNotes"
            variant="outlined"
            auto-grow
            rows="2"
            maxlength="5000"
            counter
            :label="$t('recipe.image-import-notes')"
            :hint="$t('recipe.image-import-notes-description')"
            persistent-hint
            :disabled="state.loading"
          />
        </template>
        <v-checkbox
          v-if="createMode !== 'url'"
          v-model="shouldTranslate"
          color="primary"
          hide-details
          :label="$t('recipe.should-translate-description')"
          :disabled="state.loading"
        />
        <template v-else>
          <v-checkbox
            v-model="importKeywordsAsTags"
            color="primary"
            hide-details
            :label="$t('recipe.import-original-keywords-as-tags')"
            :disabled="state.loading"
          />
          <v-checkbox
            v-model="importCategories"
            color="primary"
            hide-details
            :label="$t('recipe.import-original-categories')"
            :disabled="state.loading"
          />
        </template>
        <v-checkbox
          v-model="shouldCreateShoppingList"
          color="primary"
          hide-details
          :label="$t('recipe.create-ai-shopping-list-description')"
          :disabled="state.loading"
        />
        <v-checkbox
          v-model="includeAiTips"
          color="primary"
          hide-details
          :label="$t('recipe.include-ai-tips-description')"
          :disabled="state.loading"
        />
        <v-checkbox
          v-model="includeItemImages"
          color="primary"
          hide-details
          :label="$t('recipe.include-item-images-description')"
          :disabled="state.loading"
        />
        <v-divider class="my-4" />
        <div class="d-flex flex-column ga-3">
          <RecipeCoverImageUpload
            v-model="recipeImageFile"
            :disabled="state.loading"
          />
          <RecipeAdditionalImagesUpload
            v-model="additionalImageFiles"
            :disabled="state.loading"
          />
          <RecipeVideoAssetUpload
            v-model="videoFile"
            :disabled="state.loading"
          />
        </div>
      </v-card-text>
      <v-card-actions class="justify-center">
        <div style="width: 100%" class="text-center">
          <div style="width: 250px; margin: 0 auto">
            <BaseButton
              :disabled="!canSubmit"
              rounded
              block
              type="submit"
              :loading="state.loading"
            />
          </div>
          <v-card-text class="py-2">
            {{ statusText }}&nbsp;
          </v-card-text>
        </div>
      </v-card-actions>
    </div>
  </v-form>
</template>

<script setup lang="ts">
import { useUserApi } from "~/composables/api/api-client";
import { useCategoryStore } from "~/composables/store/use-category-store";
import { useTagStore } from "~/composables/store/use-tag-store";
import { useNewRecipeOptions } from "~/composables/use-new-recipe-options";
import { useRecipeCreatePreferences } from "~/composables/use-users/preferences";
import { alert } from "~/composables/use-toast";
import { validators } from "~/composables/use-validators";
import type { VForm } from "~/types/auto-forms";

type CreateMode = "text" | "url" | "image";

type ExtensionRecipeImportResponse = {
  ok?: boolean;
  recipeSlug?: string;
  recipe_slug?: string;
  groupSlug?: string;
  group_slug?: string;
  error?: string;
};

const props = withDefaults(defineProps<{
  showTitle?: boolean;
  returnTo?: string;
  rows?: number;
}>(), {
  showTitle: true,
  returnTo: undefined,
  rows: 14,
});

const emit = defineEmits<{
  created: [slug: string];
}>();

const state = reactive({
  loading: false,
});

const api = useUserApi();
const i18n = useI18n();
const auth = useMealieAuth();
const route = useRoute();
const groupSlug = computed(() => route.params.groupSlug as string || auth.user.value?.groupSlug || "");
const categories = useCategoryStore();
const tags = useTagStore();
const domCreateForm = ref<VForm | null>(null);
const shouldTranslate = ref(true);
const shouldCreateShoppingList = ref(true);
const includeAiTips = ref(true);
const recipeCreatePreferences = useRecipeCreatePreferences();
const includeItemImages = computed({
  get: () => recipeCreatePreferences.value.includeItemImages,
  set: (value: boolean) => {
    recipeCreatePreferences.value.includeItemImages = value;
  },
});
const recipeImageFile = ref<File | null>(null);
const additionalImageFiles = ref<File[]>([]);
const videoFile = ref<File | null>(null);
const createStatus = ref<string | null>(null);
const pendingExtensionRequestCancellations = new Set<() => void>();
const { attachVideoToRecipe } = useRecipeVideoAsset();

onBeforeUnmount(() => {
  for (const cancel of [...pendingExtensionRequestCancellations]) {
    cancel();
  }
  pendingExtensionRequestCancellations.clear();
});

function isHttpUrl(value: string | null) {
  if (!value) {
    return false;
  }

  try {
    const parsed = new URL(value);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  }
  catch {
    return false;
  }
}

const sharedQueryUrl = typeof route.query.recipe_import_url === "string" ? route.query.recipe_import_url : null;
const sharedQueryText = typeof route.query.recipe_import_text === "string" ? route.query.recipe_import_text : "";
const sharedUrl = sharedQueryUrl || (isHttpUrl(sharedQueryText) ? sharedQueryText : null);
const sharedText = sharedUrl ? "" : sharedQueryText;
const createMode = ref<CreateMode>(sharedUrl ? "url" : "text");
const recipeText = ref<string | null>(sharedText);
const recipeUrl = ref<string | null>(sharedUrl);
const uploadedImages = ref<File[]>([]);
const imageNotes = ref("");

const {
  importKeywordsAsTags,
  importCategories,
  navigateToRecipe,
} = useNewRecipeOptions({
  enableImportKeywords: true,
  enableImportCategories: true,
  enableStayInEditMode: true,
  enableParseRecipe: false,
});

const modeDescription = computed(() => {
  if (createMode.value === "url") {
    return i18n.t("recipe.create-recipe-from-link-description");
  }

  if (createMode.value === "image") {
    return i18n.t("recipe.create-recipe-from-an-image-description");
  }

  return i18n.t("recipe.create-recipe-from-text-description");
});

const canSubmit = computed(() => {
  if (createMode.value === "url") {
    return Boolean(recipeUrl.value?.trim());
  }

  if (createMode.value === "image") {
    return uploadedImages.value.length > 0;
  }

  return Boolean(recipeText.value?.trim());
});

const statusText = computed(() => {
  if (!state.loading) {
    return "";
  }

  if (createStatus.value) {
    return createStatus.value;
  }

  if (createMode.value === "url") {
    return i18n.t("recipe.please-wait-link-processing");
  }

  if (createMode.value === "image") {
    return uploadedImages.value.length > 1
      ? i18n.t("recipe.please-wait-images-processing")
      : i18n.t("recipe.please-wait-image-procesing");
  }

  return i18n.t("recipe.please-wait-text-processing");
});

const uploadedImagesRule = (value: File[] | File | null) => {
  if (createMode.value !== "image") {
    return true;
  }

  const files = Array.isArray(value) ? value : value ? [value] : [];
  return files.length > 0 || i18n.t("recipe.upload-images");
};

function createTextErrorMessage(error: unknown) {
  const typedError = error as {
    message?: string;
    response?: {
      data?: {
        detail?: { exception?: string; message?: string } | string;
        message?: string;
      };
    };
  };
  const responseData = typedError.response?.data;
  const detail = typeof responseData?.detail === "string" ? { message: responseData.detail } : responseData?.detail;
  if (detail?.exception === "NotARecipe") {
    return i18n.t("recipe.recipe-text-not-recognized");
  }

  return detail?.message || responseData?.message || typedError.message || i18n.t("events.something-went-wrong");
}

function createLinkErrorMessage(error: unknown) {
  const typedError = error as { message?: string; response?: { data?: { detail?: { message?: string } } } };
  return typedError.response?.data?.detail?.message || i18n.t("recipe.recipe-link-import-error");
}

function extensionRecipeSlug(response: ExtensionRecipeImportResponse | null) {
  return response?.recipeSlug || response?.recipe_slug || null;
}

function extensionGroupSlug(response: ExtensionRecipeImportResponse | null) {
  return response?.groupSlug || response?.group_slug || groupSlug.value;
}

function fileBaseName(fileName: string) {
  const lastDot = fileName.lastIndexOf(".");
  return lastDot > 0 ? fileName.substring(0, lastDot) : fileName;
}

async function createRecipe() {
  const isValid = await domCreateForm.value?.validate();
  if (!isValid?.valid) {
    return;
  }

  createStatus.value = null;
  state.loading = true;

  try {
    if (createMode.value === "url") {
      await createRecipeFromUrl();
      return;
    }

    if (createMode.value === "image") {
      await createRecipeFromImages();
      return;
    }

    await createRecipeFromText();
  }
  catch (error) {
    alert.error(createTextErrorMessage(error));
    state.loading = false;
    createStatus.value = null;
  }
}

async function createRecipeFromText() {
  const text = recipeText.value?.trim();
  if (!text) {
    state.loading = false;
    return;
  }

  const { data, error } = await api.recipes.createOneFromText({
    text,
    translateLanguage: shouldTranslate.value ? i18n.locale.value : null,
    includeAiTips: includeAiTips.value,
    autoImage: true,
    includeItemImages: includeItemImages.value,
  });

  if (error || !data) {
    alert.error(createTextErrorMessage(error));
    state.loading = false;
    return;
  }

  await attachMediaToRecipe(data);
  await createShoppingListForRecipe(data);
  await refreshRecipeOrganizers();

  emit("created", data);
  navigateToRecipe(data, groupSlug.value, props.returnTo || route.path);
}

async function createRecipeFromImages() {
  if (!uploadedImages.value.length) {
    state.loading = false;
    return;
  }

  const translateLanguage = shouldTranslate.value ? i18n.locale.value : null;
  const { data, error } = await api.recipes.createOneFromImages(
    uploadedImages.value,
    translateLanguage,
    includeAiTips.value,
    includeItemImages.value,
    imageNotes.value.trim() || null,
  );

  if (error || !data) {
    alert.error(createTextErrorMessage(error));
    state.loading = false;
    return;
  }

  await attachMediaToRecipe(data);
  await createShoppingListForRecipe(data);
  await refreshRecipeOrganizers();
  emit("created", data);
  navigateToRecipe(data, groupSlug.value, props.returnTo || route.path);
}

async function createRecipeFromUrl() {
  const url = recipeUrl.value?.trim();
  if (!url) {
    state.loading = false;
    return;
  }

  const { response, error } = await api.recipes.createOneByUrl(
    url,
    importKeywordsAsTags.value,
    importCategories.value,
    (message) => {
      createStatus.value = message;
    },
    true,
    shouldTranslate.value ? i18n.locale.value : null,
  );
  createStatus.value = null;

  if (error || response?.status !== 201 || !response?.data) {
    const extensionResponse = await createRecipeFromUrlViaExtension(url);
    const extensionSlug = extensionRecipeSlug(extensionResponse);
    if (extensionResponse?.ok && extensionSlug) {
      await attachMediaToRecipe(extensionSlug);
      await ensureRecipeItemImages(extensionSlug);
      await refreshRecipeOrganizers();
      emit("created", extensionSlug);
      navigateToRecipe(extensionSlug, extensionGroupSlug(extensionResponse), props.returnTo || route.path);
      return;
    }

    if (extensionResponse?.error) {
      alert.error(extensionResponse.error);
      state.loading = false;
      return;
    }

    alert.error(createLinkErrorMessage(error));
    state.loading = false;
    return;
  }

  await attachMediaToRecipe(response.data);
  await ensureRecipeItemImages(response.data);
  await createShoppingListForRecipe(response.data);
  await refreshRecipeOrganizers();
  emit("created", response.data);
  navigateToRecipe(response.data, groupSlug.value, props.returnTo || route.path);
}

async function createRecipeFromUrlViaExtension(url: string): Promise<ExtensionRecipeImportResponse | null> {
  if (!import.meta.client) {
    return null;
  }

  const requestId = `mealie-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  createStatus.value = i18n.t("recipe.recipe-link-extension-fallback-status");

  return await new Promise((resolve) => {
    let acknowledged = false;
    let settled = false;
    let ackTimer: ReturnType<typeof setTimeout> | null = null;
    let finalTimer: ReturnType<typeof setTimeout> | null = null;

    function cleanup() {
      window.removeEventListener("message", onMessage);
      if (ackTimer) {
        clearTimeout(ackTimer);
      }
      if (finalTimer) {
        clearTimeout(finalTimer);
      }
      pendingExtensionRequestCancellations.delete(cancel);
    }

    function finish(response: ExtensionRecipeImportResponse | null) {
      if (settled) {
        return;
      }

      settled = true;
      cleanup();
      resolve(response);
    }

    function cancel() {
      finish(null);
    }

    function onMessage(event: MessageEvent) {
      if (event.source !== window) {
        return;
      }

      const data = event.data as { type?: string; requestId?: string; response?: ExtensionRecipeImportResponse };
      if (!data || data.requestId !== requestId) {
        return;
      }

      if (data.type === "MEALIE_EXTENSION_IMPORT_RECIPE_URL_ACK") {
        acknowledged = true;
        if (ackTimer) {
          clearTimeout(ackTimer);
        }
        createStatus.value = i18n.t("recipe.recipe-link-extension-extracting-status");
        return;
      }

      if (data.type === "MEALIE_EXTENSION_IMPORT_RECIPE_URL_RESULT") {
        finish(data.response || { ok: false, error: i18n.t("recipe.recipe-link-extension-not-available") });
      }
    }

    pendingExtensionRequestCancellations.add(cancel);
    window.addEventListener("message", onMessage);
    window.postMessage(
      {
        type: "MEALIE_EXTENSION_IMPORT_RECIPE_URL",
        requestId,
        payload: {
          url,
          mealieUrl: window.location.origin,
          interfaceLanguage: i18n.locale.value,
          translateLanguage: i18n.locale.value,
          createShoppingList: shouldCreateShoppingList.value,
          organizeShoppingListWithAi: shouldCreateShoppingList.value,
          includeAiTips: includeAiTips.value,
          includeItemImages: includeItemImages.value,
        },
      },
      window.location.origin,
    );

    ackTimer = setTimeout(() => {
      if (!acknowledged) {
        finish(null);
      }
    }, 1500);

    finalTimer = setTimeout(() => {
      finish({ ok: false, error: i18n.t("recipe.recipe-link-extension-timeout") });
    }, 180000);
  });
}

async function refreshRecipeOrganizers() {
  await Promise.allSettled([
    categories.actions.refresh(),
    tags.actions.refresh(),
  ]);

  if (import.meta.client) {
    window.dispatchEvent(new CustomEvent("mealie:organizers-updated"));
  }
}

async function attachMediaToRecipe(recipeSlug: string) {
  if (recipeImageFile.value && await recipeNeedsFallbackCover(recipeSlug)) {
    try {
      const { error } = await api.recipes.updateImage(recipeSlug, recipeImageFile.value);

      if (error) {
        alert.error(i18n.t("events.something-went-wrong"));
      }
    }
    catch (e) {
      alert.error(i18n.t("events.something-went-wrong"));
      console.error("Failed to upload recipe image", e);
    }
  }

  await attachAdditionalImagesToRecipe(recipeSlug);
  await attachVideoToRecipe(recipeSlug, videoFile.value);
}

async function recipeNeedsFallbackCover(recipeSlug: string) {
  try {
    const { data, error } = await api.recipes.getOne(recipeSlug);
    if (error || !data) {
      console.warn("Unable to verify the AI recipe image; keeping it unchanged");
      return false;
    }

    if (typeof data.image === "string") {
      return !data.image.trim();
    }

    return !data.image;
  }
  catch (error) {
    console.warn("Unable to verify the AI recipe image; keeping it unchanged", error);
    return false;
  }
}

async function ensureRecipeItemImages(recipeSlug: string) {
  if (!includeItemImages.value) {
    return;
  }

  try {
    createStatus.value = i18n.t("recipe.finding-item-images");
    await api.recipes.ensureItemImages(recipeSlug);
  }
  catch (e) {
    console.error("Failed to ensure recipe item images", e);
  }
}

async function attachAdditionalImagesToRecipe(recipeSlug: string) {
  if (!additionalImageFiles.value.length) {
    return;
  }

  let hasError = false;

  for (const file of additionalImageFiles.value) {
    try {
      const { error } = await api.recipes.createAsset(recipeSlug, {
        name: fileBaseName(file.name),
        icon: "mdi-file-image",
        file,
        extension: file.name.split(".").pop() || "",
      });

      if (error) {
        hasError = true;
      }
    }
    catch (e) {
      hasError = true;
      console.error("Failed to upload additional recipe image", e);
    }
  }

  if (hasError) {
    alert.error(i18n.t("events.something-went-wrong"));
  }
}

async function createShoppingListForRecipe(recipeSlug: string) {
  if (!shouldCreateShoppingList.value) {
    return;
  }

  createStatus.value = i18n.t("recipe.creating-ai-shopping-list");

  try {
    createStatus.value = i18n.t("recipe.organizing-ai-shopping-list");
    const { data, error } = await api.recipes.createAIShoppingList(recipeSlug, {
      includeAiTips: includeAiTips.value,
      organizeShoppingListWithAi: true,
      includeItemImages: includeItemImages.value,
      translateLanguage: shouldTranslate.value ? i18n.locale.value : null,
    });
    if (error || !data?.shoppingListId) {
      alert.error(i18n.t("recipe.ai-shopping-list-create-failed"));
      return;
    }
    if (data.shoppingListError) {
      alert.error(data.shoppingListError);
      return;
    }

    if (import.meta.client) {
      window.dispatchEvent(new CustomEvent("mealie:organizers-updated"));
    }
    alert.success(i18n.t("recipe.ai-shopping-list-created"));
  }
  catch (e) {
    console.error("Failed to create AI shopping list", e);
    alert.error(i18n.t("recipe.ai-shopping-list-create-failed"));
  }
}
</script>
