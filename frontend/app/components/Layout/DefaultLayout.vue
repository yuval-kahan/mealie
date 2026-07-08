<template>
  <v-app dark>
    <TheSnackbar />

    <AppHeader>
      <v-btn
        icon
        @click.stop="sidebar = !sidebar"
      >
        <v-icon> {{ $globals.icons.menu }}</v-icon>
      </v-btn>
    </AppHeader>

    <AppSidebar
      v-model="sidebar"
      v-model:organizer-preferences="organizerSidebarPreferences"
      :top-link="topLinks"
      :secondary-links="sidebarCookbookLinks || []"
      :organizer-sections="organizerSidebarSections"
    >
      <BaseDialog
        v-model="quickTextRecipeDialog"
        :title="$t('recipe.create-recipe-from-text')"
        :icon="$globals.icons.textBoxCheckOutline"
        width="880"
        max-width="96vw"
        disable-submit-on-enter
      >
        <RecipeCreateFromTextForm
          :show-title="false"
          :rows="10"
          :return-to="route.path"
          @created="quickTextRecipeDialog = false"
        />
      </BaseDialog>
      <BaseDialog
        v-model="uploadedBookDialog"
        :title="$t('cookbook.upload-book')"
        :icon="$globals.icons.upload"
        width="560"
        max-width="96vw"
        can-submit
        keep-open
        disable-submit-on-enter
        :loading="uploadedBookUploading"
        :submit-text="$t('cookbook.upload-book')"
        :submit-icon="$globals.icons.upload"
        :submit-disabled="!uploadedBookFiles.length"
        @submit="uploadBook"
        @close="resetUploadBookForm"
      >
        <v-card-text class="pt-4">
          <v-text-field
            v-model="uploadedBookName"
            variant="outlined"
            density="comfortable"
            :label="$t('cookbook.uploaded-book-name')"
            :placeholder="$t('cookbook.uploaded-book-name-placeholder')"
            :disabled="hasMultipleUploadedBookFiles"
          />
          <v-file-input
            v-model="uploadedBookFile"
            :accept="uploadedBookAccept"
            variant="solo-filled"
            rounded
            clearable
            prepend-icon=""
            :prepend-inner-icon="$globals.icons.book"
            :label="$t('cookbook.book-file')"
            :hint="$t('cookbook.supported-book-files')"
            persistent-hint
            truncate-length="100"
            @update:model-value="onUploadedBookFileSelected"
          />
          <input
            ref="uploadedBookFolderInput"
            class="d-none"
            type="file"
            :accept="uploadedBookAccept"
            multiple
            webkitdirectory
            directory
            @change="onUploadedBookFolderSelected"
          >
          <div class="d-flex align-center ga-2 mt-2 mb-1">
            <v-btn
              variant="tonal"
              color="primary"
              :prepend-icon="$globals.icons.folderOutline"
              :disabled="uploadedBookUploading"
              @click="openUploadedBookFolderPicker"
            >
              {{ $t("cookbook.select-book-folder") }}
            </v-btn>
            <v-chip
              v-if="uploadedBookFiles.length"
              size="small"
              color="primary"
              variant="tonal"
            >
              {{ $t("cookbook.selected-book-files", { count: uploadedBookFiles.length }) }}
            </v-chip>
          </div>
          <v-alert
            v-if="hasMultipleUploadedBookFiles"
            density="compact"
            variant="tonal"
            type="info"
            class="mb-3"
          >
            {{ $t("cookbook.bulk-upload-ai-disabled") }}
          </v-alert>
          <v-radio-group
            v-model="uploadedBookAction"
            density="compact"
            :label="$t('cookbook.after-upload-action')"
            :disabled="hasMultipleUploadedBookFiles"
          >
            <v-radio
              value="none"
              :label="$t('cookbook.upload-only')"
            />
            <v-radio
              value="extract"
              :label="$t('cookbook.extract-recipes-after-upload')"
            />
            <v-radio
              value="translate"
              :label="$t('cookbook.translate-book-after-upload')"
            />
          </v-radio-group>
          <v-combobox
            v-if="uploadedBookAction === 'translate'"
            v-model="uploadedBookTargetLanguage"
            :items="uploadedBookTranslationLanguageOptions"
            variant="outlined"
            density="comfortable"
            :label="$t('cookbook.translation-language')"
          />
          <v-text-field
            v-model.number="uploadedBookPagesPerChunk"
            type="number"
            min="1"
            max="100"
            variant="outlined"
            density="comfortable"
            :label="$t('cookbook.pages-per-ai-chunk')"
          />
        </v-card-text>
      </BaseDialog>
      <BaseDialog
        v-model="uploadedBookTranslationDialog"
        :title="$t('cookbook.translate-book-with-ai')"
        :icon="$globals.icons.translate"
        width="520"
        max-width="96vw"
        can-submit
        keep-open
        disable-submit-on-enter
        :loading="uploadedBookTranslationStarting"
        :submit-text="$t('cookbook.start-translation')"
        :submit-icon="$globals.icons.translate"
        :submit-disabled="!selectedUploadedBook || isUploadedBookExtracting(selectedUploadedBook) || isUploadedBookTranslating(selectedUploadedBook)"
        @submit="startSelectedUploadedBookTranslation"
      >
        <v-card-text class="pt-4">
          <div
            v-if="selectedUploadedBook"
            class="text-subtitle-2 mb-3"
          >
            {{ selectedUploadedBook.name }}
          </div>
          <v-combobox
            v-model="uploadedBookTargetLanguage"
            :items="uploadedBookTranslationLanguageOptions"
            variant="outlined"
            density="comfortable"
            :label="$t('cookbook.translation-language')"
          />
          <v-text-field
            v-model.number="uploadedBookPagesPerChunk"
            type="number"
            min="1"
            max="100"
            variant="outlined"
            density="comfortable"
            :label="$t('cookbook.pages-per-ai-chunk')"
          />
          <v-alert
            v-if="selectedUploadedBook"
            density="compact"
            variant="tonal"
            :type="['failed', 'partial_failed'].includes(selectedUploadedBook.translationStatus) ? 'error' : 'info'"
          >
            {{ uploadedBookTranslationStatusText(selectedUploadedBook) }}
          </v-alert>
        </v-card-text>
      </BaseDialog>
      <BaseDialog
        v-model="uploadedBookDeleteDialog"
        :title="$t('cookbook.delete-book')"
        :icon="$globals.icons.delete"
        color="error"
        width="520"
        max-width="96vw"
        can-confirm
        :loading="uploadedBookDeleting"
        :submit-disabled="uploadedBookDeleting || !selectedUploadedBook || isUploadedBookExtracting(selectedUploadedBook) || isUploadedBookTranslating(selectedUploadedBook)"
        @confirm="deleteSelectedUploadedBook"
      >
        <v-card-text class="pt-4">
          <p>
            {{ $t("cookbook.delete-uploaded-book-confirm") }}
          </p>
          <p
            v-if="selectedUploadedBook"
            class="font-weight-bold mb-2"
          >
            {{ selectedUploadedBook.name }}
          </p>
          <v-alert
            v-if="selectedUploadedBook && !selectedUploadedBook.isTranslatedBook"
            density="compact"
            variant="tonal"
            type="warning"
          >
            {{ $t("cookbook.delete-uploaded-book-with-translations-warning") }}
          </v-alert>
          <v-alert
            v-if="selectedUploadedBook && (isUploadedBookExtracting(selectedUploadedBook) || isUploadedBookTranslating(selectedUploadedBook))"
            density="compact"
            variant="tonal"
            type="error"
            class="mt-3"
          >
            {{ $t("cookbook.cannot-delete-uploaded-book-processing") }}
          </v-alert>
        </v-card-text>
      </BaseDialog>
      <BaseDialog
        v-model="uploadedBookExtractionDialog"
        :title="$t('cookbook.extract-recipes-with-ai')"
        :icon="$globals.icons.robot"
        width="520"
        max-width="96vw"
        can-submit
        keep-open
        disable-submit-on-enter
        :loading="uploadedBookExtractionStarting"
        :submit-text="$t('cookbook.start-extraction')"
        :submit-icon="$globals.icons.robot"
        :submit-disabled="!selectedUploadedBook || isUploadedBookExtracting(selectedUploadedBook) || isUploadedBookTranslating(selectedUploadedBook)"
        @submit="startSelectedUploadedBookExtraction"
      >
        <v-card-text class="pt-4">
          <div
            v-if="selectedUploadedBook"
            class="text-subtitle-2 mb-3"
          >
            {{ selectedUploadedBook.name }}
          </div>
          <v-text-field
            v-model.number="uploadedBookPagesPerChunk"
            type="number"
            min="1"
            max="100"
            variant="outlined"
            density="comfortable"
            :label="$t('cookbook.pages-per-ai-chunk')"
          />
          <v-alert
            v-if="selectedUploadedBook"
            density="compact"
            variant="tonal"
            :type="['failed', 'partial_failed'].includes(selectedUploadedBook.extractionStatus) ? 'error' : 'info'"
          >
            {{ uploadedBookExtractionStatusText(selectedUploadedBook) }}
          </v-alert>
        </v-card-text>
      </BaseDialog>
      <BaseDialog
        v-model="backgroundJobsDialog"
        :title="$t('cookbook.background-jobs')"
        :icon="$globals.icons.timelineText"
        width="760"
        max-width="96vw"
      >
        <v-card-text class="pt-4">
          <div class="d-flex align-center justify-space-between ga-3 mb-3">
            <div class="text-body-2 text-medium-emphasis">
              {{ $t("cookbook.background-jobs-description") }}
            </div>
            <v-btn
              variant="text"
              color="primary"
              :prepend-icon="$globals.icons.refresh"
              :loading="uploadedBookRefreshInFlight"
              @click="refreshUploadedBooks"
            >
              {{ $t("general.refresh") }}
            </v-btn>
          </div>
          <v-alert
            v-if="!backgroundJobs.length"
            density="comfortable"
            variant="tonal"
            type="info"
          >
            {{ $t("cookbook.background-jobs-empty") }}
          </v-alert>
          <v-list
            v-else
            density="comfortable"
            class="background-jobs-list"
          >
            <template
              v-for="job in backgroundJobs"
              :key="job.key"
            >
              <v-list-item class="px-0 py-3">
                <template #prepend>
                  <v-avatar
                    rounded="lg"
                    :color="job.color"
                    variant="tonal"
                  >
                    <v-icon>{{ job.icon }}</v-icon>
                  </v-avatar>
                </template>
                <v-list-item-title class="font-weight-bold">
                  {{ job.title }}
                </v-list-item-title>
                <v-list-item-subtitle class="mt-1">
                  {{ job.subtitle }}
                </v-list-item-subtitle>
                <div class="mt-3">
                  <div class="d-flex align-center justify-space-between ga-3 mb-1">
                    <v-chip
                      size="small"
                      :color="job.color"
                      variant="tonal"
                    >
                      {{ job.statusText }}
                    </v-chip>
                    <span class="text-caption text-medium-emphasis">
                      {{ job.progressText }}
                    </span>
                  </div>
                  <v-progress-linear
                    :model-value="job.progress"
                    :indeterminate="job.active && !job.total"
                    :color="job.color"
                    height="8"
                    rounded
                  />
                  <div class="text-caption text-medium-emphasis mt-2">
                    {{ job.detailText }}
                  </div>
                  <v-alert
                    v-if="job.error"
                    density="compact"
                    variant="tonal"
                    type="warning"
                    class="mt-2"
                  >
                    {{ job.error }}
                  </v-alert>
                </div>
                <template #append>
                  <div class="d-flex align-center ga-1">
                    <v-btn
                      icon
                      variant="text"
                      :title="$t('cookbook.background-job-open-book')"
                      @click="openUploadedBookFile(job.book)"
                    >
                      <v-icon>{{ $globals.icons.openInNew }}</v-icon>
                    </v-btn>
                    <v-btn
                      v-if="job.canRetry"
                      icon
                      variant="text"
                      color="primary"
                      :title="$t('cookbook.background-job-retry')"
                      @click="retryBackgroundJob(job)"
                    >
                      <v-icon>{{ $globals.icons.refresh }}</v-icon>
                    </v-btn>
                    <v-btn
                      v-if="job.canCancel"
                      icon
                      variant="text"
                      color="error"
                      :loading="backgroundJobCancelling.has(job.key)"
                      :title="$t('cookbook.background-job-cancel')"
                      @click="cancelBackgroundJob(job)"
                    >
                      <v-icon>{{ $globals.icons.close }}</v-icon>
                    </v-btn>
                  </div>
                </template>
              </v-list-item>
              <v-divider />
            </template>
          </v-list>
        </v-card-text>
      </BaseDialog>
      <v-menu
        offset-y
        nudge-bottom="5"
        close-delay="50"
        nudge-right="15"
      >
        <template #activator="{ props }">
          <v-btn
            v-if="isOwnGroup"
            rounded
            size="large"
            class="ml-2 mt-3"
            v-bind="props"
            variant="elevated"
            elevation="2"
            :color="$vuetify.theme.current.dark ? 'background-lighten-1' : 'background-darken-1'"
          >
            <v-icon
              start
              size="large"
              color="primary"
            >
              {{ $globals.icons.createAlt }}
            </v-icon>
            {{ $t("general.create") }}
          </v-btn>
        </template>
        <v-list
          density="comfortable"
          class="mb-0 mt-1 py-0"
          variant="flat"
        >
          <template v-for="(item, index) in createLinks">
            <div
              v-if="!item.hide"
              :key="item.title"
            >
              <v-divider
                v-if="item.insertDivider"
                :key="index"
                class="mx-2"
              />
              <v-list-item
                v-if="!item.restricted || isOwnGroup"
                :key="item.title"
                :to="item.to"
                exact
                class="my-1"
              >
                <template #prepend>
                  <v-icon
                    size="40"
                    :icon="item.icon"
                  />
                </template>
                <v-list-item-title class="font-weight-medium" style="font-size: small;">
                  {{ item.title }}
                </v-list-item-title>
                <v-list-item-subtitle class="font-weight-medium" style="font-size: small;">
                  {{ item.subtitle }}
                </v-list-item-subtitle>
              </v-list-item>
            </div>
          </template>
        </v-list>
      </v-menu>
      <v-btn
        v-if="isOwnGroup"
        rounded
        size="default"
        class="ml-2 mt-2 mb-2 quick-create-shortcut-btn"
        variant="tonal"
        :color="$vuetify.theme.current.dark ? 'background-lighten-1' : 'background-darken-1'"
        @click="quickTextRecipeDialog = true"
      >
        <v-icon
          start
          color="primary"
        >
          {{ $globals.icons.textBoxCheckOutline }}
        </v-icon>
        {{ $t("recipe.create-from-text") }}
      </v-btn>
      <v-btn
        v-if="isOwnGroup"
        rounded
        size="default"
        class="ml-2 mt-0 mb-2 quick-create-shortcut-btn"
        variant="tonal"
        :color="$vuetify.theme.current.dark ? 'background-lighten-1' : 'background-darken-1'"
        :loading="manualDraftCreateLoading"
        @click="createManualDraftRecipe"
      >
        <v-icon
          start
          color="primary"
        >
          {{ $globals.icons.edit }}
        </v-icon>
        {{ $t("new-recipe.create-manually") }}
      </v-btn>
      <v-btn
        v-if="isOwnGroup"
        rounded
        size="default"
        class="ml-2 mt-0 mb-2 quick-create-shortcut-btn"
        variant="tonal"
        :color="$vuetify.theme.current.dark ? 'background-lighten-1' : 'background-darken-1'"
        @click="backgroundJobsDialog = true"
      >
        <v-icon
          start
          color="primary"
        >
          {{ $globals.icons.timelineText }}
        </v-icon>
        <span
          v-if="activeBackgroundJobCount > 0"
          class="background-job-inline-count"
        >
          {{ activeBackgroundJobCount }}
        </span>
        {{ $t("cookbook.background-jobs") }}
      </v-btn>
    </AppSidebar>
    <v-main class="pt-12">
      <v-scroll-x-transition>
        <div>
          <NuxtPage />
        </div>
      </v-scroll-x-transition>
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
import { useLoggedInState } from "~/composables/use-logged-in-state";
import type { OrganizerSidebarSection, SideBarLink } from "~/types/application-types";
import { useGroupSelf } from "~/composables/use-groups";
import { useCookbookPreferences, useOrganizerSidebarPreferences, useUserSearchQuerySession } from "~/composables/use-users/preferences";
import { useCookbookStore, usePublicCookbookStore } from "~/composables/store/use-cookbook-store";
import { useCategoryStore, usePublicCategoryStore } from "~/composables/store/use-category-store";
import { usePublicTagStore, useTagStore } from "~/composables/store/use-tag-store";
import type { ReadCookBook } from "~/lib/api/types/cookbook";
import type { RecipeCategory, RecipeTag } from "~/lib/api/types/recipe";
import type { UploadedBook } from "~/lib/api/types/uploaded-book";
import type { ShoppingListSummary } from "~/lib/api/types/household";
import { useUserApi } from "~/composables/api/api-client";
import { alert } from "~/composables/use-toast";

