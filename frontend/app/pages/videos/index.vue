<template>
  <v-container class="narrow-container video-library-page">
    <BaseDialog
      v-model="createDialogOpen"
      :title="$t('video-library.save-video')"
      :icon="$globals.icons.video"
      can-submit
      keep-open
      :loading="saving"
      :submit-disabled="!canCreate"
      @submit="submitVideo"
      @close="resetCreateForm"
    >
      <v-card-text>
        <v-btn-toggle v-model="createMode" mandatory divided density="comfortable" class="mb-4">
          <v-btn value="ai" :prepend-icon="$globals.icons.robot">
            {{ $t("video-library.with-ai") }}
          </v-btn>
          <v-btn value="manual" :prepend-icon="$globals.icons.edit">
            {{ $t("video-library.manual") }}
          </v-btn>
        </v-btn-toggle>

        <v-text-field
          v-model="createForm.url"
          :label="$t('video-library.video-url')"
          type="url"
          :prepend-inner-icon="$globals.icons.link"
          autofocus
        />
        <template v-if="createMode === 'manual'">
          <v-text-field v-model="createForm.title" :label="$t('video-library.title')" />
          <v-textarea
            v-model="createForm.description"
            :label="$t('video-library.description')"
            rows="4"
            auto-grow
          />
        </template>
        <v-alert v-else type="info" variant="tonal" density="compact" class="mb-3">
          {{ $t("video-library.ai-help") }}
        </v-alert>

        <v-select
          v-if="createMode === 'ai'"
          v-model="createForm.targetLanguage"
          :items="targetLanguages"
          :label="$t('video-library.output-language')"
        />
        <v-checkbox
          v-model="createForm.downloadVideo"
          :label="$t('video-library.download-video')"
          density="compact"
          hide-details
        />
        <template v-if="createMode === 'ai'">
          <v-checkbox
            v-model="createForm.createRecipe"
            :label="$t('video-library.create-recipe-if-present')"
            density="compact"
            hide-details
          />
          <v-checkbox
            v-model="createForm.createShoppingList"
            :disabled="!createForm.createRecipe"
            :label="$t('video-library.create-shopping-list')"
            density="compact"
            hide-details
          />
          <v-checkbox
            v-model="createForm.organizeShoppingList"
            :disabled="!createForm.createRecipe || !createForm.createShoppingList"
            :label="$t('video-library.organize-shopping-list')"
            density="compact"
            hide-details
          />
          <v-checkbox
            v-model="createForm.includeAiTips"
            :label="$t('video-library.include-ai-tips')"
            density="compact"
            hide-details
          />
          <v-checkbox
            v-model="createForm.includeMiseEnPlace"
            :label="$t('video-library.include-mise-en-place')"
            density="compact"
            hide-details
          />
        </template>
        <v-btn
          class="mt-4"
          variant="tonal"
          color="primary"
          :prepend-icon="$globals.icons.cog"
          @click="settingsDialogOpen = true"
        >
          {{ $t("video-library.download-settings") }}
        </v-btn>
      </v-card-text>
    </BaseDialog>

    <BaseDialog
      v-model="settingsDialogOpen"
      :title="$t('video-library.download-settings')"
      :icon="$globals.icons.cog"
      can-submit
      keep-open
      :loading="savingSettings"
      @submit="saveSettings"
    >
      <v-card-text>
        <v-checkbox
          v-model="settings.downloadByDefault"
          :label="$t('video-library.download-by-default')"
          density="compact"
        />
        <div class="video-settings-grid">
          <v-select v-model="settings.quality" :items="qualityOptions" :label="$t('video-library.quality')" />
          <v-select v-model="settings.container" :items="containerOptions" :label="$t('video-library.format')" />
          <v-select v-model="settings.codec" :items="codecOptions" :label="$t('video-library.codec')" />
          <v-select
            v-model="settings.audioQuality"
            :items="audioQualityOptions"
            :label="$t('video-library.audio-quality')"
          />
        </div>
        <v-checkbox v-model="settings.audioOnly" :label="$t('video-library.audio-only')" density="compact" hide-details />
        <v-checkbox v-model="settings.saveThumbnail" :label="$t('video-library.save-thumbnail')" density="compact" hide-details />
        <v-checkbox v-model="settings.saveMetadata" :label="$t('video-library.save-metadata')" density="compact" hide-details />
        <v-checkbox
          v-model="settings.fallbackToLowerQuality"
          :label="$t('video-library.quality-fallback')"
          density="compact"
          hide-details
        />
      </v-card-text>
    </BaseDialog>

    <BaseDialog
      v-model="editDialogOpen"
      :title="$t('video-library.edit-video')"
      :icon="$globals.icons.edit"
      can-submit
      keep-open
      :loading="saving"
      :submit-disabled="!editForm.title.trim()"
      @submit="saveVideoEdit"
    >
      <v-card-text>
        <v-text-field v-model="editForm.title" :label="$t('video-library.title')" autofocus />
        <v-text-field v-model="editForm.creator" :label="$t('video-library.creator')" />
        <v-textarea v-model="editForm.description" :label="$t('video-library.description')" rows="5" auto-grow />
        <v-combobox
          v-model="editForm.categories"
          :label="$t('video-library.categories')"
          multiple
          chips
          closable-chips
          clearable
        />
        <v-combobox
          v-model="editForm.tags"
          :label="$t('video-library.tags')"
          multiple
          chips
          closable-chips
          clearable
        />
      </v-card-text>
    </BaseDialog>

    <BaseDialog
      v-model="deleteDialogOpen"
      :title="$t('video-library.delete-video')"
      :icon="$globals.icons.delete"
      color="error"
      can-confirm
      @confirm="deleteVideo"
    >
      <v-card-text>
        {{ $t("video-library.delete-confirm") }}
        <v-progress-linear v-if="deletePreviewLoading" indeterminate color="primary" class="mt-4" />
        <template v-else-if="deletePreview">
          <v-checkbox
            v-if="deletePreview.recipeIds.length"
            v-model="deleteLinkedRecipes"
            :label="$t('video-library.delete-linked-recipes', { names: deletePreview.recipeNames.join(', ') })"
            density="compact"
            hide-details
            class="mt-4"
          />
          <v-checkbox
            v-if="deletePreview.shoppingListIds.length"
            v-model="deleteLinkedShoppingLists"
            :label="$t('video-library.delete-linked-lists', { names: deletePreview.shoppingListNames.join(', ') })"
            density="compact"
            hide-details
          />
          <v-alert
            v-if="deletePreview.recipeIds.length || deletePreview.shoppingListIds.length"
            type="info"
            variant="tonal"
            density="compact"
            class="mt-4"
          >
            {{ $t("video-library.links-remain-by-default") }}
          </v-alert>
        </template>
      </v-card-text>
    </BaseDialog>

    <BasePageTitle divider>
      <template #title>
        {{ $t("video-library.videos") }}
      </template>
      <template #subtitle>
        {{ $t("video-library.description-page") }}
      </template>
    </BasePageTitle>

    <div class="video-library-toolbar mb-6">
      <v-text-field
        v-model="search"
        :label="$t('search.search')"
        :prepend-inner-icon="$globals.icons.search"
        density="compact"
        clearable
        hide-details
      />
      <v-btn variant="tonal" color="primary" :prepend-icon="$globals.icons.cog" @click="openSettings">
        {{ $t("video-library.settings") }}
      </v-btn>
      <v-btn color="primary" :prepend-icon="$globals.icons.create" @click="openCreateDialog">
        {{ $t("video-library.save-video") }}
      </v-btn>
    </div>

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />
    <div v-else-if="filteredVideos.length" class="video-library-grid">
      <v-card v-for="video in filteredVideos" :key="video.id" class="video-library-card" variant="outlined">
        <div class="video-library-media">
          <video
            v-if="video.hasLocalMedia"
            controls
            preload="metadata"
            :poster="thumbnailUrl(video)"
          >
            <source :src="api.videos.mediaUrl(video.id)">
          </video>
          <v-img v-else-if="video.hasLocalThumbnail || video.thumbnailUrl" :src="thumbnailUrl(video)" cover />
          <div v-else class="video-library-placeholder">
            <v-icon size="72" color="primary">
              {{ $globals.icons.video }}
            </v-icon>
          </div>
        </div>

        <v-card-title class="video-card-title">
          {{ video.title }}
        </v-card-title>
        <v-card-subtitle class="video-card-subtitle">
          <span v-if="video.creator">{{ video.creator }}</span>
          <span v-if="video.platform">{{ video.platform }}</span>
          <span v-if="video.durationSeconds">{{ formatDuration(video.durationSeconds) }}</span>
        </v-card-subtitle>

        <v-card-text class="video-card-body">
          <p v-if="video.description" class="video-description">
            {{ video.description }}
          </p>
          <div class="d-flex flex-wrap ga-1 mt-2">
            <v-chip v-for="category in video.categories" :key="`category-${category}`" size="x-small" color="primary" variant="tonal">
              {{ category }}
            </v-chip>
            <v-chip v-for="tag in video.tags.slice(0, 6)" :key="`tag-${tag}`" size="x-small" variant="outlined">
              {{ tag }}
            </v-chip>
          </div>

          <div class="video-status-row mt-3">
            <v-chip size="small" :color="statusColor(video.processingStatus)" variant="tonal">
              {{ statusText(video.processingStatus) }}
            </v-chip>
            <span v-if="video.localResolution">{{ video.localResolution }}</span>
            <span v-if="video.localFileSize">{{ formatFileSize(video.localFileSize) }}</span>
          </div>
          <v-progress-linear
            v-if="isActive(video)"
            :model-value="video.processingProgress"
            color="primary"
            height="6"
            rounded
            class="mt-2"
          />
          <v-alert v-if="video.processingError" type="error" variant="tonal" density="compact" class="mt-3 video-error">
            {{ video.processingError }}
          </v-alert>

          <div v-if="video.recipeSlugs.length || video.shoppingListIds.length" class="video-links mt-3">
            <NuxtLink
              v-for="(slug, index) in video.recipeSlugs"
              :key="slug"
              :to="`/g/${groupSlug}/r/${slug}`"
            >
              {{ $t("video-library.open-recipe", { number: index + 1 }) }}
            </NuxtLink>
            <NuxtLink
              v-for="(listId, index) in video.shoppingListIds"
              :key="listId"
              :to="`/shopping-lists/${listId}`"
            >
              {{ $t("video-library.open-shopping-list", { number: index + 1 }) }}
            </NuxtLink>
          </div>
        </v-card-text>

        <v-card-actions class="video-card-actions">
          <LinkedResourcesButton
            v-if="video.recipeIds.length || video.shoppingListIds.length"
            entity-type="video"
            :entity-id="video.id"
            :count="video.recipeIds.length + video.shoppingListIds.length"
          />
          <v-btn :href="video.url" target="_blank" icon variant="text" :title="$t('video-library.open-source')">
            <v-icon>{{ $globals.icons.openInNew }}</v-icon>
          </v-btn>
          <v-btn
            v-if="isActive(video)"
            icon
            variant="text"
            color="warning"
            :title="$t('video-library.cancel-processing')"
            @click="cancelProcessing(video)"
          >
            <v-icon>{{ $globals.icons.close }}</v-icon>
          </v-btn>
          <v-btn
            v-if="['failed', 'cancelled'].includes(video.processingStatus)"
            icon
            variant="text"
            color="primary"
            :title="$t('video-library.retry')"
            @click="retryProcessing(video)"
          >
            <v-icon>{{ $globals.icons.refresh }}</v-icon>
          </v-btn>
          <v-spacer />
          <v-btn icon variant="text" :title="$t('general.edit')" @click="openEditDialog(video)">
            <v-icon>{{ $globals.icons.edit }}</v-icon>
          </v-btn>
          <v-btn
            icon
            variant="text"
            color="error"
            :disabled="isActive(video)"
            :title="$t('general.delete')"
            @click="openDeleteDialog(video)"
          >
            <v-icon>{{ $globals.icons.delete }}</v-icon>
          </v-btn>
        </v-card-actions>
      </v-card>
    </div>
    <v-alert v-else type="info" variant="tonal">
      {{ $t("video-library.no-videos") }}
    </v-alert>
  </v-container>
