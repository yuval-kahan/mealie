<template>
  <v-card
    v-if="mediaItems.length > 0 || edit"
    flat
    class="recipe-media-assets px-4 px-md-6 pb-4"
  >
    <div
      v-if="edit"
      class="d-flex align-center justify-end flex-wrap ga-2 mb-3"
    >
      <AppButtonUpload
        :post="false"
        :text="$t('recipe.upload-image')"
        :icon="$globals.icons.fileImage"
        accept="image/*,.jpg,.jpeg,.png,.gif,.webp,.bmp,.avif"
        @uploaded="file => addMediaAsset(file, 'image')"
      />
      <RecipeVideoAssetUpload
        v-model="newVideoFile"
        @update:model-value="file => addMediaAsset(file, 'video')"
      />
    </div>

    <div
      v-if="mediaItems.length > 0"
      class="recipe-media-size-control d-flex align-center ga-2 mb-2"
    >
      <v-btn
        icon
        size="small"
        variant="text"
        :disabled="mediaSize <= 25"
        @click="setMediaSize(mediaSize - 5)"
      >
        <v-icon :icon="$globals.icons.minus" />
      </v-btn>
      <v-slider
        :model-value="mediaSize"
        :aria-label="$t('asset.video-size')"
        min="25"
        max="100"
        step="5"
        density="compact"
        hide-details
        @update:model-value="value => setMediaSize(Number(value))"
      />
      <v-btn
        icon
        size="small"
        variant="text"
        :disabled="mediaSize >= 100"
        @click="setMediaSize(mediaSize + 5)"
      >
        <v-icon :icon="$globals.icons.createAlt" />
      </v-btn>
    </div>

    <div
      v-if="mediaItems.length > 0"
      class="recipe-media-row"
    >
      <div
        v-for="item in mediaItems"
        :key="item.key"
        class="recipe-media-item"
        :class="{ 'recipe-media-video-item': item.type === 'video' }"
        :style="{ flexBasis: `${mediaSize}%`, maxWidth: `${mediaSize}%` }"
      >
        <template v-if="item.type === 'video'">
          <div class="recipe-media-video-frame">
            <video
              class="recipe-media-video"
              :src="item.src"
              controls
              playsinline
              preload="metadata"
            />
          </div>
        </template>

        <v-img
          v-else
          :src="item.src"
          :alt="item.name"
          class="recipe-media-image"
          cover
          @error="hidePrimaryImage(item)"
        />

        <div class="recipe-media-caption d-flex align-center justify-space-between ga-2">
          <span class="text-truncate">{{ item.name }}</span>
          <v-btn
            v-if="edit && item.asset"
            icon
            size="small"
            variant="text"
            @click="removeAsset(item.asset)"
          >
            <v-icon :icon="$globals.icons.delete" />
          </v-btn>
        </div>
      </div>
    </div>
  </v-card>
</template>

<script setup lang="ts">
import { useLocalStorage } from "@vueuse/core";
import { useStaticRoutes, useUserApi } from "~/composables/api";
import { usePageState } from "~/composables/recipe-page/shared-state";
import { alert } from "~/composables/use-toast";
import type { NoUndefinedField } from "~/lib/api/types/non-generated";
import type { Recipe, RecipeAsset } from "~/lib/api/types/recipe";

type MediaType = "image" | "video";

type MediaItem = {
  key: string;
  type: MediaType;
  name: string;
  src: string;
  asset?: RecipeAsset;
};

const props = defineProps<{
  recipe: NoUndefinedField<Recipe>;
  edit?: boolean;
}>();

const model = defineModel<RecipeAsset[] | null>({ required: true });

const emit = defineEmits<{
  "asset-uploaded": [asset: RecipeAsset];
}>();

const api = useUserApi();
const i18n = useI18n();
const { $globals } = useNuxtApp();
const { recipeAssetPath, recipeImage } = useStaticRoutes();
const { imageKey } = usePageState(props.recipe.slug);
const mediaSize = useLocalStorage("recipe-top-media-size-v1", 25);
const hideRecipeImage = ref(false);
const newVideoFile = ref<File | null>(null);

