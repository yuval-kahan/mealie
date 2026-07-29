<template>
  <BaseDialog
    v-model="dialogOpen"
    :title="book ? $t('wanted-book.edit') : $t('wanted-book.quick-add')"
    :icon="$globals.icons.book"
    width="820"
    max-width="96vw"
    can-submit
    keep-open
    disable-submit-on-enter
    :loading="saving"
    :submit-disabled="!canSubmit"
    :submit-text="$t('general.save')"
    @submit="submit"
    @close="reset"
  >
    <v-card-text class="pt-4">
      <v-btn-toggle
        v-if="!book"
        v-model="mode"
        mandatory
        divided
        density="comfortable"
        class="mb-4"
      >
        <v-btn value="manual" :prepend-icon="$globals.icons.edit">
          {{ $t("wanted-book.manual") }}
        </v-btn>
        <v-btn value="ai" :prepend-icon="$globals.icons.robot">
          {{ $t("wanted-book.add-with-ai") }}
        </v-btn>
      </v-btn-toggle>

      <template v-if="mode === 'ai' && !book">
        <v-textarea
          v-model="aiPrompt"
          :label="$t('wanted-book.ai-prompt')"
          :hint="$t('wanted-book.ai-prompt-hint')"
          persistent-hint
          rows="5"
          auto-grow
          variant="outlined"
        />
        <v-text-field
          v-model="aiUrl"
          :label="$t('wanted-book.source-url')"
          :prepend-inner-icon="$globals.icons.link"
          type="url"
          variant="outlined"
          density="comfortable"
        />
      </template>

      <template v-else>
        <v-text-field
          v-model="form.title"
          :label="$t('wanted-book.title')"
          autofocus
          variant="outlined"
          density="comfortable"
        />
        <v-text-field
          v-model="form.subtitle"
          :label="$t('wanted-book.subtitle')"
          variant="outlined"
          density="comfortable"
        />
        <v-combobox
          v-model="form.authors"
          :label="$t('wanted-book.authors')"
          multiple
          chips
          closable-chips
          clearable
          variant="outlined"
          density="comfortable"
        />
        <v-row dense>
          <v-col cols="12" md="6">
            <v-text-field
              v-model="form.isbn10"
              label="ISBN-10"
              variant="outlined"
              density="comfortable"
            />
          </v-col>
          <v-col cols="12" md="6">
            <v-text-field
              v-model="form.isbn13"
              label="ISBN-13"
              variant="outlined"
              density="comfortable"
            />
          </v-col>
        </v-row>
        <v-row dense>
          <v-col cols="12" md="8">
            <v-text-field
              v-model="form.publisher"
              :label="$t('wanted-book.publisher')"
              variant="outlined"
              density="comfortable"
            />
          </v-col>
          <v-col cols="12" md="4">
            <v-text-field
              v-model.number="form.publishedYear"
              :label="$t('wanted-book.published-year')"
              type="number"
              min="1"
              max="9999"
              variant="outlined"
              density="comfortable"
            />
          </v-col>
        </v-row>
        <v-textarea
          v-model="form.summary"
          :label="$t('wanted-book.summary')"
          rows="4"
          auto-grow
          variant="outlined"
        />
        <v-text-field
          v-model="form.sourceUrl"
          :label="$t('wanted-book.source-url')"
          :prepend-inner-icon="$globals.icons.link"
          type="url"
          variant="outlined"
          density="comfortable"
        />
        <v-combobox
          v-model="form.categories"
          :label="$t('category.categories')"
          multiple
          chips
          closable-chips
          clearable
          variant="outlined"
          density="comfortable"
        />
        <v-combobox
          v-model="form.tags"
          :label="$t('tag.tags')"
          multiple
          chips
          closable-chips
          clearable
          variant="outlined"
          density="comfortable"
        />
        <v-textarea
          v-model="form.notes"
          :label="$t('wanted-book.notes')"
          rows="3"
          auto-grow
          variant="outlined"
        />

        <v-divider class="my-4" />
        <v-file-input
          v-model="imageFile"
          accept="image/*"
          :label="$t('wanted-book.cover')"
          :prepend-inner-icon="$globals.icons.fileImage"
          prepend-icon=""
          clearable
          variant="outlined"
          density="comfortable"
        />
        <v-text-field
          v-model="form.coverSourceUrl"
          :label="$t('wanted-book.cover-url')"
          :prepend-inner-icon="$globals.icons.link"
          type="url"
          variant="outlined"
          density="comfortable"
        />
      </template>
    </v-card-text>
  </BaseDialog>