const i18n = useI18n();
const { $globals } = useNuxtApp();
const display = useDisplay();
const auth = useMealieAuth();
const { isOwnGroup } = useLoggedInState();
const { group } = useGroupSelf();
const api = useUserApi(i18n);

const route = useRoute();
const groupSlug = computed(() => route.params.groupSlug as string || auth.user.value?.groupSlug || "");

const cookbookPreferences = useCookbookPreferences();
const organizerSidebarPreferences = useOrganizerSidebarPreferences();
const searchQuerySession = useUserSearchQuerySession();
const ownCookbookStore = computed(() => isOwnGroup.value ? useCookbookStore(i18n) : null);
const ownCategoryStore = computed(() => isOwnGroup.value ? useCategoryStore(i18n) : null);
const ownTagStore = computed(() => isOwnGroup.value ? useTagStore(i18n) : null);
const publicCookbookStoreCache = new Map<string, ReturnType<typeof usePublicCookbookStore>>();
const publicCategoryStoreCache = new Map<string, ReturnType<typeof usePublicCategoryStore>>();
const publicTagStoreCache = new Map<string, ReturnType<typeof usePublicTagStore>>();
let publicStoreCacheOrder: string[] = [];
const MAX_PUBLIC_STORE_CACHE_SIZE = 8;

