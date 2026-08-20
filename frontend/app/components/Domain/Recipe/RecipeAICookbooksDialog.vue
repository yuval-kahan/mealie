<template>
  <BaseDialog
    v-model="dialog"
    :title="$t('cookbook.ai-generated-books')"
    :icon="$globals.icons.book"
    width="760"
    max-width="95vw"
    :loading="loading"
  >
    <v-card-text>
      <div class="recipe-book-filters mb-4">
        <v-text-field
          v-model="search"
          density="compact"
          hide-details
          clearable
          :prepend-inner-icon="$globals.icons.search"
          :label="$t('search.search')"
        />
        <v-autocomplete
          v-model="organizerFilter"
          density="compact"
          hide-details
          clearable
          :items="organizerOptions"
          :custom-filter="normalizeFilter"
          :label="$t('cookbook.categories-and-tags')"
        />
      </div>

      <v-list v-if="filteredBooks.length" lines="two" class="recipe-ai-book-list">
        <v-list-item v-for="book in filteredBooks" :key="book.id">
          <template #prepend>
            <v-checkbox-btn
              :model-value="bookIncludesRecipe(book)"
              :loading="busyBookIds.has(book.id)"
              @update:model-value="setBookMembership(book, Boolean($event))"
            />
          </template>
          <v-list-item-title>{{ book.name }}</v-list-item-title>
          <v-list-item-subtitle>
            {{ bookOrganizers(book).join(" · ") }}
          </v-list-item-subtitle>
          <template #append>
            <v-btn
              icon
              variant="text"
              size="small"
              :href="api.uploadedBooks.openUrl(book.id)"
              target="_blank"
              :title="$t('cookbook.open-book')"
            >
              <v-icon>{{ $globals.icons.openInNew }}</v-icon>
            </v-btn>
          </template>
        </v-list-item>
      </v-list>
      <v-alert v-else type="info" variant="tonal">
        {{ $t("cookbook.no-library-books") }}
      </v-alert>

      <template v-if="moveSourceOptions.length && moveTargetOptions.length">
        <v-divider class="my-4" />
        <div class="recipe-book-transfer">
          <v-autocomplete
            v-model="moveSourceId"
            density="compact"
            hide-details
            clearable
            :items="moveSourceOptions"
            item-title="title"
            item-value="value"
            :custom-filter="normalizeFilter"
            :label="`${$t('recipe.source')}: ${$t('cookbook.ai-generated-books')}`"
          />
          <v-autocomplete
            v-model="moveTargetId"
            density="compact"
            hide-details
            clearable
            :items="moveTargetOptions"
            item-title="title"
            item-value="value"
            :custom-filter="normalizeFilter"
            :label="`${$t('general.transfer')}: ${$t('cookbook.ai-generated-books')}`"
          />
          <v-btn
            color="primary"
            :prepend-icon="$globals.icons.forward"
            :loading="movingRecipe"
            :disabled="!moveSourceId || !moveTargetId || moveSourceId === moveTargetId"
            @click="moveRecipe"
          >
            {{ $t("general.transfer") }}
          </v-btn>
        </div>
      </template>
    </v-card-text>
  </BaseDialog>
</template>

<script setup lang="ts">
import type { UploadedBook } from "~/lib/api/types/uploaded-book";
import { useUserApi } from "~/composables/api/api-client";
import { alert } from "~/composables/use-toast";
import { normalizeFilter } from "~/composables/use-utils";

interface Props {
  modelValue: boolean;
  recipeSlug: string;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  "update:modelValue": [value: boolean];
}>();
const dialog = computed({
  get: () => props.modelValue,
  set: value => emit("update:modelValue", value),
});
const api = useUserApi();
const i18n = useI18n();
const books = ref<UploadedBook[]>([]);
const loading = ref(false);
const search = ref("");
const organizerFilter = ref<string | null>(null);
const busyBookIds = ref<Set<string>>(new Set());
const moveSourceId = ref<string | null>(null);
const moveTargetId = ref<string | null>(null);
const movingRecipe = ref(false);
let loadVersion = 0;

const aiBooks = computed(() => books.value.filter(book => Boolean(book.bookMetadata?.generated_by_ai)));
const organizerOptions = computed(() => Array.from(new Set(aiBooks.value.flatMap(bookOrganizers)))
  .sort((left, right) => left.localeCompare(right, i18n.locale.value, { numeric: true, sensitivity: "base" })));
const filteredBooks = computed(() => {
  const term = search.value.trim().toLocaleLowerCase();
  return aiBooks.value.filter((book) => {
    const organizers = bookOrganizers(book);
    return (!term || [book.name, ...organizers].join(" ").toLocaleLowerCase().includes(term))
      && (!organizerFilter.value || organizers.includes(organizerFilter.value));
  });
});
const moveSourceOptions = computed(() => aiBooks.value
  .filter(bookIncludesRecipe)
  .map(book => ({ title: book.name, value: book.id }))
  .sort((left, right) => left.title.localeCompare(right.title, i18n.locale.value, { numeric: true, sensitivity: "base" })));