</template>

<script setup lang="ts">
import type {
  VideoCreate,
  VideoDeletePreview,
  VideoDownloadSettings,
  VideoRecord,
  VideoUpdate,
} from "~/lib/api/types/video";
import { useUserApi } from "~/composables/api/api-client";
import { alert } from "~/composables/use-toast";
import LinkedResourcesButton from "~/components/Domain/LinkedResources/LinkedResourcesButton.vue";

const ACTIVE_STATUSES = new Set(["pending", "metadata", "downloading", "processing"]);
const i18n = useI18n();
const api = useUserApi();
const auth = useMealieAuth();
const route = useRoute();
const router = useRouter();
const groupSlug = computed(() => auth.user.value?.groupSlug || "home");

const videos = ref<VideoRecord[]>([]);
const loading = ref(true);
const saving = ref(false);
const savingSettings = ref(false);
const search = ref("");
const createDialogOpen = ref(false);
const settingsDialogOpen = ref(false);
const editDialogOpen = ref(false);
const deleteDialogOpen = ref(false);
const createMode = ref<"ai" | "manual">("ai");
const editingVideo = ref<VideoRecord | null>(null);
const deletingVideo = ref<VideoRecord | null>(null);
const deletePreview = ref<VideoDeletePreview>();
const deletePreviewLoading = ref(false);
const deleteLinkedRecipes = ref(false);
const deleteLinkedShoppingLists = ref(false);
let pollTimer: ReturnType<typeof setTimeout> | undefined;
let pageMounted = false;

