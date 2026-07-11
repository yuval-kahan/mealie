<template>
  <div>
    <!-- Create Dialog -->
    <BaseDialog
      v-if="createTarget"
      v-model="dialogStates.create"
      width="100%"
      max-width="1100px"
      :icon="$globals.icons.pages"
      :title="$t('cookbook.create-a-cookbook')"
      :submit-icon="$globals.icons.save"
      :submit-text="$t('general.save')"
      :submit-disabled="!createTarget.queryFilterString"
      can-submit
      @submit="actions.updateOne(createTarget)"
      @cancel="deleteCreateTarget()"
    >
      <v-card-text>
        <CookbookEditor :key="createTargetKey" v-model="createTarget" />
      </v-card-text>
    </BaseDialog>

    <!-- Delete Dialog -->
    <BaseDialog
      v-model="dialogStates.delete"
      :title="$t('general.delete-with-name', { name: $t('cookbook.cookbook') })"
      :icon="$globals.icons.alertCircle"
      color="error"
      can-confirm
      @confirm="deleteCookbook()"
    >
      <v-card-text>
        <p>{{ $t("general.confirm-delete-generic-with-name", { name: $t("cookbook.cookbook") }) }}</p>
        <p v-if="deleteTarget" class="mt-4 ml-4">
          {{ deleteTarget.name }}
        </p>
      </v-card-text>
    </BaseDialog>

    <BaseDialog
      v-model="aiBookDialog"
      :title="$t('cookbook.create-book-with-ai')"
      :icon="$globals.icons.robot"
      width="680"
      max-width="96vw"
      can-submit
      keep-open
      :loading="aiBookCreating"
      :submit-disabled="aiBookSubmitDisabled"
      @submit="createAIBook"
    >
      <v-card-text class="pt-4">
        <v-btn-toggle v-model="aiBookMode" mandatory divided color="primary" class="mb-4">
          <v-btn value="preset" :prepend-icon="$globals.icons.formatListCheck">
            {{ $t("cookbook.ai-book-preset") }}
          </v-btn>
          <v-btn value="prompt" :prepend-icon="$globals.icons.messageText">
            {{ $t("cookbook.ai-book-free-definition") }}
          </v-btn>
        </v-btn-toggle>
        <v-select
          v-if="aiBookMode === 'preset'"
          v-model="aiBookPreset"
          :items="aiBookPresetOptions"
          item-title="title"
          item-value="value"
          variant="outlined"
          :label="$t('cookbook.ai-book-preset')"
        />
        <v-textarea
          v-else
          v-model="aiBookPrompt"
          variant="outlined"
          rows="4"
          auto-grow
          maxlength="2000"
          counter
          :label="$t('cookbook.ai-book-free-definition')"
          :placeholder="$t('cookbook.ai-book-prompt-placeholder')"
        />
        <v-text-field
          v-model="aiBookTitle"
          variant="outlined"
          :label="$t('cookbook.ai-book-title-optional')"
        />
        <v-row dense>
          <v-col cols="12" sm="6">
            <v-number-input
              v-model="aiBookMaxRecipes"
              :min="5"
              :max="200"
              variant="outlined"
              control-variant="stacked"
              :label="$t('cookbook.recipes-per-volume')"
            />
          </v-col>
          <v-col cols="12" sm="6">
            <v-number-input
              v-model="aiBookMaxPages"
              :min="40"
              :max="1000"
              variant="outlined"
              control-variant="stacked"
              :label="$t('cookbook.estimated-pages-per-volume')"
            />
          </v-col>
        </v-row>
        <v-alert density="compact" variant="tonal" type="info">
          {{ $t("cookbook.ai-book-volume-description") }}
        </v-alert>
      </v-card-text>
    </BaseDialog>

    <BaseDialog
      v-model="uploadedBookDeleteDialog"
      :title="$t('cookbook.delete-book')"
      :icon="$globals.icons.delete"
      color="error"
      can-confirm
      :loading="uploadedBookDeleting"
      @confirm="deleteUploadedBook"
    >
      <v-card-text>
        {{ $t("cookbook.delete-uploaded-book-confirm") }}
        <strong v-if="uploadedBookDeleteTarget" class="d-block mt-3">{{ uploadedBookDeleteTarget.name }}</strong>
      </v-card-text>
    </BaseDialog>

    <UploadedBookRecipeDeleteDialog
      v-model="bookRecipeDeleteDialog"
      :book="bookRecipeDeleteTarget"
      @deleted="handleBookRecipesDeleted"
    />

    <!-- Cookbook Page -->
    <!-- Page Title -->
    <v-container class="lg-container">
      <BasePageTitle divider>
        <template #header>
          <v-img width="100%" max-height="100" max-width="100" src="/svgs/manage-cookbooks.svg" />
        </template>
        <template #title>
          {{ $t("cookbook.cookbooks") }}
        </template>
        {{ $t("cookbook.description") }}
      </BasePageTitle>

      <div class="my-6">
        <v-checkbox
          v-model="cookbookPreferences.hideOtherHouseholds"
          :label="$t('cookbook.hide-cookbooks-from-other-households')"
          hide-details
          color="primary"
        />
        <div class="ml-10 mt-n3">
          <p class="text-subtitle-2 my-0 py-0">
            {{ $t("cookbook.hide-cookbooks-from-other-households-description") }}
          </p>
        </div>
      </div>

      <!-- Create New -->
      <BaseButton create @click="createCookbook" />

      <!-- Cookbook List -->
      <v-expansion-panels class="mt-2">
        <VueDraggable
          v-model="myCookbooks"
          handle=".handle"
          :delay="250"
          :delay-on-touch-only="true"
          style="width: 100%"
          @end="updateAll(myCookbooks)"
        >
          <v-expansion-panel
            v-for="(cookbook, index) in myCookbooks"
            :key="cookbook.id"
            class="my-2 left-border rounded"
          >
            <v-expansion-panel-title disable-icon-rotate class="text-h6 opacity-80">
              <div class="d-flex align-center">
                <v-icon size="large" start>
                  {{ $globals.icons.pages }}
                </v-icon>
                {{ cookbook.name }}
              </div>
              <template #actions>
                <div class="d-flex align-center">
                  <v-btn icon variant="text" class="ml-2">
                    <v-icon>
                      {{ $globals.icons.edit }}
                    </v-icon>
                  </v-btn>
                  <v-icon class="handle" :size="40">
                    {{ $globals.icons.arrowUpDown }}
                  </v-icon>
                </div>
              </template>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <CookbookEditor
                v-model="myCookbooks[index]"
                :collapsable="false"
              />
              <v-card-actions>
                <v-spacer />
                <BaseButtonGroup
                  :buttons="[
                    {
                      icon: $globals.icons.delete,
                      text: $t('general.delete'),
                      event: 'delete',
                    },
                    {
                      icon: $globals.icons.save,
                      text: $t('general.save'),
                      event: 'save',
                      disabled: !cookbook.queryFilterString,
                    },
                  ]"
                  @delete="deleteEventHandler(myCookbooks[index])"
                  @save="actions.updateOne(myCookbooks[index])"
                />
              </v-card-actions>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </VueDraggable>
      </v-expansion-panels>

      <section class="cookbook-library mt-12 pt-8">
        <div class="d-flex flex-wrap align-center ga-3 mb-5">
          <div>
            <h2 class="text-h5 font-weight-medium">
              {{ $t("cookbook.book-library") }}
            </h2>
            <p class="text-body-2 text-medium-emphasis mb-0">
              {{ $t("cookbook.book-library-description") }}
            </p>
          </div>
          <v-spacer />
          <v-btn
            color="primary"
            variant="tonal"
            :prepend-icon="$globals.icons.robot"
            @click="aiBookDialog = true"
          >
            {{ $t("cookbook.create-book-with-ai") }}
          </v-btn>
          <v-btn
            icon
            variant="text"
            :loading="uploadedBooksLoading"
            :title="$t('general.refresh')"
            @click="loadUploadedBooks"
          >
            <v-icon :icon="$globals.icons.refresh" />
          </v-btn>
        </div>

        <div class="cookbook-library__filters mb-6">
          <v-text-field
            v-model="bookSearch"
            variant="outlined"
            density="comfortable"
            hide-details
            clearable
            :prepend-inner-icon="$globals.icons.search"
            :label="$t('search.search')"
          />
          <v-select
            v-model="bookTypeFilter"
            :items="bookTypeOptions"
            item-title="title"
            item-value="value"
            variant="outlined"
            density="comfortable"
            hide-details
            :label="$t('cookbook.book-type')"
          />
          <v-autocomplete
            v-model="bookMetadataFilters"
            :items="bookMetadataOptions"
            multiple
            chips
            closable-chips
            clearable
            variant="outlined"
            density="comfortable"
            hide-details
            :label="$t('cookbook.categories-and-tags')"
          />
        </div>

        <v-alert v-if="!uploadedBooksLoading && !filteredUploadedBooks.length" type="info" variant="tonal">
          {{ $t("cookbook.no-library-books") }}
        </v-alert>
        <div v-else class="cookbook-library__grid">
          <v-card
            v-for="book in filteredUploadedBooks"
            :key="book.id"
            variant="outlined"
            class="cookbook-library__book"
          >
            <div class="cookbook-library__cover">
              <v-img
                v-if="book.bookMetadata?.cover_file_name"
                :src="api.uploadedBooks.coverUrl(book.id)"
                :alt="book.name"
                cover
                height="260"
              >
                <template #error>
                  <div class="cookbook-library__cover-fallback">
                    <v-icon :icon="bookIcon(book)" size="72" />
                  </div>
                </template>
              </v-img>
              <div v-else class="cookbook-library__cover-fallback">
                <v-icon :icon="bookIcon(book)" size="72" />
              </div>
            </div>
            <v-card-item>
              <template #prepend>
                <v-avatar color="surface-variant" rounded="sm">
                  <v-icon :icon="bookIcon(book)" />
                </v-avatar>
              </template>
              <v-card-title class="text-subtitle-1 text-wrap">
                {{ book.name }}
              </v-card-title>
              <v-card-subtitle>
                {{ bookTypeLabel(book) }} · {{ book.extension.toUpperCase() }}
              </v-card-subtitle>
            </v-card-item>
            <v-card-text class="pt-0">
              <p v-if="bookClassification(book)?.summary" class="book-summary mb-3">
                {{ bookClassification(book)?.summary }}
              </p>
              <div class="d-flex flex-wrap ga-1">
                <v-chip
                  v-for="label in bookLabels(book).slice(0, 8)"
                  :key="label"
                  size="x-small"
                  variant="tonal"
                >
                  {{ label }}
                </v-chip>
              </div>
              <v-progress-linear
                v-if="book.classificationStatus === 'processing'"
                indeterminate
                color="primary"
                class="mt-3"
              />
              <v-alert
                v-else-if="book.classificationStatus === 'failed'"
                density="compact"
                type="warning"
                variant="tonal"
                class="mt-3"
              >
                {{ $t("cookbook.book-classification-failed") }}
              </v-alert>
            </v-card-text>
            <v-card-actions>
              <v-btn variant="text" color="primary" :prepend-icon="$globals.icons.openInNew" @click="openUploadedBook(book)">
                {{ $t("cookbook.open-book") }}
              </v-btn>
              <v-spacer />
              <v-btn
                v-if="isGeneratedBook(book)"
                icon
                variant="text"
                :loading="refreshingBookIds.has(book.id)"
                :title="$t('cookbook.refresh-ai-book')"
                @click="refreshAIBook(book)"
              >
                <v-icon :icon="$globals.icons.refresh" />
              </v-btn>
              <v-btn
                v-else
                icon
                variant="text"
                :loading="book.classificationStatus === 'processing'"
                :title="$t('cookbook.organize-book-with-ai')"
                @click="classifyUploadedBook(book)"
              >
                <v-icon :icon="$globals.icons.robot" />
              </v-btn>
              <v-btn
                v-if="bookRecipeSource(book)?.extractionRecipesCreated"
                icon
                variant="text"
                color="warning"
                :title="$t('cookbook.delete-book-recipes')"
                @click="openBookRecipeDeleteDialog(book)"
              >
                <v-icon :icon="$globals.icons.broom" />
              </v-btn>
              <v-btn icon variant="text" color="error" :title="$t('general.delete')" @click="confirmUploadedBookDelete(book)">
                <v-icon :icon="$globals.icons.delete" />
              </v-btn>
            </v-card-actions>
          </v-card>
        </div>
      </section>
    </v-container>
  </div>