function pruneCacheEntry<T>(cache: Map<string, T>, slug: string) {
  cache.delete(slug);
}

function rememberPublicStoreSlug(slug: string) {
  publicStoreCacheOrder = publicStoreCacheOrder.filter(item => item !== slug);
  publicStoreCacheOrder.push(slug);

  while (publicStoreCacheOrder.length > MAX_PUBLIC_STORE_CACHE_SIZE) {
    const expiredSlug = publicStoreCacheOrder.shift();
    if (!expiredSlug) {
      continue;
    }

    pruneCacheEntry(publicCookbookStoreCache, expiredSlug);
    pruneCacheEntry(publicCategoryStoreCache, expiredSlug);
    pruneCacheEntry(publicTagStoreCache, expiredSlug);
  }
}

function getPublicCookbookStore(slug: string) {
  rememberPublicStoreSlug(slug);
  if (!publicCookbookStoreCache.has(slug)) {
    publicCookbookStoreCache.set(slug, usePublicCookbookStore(slug, i18n));
  }
  return publicCookbookStoreCache.get(slug)!;
}

function getPublicCategoryStore(slug: string) {
  rememberPublicStoreSlug(slug);
  if (!publicCategoryStoreCache.has(slug)) {
    publicCategoryStoreCache.set(slug, usePublicCategoryStore(slug, i18n));
  }
  return publicCategoryStoreCache.get(slug)!;
}

function getPublicTagStore(slug: string) {
  rememberPublicStoreSlug(slug);
  if (!publicTagStoreCache.has(slug)) {
    publicTagStoreCache.set(slug, usePublicTagStore(slug, i18n));
  }
  return publicTagStoreCache.get(slug)!;
}

const cookbooks = computed(() => {
  if (ownCookbookStore.value) {
    return ownCookbookStore.value.store.value;
  }
  else if (groupSlug.value) {
    const publicStore = getPublicCookbookStore(groupSlug.value);
    return unref(publicStore.store);
  }
  return [];
});

const categories = computed(() => {
  if (ownCategoryStore.value) {
    return ownCategoryStore.value.store.value;
  }
  else if (groupSlug.value) {
    const publicStore = getPublicCategoryStore(groupSlug.value);
    return unref(publicStore.store);
  }
  return [];
});

const tags = computed(() => {
  if (ownTagStore.value) {
    return ownTagStore.value.store.value;
  }
  else if (groupSlug.value) {
    const publicStore = getPublicTagStore(groupSlug.value);
    return unref(publicStore.store);
  }
  return [];
});

const showImageImport = computed(() => group.value?.aiProviderSettings?.imageProviderEnabled);