const settings = reactive<VideoDownloadSettings>({
  downloadByDefault: true,
  quality: "best",
  container: "mp4",
  codec: "auto",
  audioOnly: false,
  audioQuality: "best",
  saveSubtitles: false,
  saveThumbnail: true,
  saveMetadata: true,
  fallbackToLowerQuality: true,
});

const createForm = reactive<VideoCreate>({
  url: "",
  title: "",
  description: "",
  processWithAi: true,
  downloadVideo: true,
  createRecipe: true,
  createShoppingList: true,
  organizeShoppingList: true,
  includeAiTips: true,
  includeMiseEnPlace: true,
  targetLanguage: i18n.locale.value,
});

const editForm = reactive<VideoUpdate>({
  title: "",
  description: "",
  creator: "",
  categories: [],
  tags: [],
});

const qualityOptions = computed(() => [
  { title: i18n.t("video-library.best-available"), value: "best" },
  { title: "4K (2160p)", value: "2160" },
  { title: "1080p", value: "1080" },
  { title: "720p", value: "720" },
  { title: "480p", value: "480" },
]);
const containerOptions = ["mp4", "mkv", "webm"];
const codecOptions = ["auto", "h264", "h265", "vp9", "av1"];
const audioQualityOptions = ["best", "320", "256", "192", "128", "96"];
const targetLanguages = computed(() => {
  const values = [
    { title: i18n.t("video-library.site-language"), value: i18n.locale.value },
    { title: "עברית", value: "he-IL" },
    { title: "English", value: "en-US" },
  ];
  return values.filter((item, index) => values.findIndex(candidate => candidate.value === item.value) === index);
});

