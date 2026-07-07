<template>
  <v-form ref="domTextForm" @submit.prevent="createRecipe">
    <div>
      <v-card-title v-if="showTitle" class="headline">
        {{ $t("recipe.create-recipe-from-text") }}
      </v-card-title>
      <v-card-text>
        <p>{{ $t("recipe.create-recipe-from-text-description") }}</p>
        <v-textarea
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
        <v-checkbox
          v-model="shouldTranslate"
          color="primary"
          hide-details
          :label="$t('recipe.should-translate-description')"
          :disabled="state.loading"
        />
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
              :disabled="!recipeText?.trim()"
              rounded
              block
              type="submit"
              :loading="state.loading"
            />
          </div>
          <v-card-text class="py-2">
            {{ state.loading ? $t("recipe.please-wait-text-processing") : "" }}&nbsp;
          </v-card-text>
        </div>
      </v-card-actions>
    </div>
  </v-form>
</template>

<script setup lang="ts">
import { useUserApi } from "~/composables/api";
import { useNewRecipeOptions } from "~/composables/use-new-recipe-options";
import { alert } from "~/composables/use-toast";
import { validators } from "~/composables/use-validators";
import type { VForm } from "~/types/auto-forms";

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
const domTextForm = ref<VForm | null>(null);
const shouldTranslate = ref(true);
const videoFile = ref<File | null>(null);
const { attachVideoToRecipe } = useRecipeVideoAsset();

const sharedText = typeof route.query.recipe_import_text === "string" ? route.query.recipe_import_text : "";
const recipeText = ref<string | null>(sharedText);

const { parseRecipe, navigateToRecipe } = useNewRecipeOptions({
  enableImportKeywords: false,
  enableImportCategories: false,
  enableStayInEditMode: true,
  enableParseRecipe: true,
});

async function createRecipe() {
  const text = recipeText.value?.trim();
  if (!text) {
    return;
  }

  const isValid = await domTextForm.value?.validate();
  if (!isValid?.valid) {
    return;
  }

  state.loading = true;
  const { data, error } = await api.recipes.createOneFromText({
    text,
    translateLanguage: shouldTranslate.value ? i18n.locale.value : null,
  });

  if (error || !data) {
    alert.error(i18n.t("events.something-went-wrong"));
    state.loading = false;
    return;
  }

  if (videoFile.value) {
    await attachVideoToRecipe(data, videoFile.value);
  }

  emit("created", data);
  navigateToRecipe(data, groupSlug.value, props.returnTo || route.path);
}
</script>
