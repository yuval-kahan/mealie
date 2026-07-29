<template>
  <v-container class="articles-page">
    <BaseDialog
      v-model="articleDialog"
      :title="editingArticle ? $t('article.edit-article') : $t('article.create-article')"
      :icon="$globals.icons.fileSign"
      width="900"
      max-width="96vw"
      can-submit
      keep-open
      :loading="saving"
      :submit-disabled="!canSubmitArticle"
      :submit-text="$t('general.save')"
      @submit="submitArticle"
      @close="closeArticleDialog"
    >
      <v-card-text class="pt-4">
        <v-tabs
          v-if="!editingArticle"
          v-model="createMode"
          color="primary"
          density="comfortable"
        >
          <v-tab value="manual">
            {{ $t("article.manual") }}
          </v-tab>
          <v-tab value="ai-text">
            {{ $t("article.ai-text") }}
          </v-tab>
          <v-tab value="ai-link">
            {{ $t("article.ai-link") }}
          </v-tab>
          <v-tab value="ai-question">
            {{ $t("article.ai-question") }}
          </v-tab>
        </v-tabs>

        <v-window
          v-model="createMode"
          class="mt-4"
        >
          <v-window-item value="manual">
            <v-text-field
              v-model="form.title"
              :label="$t('article.title')"
              variant="outlined"
              density="comfortable"
            />
            <v-row>
              <v-col
                cols="12"
                md="6"
              >
                <v-text-field
                  v-model="form.source"
                  :label="$t('article.source')"
                  variant="outlined"
                  density="comfortable"
                />
              </v-col>
              <v-col
                cols="12"
                md="6"
              >
                <v-text-field
                  v-model="form.author"
                  :label="$t('article.author')"
                  variant="outlined"
                  density="comfortable"
                />
              </v-col>
            </v-row>
            <v-textarea
              v-model="form.summary"
              :label="$t('article.summary')"
              variant="outlined"
              rows="3"
            />
            <v-textarea
              v-model="form.content"
              :label="$t('article.content')"
              variant="outlined"
              rows="12"
            />
            <ArticleOrganizerInputs
              v-model:categories="form.categories"
              v-model:tags="form.tags"
              :category-items="categoryOptions"
              :tag-items="tagOptions"
            />
          </v-window-item>

          <v-window-item value="ai-text">
            <v-textarea
              v-model="aiText"
              :label="$t('article.article-text')"
              variant="outlined"
              rows="14"
            />
            <v-text-field
              :model-value="displayLanguage"
              :label="$t('article.target-language')"
              variant="outlined"
              density="comfortable"
              readonly
            />
          </v-window-item>

          <v-window-item value="ai-link">
            <v-text-field
              v-model="aiUrl"
              :label="$t('article.url')"
              variant="outlined"
              density="comfortable"
              :prepend-inner-icon="$globals.icons.link"
            />
            <v-text-field
              :model-value="displayLanguage"
              :label="$t('article.target-language')"
              variant="outlined"
              density="comfortable"
              readonly
            />
          </v-window-item>

          <v-window-item value="ai-question">
            <v-textarea
              v-model="aiQuestion"
              :label="$t('article.question-or-topic')"
              :hint="$t('article.question-or-topic-hint')"
              persistent-hint
              variant="outlined"
              rows="10"
            />
            <v-text-field
              :model-value="displayLanguage"
              :label="$t('article.target-language')"
              variant="outlined"
              density="comfortable"
              readonly
              class="mt-4"
            />
          </v-window-item>
        </v-window>
        <div
          v-if="!editingArticle && (createMode === 'ai-text' || createMode === 'ai-link')"
          class="article-ai-options mt-2"
        >
          <v-checkbox
            v-model="extractRecipeIfPresent"
            hide-details
            color="primary"
            density="compact"
            :label="$t('article.extract-recipe-if-present')"
          />
          <v-checkbox
            v-model="createShoppingListForExtractedRecipes"
            hide-details
            color="primary"
            density="compact"
            :disabled="!extractRecipeIfPresent"
            :label="$t('article.create-shopping-list-for-recipes')"
          />
          <v-checkbox
            v-model="organizeExtractedShoppingListWithAI"
            hide-details
            color="primary"
            density="compact"
            :disabled="!extractRecipeIfPresent || !createShoppingListForExtractedRecipes"
            :label="$t('article.organize-shopping-list-with-ai')"
          />
          <v-checkbox
            v-model="includeExtractedAiTips"
            hide-details
            color="primary"
            density="compact"
            :disabled="!extractRecipeIfPresent"
            :label="$t('recipe.include-ai-tips-description')"
          />
          <v-checkbox
            v-model="includeExtractedMiseEnPlace"
            hide-details
            color="primary"
            density="compact"
            :disabled="!extractRecipeIfPresent"
            :label="$t('recipe.include-mise-en-place-description')"
          />
          <v-checkbox
            v-model="includeExtractedItemImages"
            hide-details
            color="primary"
            density="compact"
            :disabled="!extractRecipeIfPresent"
            :label="$t('recipe.include-item-images-description')"
          />
        </div>
      </v-card-text>
    </BaseDialog>

    <BasePageTitle divider>
      <template #header>
        <v-icon
          size="72"
          color="primary"
        >
          {{ $globals.icons.fileSign }}
        </v-icon>
      </template>
      <template #title>
        {{ $t("article.articles") }}
      </template>
    </BasePageTitle>

    <div class="articles-toolbar">
      <v-text-field
        v-model="search"
        :label="$t('search.search')"
        variant="outlined"
        density="comfortable"
        hide-details
        clearable
        :prepend-inner-icon="$globals.icons.search"
      />
      <v-combobox
        v-model="selectedCategories"
        :items="categoryOptions"
        :label="$t('category.categories')"
        variant="outlined"
        density="comfortable"
        hide-details
        multiple
        chips
        clearable
      />
      <v-combobox
        v-model="selectedTags"
        :items="tagOptions"
        :label="$t('tag.tags')"
        variant="outlined"
        density="comfortable"
        hide-details
        multiple
        chips
        clearable
      />
      <BaseButton
        create
        @click="openCreateDialog"
      />
    </div>

    <div class="articles-ai-search">
      <v-text-field
        v-model="aiSearchQuery"
        :label="$t('article.ai-search')"
        variant="outlined"
        density="comfortable"
        hide-details
        clearable
        :prepend-inner-icon="$globals.icons.robot"
        @keyup.enter="runAISearch"
      />
      <v-btn
        color="primary"
        :loading="aiSearching"
        :disabled="!aiSearchQuery.trim()"
        @click="runAISearch"
      >
        <v-icon start>
          {{ $globals.icons.robot }}
        </v-icon>
        {{ $t("general.search") }}
      </v-btn>
      <v-btn
        v-if="aiSearchActive"
        variant="text"
        @click="clearAISearch"
      >
        {{ $t("general.reset") }}
      </v-btn>
    </div>

    <v-alert
      v-if="aiSearchActive && !visibleArticles.length"
      type="info"
      variant="tonal"
      class="mt-4"
    >
      {{ $t("article.no-ai-results") }}
    </v-alert>

    <BaseListPagination
      v-if="visibleArticles.length"
      v-model:page="articlePage"
      v-model:items-per-page="articlesPerPage"
      :total-items="articleTotal"
    />

    <v-row class="mt-2">
      <v-col
        v-for="article in paginatedArticles"
        :key="article.id"
        cols="12"
        md="6"
        lg="4"
      >
        <v-card
          class="article-card"
          :to="`/articles/${article.id}`"
        >
          <v-card-title class="article-card-title">
            {{ article.title }}
          </v-card-title>
          <v-card-subtitle v-if="article.author || article.source">
            {{ [article.author, article.source].filter(Boolean).join(" · ") }}
          </v-card-subtitle>
          <v-card-text>
            <p class="article-card-summary">
              {{ article.summary || article.content }}
            </p>
            <p
              v-if="aiReasons[article.id]"
              class="text-caption text-primary mb-2"
            >
              {{ aiReasons[article.id] }}
            </p>
            <div class="d-flex flex-wrap ga-1">
              <v-chip
                v-for="category in article.categories.slice(0, 3)"
                :key="`${article.id}-category-${category}`"
                size="small"
                color="primary"
                variant="tonal"
              >
                {{ category }}
              </v-chip>
              <v-chip
                v-for="tag in article.tags.slice(0, 4)"
                :key="`${article.id}-tag-${tag}`"
                size="small"
                color="accent"
                variant="tonal"
              >
                {{ tag }}
              </v-chip>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-alert
      v-if="ready && !visibleArticles.length && !aiSearchActive"
      type="info"
      variant="tonal"
      class="mt-4"
    >
      {{ $t("article.no-articles") }}
    </v-alert>
  </v-container>