const canCreate = computed(() => {
  const validUrl = /^https?:\/\//i.test(createForm.url.trim());
  return validUrl && (createMode.value === "ai" || Boolean(createForm.title?.trim()));
});
const filteredVideos = computed(() => {
  const query = search.value.trim().toLocaleLowerCase();
  if (!query) return videos.value;
  return videos.value.filter(video => [
    video.title,
    video.url,
    video.description || "",
    video.creator || "",
    video.platform || "",
    ...video.categories,
    ...video.tags,
  ].join(" ").toLocaleLowerCase().includes(query));
});

useSeoMeta({ title: i18n.t("video-library.videos") });

onMounted(async () => {
  pageMounted = true;
  await Promise.all([loadVideos(), loadSettings()]);
});

watch(
  () => route.query.create,
  (createQuery) => {
    if (createQuery !== "true") return;
    openCreateDialog();
    const query = { ...route.query };
    delete query.create;
    void router.replace({ query });
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  pageMounted = false;
  if (pollTimer) clearTimeout(pollTimer);
  pollTimer = undefined;
});

async function loadVideos(showLoading = true) {
  if (showLoading) loading.value = true;
  const { data, error } = await api.videos.getAll();
  if (!pageMounted) return;
  if (data) videos.value = data;
  if (error && showLoading) alert.error(i18n.t("events.something-went-wrong"));
  loading.value = false;
  schedulePolling();
}