const sidebar = ref<boolean>(false);
const quickTextRecipeDialog = ref(false);
const manualDraftCreateLoading = ref(false);
const uploadedBookDialog = ref(false);
const uploadedBookFile = ref<File | null>(null);
const uploadedBookFiles = ref<File[]>([]);
const uploadedBookFolderInput = ref<HTMLInputElement | null>(null);
const uploadedBookName = ref("");
const uploadedBookUploading = ref(false);
const uploadedBooks = ref<UploadedBook[]>([]);
const uploadedBookAction = ref<"none" | "extract" | "translate">("none");
const uploadedBookPagesPerChunk = ref(10);
const uploadedBookExtractionDialog = ref(false);
const uploadedBookExtractionStarting = ref(false);
const uploadedBookTranslationDialog = ref(false);
const uploadedBookTranslationStarting = ref(false);
const uploadedBookDeleteDialog = ref(false);
const uploadedBookDeleting = ref(false);
const uploadedBookTargetLanguage = ref(defaultUploadedBookTargetLanguage());
const selectedUploadedBook = ref<UploadedBook | null>(null);
const shoppingLists = ref<ShoppingListSummary[]>([]);
const backgroundJobsDialog = ref(false);
const backgroundJobCancelling = ref<Set<string>>(new Set());
const emptyCategoryIds = ref<Set<string>>(new Set());
const emptyTagIds = ref<Set<string>>(new Set());
let uploadedBookRefreshTimer: ReturnType<typeof setInterval> | null = null;
const uploadedBookRefreshInFlight = ref(false);
const router = useRouter();
const MANUAL_DRAFT_RECIPE_PREFIX = "__mealie_manual_draft__";
const ORGANIZERS_UPDATED_EVENT = "mealie:organizers-updated";
const uploadedBookTranslationLanguageOptions = computed(() => [
  i18n.t("cookbook.language-hebrew"),
  i18n.t("cookbook.language-english"),
  i18n.t("cookbook.language-arabic"),
  i18n.t("cookbook.language-french"),
  i18n.t("cookbook.language-italian"),
  i18n.t("cookbook.language-spanish"),
  i18n.t("cookbook.language-german"),
  i18n.t("cookbook.language-russian"),
]);
const uploadedBookSupportedExtensions = [
  ".pdf",
  ".epub",
  ".mobi",
  ".azw",
  ".azw3",
  ".azw4",
  ".fb2",
  ".fb2.zip",
  ".djvu",
  ".djv",
  ".cbz",
  ".cbr",
  ".cb7",
  ".cbt",
  ".txt",
  ".rtf",
  ".doc",
  ".docx",
  ".odt",
  ".html",
  ".htm",
  ".mhtml",
  ".mht",
  ".md",
  ".markdown",
  ".lit",
  ".pdb",
  ".zip",
  ".rar",
  ".7z",
];

function createManualDraftRecipeName() {
  const randomSuffix = typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `${MANUAL_DRAFT_RECIPE_PREFIX}${randomSuffix}`;
}

async function createManualDraftRecipe() {
  if (manualDraftCreateLoading.value) {
    return;
  }

  manualDraftCreateLoading.value = true;
  try {
    const { response } = await api.recipes.createOne({ name: createManualDraftRecipeName() });
    if (response?.status !== 201 || !response.data) {
      alert.error(i18n.t("recipe.recipe-creation-failed"));
      return;
    }

    await router.push(`/g/${groupSlug.value}/r/${response.data}?edit=true&manualDraft=true`);
  }
  finally {
    manualDraftCreateLoading.value = false;
  }
}
const uploadedBookAccept = [
  ...uploadedBookSupportedExtensions,
  "application/pdf",
  "application/epub+zip",
].join(",");
const hasMultipleUploadedBookFiles = computed(() => uploadedBookFiles.value.length > 1);
onMounted(() => {
  sidebar.value = display.lgAndUp.value;
  window.addEventListener(ORGANIZERS_UPDATED_EVENT, handleOrganizersUpdated);
  syncUploadedBookRefreshTimer();
});

onBeforeUnmount(() => {
  window.removeEventListener(ORGANIZERS_UPDATED_EVENT, handleOrganizersUpdated);
  clearUploadedBookRefreshTimer();
});

watch(
  () => [isOwnGroup.value, auth.user.value?.id, groupSlug.value],
  () => {
    refreshUploadedBooks();
    refreshShoppingLists();
    refreshOrganizerNavigationData();
  },
  { immediate: true },
);

function cookbookAsLink(cookbook: ReadCookBook): SideBarLink {
  return {
    key: cookbook.slug || "",
    icon: $globals.icons.pages,
    title: cookbook.name,
    to: `/g/${groupSlug.value}/cookbooks/${cookbook.slug || ""}`,
    restricted: false,
  };
}

function uploadedBookAsLink(book: UploadedBook): SideBarLink {
  const children: SideBarLink[] = [
    {
      key: `uploaded-book-${book.id}-open`,
      icon: $globals.icons.openInNew,
      title: i18n.t("cookbook.open-book"),
      href: api.uploadedBooks.fileUrl(book.id),
      restricted: true,
    },
  ];

  if (!book.isTranslatedBook) {
    children.push(
      {
        key: `uploaded-book-${book.id}-extract`,
        icon: $globals.icons.robot,
        title: uploadedBookExtractionActionTitle(book),
        onClick: () => openUploadedBookExtractionDialog(book),
        restricted: true,
      },
      {
        key: `uploaded-book-${book.id}-translate`,
        icon: $globals.icons.translate,
        title: uploadedBookTranslationActionTitle(book),
        onClick: () => openUploadedBookTranslationDialog(book),
        restricted: true,
      },
    );
  }

  children.push({
    key: `uploaded-book-${book.id}-delete`,
    icon: $globals.icons.delete,
    title: i18n.t("cookbook.delete-book"),
    onClick: () => openUploadedBookDeleteDialog(book),
    restricted: true,
  });

  return {
    key: `uploaded-book-${book.id}`,
    icon: book.isTranslatedBook ? $globals.icons.translate : book.extension === ".pdf" ? $globals.icons.filePDF : $globals.icons.book,
    title: uploadedBookNavigationTitle(book),
    childrenStartExpanded: isUploadedBookExtracting(book) || isUploadedBookTranslating(book),
    children,
    restricted: true,
  };
}

function uploadBookActionLink(): SideBarLink {
  return {
    key: "upload-book",
    icon: $globals.icons.upload,
    title: i18n.t("cookbook.upload-book"),
    restricted: true,
    onClick: () => {
      uploadedBookDialog.value = true;
    },
  };
}

function organizerItemAsLink(item: RecipeCategory | RecipeTag, queryKey: "categories" | "tags", icon: string): SideBarLink | null {
  if (!item.id) {
    return null;
  }

  return {
    key: item.id,
    icon,
    title: item.name,
    to: `/g/${groupSlug.value}?${queryKey}=${encodeURIComponent(item.id)}`,
    restricted: false,
  };
}

function sortByName<T extends { name: string }>(items: T[]) {
  return [...items].sort((a, b) => a.name.localeCompare(b.name));
}

async function refreshEmptyOrganizerItems() {
  if (!isOwnGroup.value) {
    emptyCategoryIds.value = new Set();
    emptyTagIds.value = new Set();
    return;
  }

  const [categoryResponse, tagResponse] = await Promise.allSettled([
    api.categories.getEmpty(),
    api.tags.getEmpty(),
  ]);

  if (categoryResponse.status === "fulfilled" && categoryResponse.value.data) {
    emptyCategoryIds.value = new Set(categoryResponse.value.data.map(category => category.id));
  }

  if (tagResponse.status === "fulfilled" && tagResponse.value.data) {
    emptyTagIds.value = new Set(tagResponse.value.data.map(tag => tag.id));
  }
}