</template>

<script setup lang="ts">
import { VueDraggable } from "vue-draggable-plus";
import { useCookbookStore } from "~/composables/store/use-cookbook-store";
import { useHouseholdSelf } from "@/composables/use-households";
import CookbookEditor from "~/components/Domain/Cookbook/CookbookEditor.vue";
import type { CreateCookBook, ReadCookBook } from "~/lib/api/types/cookbook";
import { useCookbookPreferences } from "~/composables/use-users/preferences";
import type { AICookbookGenerateRequest, UploadedBook, UploadedBookClassification } from "~/lib/api/types/uploaded-book";
import { useUserApi } from "~/composables/api";
import { alert } from "~/composables/use-toast";

definePageMeta({
  middleware: ["group-only"],
});

const dialogStates = reactive({
  create: false,
  delete: false,
});

const i18n = useI18n();
const route = useRoute();
const api = useUserApi();
const { $globals } = useNuxtApp();

// Set page title
useSeoMeta({
  title: i18n.t("cookbook.cookbooks"),
});

const auth = useMealieAuth();
const { store: allCookbooks, actions, updateAll } = useCookbookStore();

// Make a local reactive copy of myCookbooks
const myCookbooks = ref<ReadCookBook[]>([]);
watch(
  allCookbooks,
  (cookbooks) => {
    myCookbooks.value
      = cookbooks?.filter(
        cookbook => cookbook.householdId === auth.user.value?.householdId,
      ).sort((a, b) => a.position > b.position) ?? [];
  },
  { immediate: true },
);