const assets = computed(() => model.value ?? []);

const primaryImageUrl = computed(() => recipeImage(props.recipe.id, props.recipe.image, imageKey.value));

const mediaItems = computed<MediaItem[]>(() => {
  const items: MediaItem[] = [];

  if (!hideRecipeImage.value && props.recipe.image) {
    items.push({
      key: "recipe-image",
      type: "image",
      name: props.recipe.name || i18n.t("recipe.recipe-image"),
      src: primaryImageUrl.value,
    });
  }

  assets.value.forEach((asset, index) => {
    if (!asset.fileName) {
      return;
    }

    if (isVideo(asset)) {
      items.push({
        key: `video-${asset.fileName}-${index}`,
        type: "video",
        name: asset.name,
        src: assetURL(asset.fileName),
        asset,
      });
      return;
    }

    if (isImage(asset)) {
      items.push({
        key: `image-${asset.fileName}-${index}`,
        type: "image",
        name: asset.name,
        src: assetURL(asset.fileName),
        asset,
      });
    }
  });

  return items;
});

watch(primaryImageUrl, () => {
  hideRecipeImage.value = false;
});

function assetURL(assetName: string) {
  return recipeAssetPath(props.recipe.id, assetName);
}

function fileBaseName(fileName: string) {
  const lastDot = fileName.lastIndexOf(".");
  return lastDot > 0 ? fileName.substring(0, lastDot) : fileName;
}

function isImageFile(fileName?: string | null) {
  if (!fileName) return false;
  return /\.(png|jpe?g|gif|webp|bmp|avif)$/i.test(fileName);
}

function isVideoFile(fileName?: string | null) {
  if (!fileName) return false;
  return /\.(mp4|webm|mov|m4v|ogv)$/i.test(fileName);
}

function isImage(asset: RecipeAsset) {
  return isImageFile(asset.fileName) || asset.icon === "mdi-file-image";
}

function isVideo(asset: RecipeAsset) {
  return isVideoFile(asset.fileName) || asset.icon === "mdi-play";
}

function setMediaSize(value: number) {
  mediaSize.value = Math.min(100, Math.max(25, value));
}

function removeAsset(asset: RecipeAsset) {
  model.value = assets.value.filter(item => item !== asset);
}

function hidePrimaryImage(item: MediaItem) {
  if (item.key === "recipe-image") {
    hideRecipeImage.value = true;
  }
}

function normalizeUpload(file: File | File[] | unknown | null) {
  return file instanceof File ? file : null;
}

async function addMediaAsset(fileInput: File | File[] | unknown | null, type: MediaType) {
  const file = normalizeUpload(fileInput);
  if (!file) {
    return;
  }

  const { data, error } = await api.recipes.createAsset(props.recipe.slug, {
    name: fileBaseName(file.name),
    icon: type === "video" ? "mdi-play" : "mdi-file-image",
    file,
    extension: file.name.split(".").pop() || "",
  });

  if (error || !data) {
    alert.error(i18n.t("asset.error-submitting-form") as string);
    return;
  }

  model.value = [...assets.value, data];
  newVideoFile.value = null;
  emit("asset-uploaded", data);
}
</script>

<style scoped>
.recipe-media-assets {
  width: 100%;
}

.recipe-media-size-control {
  max-width: 100%;
}

.recipe-media-row {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: flex-start;
  gap: 4px;
}

.recipe-media-item {
  min-width: min(220px, 100%);
  min-height: 0;
}

.recipe-media-image {
  width: 100%;
  height: clamp(220px, 34vw, 420px);
  border-radius: 8px;
  background: rgb(var(--v-theme-surface-variant));
}

.recipe-media-video-frame {
  aspect-ratio: 16 / 9;
  width: 100%;
  min-height: 160px;
  max-height: 82vh;
  overflow: auto;
  resize: both;
}

.recipe-media-video {
  width: 100%;
  height: 100%;
  min-height: 160px;
  display: block;
  border-radius: 8px;
  background: #000;
  object-fit: contain;
}

.recipe-media-caption {
  min-height: 40px;
  padding: 6px 2px 0;
}
</style>
