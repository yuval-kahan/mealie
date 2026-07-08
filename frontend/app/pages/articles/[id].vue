<template>
  <v-container
    v-if="article"
    class="article-detail"
  >
    <BaseDialog
      v-model="editDialog"
      :title="$t('article.edit-article')"
      :icon="$globals.icons.fileSign"
      width="900"
      max-width="96vw"
      can-submit
      keep-open
      :loading="saving"
      :submit-disabled="!form.title.trim() || !form.content.trim()"
      :submit-text="$t('general.save')"
      @submit="saveArticle"
    >
      <v-card-text class="pt-4">
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
          rows="16"
        />
        <ArticleOrganizerInputs
          v-model:categories="form.categories"
          v-model:tags="form.tags"
          :category-items="article.categories"
          :tag-items="article.tags"
        />
      </v-card-text>
    </BaseDialog>

    <BaseDialog
      v-model="deleteDialog"
      :title="$t('general.confirm')"
      :icon="$globals.icons.alertCircle"
      color="error"
      can-confirm
      @confirm="deleteArticle"
    >
      <v-card-text>
        {{ $t("article.delete-confirm") }}
      </v-card-text>
    </BaseDialog>

    <div class="article-detail-header">
      <ButtonLink
        to="/articles"
        :text="$t('article.articles')"
        :icon="$globals.icons.backArrow"
      />
      <div class="article-actions">
        <v-btn
          color="primary"
          variant="tonal"
          :prepend-icon="$globals.icons.contentCopy"
          @click="copyArticle"
        >
          {{ $t("general.copy") }}
        </v-btn>
        <v-btn
          color="primary"
          variant="tonal"
          :prepend-icon="$globals.icons.edit"
          @click="openEditDialog"
        >
          {{ $t("general.edit") }}
        </v-btn>
        <v-btn
          color="error"
          variant="tonal"
          :prepend-icon="$globals.icons.delete"
          @click="deleteDialog = true"
        >
          {{ $t("general.delete") }}
        </v-btn>
      </div>
    </div>

    <article class="article-body">
      <h1>{{ article.title }}</h1>
      <div class="article-meta">
        <span v-if="article.author">{{ article.author }}</span>
        <span v-if="article.source">{{ article.source }}</span>
      </div>
      <p
        v-if="article.summary"
        class="article-summary"
      >
        {{ article.summary }}
      </p>
      <div class="d-flex flex-wrap ga-1 mb-6">
        <v-chip
          v-for="category in article.categories"
          :key="`category-${category}`"
          size="small"
          color="primary"
          variant="tonal"
        >
          {{ category }}
        </v-chip>
        <v-chip
          v-for="tag in article.tags"
          :key="`tag-${tag}`"
          size="small"
          color="accent"
          variant="tonal"
        >
          {{ tag }}
        </v-chip>
      </div>
      <div class="article-content">
        <SafeMarkdown :source="article.content" />
      </div>
    </article>
  </v-container>
</template>

<script setup lang="ts">
import ArticleOrganizerInputs from "~/components/Domain/Article/ArticleOrganizerInputs.vue";
import { useUserApi } from "~/composables/api/api-client";
import { useCopy } from "~/composables/use-copy";
import { alert } from "~/composables/use-toast";
import type { Article, ArticleCreate } from "~/lib/api/types/article";

const i18n = useI18n();
const { $globals } = useNuxtApp();
const route = useRoute();
const router = useRouter();
const api = useUserApi();
const { copyText } = useCopy();

const article = ref<Article | null>(null);
const editDialog = ref(false);
const deleteDialog = ref(false);
const saving = ref(false);

const form = reactive<ArticleCreate>({
  title: "",
  summary: "",
  content: "",
  source: "",
  author: "",
  categories: [],
  tags: [],
});

useSeoMeta({
  title: computed(() => article.value?.title || i18n.t("article.article")),
});

onMounted(fetchArticle);

async function fetchArticle() {
  const { data, error } = await api.articles.getOne(route.params.id as string);
  if (error || !data) {
    alert.error(i18n.t("events.something-went-wrong"));
    await router.push("/articles");
    return;
  }
  article.value = data;
}

function openEditDialog() {
  if (!article.value) {
    return;
  }
  form.title = article.value.title;
  form.summary = article.value.summary || "";
  form.content = article.value.content;
  form.source = article.value.source || "";
  form.author = article.value.author || "";
  form.categories = [...article.value.categories];
  form.tags = [...article.value.tags];
  editDialog.value = true;
}

async function saveArticle() {
  if (!article.value) {
    return;
  }
  saving.value = true;
  const { data, error } = await api.articles.updateOne(article.value.id, form).finally(() => {
    saving.value = false;
  });
  if (error || !data) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }
  article.value = data;
  editDialog.value = false;
}

async function deleteArticle() {
  if (!article.value) {
    return;
  }
  const { error } = await api.articles.deleteOne(article.value.id);
  if (error) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }
  await router.push("/articles");
}

function copyArticle() {
  if (!article.value) {
    return;
  }
  const parts = [
    article.value.title,
    article.value.author ? `${i18n.t("article.author")}: ${article.value.author}` : "",
    article.value.source ? `${i18n.t("article.source")}: ${article.value.source}` : "",
    article.value.summary || "",
    article.value.content,
    article.value.categories.length ? `${i18n.t("category.categories")}: ${article.value.categories.join(", ")}` : "",
    article.value.tags.length ? `${i18n.t("tag.tags")}: ${article.value.tags.join(", ")}` : "",
  ].filter(Boolean);
  copyText(parts.join("\n\n"));
}
</script>

<style scoped>
.article-detail {
  max-width: 980px;
}

.article-detail-header {
  align-items: center;
  display: flex;
  gap: 12px;
  justify-content: space-between;
  margin-bottom: 24px;
}

.article-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.article-body {
  border-radius: 8px;
  padding: 12px 4px 48px;
}

.article-body h1 {
  font-size: clamp(2rem, 4vw, 3.4rem);
  line-height: 1.1;
  margin-bottom: 12px;
}

.article-meta {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.article-summary {
  font-size: 1.15rem;
  line-height: 1.7;
  margin-bottom: 20px;
}

.article-content {
  font-size: 1.02rem;
  line-height: 1.8;
  white-space: normal;
}

@media (max-width: 700px) {
  .article-detail-header {
    align-items: stretch;
    flex-direction: column;
  }

  .article-actions {
    justify-content: flex-start;
  }
}
</style>