function schedulePolling() {
  if (pollTimer) clearTimeout(pollTimer);
  pollTimer = undefined;
  if (!pageMounted || !videos.value.some(isActive)) return;
  pollTimer = setTimeout(() => void loadVideos(false), 3500);
}

async function loadSettings() {
  const { data } = await api.videos.getSettings();
  if (data) Object.assign(settings, data);
}

function resetCreateForm() {
  createMode.value = "ai";
  Object.assign(createForm, {
    url: "",
    title: "",
    description: "",
    processWithAi: true,
    downloadVideo: settings.downloadByDefault,
    createRecipe: true,
    createShoppingList: true,
    organizeShoppingList: true,
    includeAiTips: true,
    includeMiseEnPlace: true,
    targetLanguage: i18n.locale.value,
  });
}

function openCreateDialog() {
  resetCreateForm();
  createDialogOpen.value = true;
}

async function submitVideo() {
  saving.value = true;
  const payload: VideoCreate = {
    ...createForm,
    processWithAi: createMode.value === "ai",
    createRecipe: createMode.value === "ai" && createForm.createRecipe,
    createShoppingList: createMode.value === "ai" && createForm.createRecipe && createForm.createShoppingList,
    organizeShoppingList: createMode.value === "ai" && createForm.createRecipe && createForm.createShoppingList && createForm.organizeShoppingList,
    includeAiTips: createMode.value === "ai" && createForm.includeAiTips,
    includeMiseEnPlace: createMode.value === "ai" && createForm.includeMiseEnPlace,
    targetLanguage: createMode.value === "ai" ? createForm.targetLanguage : null,
  };
  const { data, error } = await api.videos.createOne(payload);
  saving.value = false;
  if (!data || error) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }
  createDialogOpen.value = false;
  resetCreateForm();
  await loadVideos(false);
  alert.success(i18n.t("video-library.processing-started"));
}

async function openSettings() {
  await loadSettings();
  settingsDialogOpen.value = true;
}

async function saveSettings() {
  savingSettings.value = true;
  const payload = { ...settings };
  delete payload.id;
  const { data, error } = await api.videos.updateSettings(payload as VideoDownloadSettings);
  savingSettings.value = false;
  if (!data || error) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }
  Object.assign(settings, data);
  settingsDialogOpen.value = false;
  alert.success(i18n.t("video-library.settings-saved"));
}

function openEditDialog(video: VideoRecord) {
  editingVideo.value = video;
  Object.assign(editForm, {
    title: video.title,
    description: video.description || "",
    creator: video.creator || "",
    categories: [...video.categories],
    tags: [...video.tags],
  });
  editDialogOpen.value = true;
}