async function refreshOrganizerNavigationData() {
  const tasks: Promise<unknown>[] = [refreshEmptyOrganizerItems()];

  if (ownCategoryStore.value) {
    tasks.push(ownCategoryStore.value.actions.refresh());
  }

  if (ownTagStore.value) {
    tasks.push(ownTagStore.value.actions.refresh());
  }

  await Promise.allSettled(tasks);
}

function handleOrganizersUpdated() {
  refreshShoppingLists();
  refreshOrganizerNavigationData();
}

function clearRecipeSearchSession() {
  searchQuerySession.value.recipe = "";
}

function hasLinkedRecipes(item: RecipeCategory | RecipeTag, emptyIds: Set<string>) {
  return !!item.id && !emptyIds.has(item.id);
}

function isSupportedUploadedBookFile(file: File) {
  const fileName = file.name.toLowerCase();
  return uploadedBookSupportedExtensions.some(extension => fileName.endsWith(extension));
}

function setUploadedBookFiles(files: File[]) {
  const supportedFiles = files.filter(isSupportedUploadedBookFile);
  uploadedBookFiles.value = supportedFiles;
  uploadedBookFile.value = supportedFiles.length === 1 ? supportedFiles[0] : null;

  if (supportedFiles.length > 1) {
    uploadedBookName.value = "";
    uploadedBookAction.value = "none";
  }
}

function onUploadedBookFileSelected(value: File | File[] | null) {
  if (Array.isArray(value)) {
    setUploadedBookFiles(value);
  }
  else {
    setUploadedBookFiles(value ? [value] : []);
  }

  if (uploadedBookFolderInput.value) {
    uploadedBookFolderInput.value.value = "";
  }
}

function onUploadedBookFolderSelected(event: Event) {
  const input = event.target as HTMLInputElement;
  setUploadedBookFiles(Array.from(input.files || []));
}

function openUploadedBookFolderPicker() {
  uploadedBookFolderInput.value?.click();
}

const regularUploadedBooks = computed(() => uploadedBooks.value.filter(book => !book.isTranslatedBook));
const translatedUploadedBooks = computed(() => uploadedBooks.value.filter(book => book.isTranslatedBook));

const shoppingListLinks = computed<SideBarLink[]>(() => {
  return shoppingLists.value.map(list => ({
    key: list.id,
    icon: $globals.icons.formatListCheck,
    title: list.name || i18n.t("shopping-list.shopping-list"),
    to: `/shopping-lists/${list.id}`,
    restricted: true,
  }));
});

const currentUserHouseholdId = computed(() => auth.user.value?.householdId);
const cookbookLinks = computed<SideBarLink[]>(() => {
  const uploadedLinks = isOwnGroup.value ? regularUploadedBooks.value.map(uploadedBookAsLink) : [];
  if (!cookbooks.value?.length) {
    return uploadedLinks;
  }

  const sortedCookbooks = [...cookbooks.value].sort((a, b) => (a.position || 0) - (b.position || 0));

  const ownLinks: SideBarLink[] = [];
  const links: SideBarLink[] = [];
  const cookbooksByHousehold = sortedCookbooks.reduce((acc, cookbook) => {
    const householdName = cookbook.household?.name || "";
    (acc[householdName] ||= []).push(cookbook);
    return acc;
  }, {} as Record<string, ReadCookBook[]>);

  Object.entries(cookbooksByHousehold).forEach(([householdName, cookbooks]) => {
    if (!cookbooks.length) {
      return;
    }
    if (cookbooks[0].householdId === currentUserHouseholdId.value) {
      ownLinks.push(...cookbooks.map(cookbookAsLink));
    }
    else {
      links.push({
        key: householdName,
        icon: $globals.icons.book,
        title: householdName,
        children: cookbooks.map(cookbookAsLink),
        restricted: false,
      });
    }
  });

  links.sort((a, b) => a.title.localeCompare(b.title));
  const visibleCookbookLinks = auth.user.value && cookbookPreferences.value.hideOtherHouseholds
    ? ownLinks
    : [...ownLinks, ...links];

  return [...uploadedLinks, ...visibleCookbookLinks];
});

const translatedBookLinks = computed<SideBarLink[]>(() => {
  return isOwnGroup.value ? translatedUploadedBooks.value.map(uploadedBookAsLink) : [];
});

const sidebarCookbookLinks = computed<SideBarLink[]>(() => {
  if (!translatedBookLinks.value.length) {
    return cookbookLinks.value;
  }

  return [
    ...cookbookLinks.value,
    {
      key: "translated-uploaded-books",
      icon: $globals.icons.translate,
      title: i18n.t("cookbook.translated-books"),
      children: translatedBookLinks.value,
      childrenStartExpanded: translatedUploadedBooks.value.some(isUploadedBookTranslating),
      restricted: true,
    },
  ];
});

const categoryLinks = computed<SideBarLink[]>(() => {
  return sortByName(categories.value)
    .filter(category => hasLinkedRecipes(category, emptyCategoryIds.value))
    .map(category => organizerItemAsLink(category, "categories", $globals.icons.categories))
    .filter((link): link is SideBarLink => !!link);
});

const tagLinks = computed<SideBarLink[]>(() => {
  return sortByName(tags.value)
    .filter(tag => hasLinkedRecipes(tag, emptyTagIds.value))
    .map(tag => organizerItemAsLink(tag, "tags", $globals.icons.tags))
    .filter((link): link is SideBarLink => !!link);
});

function resetUploadBookForm() {
  if (uploadedBookUploading.value) {
    return;
  }

  uploadedBookFile.value = null;
  uploadedBookFiles.value = [];
  if (uploadedBookFolderInput.value) {
    uploadedBookFolderInput.value.value = "";
  }
  uploadedBookName.value = "";
  uploadedBookAction.value = "none";
  uploadedBookPagesPerChunk.value = 10;
  uploadedBookTargetLanguage.value = defaultUploadedBookTargetLanguage();
}

async function refreshUploadedBooks() {
  if (uploadedBookRefreshInFlight.value) {
    return;
  }

  if (!isOwnGroup.value || !auth.user.value) {
    uploadedBooks.value = [];
    return;
  }

  uploadedBookRefreshInFlight.value = true;
  try {
    const { data } = await api.uploadedBooks.getAll();
    uploadedBooks.value = data || [];
    if (selectedUploadedBook.value) {
      selectedUploadedBook.value = uploadedBooks.value.find(book => book.id === selectedUploadedBook.value?.id) || selectedUploadedBook.value;
    }
  }
  finally {
    uploadedBookRefreshInFlight.value = false;
    syncUploadedBookRefreshTimer();
  }
}

async function refreshShoppingLists() {
  if (!isOwnGroup.value || !auth.user.value) {
    shoppingLists.value = [];
    return;
  }

  const { data } = await api.shopping.lists.getAll(1, -1, { orderBy: "name", orderDirection: "asc" });
  shoppingLists.value = data?.items || [];
}

