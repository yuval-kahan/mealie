<template>
  <v-container class="narrow-container">
    <WantedBookCreateDialog
      v-model="dialogOpen"
      :book="editingBook"
      @saved="handleSaved"
    />
    <BaseDialog
      v-model="deleteDialogOpen"
      :title="$t('general.confirm')"
      :icon="$globals.icons.delete"
      color="error"
      can-confirm
      @confirm="deleteBook"
    >
      <v-card-text>
        {{ $t("wanted-book.delete-confirm", { title: deletingBook?.title || "" }) }}
      </v-card-text>
    </BaseDialog>

    <BasePageTitle divider>
      <template #title>
        {{ $t("wanted-book.books-to-buy") }}
      </template>
      <template #subtitle>
        {{ $t("wanted-book.description") }}
      </template>
    </BasePageTitle>

    <div class="wanted-toolbar mb-5">
      <v-text-field
        v-model="search"
        :label="$t('search.search')"
        :prepend-inner-icon="$globals.icons.search"
        density="comfortable"
        clearable
        hide-details
      />
      <BaseButton create @click="openCreate" />
    </div>

    <BaseListPagination
      v-if="filteredBooks.length"
      v-model:page="bookPage"
      v-model:items-per-page="booksPerPage"
      :total-items="bookTotal"
    />

    <v-progress-linear v-if="loading" indeterminate color="primary" />
    <div v-else-if="paginatedBooks.length" class="wanted-grid mt-4">
      <v-card v-for="book in paginatedBooks" :key="book.id" class="wanted-card" variant="outlined">
        <v-img
          v-if="book.hasImage && !imageErrors.has(book.id)"
          :src="api.wantedBooks.imageUrl(book)"
          :alt="book.title"
          height="280"
          cover
          @error="imageErrors.add(book.id)"
        />
        <div v-else class="wanted-cover-placeholder">
          <v-icon size="80" color="primary">
            {{ $globals.icons.book }}
          </v-icon>
        </div>
        <v-card-title class="wanted-title">
          {{ book.title }}
        </v-card-title>
        <v-card-subtitle v-if="book.subtitle">
          {{ book.subtitle }}
        </v-card-subtitle>
        <v-card-text class="wanted-content">
          <p v-if="book.authors.length" class="font-weight-medium mb-2">
            {{ book.authors.join(", ") }}
          </p>
          <p v-if="book.summary" class="wanted-summary">
            {{ book.summary }}
          </p>
          <div class="d-flex flex-wrap ga-1 mt-3">
            <v-chip v-if="book.isbn13" size="small" variant="tonal">
              ISBN-13 {{ book.isbn13 }}
            </v-chip>
            <v-chip v-if="book.isbn10" size="small" variant="tonal">
              ISBN-10 {{ book.isbn10 }}
            </v-chip>
            <v-chip v-for="category in book.categories.slice(0, 3)" :key="category" size="small" color="primary" variant="tonal">
              {{ category }}
            </v-chip>
          </div>
        </v-card-text>
        <v-card-actions>
          <a v-if="book.sourceUrl" :href="book.sourceUrl" target="_blank" rel="noopener" class="text-decoration-none">
            <v-btn icon variant="text" :title="$t('wanted-book.open-source')">
              <v-icon>{{ $globals.icons.openInNew }}</v-icon>
            </v-btn>
          </a>
          <v-spacer />
          <v-btn icon variant="text" :title="$t('general.edit')" @click="openEdit(book)">
            <v-icon>{{ $globals.icons.edit }}</v-icon>
          </v-btn>
          <v-btn icon variant="text" color="error" :title="$t('general.delete')" @click="openDelete(book)">
            <v-icon>{{ $globals.icons.delete }}</v-icon>
          </v-btn>
        </v-card-actions>
      </v-card>
    </div>
    <v-alert v-else type="info" variant="tonal">
      {{ $t("wanted-book.no-books") }}
    </v-alert>
  </v-container>
</template>

<script setup lang="ts">
import type { WantedBook } from "~/lib/api/types/wanted-book";
import { useUserApi } from "~/composables/api/api-client";
import { alert } from "~/composables/use-toast";

const i18n = useI18n();
const api = useUserApi();
const books = ref<WantedBook[]>([]);
const loading = ref(true);
const search = ref("");
const dialogOpen = ref(false);
const deleteDialogOpen = ref(false);
const editingBook = ref<WantedBook | null>(null);
const deletingBook = ref<WantedBook | null>(null);
const imageErrors = reactive(new Set<string>());

useSeoMeta({ title: i18n.t("wanted-book.books-to-buy") });

const filteredBooks = computed(() => {
  const query = search.value.trim().toLocaleLowerCase();
  if (!query) return books.value;
  return books.value.filter(book => [
    book.title,
    book.subtitle || "",
    book.authors.join(" "),
    book.isbn10 || "",
    book.isbn13 || "",
    book.publisher || "",
    book.categories.join(" "),
    book.tags.join(" "),
  ].join(" ").toLocaleLowerCase().includes(query));
});
const {
  page: bookPage,
  itemsPerPage: booksPerPage,
  totalItems: bookTotal,
  paginatedItems: paginatedBooks,
} = useListPagination(filteredBooks, 100, "wanted-books");

onMounted(loadBooks);

async function loadBooks() {
  loading.value = true;
  const { data, error } = await api.wantedBooks.getAll();
  books.value = data || [];
  if (error) alert.error(i18n.t("events.something-went-wrong"));
  loading.value = false;
}

function openCreate() {
  editingBook.value = null;
  dialogOpen.value = true;
}

function openEdit(book: WantedBook) {
  editingBook.value = book;
  dialogOpen.value = true;
}

function openDelete(book: WantedBook) {
  deletingBook.value = book;
  deleteDialogOpen.value = true;
}

async function handleSaved() {
  editingBook.value = null;
  imageErrors.clear();
  await loadBooks();
}

async function deleteBook() {
  if (!deletingBook.value) return;
  const { error } = await api.wantedBooks.deleteOne(deletingBook.value.id);
  if (error) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }
  deleteDialogOpen.value = false;
  deletingBook.value = null;
  await loadBooks();
}
</script>

<style scoped>
.wanted-toolbar {
  align-items: center;
  display: grid;
  gap: 12px;
  grid-template-columns: minmax(260px, 1fr) auto;
}

.wanted-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 280px), 1fr));
}

.wanted-card {
  display: flex;
  flex-direction: column;
  min-height: 520px;
}

.wanted-cover-placeholder {
  align-items: center;
  background: rgb(var(--v-theme-surface-variant));
  display: flex;
  height: 280px;
  justify-content: center;
}

.wanted-title {
  overflow-wrap: anywhere;
  white-space: normal;
}

.wanted-content {
  flex: 1;
}

.wanted-summary {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 5;
}

@media (max-width: 600px) {
  .wanted-toolbar {
    grid-template-columns: 1fr;
  }
}
</style>