</template>

<script setup lang="ts">
import ArticleOrganizerInputs from "~/components/Domain/Article/ArticleOrganizerInputs.vue";
import { useUserApi } from "~/composables/api/api-client";
import { alert } from "~/composables/use-toast";
import type { Article, ArticleCreate } from "~/lib/api/types/article";

const i18n = useI18n();
const { $globals } = useNuxtApp();
const api = useUserApi();
const route = useRoute();
const router = useRouter();
const ARTICLES_UPDATED_EVENT = "mealie:articles-updated";

useSeoMeta({
  title: i18n.t("article.articles"),
});

const ready = ref(false);
const articles = ref<Article[]>([]);
const articleDialog = ref(false);
const editingArticle = ref<Article | null>(null);
const saving = ref(false);
const createMode = ref<"manual" | "ai-text" | "ai-link" | "ai-question">("manual");
const search = ref("");
const selectedCategories = ref<string[]>([]);
const selectedTags = ref<string[]>([]);
const aiSearchQuery = ref("");
const aiSearching = ref(false);
const aiSearchIds = ref<string[]>([]);
const aiReasons = ref<Record<string, string>>({});
const aiText = ref("");
const aiUrl = ref("");
const aiQuestion = ref("");
const extractRecipeIfPresent = ref(true);
const createShoppingListForExtractedRecipes = ref(true);
const organizeExtractedShoppingListWithAI = ref(true);
const includeExtractedAiTips = ref(true);
const includeExtractedMiseEnPlace = ref(true);
const includeExtractedItemImages = ref(true);