const { household } = useHouseholdSelf();
const cookbookPreferences = useCookbookPreferences();

const uploadedBooks = ref<UploadedBook[]>([]);
const uploadedBooksLoading = ref(false);
const bookSearch = ref("");
const bookTypeFilter = ref("all");
const bookMetadataFilters = ref<string[]>([]);
const aiBookDialog = ref(route.query.generate === "true");
const aiBookCreating = ref(false);
const aiBookMode = ref<"preset" | "prompt">("preset");
const aiBookPreset = ref("Italian food");
const aiBookPrompt = ref("");
const aiBookTitle = ref("");
const aiBookMaxRecipes = ref(100);
const aiBookMaxPages = ref(300);
const refreshingBookIds = ref(new Set<string>());
const uploadedBookDeleteDialog = ref(false);
const uploadedBookDeleteTarget = ref<UploadedBook | null>(null);
const uploadedBookDeleting = ref(false);
const bookRecipeDeleteDialog = ref(false);
const bookRecipeDeleteTarget = ref<UploadedBook | null>(null);
let classificationRefreshTimer: number | null = null;

const aiBookPresetOptions = computed(() => [
  { title: i18n.t("cookbook.preset-italian"), value: "Italian food" },
  { title: i18n.t("cookbook.preset-dinner"), value: "Dinner recipes" },
  { title: i18n.t("cookbook.preset-michelin"), value: "Michelin-level chef recipes" },
  { title: i18n.t("cookbook.preset-baking"), value: "Baking and pastry" },
  { title: i18n.t("cookbook.preset-quick"), value: "Quick recipes" },
  { title: i18n.t("cookbook.preset-vegetarian"), value: "Vegetarian recipes" },
]);
const bookTypeOptions = computed(() => [
  { title: i18n.t("cookbook.all-books"), value: "all" },
  { title: i18n.t("cookbook.uploaded-books"), value: "uploaded" },
  { title: i18n.t("cookbook.translated-books"), value: "translated" },
  { title: i18n.t("cookbook.ai-generated-books"), value: "generated" },
]);
const aiBookSubmitDisabled = computed(() =>
  aiBookMode.value === "preset" ? !aiBookPreset.value.trim() : !aiBookPrompt.value.trim(),
);