async function uploadBook() {
  const files = uploadedBookFiles.value;
  if (!files.length) {
    return;
  }

  uploadedBookUploading.value = true;
  const uploaded: UploadedBook[] = [];
  let firstError: unknown = null;

  try {
    for (const file of files) {
      const { data, error } = await api.uploadedBooks.upload(file, hasMultipleUploadedBookFiles.value ? null : uploadedBookName.value);
      if (data) {
        uploaded.push(data);
      }
      else if (!firstError) {
        firstError = error;
      }
    }
  }
  finally {
    uploadedBookUploading.value = false;
  }

  if (!uploaded.length) {
    const fallback = i18n.t("cookbook.upload-book-failed");
    const detail = (firstError as { response?: { data?: { detail?: unknown }; status?: number } })?.response?.data?.detail;
    const status = (firstError as { response?: { status?: number } })?.response?.status;
    alert.error(typeof detail === "string" ? detail : status ? `${fallback} (${status})` : fallback);
    return;
  }

  if (uploaded.length === 1) {
    alert.success(i18n.t("cookbook.upload-book-success"));
  }
  else if (uploaded.length === files.length) {
    alert.success(i18n.t("cookbook.upload-books-success", { count: uploaded.length }));
  }
  else {
    alert.info(i18n.t("cookbook.upload-books-partial-success", { uploaded: uploaded.length, total: files.length }));
  }

  if (uploaded.length === 1 && uploadedBookAction.value === "extract") {
    await startUploadedBookExtraction(uploaded[0], false);
  }
  else if (uploaded.length === 1 && uploadedBookAction.value === "translate") {
    await startUploadedBookTranslation(uploaded[0], false);
  }

  uploadedBookDialog.value = false;
  resetUploadBookForm();
  await refreshUploadedBooks();
}

function clearUploadedBookRefreshTimer() {
  if (uploadedBookRefreshTimer) {
    clearInterval(uploadedBookRefreshTimer);
    uploadedBookRefreshTimer = null;
  }
}

function syncUploadedBookRefreshTimer() {
  if (!import.meta.client) {
    return;
  }

  const hasProcessingBooks = uploadedBooks.value.some(book => isUploadedBookExtracting(book) || isUploadedBookTranslating(book));
  if (hasProcessingBooks && !uploadedBookRefreshTimer) {
    uploadedBookRefreshTimer = setInterval(() => {
      refreshUploadedBooks();
    }, 6000);
  }
  else if (!hasProcessingBooks) {
    clearUploadedBookRefreshTimer();
  }
}

function isUploadedBookExtracting(book: UploadedBook) {
  return ["processing", "retrying"].includes(book.extractionStatus);
}

function isUploadedBookTranslating(book: UploadedBook) {
  return ["processing", "retrying"].includes(book.translationStatus);
}

type BackgroundJobType = "extraction" | "translation";

interface BackgroundJob {
  key: string;
  type: BackgroundJobType;
  book: UploadedBook;
  title: string;
  subtitle: string;
  status: string;
  statusText: string;
  detailText: string;
  progressText: string;
  progress: number;
  total: number;
  active: boolean;
  canCancel: boolean;
  canRetry: boolean;
  error: string | null;
  icon: string;
  color: string;
}

const visibleBackgroundJobStatuses = new Set(["processing", "retrying", "partial_failed", "failed", "cancelled"]);
const retryableBackgroundJobStatuses = new Set(["partial_failed", "failed", "cancelled"]);
const BACKGROUND_JOB_STALE_MS = 30 * 60 * 1000;

const backgroundJobs = computed<BackgroundJob[]>(() => {
  const jobs = uploadedBooks.value
    .flatMap((book) => {
      const bookJobs = [
        uploadedBookBackgroundJob(book, "extraction"),
        uploadedBookBackgroundJob(book, "translation"),
      ];
      return bookJobs.filter((job): job is BackgroundJob => !!job);
    })
    .sort((a, b) => Number(b.active) - Number(a.active) || a.title.localeCompare(b.title));

  return jobs;
});

const activeBackgroundJobCount = computed(() => backgroundJobs.value.filter(job => job.active).length);

function uploadedBookBackgroundJob(book: UploadedBook, type: BackgroundJobType): BackgroundJob | null {
  const isExtraction = type === "extraction";
  const status = isExtraction ? book.extractionStatus : book.translationStatus;

  if (!visibleBackgroundJobStatuses.has(status)) {
    return null;
  }

  const total = isExtraction ? book.extractionTotalChunks : book.translationTotalChunks;
  const completed = isExtraction ? book.extractionCompletedChunks : book.translationCompletedChunks;
  const failed = isExtraction ? book.extractionFailedChunks : book.translationFailedChunks;
  const retries = isExtraction ? book.extractionRetryCount : book.translationRetryCount;
  const processed = Math.min(total || 0, completed + failed);
  const active = ["processing", "retrying"].includes(status);
  const error = isExtraction ? book.extractionError : book.translationError;
  const stale = active && isBackgroundJobStale(book);
  const detailText = isExtraction
    ? i18n.t("cookbook.background-job-extraction-detail", {
        found: book.extractionRecipesFound,
        created: book.extractionRecipesCreated,
        failed,
        retries,
      })
    : i18n.t("cookbook.background-job-translation-detail", {
        language: book.translationLanguage || defaultUploadedBookTargetLanguage(),
        failed,
        retries,
      });

  return {
    key: `${type}-${book.id}`,
    type,
    book,
    title: book.name,
    subtitle: isExtraction ? i18n.t("cookbook.background-job-extraction") : i18n.t("cookbook.background-job-translation"),
    status,
    statusText: stale ? i18n.t("cookbook.background-job-status-stale") : backgroundJobStatusText(status),
    detailText: stale ? `${detailText} · ${i18n.t("cookbook.background-job-stale-hint")}` : detailText,
    progressText: i18n.t("cookbook.background-job-progress", {
      completed,
      total: total || "?",
    }),
    progress: total ? Math.round((processed / total) * 100) : active ? 0 : 100,
    total,
    active,
    canCancel: active,
    canRetry: retryableBackgroundJobStatuses.has(status),
    error: error && error !== "Cancelled by user" ? error : null,
    icon: isExtraction ? $globals.icons.robot : $globals.icons.translate,
    color: stale ? "warning" : backgroundJobStatusColor(status),
  };
}

function isBackgroundJobStale(book: UploadedBook) {
  const updatedAt = Date.parse(book.updatedAt || "");
  return Number.isFinite(updatedAt) && Date.now() - updatedAt > BACKGROUND_JOB_STALE_MS;
}

function backgroundJobStatusText(status: string) {
  return i18n.t(`cookbook.background-job-status-${status.replace("_", "-")}`);
}

function backgroundJobStatusColor(status: string) {
  if (status === "processing") {
    return "primary";
  }
  if (status === "retrying") {
    return "warning";
  }
  if (status === "partial_failed" || status === "failed") {
    return "error";
  }
  if (status === "cancelled") {
    return "grey";
  }
  return "success";
}

function setBackgroundJobCancelling(key: string, cancelling: boolean) {
  const next = new Set(backgroundJobCancelling.value);
  if (cancelling) {
    next.add(key);
  }
  else {
    next.delete(key);
  }
  backgroundJobCancelling.value = next;
}

function openUploadedBookFile(book: UploadedBook) {
  if (!import.meta.client) {
    return;
  }
  window.open(api.uploadedBooks.fileUrl(book.id), "_blank", "noopener");
}

