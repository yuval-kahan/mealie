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
        <v-file-input
          v-else
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
          v-model="parseRecipe"
          color="primary"
          hide-details
          :label="$t('recipe.parse-recipe-ingredients-after-import')"
          :disabled="state.loading"
        />
        <v-divider class="my-4" />
        <RecipeVideoAssetUpload
          v-model="videoFile"
          :disabled="state.loading"
        />
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
import { useUserApi } from "~/composables/api";
import { useTagStore } from "~/composables/store/use-tag-store";
import { useNewRecipeOptions } from "~/composables/use-new-recipe-options";
import { alert } from "~/composables/use-toast";
import { validators } from "~/composables/use-validators";
import type { VForm } from "~/types/auto-forms";

type CreateMode = "text" | "url" | "image";

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
const tags = useTagStore();
const domCreateForm = ref<VForm | null>(null);
const shouldTranslate = ref(true);
const videoFile = ref<File | null>(null);
const createStatus = ref<string | null>(null);
const { attachVideoToRecipe } = useRecipeVideoAsset();

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

const {
  importKeywordsAsTags,
  importCategories,
  parseRecipe,
  navigateToRecipe,
} = useNewRecipeOptions({
  enableImportKeywords: true,
  enableImportCategories: true,
  enableStayInEditMode: true,
  enableParseRecipe: true,
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
  const typedError = error as { response?: { data?: { detail?: { exception?: string; message?: string } } } };
  const detail = typedError.response?.data?.detail;
  if (detail?.exception === "NotARecipe") {
    return i18n.t("recipe.recipe-text-not-recognized");
  }

  return detail?.message || i18n.t("events.something-went-wrong");
}

function createLinkErrorMessage(error: unknown) {
  const typedError = error as { message?: string; response?: { data?: { detail?: { message?: string } } } };
  return typedError.response?.data?.detail?.message || i18n.t("recipe.recipe-link-import-error");
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
  catch {
    alert.error(i18n.t("events.something-went-wrong"));
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
  });

  if (error || !data) {
    alert.error(createTextErrorMessage(error));
    state.loading = false;
    return;
  }

  if (videoFile.value) {
    await attachVideoToRecipe(data, videoFile.value);
  }

  emit("created", data);
  navigateToRecipe(data, groupSlug.value, props.returnTo || route.path);
}

async function createRecipeFromImages() {
  if (!uploadedImages.value.length) {
    state.loading = false;
    return;
  }

  const translateLanguage = shouldTranslate.value ? i18n.locale.value : null;
  const { data, error } = await api.recipes.createOneFromImages(uploadedImages.value, translateLanguage);

  if (error || !data) {
    alert.error(i18n.t("events.something-went-wrong"));
    state.loading = false;
    return;
  }

  await attachVideoToRecipe(data, videoFile.value);
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
  );
  createStatus.value = null;

  if (error || response?.status !== 201 || !response?.data) {
    alert.error(createLinkErrorMessage(error));
    state.loading = false;
    return;
  }

  if (importKeywordsAsTags.value) {
    tags.actions.refresh();
  }

  await attachVideoToRecipe(response.data, videoFile.value);
  emit("created", response.data);
  navigateToRecipe(response.data, groupSlug.value, props.returnTo || route.path);
}
</script>