const form = reactive<ArticleCreate>({
  title: "",
  summary: "",
  content: "",
  source: "",
  author: "",
  categories: [],
  tags: [],
});

const displayLanguage = computed(defaultLanguage);
const categoryOptions = computed(() => sortedUnique(articles.value.flatMap(article => article.categories)));
const tagOptions = computed(() => sortedUnique(articles.value.flatMap(article => article.tags)));
const aiSearchActive = computed(() => aiSearchIds.value.length > 0);

const canSubmitArticle = computed(() => {
  if (editingArticle.value || createMode.value === "manual") {
    return Boolean(form.title.trim() && form.content.trim());
  }
  if (createMode.value === "ai-text") {
    return Boolean(aiText.value.trim());
  }
  if (createMode.value === "ai-link") {
    return Boolean(aiUrl.value.trim());
  }
  return Boolean(aiQuestion.value.trim());
});

const filteredArticles = computed(() => {
  const query = search.value.trim().toLocaleLowerCase();
  const selectedCategorySet = new Set(selectedCategories.value.map(item => item.toLocaleLowerCase()));
  const selectedTagSet = new Set(selectedTags.value.map(item => item.toLocaleLowerCase()));

  return articles.value.filter((article) => {
    const articleCategories = article.categories.map(item => item.toLocaleLowerCase());
    const articleTags = article.tags.map(item => item.toLocaleLowerCase());
    const text = [
      article.title,
      article.summary,
      article.content,
      article.source,
      article.author,
      article.categories.join(" "),
      article.tags.join(" "),
    ].join(" ").toLocaleLowerCase();

    return (!query || text.includes(query))
      && (!selectedCategorySet.size || articleCategories.some(item => selectedCategorySet.has(item)))
      && (!selectedTagSet.size || articleTags.some(item => selectedTagSet.has(item)));
  });
});

const visibleArticles = computed(() => {
  if (!aiSearchActive.value) {
    return filteredArticles.value;
  }

  const byId = new Map(filteredArticles.value.map(article => [article.id, article]));
  return aiSearchIds.value.map(id => byId.get(id)).filter((article): article is Article => !!article);
});
const {
  page: articlePage,
  itemsPerPage: articlesPerPage,
  totalItems: articleTotal,
  paginatedItems: paginatedArticles,
} = useListPagination(visibleArticles);

onMounted(async () => {
  await refreshArticles();
  openCreateDialogFromRoute();
  window.addEventListener(ARTICLES_UPDATED_EVENT, handleArticlesUpdated);
});

onUnmounted(() => {
  window.removeEventListener(ARTICLES_UPDATED_EVENT, handleArticlesUpdated);
});

watch(
  () => route.query.create,
  () => {
    openCreateDialogFromRoute();
  },
);

function defaultLanguage() {
  const locale = String(i18n.locale.value || "").toLocaleLowerCase();
  if (locale.startsWith("he")) {
    return i18n.t("cookbook.language-hebrew");
  }
  if (locale.startsWith("ar")) {
    return i18n.t("cookbook.language-arabic");
  }
  return i18n.t("cookbook.language-english");
}

function sortedUnique(values: string[]) {
  return Array.from(new Set(values.map(item => item.trim()).filter(Boolean))).sort((a, b) => a.localeCompare(b));
}

