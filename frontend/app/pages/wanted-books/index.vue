<template>
  <v-container class="narrow-container">
    <WantedBookCreateDialog
      v-model="dialogOpen"
      :book="editingBook"
      @saved="handleSaved"
    />
    <BaseDialog
      v-model="detailDialogOpen"
      :title="selectedBook?.title || $t('wanted-book.books-to-buy')"
      :icon="$globals.icons.book"
      width="920"
    >
      <div v-if="selectedBook" class="wanted-detail">
        <div class="wanted-detail__cover">
          <v-img
            v-if="selectedBook.hasImage && !imageErrors.has(selectedBook.id)"
            :src="api.wantedBooks.imageUrl(selectedBook)"
            :alt="selectedBook.title"
            max-height="460"
            cover
            @error="imageErrors.add(selectedBook.id)"
          />
          <div v-else class="wanted-cover-placeholder wanted-cover-placeholder--detail">
            <v-icon size="96" color="primary">
              {{ $globals.icons.book }}
            </v-icon>
          </div>
        </div>
        <div class="wanted-detail__content">
          <h2>{{ selectedBook.title }}</h2>
          <p v-if="selectedBook.subtitle" class="text-medium-emphasis">
            {{ selectedBook.subtitle }}
          </p>
          <p v-if="selectedBook.authors.length">
            <strong>{{ $t("wanted-book.authors") }}:</strong> {{ selectedBook.authors.join(", ") }}
          </p>
          <p v-if="selectedBook.publisher">
            <strong>{{ $t("wanted-book.publisher") }}:</strong> {{ selectedBook.publisher }}
          </p>
          <p v-if="selectedBook.publishedYear">
            <strong>{{ $t("wanted-book.published-year") }}:</strong> {{ selectedBook.publishedYear }}
          </p>
          <p v-if="selectedBook.isbn13">
            <strong>ISBN-13:</strong> {{ selectedBook.isbn13 }}
          </p>
          <p v-if="selectedBook.isbn10">
            <strong>ISBN-10:</strong> {{ selectedBook.isbn10 }}
          </p>
          <section v-if="selectedBook.summary">
            <h3>{{ $t("wanted-book.summary") }}</h3>
            <p class="wanted-detail__prose">
              {{ selectedBook.summary }}
            </p>
          </section>
          <section v-if="selectedBook.notes">
            <h3>{{ $t("wanted-book.notes") }}</h3>
            <p class="wanted-detail__prose">
              {{ selectedBook.notes }}
            </p>
          </section>
          <div class="d-flex flex-wrap ga-1">
            <v-chip v-for="category in selectedBook.categories" :key="`category-${category}`" size="small" color="primary" variant="tonal">
              {{ category }}
            </v-chip>
            <v-chip v-for="tag in selectedBook.tags" :key="`tag-${tag}`" size="small" variant="outlined">
              {{ tag }}
            </v-chip>
          </div>
          <a v-if="selectedBook.sourceUrl" :href="selectedBook.sourceUrl" target="_blank" rel="noopener" class="wanted-source-link">
            <v-icon size="18">
              {{ $globals.icons.openInNew }}
            </v-icon>
            {{ $t("wanted-book.open-source") }}
          </a>
        </div>
      </div>
      <template #custom-card-action>
        <v-btn v-if="selectedBook" variant="text" color="primary" @click="openEditFromDetail">
          <v-icon start>
            {{ $globals.icons.edit }}
          </v-icon>
          {{ $t("general.edit") }}
        </v-btn>
      </template>
    </BaseDialog>
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
    <div class="wanted-filters mb-5">
      <v-autocomplete
        v-model="selectedAuthor"
        :items="authorOptions"
        :label="$t('wanted-book.authors')"
        density="compact"
        clearable
        hide-details
      />
      <v-autocomplete
        v-model="selectedCategory"
        :items="categoryOptions"
        :label="$t('category.categories')"
        density="compact"
        clearable
        hide-details
      />
      <BaseListSortControls
        v-model:sort-by="bookSortBy"
        v-model:sort-direction="bookSortDirection"
        :options="bookSortOptions"
      />
    </div>

    <BaseListPagination
      v-if="filteredBooks.length"
      v-model:page="bookPage"
      v-model:items-per-page="booksPerPage"
      :total-items="bookTotal"
    />

    <v-progress-linear v-if="loading" indeterminate color="primary" />
    <div v-else-if="paginatedBooks.length" class="wanted-grid mt-4">
      <v-card
        v-for="book in paginatedBooks"
        :key="book.id"
        class="wanted-card"
        variant="outlined"
        role="button"
        tabindex="0"
        @click="openDetail(book)"
        @keydown.enter="openDetail(book)"
      >
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
          <a
            v-if="book.sourceUrl"
            :href="book.sourceUrl"
            target="_blank"
            rel="noopener"
            class="text-decoration-none"
            @click.stop
          >
            <v-btn icon variant="text" :title="$t('wanted-book.open-source')">
              <v-icon>{{ $globals.icons.openInNew }}</v-icon>
            </v-btn>
          </a>
          <v-spacer />
          <v-btn icon variant="text" :title="$t('general.edit')" @click.stop="openEdit(book)">
            <v-icon>{{ $globals.icons.edit }}</v-icon>
          </v-btn>
          <v-btn icon variant="text" color="error" :title="$t('general.delete')" @click.stop="openDelete(book)">
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
const selectedAuthor = ref<string | null>(null);
const selectedCategory = ref<string | null>(null);
const dialogOpen = ref(false);
const deleteDialogOpen = ref(false);
const detailDialogOpen = ref(false);
const editingBook = ref<WantedBook | null>(null);
const deletingBook = ref<WantedBook | null>(null);
const selectedBook = ref<WantedBook | null>(null);
const imageErrors = reactive(new Set<string>());