</template>

<script setup lang="ts">
import type { WantedBook, WantedBookCreate } from "~/lib/api/types/wanted-book";
import { useUserApi } from "~/composables/api/api-client";
import { alert } from "~/composables/use-toast";

const props = defineProps<{ book?: WantedBook | null }>();
const emit = defineEmits<{ saved: [book: WantedBook] }>();
const dialogOpen = defineModel<boolean>({ default: false });
const i18n = useI18n();
const api = useUserApi();
const saving = ref(false);
const mode = ref<"manual" | "ai">("manual");
const aiPrompt = ref("");
const aiUrl = ref("");
const imageFile = ref<File | File[] | null>(null);

const emptyForm = (): WantedBookCreate => ({
  title: "",
  subtitle: "",
  authors: [],
  isbn10: "",
  isbn13: "",
  publisher: "",
  publishedYear: null,
  summary: "",
  sourceUrl: "",
  coverSourceUrl: "",
  categories: [],
  tags: [],
  notes: "",
});
const form = reactive<WantedBookCreate>(emptyForm());
const canSubmit = computed(() => mode.value === "ai" && !props.book
  ? Boolean(aiPrompt.value.trim() || aiUrl.value.trim())
  : Boolean(form.title.trim()));

watch(() => [dialogOpen.value, props.book] as const, ([open]) => {
  if (open) load();
});

function load() {
  mode.value = "manual";
  aiPrompt.value = "";
  aiUrl.value = "";
  imageFile.value = null;
  Object.assign(form, props.book
    ? {
        title: props.book.title,
        subtitle: props.book.subtitle || "",
        authors: [...props.book.authors],
        isbn10: props.book.isbn10 || "",
        isbn13: props.book.isbn13 || "",
        publisher: props.book.publisher || "",
        publishedYear: props.book.publishedYear || null,
        summary: props.book.summary || "",
        sourceUrl: props.book.sourceUrl || "",
        coverSourceUrl: props.book.coverSourceUrl || "",
        categories: [...props.book.categories],
        tags: [...props.book.tags],
        notes: props.book.notes || "",
      }
    : emptyForm());
}

function reset() {
  load();
  Object.assign(form, emptyForm());
}

function selectedImage() {
  if (imageFile.value instanceof File) return imageFile.value;
  return Array.isArray(imageFile.value) ? imageFile.value[0] || null : null;
}

async function submit() {
  saving.value = true;
  const response = props.book
    ? await api.wantedBooks.updateOne(props.book.id, form)
    : mode.value === "ai"
      ? await api.wantedBooks.createWithAI({ prompt: aiPrompt.value || null, url: aiUrl.value || null })
      : await api.wantedBooks.createOne(form);

  if (!response.data || response.error) {
    saving.value = false;
    const detail = response.error?.response?.data?.detail;
    alert.error(typeof detail?.message === "string" ? detail.message : i18n.t("events.something-went-wrong"));
    return;
  }

  let saved = response.data;
  const file = selectedImage();
  if (file) {
    const imageResponse = await api.wantedBooks.uploadImage(saved.id, file);
    if (imageResponse.data) saved = imageResponse.data;
  }
  saving.value = false;
  emit("saved", saved);
  dialogOpen.value = false;
  reset();
}
</script>