async function cancelBackgroundJob(job: BackgroundJob) {
  if (!job.canCancel || backgroundJobCancelling.value.has(job.key)) {
    return;
  }

  setBackgroundJobCancelling(job.key, true);
  const { data, error } = await (job.type === "extraction"
    ? api.uploadedBooks.cancelExtraction(job.book.id)
    : api.uploadedBooks.cancelTranslation(job.book.id)
  ).finally(() => {
    setBackgroundJobCancelling(job.key, false);
  });

  if (!data) {
    const detail = error?.response?.data?.detail;
    alert.error(typeof detail === "string" ? detail : i18n.t("cookbook.background-job-cancel-failed"));
    return;
  }

  selectedUploadedBook.value = data;
  alert.success(i18n.t("cookbook.background-job-cancelled"));
  await refreshUploadedBooks();
}

async function retryBackgroundJob(job: BackgroundJob) {
  uploadedBookPagesPerChunk.value = job.type === "extraction"
    ? job.book.extractionPagesPerChunk || 10
    : job.book.translationPagesPerChunk || 10;

  if (job.type === "extraction") {
    uploadedBookTargetLanguage.value = job.book.extractionTranslateLanguage || defaultUploadedBookTargetLanguage();
    await startUploadedBookExtraction(job.book, false);
  }
  else {
    uploadedBookTargetLanguage.value = job.book.translationLanguage || defaultUploadedBookTargetLanguage();
    await startUploadedBookTranslation(job.book, false);
  }
}

function uploadedBookNavigationTitle(book: UploadedBook) {
  if (isUploadedBookExtracting(book)) {
    const total = book.extractionTotalChunks || "?";
    return `${book.name} (${book.extractionCompletedChunks}/${total})`;
  }

  if (isUploadedBookTranslating(book)) {
    const total = book.translationTotalChunks || "?";
    return `${book.name} (${book.translationCompletedChunks}/${total})`;
  }

  if (book.isTranslatedBook && book.translationLanguage) {
    return `${book.name}`;
  }

  if (!isUploadedBookExtracting(book)) {
    return book.name;
  }

  return book.name;
}

function uploadedBookExtractionActionTitle(book: UploadedBook) {
  if (isUploadedBookExtracting(book) || isUploadedBookTranslating(book)) {
    return i18n.t("cookbook.extraction-running");
  }
  if (book.extractionStatus === "completed") {
    return i18n.t("cookbook.extract-again-with-ai");
  }
  return i18n.t("cookbook.extract-recipes-with-ai");
}

function uploadedBookTranslationActionTitle(book: UploadedBook) {
  if (isUploadedBookExtracting(book) || isUploadedBookTranslating(book)) {
    return i18n.t("cookbook.translation-running");
  }
  if (book.translationStatus === "completed") {
    return i18n.t("cookbook.translate-again-with-ai");
  }
  return i18n.t("cookbook.translate-book-with-ai");
}

function uploadedBookExtractionStatusText(book: UploadedBook) {
  if (isUploadedBookExtracting(book)) {
    return i18n.t("cookbook.extraction-progress", {
      completed: book.extractionCompletedChunks,
      total: book.extractionTotalChunks || "?",
      created: book.extractionRecipesCreated,
      failed: book.extractionFailedChunks || 0,
      retries: book.extractionRetryCount || 0,
    });
  }
  if (book.extractionStatus === "completed") {
    return i18n.t("cookbook.extraction-completed", {
      found: book.extractionRecipesFound,
      created: book.extractionRecipesCreated,
    });
  }
  if (book.extractionStatus === "partial_failed") {
    return i18n.t("cookbook.extraction-partial-failed", {
      completed: book.extractionCompletedChunks,
      total: book.extractionTotalChunks || "?",
      failed: book.extractionFailedChunks || 0,
      created: book.extractionRecipesCreated,
    });
  }
  if (book.extractionStatus === "failed") {
    return book.extractionError || i18n.t("cookbook.extraction-failed");
  }
  if (book.extractionStatus === "cancelled") {
    return i18n.t("cookbook.extraction-cancelled");
  }
  return i18n.t("cookbook.extraction-not-started");
}

function uploadedBookTranslationStatusText(book: UploadedBook) {
  if (isUploadedBookTranslating(book)) {
    return i18n.t("cookbook.translation-progress", {
      completed: book.translationCompletedChunks,
      total: book.translationTotalChunks || "?",
      failed: book.translationFailedChunks || 0,
      retries: book.translationRetryCount || 0,
    });
  }
  if (book.translationStatus === "completed") {
    return i18n.t("cookbook.translation-completed", {
      language: book.translationLanguage || uploadedBookTargetLanguage.value,
    });
  }
  if (book.translationStatus === "partial_failed") {
    return i18n.t("cookbook.translation-partial-failed", {
      completed: book.translationCompletedChunks,
      total: book.translationTotalChunks || "?",
      failed: book.translationFailedChunks || 0,
    });
  }
  if (book.translationStatus === "failed") {
    return book.translationError || i18n.t("cookbook.translation-failed");
  }
  if (book.translationStatus === "cancelled") {
    return i18n.t("cookbook.translation-cancelled");
  }
  return i18n.t("cookbook.translation-not-started");
}

function openUploadedBookExtractionDialog(book: UploadedBook) {
  selectedUploadedBook.value = book;
  uploadedBookPagesPerChunk.value = book.extractionPagesPerChunk || 10;
  uploadedBookTargetLanguage.value = book.extractionTranslateLanguage || defaultUploadedBookTargetLanguage();
  uploadedBookExtractionDialog.value = true;
}

function openUploadedBookTranslationDialog(book: UploadedBook) {
  selectedUploadedBook.value = book;
  uploadedBookPagesPerChunk.value = book.translationPagesPerChunk || 10;
  uploadedBookTargetLanguage.value = book.translationLanguage || defaultUploadedBookTargetLanguage();
  uploadedBookTranslationDialog.value = true;
}

function openUploadedBookDeleteDialog(book: UploadedBook) {
  selectedUploadedBook.value = book;
  uploadedBookDeleteDialog.value = true;
}

async function startSelectedUploadedBookExtraction() {
  if (!selectedUploadedBook.value) {
    return;
  }
  await startUploadedBookExtraction(selectedUploadedBook.value, true);
}

async function startSelectedUploadedBookTranslation() {
  if (!selectedUploadedBook.value) {
    return;
  }
  await startUploadedBookTranslation(selectedUploadedBook.value, true);
}

async function deleteSelectedUploadedBook() {
  if (!selectedUploadedBook.value) {
    return;
  }

  uploadedBookDeleting.value = true;
  const { error } = await api.uploadedBooks.delete(selectedUploadedBook.value.id).finally(() => {
    uploadedBookDeleting.value = false;
  });

  if (error) {
    const fallback = i18n.t("cookbook.delete-uploaded-book-failed");
    const detail = error?.response?.data?.detail;
    alert.error(typeof detail === "string" ? detail : fallback);
    return;
  }

  alert.success(i18n.t("cookbook.delete-uploaded-book-success"));
  uploadedBookDeleteDialog.value = false;
  selectedUploadedBook.value = null;
  await refreshUploadedBooks();
}

