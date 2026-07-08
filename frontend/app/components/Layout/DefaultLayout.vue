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
import { useCookbookPreferences, useOrganizerSidebarPreferences } from "~/composables/use-users/preferences";
import { useCookbookStore, usePublicCookbookStore } from "~/composables/store/use-cookbook-store";
import { useCategoryStore, usePublicCategoryStore } from "~/composables/store/use-category-store";
import { usePublicTagStore, useTagStore } from "~/composables/store/use-tag-store";
import type { ReadCookBook } from "~/lib/api/types/cookbook";
import type { RecipeCategory, RecipeTag } from "~/lib/api/types/recipe";
import type { UploadedBook } from "~/lib/api/types/uploaded-book";
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
const ownCookbookStore = computed(() => isOwnGroup.value ? useCookbookStore(i18n) : null);
const ownCategoryStore = computed(() => isOwnGroup.value ? useCategoryStore(i18n) : null);
const ownTagStore = computed(() => isOwnGroup.value ? useTagStore(i18n) : null);
const publicCookbookStoreCache = ref<Record<string, ReturnType<typeof usePublicCookbookStore>>>({});
const publicCategoryStoreCache = ref<Record<string, ReturnType<typeof usePublicCategoryStore>>>({});
const publicTagStoreCache = ref<Record<string, ReturnType<typeof usePublicTagStore>>>({});
const publicStoreCacheOrder = ref<string[]>([]);
const MAX_PUBLIC_STORE_CACHE_SIZE = 8;

function pruneCacheEntry<T>(cache: Ref<Record<string, T>>, slug: string) {
  cache.value = Object.fromEntries(Object.entries(cache.value).filter(([key]) => key !== slug)) as Record<string, T>;
}

function rememberPublicStoreSlug(slug: string) {
  publicStoreCacheOrder.value = publicStoreCacheOrder.value.filter(item => item !== slug);
  publicStoreCacheOrder.value.push(slug);

  while (publicStoreCacheOrder.value.length > MAX_PUBLIC_STORE_CACHE_SIZE) {
    const expiredSlug = publicStoreCacheOrder.value.shift();
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
  if (!publicCookbookStoreCache.value[slug]) {
    publicCookbookStoreCache.value[slug] = usePublicCookbookStore(slug, i18n);
  }
  return publicCookbookStoreCache.value[slug];
}

function getPublicCategoryStore(slug: string) {
  rememberPublicStoreSlug(slug);
  if (!publicCategoryStoreCache.value[slug]) {
    publicCategoryStoreCache.value[slug] = usePublicCategoryStore(slug, i18n);
  }
  return publicCategoryStoreCache.value[slug];
}

function getPublicTagStore(slug: string) {
  rememberPublicStoreSlug(slug);
  if (!publicTagStoreCache.value[slug]) {
    publicTagStoreCache.value[slug] = usePublicTagStore(slug, i18n);
  }
  return publicTagStoreCache.value[slug];
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
let uploadedBookRefreshTimer: ReturnType<typeof setInterval> | null = null;
let uploadedBookRefreshInFlight = false;
const router = useRouter();
const MANUAL_DRAFT_RECIPE_PREFIX = "__mealie_manual_draft__";
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
  syncUploadedBookRefreshTimer();
});

onBeforeUnmount(() => {
  clearUploadedBookRefreshTimer();
});

watch(
  () => [isOwnGroup.value, auth.user.value?.id],
  () => {
    refreshUploadedBooks();
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
    .map(category => organizerItemAsLink(category, "categories", $globals.icons.categories))
    .filter((link): link is SideBarLink => !!link);
});

const tagLinks = computed<SideBarLink[]>(() => {
  return sortByName(tags.value)
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
  if (uploadedBookRefreshInFlight) {
    return;
  }

  if (!isOwnGroup.value || !auth.user.value) {
    uploadedBooks.value = [];
    return;
  }

  uploadedBookRefreshInFlight = true;
  try {
    const { data } = await api.uploadedBooks.getAll();
    uploadedBooks.value = data || [];
    if (selectedUploadedBook.value) {
      selectedUploadedBook.value = uploadedBooks.value.find(book => book.id === selectedUploadedBook.value?.id) || selectedUploadedBook.value;
    }
  }
  finally {
    uploadedBookRefreshInFlight = false;
    syncUploadedBookRefreshTimer();
  }
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
</style>