function bookClassification(book: UploadedBook): UploadedBookClassification | undefined {
  return book.bookMetadata?.classification;
}

function isGeneratedBook(book: UploadedBook) {
  return book.bookMetadata?.generated_by_ai === true;
}

function bookRecipeSource(book: UploadedBook) {
  if (!book.isTranslatedBook) {
    return book;
  }
  return uploadedBooks.value.find(candidate => candidate.id === book.translatedFromBookId) || null;
}

function bookLabels(book: UploadedBook) {
  const classification = bookClassification(book);
  return Array.from(new Set([
    ...(classification?.cuisines || []),
    ...(classification?.categories || []),
    ...(classification?.tags || []),
    classification?.difficulty,
    classification?.teaching_level,
  ].filter((value): value is string => Boolean(value && value !== "unspecified"))));
}

const bookMetadataOptions = computed(() =>
  Array.from(new Set(uploadedBooks.value.flatMap(bookLabels))).sort((a, b) => a.localeCompare(b)),
);

function matchesBookType(book: UploadedBook) {
  if (bookTypeFilter.value === "generated") return isGeneratedBook(book);
  if (bookTypeFilter.value === "translated") return book.isTranslatedBook;
  if (bookTypeFilter.value === "uploaded") return !book.isTranslatedBook && !isGeneratedBook(book);
  return true;
}