async function startUploadedBookExtraction(book: UploadedBook, closeDialog: boolean) {
  const pagesPerChunk = Math.min(Math.max(Number(uploadedBookPagesPerChunk.value) || 10, 1), 100);
  uploadedBookExtractionStarting.value = true;
  const { data, error } = await api.uploadedBooks.extractRecipes(book.id, {
    pagesPerChunk,
    translateLanguage: "Hebrew",
  }).finally(() => {
    uploadedBookExtractionStarting.value = false;
  });

  if (!data) {
    const fallback = i18n.t("cookbook.extraction-start-failed");
    const detail = error?.response?.data?.detail;
    const message = typeof detail === "string" ? detail : fallback;
    alert.error(message);
    return;
  }

  selectedUploadedBook.value = data;
  alert.success(i18n.t("cookbook.extraction-started"));
  if (closeDialog) {
    uploadedBookExtractionDialog.value = false;
  }
  await refreshUploadedBooks();
}

async function startUploadedBookTranslation(book: UploadedBook, closeDialog: boolean) {
  const pagesPerChunk = Math.min(Math.max(Number(uploadedBookPagesPerChunk.value) || 10, 1), 100);
  const targetLanguage = (uploadedBookTargetLanguage.value || defaultUploadedBookTargetLanguage()).trim();
  uploadedBookTranslationStarting.value = true;
  const { data, error } = await api.uploadedBooks.translate(book.id, {
    pagesPerChunk,
    targetLanguage,
  }).finally(() => {
    uploadedBookTranslationStarting.value = false;
  });

  if (!data) {
    const fallback = i18n.t("cookbook.translation-start-failed");
    const detail = error?.response?.data?.detail;
    const message = typeof detail === "string" ? detail : fallback;
    alert.error(message);
    return;
  }

  selectedUploadedBook.value = data;
  alert.success(i18n.t("cookbook.translation-started"));
  if (closeDialog) {
    uploadedBookTranslationDialog.value = false;
  }
  await refreshUploadedBooks();
}

function defaultUploadedBookTargetLanguage() {
  const locale = String(i18n.locale.value || "").toLowerCase();
  if (locale.startsWith("he")) {
    return i18n.t("cookbook.language-hebrew");
  }
  if (locale.startsWith("ar")) {
    return i18n.t("cookbook.language-arabic");
  }
  return i18n.t("cookbook.language-english");
}

const organizerSidebarSections = computed<OrganizerSidebarSection[]>(() => [
  {
    key: "shoppingLists",
    icon: $globals.icons.formatListCheck,
    title: i18n.t("shopping-list.shopping-lists"),
    links: shoppingListLinks.value,
  },
  {
    key: "cookbooks",
    icon: $globals.icons.book,
    title: i18n.t("cookbook.cookbooks"),
    links: cookbookLinks.value,
  },
  {
    key: "translatedBooks",
    icon: $globals.icons.translate,
    title: i18n.t("cookbook.translated-books"),
    links: translatedBookLinks.value,
  },
  {
    key: "categories",
    icon: $globals.icons.categories,
    title: i18n.t("category.categories"),
    links: categoryLinks.value,
  },
  {
    key: "tags",
    icon: $globals.icons.tags,
    title: i18n.t("tag.tags"),
    links: tagLinks.value,
  },
]);

const createLinks = computed(() => [
  {
    insertDivider: false,
    icon: $globals.icons.link,
    title: i18n.t("general.import"),
    subtitle: i18n.t("new-recipe.import-by-url"),
    to: `/g/${groupSlug.value}/r/create/url`,
    restricted: true,
    hide: false,
  },
  {
    insertDivider: false,
    icon: $globals.icons.fileImage,
    title: i18n.t("recipe.create-from-images"),
    subtitle: i18n.t("recipe.create-recipe-from-images"),
    to: `/g/${groupSlug.value}/r/create/image`,
    restricted: true,
    hide: !showImageImport.value,
  },
  {
    insertDivider: true,
    icon: $globals.icons.edit,
    title: i18n.t("general.create"),
    subtitle: i18n.t("new-recipe.create-manually"),
    to: `/g/${groupSlug.value}/r/create/new`,
    restricted: true,
    hide: false,
  },
]);

const topLinks = computed<SideBarLink[]>(() => [
  {
    icon: $globals.icons.silverwareForkKnife,
    to: `/g/${groupSlug.value}`,
    title: i18n.t("general.recipes"),
    onClick: clearRecipeSearchSession,
    restricted: false,
  },
  {
    icon: $globals.icons.search,
    to: `/g/${groupSlug.value}/recipes/finder`,
    title: i18n.t("recipe-finder.recipe-finder"),
    restricted: false,
  },
  {
    icon: $globals.icons.calendarMultiselect,
    title: i18n.t("meal-plan.meal-planner"),
    to: "/household/mealplan/planner/view",
    restricted: true,
  },
  {
    icon: $globals.icons.formatListCheck,
    title: i18n.t("shopping-list.shopping-lists"),
    to: "/shopping-lists",
    restricted: true,
  },
  {
    icon: $globals.icons.fileSign,
    title: i18n.t("article.articles"),
    to: "/articles",
    restricted: true,
  },
  {
    icon: $globals.icons.timelineText,
    title: i18n.t("recipe.timeline"),
    to: `/g/${groupSlug.value}/recipes/timeline`,
    restricted: true,
  },
  {
    icon: $globals.icons.book,
    to: `/g/${groupSlug.value}/cookbooks`,
    title: i18n.t("cookbook.cookbooks"),
    restricted: true,
  },
  uploadBookActionLink(),
  {
    icon: $globals.icons.organizers,
    title: i18n.t("general.organizers"),
    restricted: true,
    children: [
      {
        icon: $globals.icons.categories,
        to: `/g/${groupSlug.value}/recipes/categories`,
        title: i18n.t("sidebar.categories"),
        restricted: true,
      },
      {
        icon: $globals.icons.tags,
        to: `/g/${groupSlug.value}/recipes/tags`,
        title: i18n.t("sidebar.tags"),
        restricted: true,
      },
      {
        icon: $globals.icons.potSteam,
        to: `/g/${groupSlug.value}/recipes/tools`,
        title: i18n.t("tool.tools"),
        restricted: true,
      },
    ],
  },
]);
</script>

<style scoped>
.quick-create-shortcut-btn {
  min-width: 170px;
  justify-content: flex-start;
  transition:
    background-color 0.2s ease,
    box-shadow 0.2s ease,
    opacity 0.2s ease;
}

.quick-create-shortcut-btn:hover {
  background-color: rgba(var(--v-theme-primary), 0.08);
  box-shadow: none;
}

.quick-create-shortcut-btn :deep(.v-btn__content) {
  color: rgba(var(--v-theme-on-surface), var(--v-high-emphasis-opacity));
  justify-content: flex-start;
  width: 100%;
}

.quick-create-shortcut-btn :deep(.v-btn__prepend) {
  margin-inline-start: 0;
}

.background-job-inline-count {
  align-items: center;
  background-color: rgb(var(--v-theme-primary));
  border-radius: 999px;
  color: rgb(var(--v-theme-on-primary));
  display: inline-flex;
  font-size: 0.72rem;
  font-weight: 700;
  height: 18px;
  justify-content: center;
  line-height: 1;
  margin-inline-end: 6px;
  min-width: 18px;
  padding: 0 5px;
}
</style>