async function refreshArticles() {
  const { data, error } = await api.articles.getAll();
  if (error || !data) {
    alert.error(i18n.t("events.something-went-wrong"));
    ready.value = true;
    return;
  }
  articles.value = data;
  ready.value = true;
}

function resetArticleForm() {
  editingArticle.value = null;
  createMode.value = "manual";
  form.title = "";
  form.summary = "";
  form.content = "";
  form.source = "";
  form.author = "";
  form.categories = [];
  form.tags = [];
  aiText.value = "";
  aiUrl.value = "";
  aiQuestion.value = "";
  extractRecipeIfPresent.value = true;
  createShoppingListForExtractedRecipes.value = true;
  organizeExtractedShoppingListWithAI.value = true;
  includeExtractedAiTips.value = true;
  includeExtractedMiseEnPlace.value = true;
  includeExtractedItemImages.value = true;
}

function openCreateDialog() {
  resetArticleForm();
  articleDialog.value = true;
}

function openCreateDialogFromRoute() {
  if (route.query.create === "1" || route.query.create === "true") {
    openCreateDialog();
  }
}

function closeArticleDialog() {
  resetArticleForm();
  clearCreateQuery();
}

function clearCreateQuery() {
  if (!route.query.create) {
    return;
  }

  const nextQuery = { ...route.query };
  delete nextQuery.create;
  void router.replace({ path: route.path, query: nextQuery });
}

async function submitArticle() {
  saving.value = true;
  const result = await (async () => {
    if (editingArticle.value) {
      return await api.articles.updateOne(editingArticle.value.id, form);
    }
    if (createMode.value === "manual") {
      return await api.articles.createOne(form);
    }
    if (createMode.value === "ai-question") {
      return await api.articles.createFromQuestion({
        question: aiQuestion.value,
        targetLanguage: displayLanguage.value,
      });
    }
    return await api.articles.createWithAI({
      text: createMode.value === "ai-text" ? aiText.value : null,
      url: createMode.value === "ai-link" ? aiUrl.value : null,
      translateLanguage: displayLanguage.value,
      createRecipeIfPresent: extractRecipeIfPresent.value,
      createShoppingList: extractRecipeIfPresent.value && createShoppingListForExtractedRecipes.value,
      organizeShoppingListWithAi: extractRecipeIfPresent.value
        && createShoppingListForExtractedRecipes.value
        && organizeExtractedShoppingListWithAI.value,
      includeAiTips: includeExtractedAiTips.value,
      includeMiseEnPlace: includeExtractedMiseEnPlace.value,
      includeItemImages: includeExtractedItemImages.value,
    });
  })().finally(() => {
    saving.value = false;
  });

  if (result.error || !result.data) {
    const detail = result.error?.response?.data?.detail;
    const message = typeof detail?.message === "string" ? detail.message : i18n.t("events.something-went-wrong");
    alert.error(message);
    return;
  }

  articleDialog.value = false;
  resetArticleForm();
  clearCreateQuery();
  await refreshArticles();
}

async function runAISearch() {
  if (!aiSearchQuery.value.trim()) {
    return;
  }

  aiSearching.value = true;
  const { data, error } = await api.articles.searchWithAI({
    query: aiSearchQuery.value,
    limit: 30,
  }).finally(() => {
    aiSearching.value = false;
  });

  if (error || !data) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }

  aiSearchIds.value = data.items.map(item => item.id);
  aiReasons.value = Object.fromEntries(data.items.map(item => [item.id, item.reason]));
}

function clearAISearch() {
  aiSearchQuery.value = "";
  aiSearchIds.value = [];
  aiReasons.value = {};
}

function handleArticlesUpdated() {
  void refreshArticles();
}
</script>

<style scoped>
.articles-page {
  max-width: 1180px;
}

.articles-toolbar,
.articles-ai-search {
  display: grid;
  gap: 12px;
  grid-template-columns: minmax(180px, 1fr) minmax(160px, 240px) minmax(160px, 240px) auto;
  margin-top: 18px;
}

.articles-ai-search {
  grid-template-columns: minmax(220px, 1fr) auto auto;
}

.article-ai-options {
  display: grid;
  gap: 2px 12px;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}

.article-card {
  border-radius: 8px;
  height: 100%;
}

.article-card-title {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  min-height: 64px;
  overflow: hidden;
  white-space: normal;
}

.article-card-summary {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
  line-clamp: 4;
  min-height: 86px;
  overflow: hidden;
  white-space: pre-wrap;
}

@media (max-width: 960px) {
  .articles-toolbar,
  .articles-ai-search {
    grid-template-columns: 1fr;
  }
}
</style>
