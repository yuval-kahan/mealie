<template>
  <BaseDialog
    v-model="dialog"
    :title="$t('cookbook.rename-book')"
    :icon="$globals.icons.edit"
    can-submit
    keep-open
    :loading="saving"
    :submit-disabled="!normalizedName || normalizedName === book?.name"
    :submit-text="$t('general.save')"
    :submit-icon="$globals.icons.save"
    @submit="save"
  >
    <v-card-text class="pt-4">
      <v-text-field
        v-model="name"
        autofocus
        maxlength="255"
        counter
        variant="outlined"
        :label="$t('cookbook.uploaded-book-name')"
        @keydown.enter.prevent="save"
      />
    </v-card-text>
  </BaseDialog>
</template>

<script setup lang="ts">
import type { UploadedBook } from "~/lib/api/types/uploaded-book";
import { useUserApi } from "~/composables/api/api-client";
import { alert } from "~/composables/use-toast";

interface Props {
  modelValue: boolean;
  book: UploadedBook | null;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  "update:modelValue": [value: boolean];
  "renamed": [book: UploadedBook];
}>();

const api = useUserApi();
const i18n = useI18n();
const name = ref("");
const saving = ref(false);
const normalizedName = computed(() => name.value.trim());
const dialog = computed({
  get: () => props.modelValue,
  set: value => emit("update:modelValue", value),
});

watch(
  () => [props.modelValue, props.book?.id] as const,
  ([open]) => {
    if (open) name.value = props.book?.name || "";
  },
  { immediate: true },
);

async function save() {
  if (!props.book || !normalizedName.value || normalizedName.value === props.book.name || saving.value) return;
  saving.value = true;
  try {
    const { data, error } = await api.uploadedBooks.rename(props.book.id, normalizedName.value);
    if (error || !data) {
      alert.error(i18n.t("cookbook.rename-book-failed"));
      return;
    }
    alert.success(i18n.t("cookbook.rename-book-success"));
    emit("renamed", data);
    dialog.value = false;
  }
  finally {
    saving.value = false;
  }
}
</script>