const moveTargetOptions = computed(() => aiBooks.value
  .filter(book => book.id !== moveSourceId.value)
  .map(book => ({ title: book.name, value: book.id }))
  .sort((left, right) => left.title.localeCompare(right.title, i18n.locale.value, { numeric: true, sensitivity: "base" })));

watch(
  () => props.modelValue,
  (open) => {
    if (open) void loadBooks();
    else {
      loadVersion += 1;
      moveSourceId.value = null;
      moveTargetId.value = null;
    }
  },
);

watch(moveSourceOptions, (options) => {
  if (!options.some(option => option.value === moveSourceId.value)) {
    moveSourceId.value = options[0]?.value || null;
  }
}, { immediate: true });

watch(moveTargetOptions, (options) => {
  if (!options.some(option => option.value === moveTargetId.value)) {
    moveTargetId.value = options[0]?.value || null;
  }
}, { immediate: true });

function bookOrganizers(book: UploadedBook) {
  const classification = book.bookMetadata?.classification;
  return [...(classification?.categories || []), ...(classification?.tags || [])].filter(Boolean);
}

function bookIncludesRecipe(book: UploadedBook) {
  return (book.bookMetadata?.included_recipe_slugs || []).includes(props.recipeSlug);
}

function setBookBusy(id: string, busy: boolean) {
  const next = new Set(busyBookIds.value);
  if (busy) next.add(id);
  else next.delete(id);
  busyBookIds.value = next;
}

async function loadBooks() {
  const version = ++loadVersion;
  loading.value = true;
  try {
    const { data, error } = await api.uploadedBooks.getAll();
    if (error || !data || version !== loadVersion) {
      if (version === loadVersion) alert.error(i18n.t("events.something-went-wrong"));
      return;
    }
    books.value = data;
  }
  finally {
    if (version === loadVersion) loading.value = false;
  }
}

async function setBookMembership(book: UploadedBook, included: boolean) {
  if (busyBookIds.value.has(book.id)) return;
  const previous = books.value;
  const slugs = new Set(book.bookMetadata?.included_recipe_slugs || []);
  if (included) slugs.add(props.recipeSlug);
  else slugs.delete(props.recipeSlug);
  books.value = books.value.map(item => item.id === book.id
    ? { ...item, bookMetadata: { ...item.bookMetadata, included_recipe_slugs: [...slugs] } }
    : item);
  setBookBusy(book.id, true);
  try {
    const response = included
      ? await api.uploadedBooks.addRecipeToAiBook(book.id, props.recipeSlug)
      : await api.uploadedBooks.removeRecipeFromAiBook(book.id, props.recipeSlug);
    if (response.error || !response.data) {
      books.value = previous;
      alert.error(i18n.t("events.something-went-wrong"));
      return;
    }
    books.value = books.value.map(item => item.id === book.id ? response.data! : item);
  }
  finally {
    setBookBusy(book.id, false);
  }
}

async function moveRecipe() {
  if (!moveSourceId.value || !moveTargetId.value || moveSourceId.value === moveTargetId.value || movingRecipe.value) {
    return;
  }

  const sourceId = moveSourceId.value;
  const targetId = moveTargetId.value;
  const source = books.value.find(book => book.id === sourceId);
  const target = books.value.find(book => book.id === targetId);
  if (!source || !target) return;

  movingRecipe.value = true;
  setBookBusy(sourceId, true);
  setBookBusy(targetId, true);
  try {
    const targetAlreadyIncludesRecipe = bookIncludesRecipe(target);
    if (!targetAlreadyIncludesRecipe) {
      const addResponse = await api.uploadedBooks.addRecipeToAiBook(targetId, props.recipeSlug);
      if (addResponse.error || !addResponse.data) {
        alert.error(i18n.t("events.something-went-wrong"));
        return;
      }
      books.value = books.value.map(book => book.id === targetId ? addResponse.data! : book);
    }

    const removeResponse = await api.uploadedBooks.removeRecipeFromAiBook(sourceId, props.recipeSlug);
    if (removeResponse.error || !removeResponse.data) {
      if (!targetAlreadyIncludesRecipe) {
        await api.uploadedBooks.removeRecipeFromAiBook(targetId, props.recipeSlug);
        await loadBooks();
      }
      alert.error(i18n.t("events.something-went-wrong"));
      return;
    }
    books.value = books.value.map(book => book.id === sourceId ? removeResponse.data! : book);
    alert.success(i18n.t("events.updated"));
  }
  finally {
    setBookBusy(sourceId, false);
    setBookBusy(targetId, false);
    movingRecipe.value = false;
  }
}
</script>

<style scoped>
.recipe-book-filters {
  display: grid;
  gap: 12px;
  grid-template-columns: minmax(0, 1.4fr) minmax(180px, 1fr);
}
.recipe-ai-book-list {
  max-height: min(55vh, 540px);
  overflow-y: auto;
}
.recipe-book-transfer {
  align-items: center;
  display: grid;
  gap: 12px;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
}
@media (max-width: 600px) {
  .recipe-book-filters,
  .recipe-book-transfer {
    grid-template-columns: 1fr;
  }
}
</style>