async function saveVideoEdit() {
  if (!editingVideo.value) return;
  saving.value = true;
  const { data, error } = await api.videos.updateOne(editingVideo.value.id, editForm);
  saving.value = false;
  if (!data || error) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }
  editDialogOpen.value = false;
  editingVideo.value = null;
  await loadVideos(false);
}

async function retryProcessing(video: VideoRecord) {
  const { error } = await api.videos.retry(video.id);
  if (error) alert.error(i18n.t("events.something-went-wrong"));
  await loadVideos(false);
}

async function cancelProcessing(video: VideoRecord) {
  const { error } = await api.videos.cancel(video.id);
  if (error) alert.error(i18n.t("events.something-went-wrong"));
  else alert.success(i18n.t("video-library.cancel-requested"));
  await loadVideos(false);
}

async function openDeleteDialog(video: VideoRecord) {
  deletingVideo.value = video;
  deletePreview.value = undefined;
  deleteLinkedRecipes.value = false;
  deleteLinkedShoppingLists.value = false;
  deleteDialogOpen.value = true;
  deletePreviewLoading.value = true;
  try {
    const { data } = await api.videos.deletePreview(video.id);
    if (data) deletePreview.value = data;
  }
  finally {
    deletePreviewLoading.value = false;
  }
}

async function deleteVideo() {
  if (!deletingVideo.value) return;
  const { error } = await api.videos.deleteOne(deletingVideo.value.id, {
    deleteRecipes: deleteLinkedRecipes.value,
    deleteShoppingLists: deleteLinkedShoppingLists.value,
  });
  if (error) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }
  deletingVideo.value = null;
  await loadVideos(false);
}

function isActive(video: VideoRecord) {
  return ACTIVE_STATUSES.has(video.processingStatus);
}

function thumbnailUrl(video: VideoRecord) {
  return video.hasLocalThumbnail ? api.videos.thumbnailUrl(video.id) : video.thumbnailUrl || undefined;
}

function statusText(value: string) {
  const key = `video-library.status-${value}`;
  return i18n.te(key) ? i18n.t(key) : value;
}

function statusColor(value: string) {
  if (value === "completed") return "success";
  if (value === "failed") return "error";
  if (value === "cancelled") return "warning";
  return "primary";
}

function formatDuration(seconds: number) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remaining = seconds % 60;
  return hours ? `${hours}:${String(minutes).padStart(2, "0")}:${String(remaining).padStart(2, "0")}` : `${minutes}:${String(remaining).padStart(2, "0")}`;
}

function formatFileSize(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
}
</script>

<style scoped>
.video-library-toolbar {
  align-items: center;
  display: grid;
  gap: 12px;
  grid-template-columns: minmax(220px, 1fr) auto auto;
}

.video-library-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 330px), 1fr));
}

.video-library-card {
  display: flex;
  flex-direction: column;
  min-height: 540px;
}

.video-library-media {
  aspect-ratio: 16 / 9;
  background: #111;
  overflow: hidden;
  width: 100%;
}

.video-library-media video,
.video-library-media :deep(.v-img) {
  height: 100%;
  object-fit: contain;
  width: 100%;
}

.video-library-placeholder {
  align-items: center;
  background: rgb(var(--v-theme-surface-variant));
  display: flex;
  height: 100%;
  justify-content: center;
}

.video-card-title {
  font-size: 1rem;
  line-height: 1.35;
  min-height: 66px;
  overflow: hidden;
  white-space: normal;
}

.video-card-subtitle {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 10px;
  min-height: 44px;
  white-space: normal;
}

.video-card-body {
  flex: 1;
}

.video-description {
  display: -webkit-box;
  line-height: 1.45;
  margin: 0;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
}

.video-status-row,
.video-links {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
}

.video-links a {
  color: rgb(var(--v-theme-primary));
  font-weight: 600;
}

.video-error {
  overflow-wrap: anywhere;
}

.video-card-actions {
  min-height: 52px;
}

.video-settings-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

@media (max-width: 700px) {
  .video-library-toolbar,
  .video-settings-grid {
    grid-template-columns: 1fr;
  }
}
</style>