const filteredUploadedBooks = computed(() => {
  const query = bookSearch.value.trim().toLocaleLowerCase();
  return uploadedBooks.value.filter((book) => {
    if (!matchesBookType(book)) return false;
    const labels = bookLabels(book);
    if (bookMetadataFilters.value.some(filter => !labels.includes(filter))) return false;
    if (!query) return true;
    return `${book.name} ${book.originalFileName} ${labels.join(" ")} ${bookClassification(book)?.summary || ""}`
      .toLocaleLowerCase()
      .includes(query);
  });
});

async function loadUploadedBooks() {
  uploadedBooksLoading.value = true;
  try {
    const { data } = await api.uploadedBooks.getAll();
    uploadedBooks.value = data || [];
  }
  finally {
    uploadedBooksLoading.value = false;
  }
}

function openUploadedBook(book: UploadedBook) {
  window.open(api.uploadedBooks.fileUrl(book.id), "_blank", "noopener");
}

async function classifyUploadedBook(book: UploadedBook) {
  const { data, error } = await api.uploadedBooks.classify(book.id);
  if (error || !data) {
    alert.error(i18n.t("cookbook.book-classification-failed"));
    return;
  }
  const index = uploadedBooks.value.findIndex(item => item.id === book.id);
  if (index >= 0) uploadedBooks.value[index] = data;
  if (classificationRefreshTimer !== null) {
    window.clearTimeout(classificationRefreshTimer);
  }
  classificationRefreshTimer = window.setTimeout(() => {
    classificationRefreshTimer = null;
    void loadUploadedBooks();
  }, 5000);
}

async function createAIBook() {
  const payload: AICookbookGenerateRequest = {
    mode: aiBookMode.value,
    preset: aiBookMode.value === "preset" ? aiBookPreset.value : null,
    prompt: aiBookMode.value === "prompt" ? aiBookPrompt.value.trim() : null,
    title: aiBookTitle.value.trim() || null,
    maxRecipesPerVolume: aiBookMaxRecipes.value,
    maxEstimatedPagesPerVolume: aiBookMaxPages.value,
  };
  aiBookCreating.value = true;
  try {
    const { data, error } = await api.uploadedBooks.generate(payload);
    if (error || !data?.length) {
      alert.error(i18n.t("cookbook.ai-book-create-failed"));
      return;
    }
    aiBookDialog.value = false;
    alert.success(i18n.t("cookbook.ai-book-created", { count: data.length }));
    await loadUploadedBooks();
  }
  finally {
    aiBookCreating.value = false;
  }
}

async function refreshAIBook(book: UploadedBook) {
  refreshingBookIds.value = new Set(refreshingBookIds.value).add(book.id);
  try {
    const { error } = await api.uploadedBooks.refreshAi(book.id);
    if (error) alert.error(i18n.t("cookbook.ai-book-refresh-failed"));
    else alert.success(i18n.t("cookbook.ai-book-refreshed"));
    await loadUploadedBooks();
  }
  finally {
    const next = new Set(refreshingBookIds.value);
    next.delete(book.id);
    refreshingBookIds.value = next;
  }
}

function confirmUploadedBookDelete(book: UploadedBook) {
  uploadedBookDeleteTarget.value = book;
  uploadedBookDeleteDialog.value = true;
}

function openBookRecipeDeleteDialog(book: UploadedBook) {
  bookRecipeDeleteTarget.value = bookRecipeSource(book) || book;
  bookRecipeDeleteDialog.value = true;
}

function handleBookRecipesDeleted(bookId: string, _deletedCount: number, remainingCount: number) {
  const book = uploadedBooks.value.find(item => item.id === bookId);
  if (book) {
    book.extractionRecipesCreated = remainingCount;
  }
  bookRecipeDeleteTarget.value = null;
}