useSeoMeta({ title: i18n.t("wanted-book.books-to-buy") });

const authorOptions = computed(() => [...new Set(books.value.flatMap(book => book.authors))]
  .sort((left, right) => left.localeCompare(right, i18n.locale.value, { sensitivity: "base" })));
const categoryOptions = computed(() => [...new Set(books.value.flatMap(book => book.categories))]
  .sort((left, right) => left.localeCompare(right, i18n.locale.value, { sensitivity: "base" })));
const WANTED_BOOK_SORT_KEYS = ["title", "author", "publishedYear", "created"] as const;
type WantedBookSortKey = typeof WANTED_BOOK_SORT_KEYS[number];
const {
  sortBy: bookSortBy,
  sortDirection: bookSortDirection,
} = usePersistedListSort(WANTED_BOOK_SORT_KEYS, "title", "asc", "wanted-books");
const bookSortOptions = computed<{ title: string; value: WantedBookSortKey }[]>(() => [
  { title: i18n.t("wanted-book.title"), value: "title" },
  { title: i18n.t("wanted-book.authors"), value: "author" },
  { title: i18n.t("wanted-book.published-year"), value: "publishedYear" },
  { title: i18n.t("catalog.created-at"), value: "created" },
]);

const filteredBooks = computed(() => {
  const query = search.value.trim().toLocaleLowerCase();
  return books.value.filter((book) => {
    if (selectedAuthor.value && !book.authors.includes(selectedAuthor.value)) return false;
    if (selectedCategory.value && !book.categories.includes(selectedCategory.value)) return false;
    if (!query) return true;
    return [
      book.title,
      book.subtitle || "",
      book.authors.join(" "),
      book.isbn10 || "",
      book.isbn13 || "",
      book.publisher || "",
      book.categories.join(" "),
      book.tags.join(" "),
    ].join(" ").toLocaleLowerCase().includes(query);
  });
});
const sortedBooks = sortListItems(
  filteredBooks,
  book => ({
    title: book.title,
    author: book.authors[0],
    publishedYear: book.publishedYear,
    created: book.createdAt,
  })[bookSortBy.value],
  bookSortDirection,
  i18n.locale,
);
const {
  page: bookPage,
  itemsPerPage: booksPerPage,
  totalItems: bookTotal,
  paginatedItems: paginatedBooks,
} = useListPagination(sortedBooks, 100, "wanted-books");

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

function openDetail(book: WantedBook) {
  selectedBook.value = book;
  detailDialogOpen.value = true;
}

function openEditFromDetail() {
  if (!selectedBook.value) return;
  detailDialogOpen.value = false;
  openEdit(selectedBook.value);
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

.wanted-filters {
  align-items: start;
  display: grid;
  gap: 12px;
  grid-template-columns: minmax(170px, 0.8fr) minmax(170px, 0.8fr) minmax(280px, 1.6fr);
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
  cursor: pointer;
  transition:
    border-color 140ms ease,
    box-shadow 140ms ease,
    transform 140ms ease;
}

.wanted-card:hover,
.wanted-card:focus-visible {
  border-color: rgb(var(--v-theme-primary));
  box-shadow: 0 5px 16px rgba(0, 0, 0, 0.13);
  outline: none;
  transform: translateY(-2px);
}

.wanted-cover-placeholder {
  align-items: center;
  background: rgb(var(--v-theme-surface-variant));
  display: flex;
  height: 280px;
  justify-content: center;
}

.wanted-cover-placeholder--detail {
  height: 420px;
}

.wanted-detail {
  display: grid;
  gap: 24px;
  grid-template-columns: minmax(220px, 320px) minmax(0, 1fr);
  padding: 20px;
}

.wanted-detail__cover {
  overflow: hidden;
  align-self: start;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
}

.wanted-detail__content h2,
.wanted-detail__content h3 {
  margin-block: 0 10px;
}

.wanted-detail__prose {
  line-height: 1.7;
  white-space: pre-wrap;
}

.wanted-source-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 18px;
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

  .wanted-filters {
    grid-template-columns: 1fr;
  }

  .wanted-detail {
    grid-template-columns: 1fr;
    padding: 10px;
  }
}
</style>
