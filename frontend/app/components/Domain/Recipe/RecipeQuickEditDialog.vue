<template>
  <BaseDialog
    v-model="dialog"
    :title="$t('recipe.quick-edit')"
    :icon="$globals.icons.edit"
    width="1050"
    max-width="96vw"
    :loading="loading || saving"
    can-submit
    :submit-text="$t('general.save')"
    :submit-icon="$globals.icons.save"
    :submit-disabled="!canSave"
    @submit="save"
    @cancel="close"
  >
    <v-card-text>
      <RecipeQuickEditForm v-if="draft" v-model="draft" />
    </v-card-text>
  </BaseDialog>
</template>

<script setup lang="ts">
import RecipeQuickEditForm from "./RecipeQuickEditForm.vue";
import type { Recipe } from "~/lib/api/types/recipe";
import { useUserApi } from "~/composables/api/api-client";
import { deepCopy } from "~/composables/use-utils";
import { alert } from "~/composables/use-toast";

interface Props {
  modelValue: boolean;
  recipeSlug: string;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  "update:modelValue": [value: boolean];
  "saved": [payload: { slug: string; name: string; recipe: Recipe }];
}>();

const api = useUserApi();
const i18n = useI18n();
const draft = ref<Recipe | null>(null);
const loading = ref(false);
const saving = ref(false);
let loadVersion = 0;

const dialog = computed({
  get: () => props.modelValue,
  set: value => emit("update:modelValue", value),
});
const canSave = computed(() => Boolean(draft.value?.name?.trim()) && !loading.value && !saving.value);

watch(
  () => props.modelValue,
  open => open ? void loadRecipe() : reset(),
);

onBeforeUnmount(reset);

function reset() {
  loadVersion += 1;
  draft.value = null;
  loading.value = false;
  saving.value = false;
}

function close() {
  dialog.value = false;
  reset();
}

async function loadRecipe() {
  const version = ++loadVersion;
  loading.value = true;
  try {
    const { data, error } = await api.recipes.getOne(props.recipeSlug);
    if (version !== loadVersion) return;
    if (error || !data) {
      alert.error(i18n.t("events.something-went-wrong"));
      close();
      return;
    }
    draft.value = deepCopy(data);
  }
  finally {
    if (version === loadVersion) loading.value = false;
  }
}

async function save() {
  if (!draft.value || !canSave.value) return;
  saving.value = true;
  try {
    draft.value.name = draft.value.name?.trim() || "";
    const { data, error } = await api.recipes.updateOne(props.recipeSlug, draft.value);
    if (error || !data) {
      alert.error(i18n.t("events.something-went-wrong"));
      return;
    }
    alert.success(i18n.t("recipe.quick-edit-saved"));
    emit("saved", { slug: data.slug, name: data.name || "", recipe: data });
    dialog.value = false;
  }
  finally {
    saving.value = false;
  }
}
</script>