async function deleteUploadedBook() {
  if (!uploadedBookDeleteTarget.value) return;
  uploadedBookDeleting.value = true;
  try {
    const { error } = await api.uploadedBooks.delete(uploadedBookDeleteTarget.value.id);
    if (error) alert.error(i18n.t("cookbook.delete-book-failed"));
    else uploadedBooks.value = uploadedBooks.value.filter(book => book.id !== uploadedBookDeleteTarget.value?.id);
    uploadedBookDeleteDialog.value = false;
    uploadedBookDeleteTarget.value = null;
  }
  finally {
    uploadedBookDeleting.value = false;
  }
}

function bookTypeLabel(book: UploadedBook) {
  if (isGeneratedBook(book)) return i18n.t("cookbook.ai-generated-book");
  if (book.isTranslatedBook) return i18n.t("cookbook.translated-book");
  return i18n.t("cookbook.uploaded-book");
}

function bookIcon(book: UploadedBook) {
  if (isGeneratedBook(book)) return $globals.icons.robot;
  if (book.isTranslatedBook) return $globals.icons.translate;
  return book.extension === ".pdf" ? $globals.icons.filePDF : $globals.icons.book;
}

// create
const createTargetKey = ref(0);
const createTarget = ref<ReadCookBook | null>(null);
async function createCookbook() {
  const name = i18n.t("cookbook.household-cookbook-name", [
    household.value?.name || "",
    String((myCookbooks.value?.length ?? 0) + 1),
  ]) as string;

  const data = { name } as CreateCookBook;
  await actions.createOne(data).then((cookbook) => {
    if (!cookbook) {
      return;
    }

    myCookbooks.value.push(cookbook);
    createTarget.value = cookbook as ReadCookBook;
    createTargetKey.value++;
  });
  dialogStates.create = true;
}

// delete
const deleteTarget = ref<ReadCookBook | null>(null);
function deleteEventHandler(item: ReadCookBook) {
  deleteTarget.value = item;
  dialogStates.delete = true;
}
async function deleteCookbook() {
  if (!deleteTarget.value) {
    return;
  }
  await actions.deleteOne(deleteTarget.value.id);
  myCookbooks.value = myCookbooks.value.filter(c => c.id !== deleteTarget.value?.id);
  dialogStates.delete = false;
  deleteTarget.value = null;
}

async function deleteCreateTarget() {
  if (!createTarget.value?.id) {
    return;
  }
  await actions.deleteOne(createTarget.value.id);
  myCookbooks.value = myCookbooks.value.filter(c => c.id !== createTarget.value?.id);
  dialogStates.create = false;
  createTarget.value = null;
}
function handleUnmount() {
  if (!createTarget.value?.id || createTarget.value.queryFilterString) {
    return;
  }
  deleteCreateTarget();
}
onMounted(() => {
  window.addEventListener("beforeunload", handleUnmount);
  loadUploadedBooks();
});
onBeforeUnmount(() => {
  if (classificationRefreshTimer !== null) {
    window.clearTimeout(classificationRefreshTimer);
    classificationRefreshTimer = null;
  }
  handleUnmount();
  window.removeEventListener("beforeunload", handleUnmount);
});
</script>

<style scoped>
.cookbook-library {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.cookbook-library__filters {
  display: grid;
  grid-template-columns: minmax(240px, 1.4fr) minmax(180px, 0.7fr) minmax(260px, 1fr);
  gap: 12px;
}

.cookbook-library__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.cookbook-library__book {
  display: flex;
  flex-direction: column;
  min-height: 250px;
  border-radius: 8px;
}

.cookbook-library__cover {
  aspect-ratio: 4 / 3;
  background: rgb(var(--v-theme-surface-variant));
  overflow: hidden;
  width: 100%;
}

.cookbook-library__cover-fallback {
  align-items: center;
  color: rgba(var(--v-theme-on-surface), 0.54);
  display: flex;
  height: 260px;
  justify-content: center;
  width: 100%;
}

.cookbook-library__book .v-card-actions {
  margin-top: auto;
}

.book-summary {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

@media (max-width: 900px) {
  .cookbook-library__filters {
    grid-template-columns: 1fr;
  }
}
</style>
