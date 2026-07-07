<template>
  <div v-if="visibleAssets.length > 0 || (edit && !hideMediaAssets)">
    <v-card class="mt-4">
      <v-list-item class="pr-2 pl-0">
        <v-card-title>
          {{ $t("asset.assets") }}
        </v-card-title>
        <template #append>
          <div v-if="edit" class="d-flex align-center ga-1">
            <AppButtonUpload
              v-if="showVideoUpload"
              :post="false"
              :text="$t('recipe.upload-video')"
              :icon="$globals.icons.play"
              accept="video/mp4,video/webm,video/quicktime,video/x-m4v,video/ogg,.mp4,.webm,.mov,.m4v,.ogv"
              @uploaded="addVideoAsset"
            />
            <v-btn
              variant="plain"
              :icon="$globals.icons.create"
              @click="state.newAssetDialog = true"
            />
          </div>
        </template>
      </v-list-item>
      <v-divider class="mx-2" />
      <v-list
        v-if="visibleAssets.length > 0"
        lines="two"
        :flat="!edit"
      >
        <template
          v-for="(item, i) in visibleAssets"
          :key="`${item.fileName ?? item.name}-${i}`"
        >
          <v-list-item
            :href="!edit && !isVideo(item.fileName) ? assetURL(item.fileName ?? '') : undefined"
            target="_blank"
            class="pr-2"
          >
            <template #prepend>
              <v-avatar size="48" rounded="lg" class="elevation-1">
                <v-img
                  v-if="isImage(item.fileName)"
                  :src="assetURL(item.fileName ?? '')"
                  :alt="item.name"
                  loading="lazy"
                  cover
                />
                <v-icon v-else-if="isVideo(item.fileName)" size="large">
                  {{ $globals.icons.play }}
                </v-icon>
                <v-icon v-else size="large">
                  {{ getIconDefinition(item.icon).icon }}
                </v-icon>
              </v-avatar>
            </template>

            <v-list-item-title>
              {{ item.name }}
            </v-list-item-title>
            <template #append>
              <v-menu v-if="edit" location="bottom end">
                <template #activator="{ props: menuProps }">
                  <v-btn
                    v-bind="menuProps"
                    icon
                    variant="plain"
                  >
                    <v-icon :icon="$globals.icons.dotsVertical" />
                  </v-btn>
                </template>
                <v-list density="compact" min-width="220">
                  <v-list-item
                    :href="assetURL(item.fileName ?? '')"
                    :prepend-icon="$globals.icons.eye"
                    :title="$t('general.view')"
                    target="_blank"
                  />
                  <v-list-item
                    :href="assetURL(item.fileName ?? '')"
                    :prepend-icon="$globals.icons.download"
                    :title="$t('general.download')"
                    download
                  />
                  <v-list-item
                    v-if="edit"
                    :prepend-icon="$globals.icons.contentCopy"
                    :title="$t('general.copy')"
                    @click="copyText(assetEmbed(item.fileName ?? ''))"
                  />
                  <v-list-item
                    v-if="edit"
                    :prepend-icon="$globals.icons.delete"
                    :title="$t('general.delete')"
                    @click="removeAsset(item)"
                  />
                </v-list>
              </v-menu>
              <v-btn
                v-if="!edit"
                icon
                variant="plain"
                :href="assetURL(item.fileName ?? '')"
                download
              >
                <v-icon> {{ $globals.icons.download }} </v-icon>
              </v-btn>
            </template>
          </v-list-item>
          <div
            v-if="showVideoPlayers && isVideo(item.fileName)"
            class="recipe-asset-video-wrap px-4 pb-4"
          >
            <div class="d-flex align-center ga-2 mb-2">
              <v-btn
                icon
                size="small"
                variant="text"
                :disabled="videoSize(item.fileName) <= 45"
                @click="setVideoSize(item.fileName, videoSize(item.fileName) - 10)"
              >
                <v-icon :icon="$globals.icons.minus" />
              </v-btn>
              <v-slider
                :model-value="videoSize(item.fileName)"
                :aria-label="$t('asset.video-size')"
                min="45"
                max="100"
                step="5"
                density="compact"
                hide-details
                @update:model-value="value => setVideoSize(item.fileName, Number(value))"
              />
              <v-btn
                icon
                size="small"
                variant="text"
                :disabled="videoSize(item.fileName) >= 100"
                @click="setVideoSize(item.fileName, videoSize(item.fileName) + 10)"
              >
                <v-icon :icon="$globals.icons.createAlt" />
              </v-btn>
            </div>
            <div
              class="recipe-asset-video-frame"
              :style="{ width: `${videoSize(item.fileName)}%` }"
            >
              <video
                class="recipe-asset-video"
                controls
                playsinline
                preload="metadata"
              >
                <source
                  :src="assetURL(item.fileName ?? '')"
                  :type="videoMimeType(item.fileName)"
                >
              </video>
            </div>
          </div>
        </template>
      </v-list>
    </v-card>
    <div class="d-flex ml-auto mt-2">
      <v-spacer />
      <BaseDialog
        v-model="state.newAssetDialog"
        :title="$t('asset.new-asset')"
        :icon="getIconDefinition(state.newAsset.icon).icon"
        can-submit
        @submit="addAsset"
      >
        <v-card-text class="pt-4">
          <v-text-field
            v-model="state.newAsset.name"
            :label="$t('general.name')"
          />
          <div class="d-flex justify-space-between">
            <v-select
              v-model="state.newAsset.icon"
              density="compact"
              :prepend-icon="getIconDefinition(state.newAsset.icon).icon"
              :items="iconOptions"
              item-title="title"
              item-value="name"
              class="mr-2"
            >
              <template #item="{ props: itemProps, item }">
                <v-list-item v-bind="itemProps">
                  <template #prepend>
                    <v-avatar>
                      <v-icon>
                        {{ item.raw.icon }}
                      </v-icon>
                    </v-avatar>
                  </template>
                </v-list-item>
              </template>
            </v-select>
            <AppButtonUpload
              :post="false"
              file-name="file"
              :text-btn="false"
              @uploaded="setFileObject"
            />
          </div>
        </v-card-text>
      </BaseDialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useLocalStorage } from "@vueuse/core";
import { useStaticRoutes, useUserApi } from "~/composables/api";
import { alert } from "~/composables/use-toast";
import type { RecipeAsset } from "~/lib/api/types/recipe";
import { useCopy } from "~/composables/use-copy";

const props = defineProps({
  slug: {
    type: String,
    required: true,
  },
  recipeId: {
    type: String,
    required: true,
  },
  edit: {
    type: Boolean,
    default: true,
  },
  showVideoPlayers: {
    type: Boolean,
    default: true,
  },
  showVideoUpload: {
    type: Boolean,
    default: true,
  },
  hideMediaAssets: {
    type: Boolean,
    default: false,
  },
});

const model = defineModel<RecipeAsset[]>({ required: true });

const emit = defineEmits<{
  "asset-uploaded": [asset: RecipeAsset];
}>();

const api = useUserApi();

const state = reactive({
  newAssetDialog: false,
  fileObject: {} as File,
  newAsset: {
    name: "",
    icon: "mdi-file",
  },
});

const i18n = useI18n();
const { $globals } = useNuxtApp();
const { copyText } = useCopy();
const videoSizes = useLocalStorage<Record<string, number>>("recipe-asset-video-sizes", {});

const visibleAssets = computed(() => {
  if (!props.hideMediaAssets) {
    return model.value;
  }

  return model.value.filter(item => !isMediaAsset(item));
});

const iconOptions = [
  {
    name: "mdi-file",
    title: i18n.t("asset.file"),
    icon: $globals.icons.file,
  },
  {
    name: "mdi-file-pdf-box",
    title: i18n.t("asset.pdf"),
    icon: $globals.icons.filePDF,
  },
  {
    name: "mdi-file-image",
    title: i18n.t("asset.image"),
    icon: $globals.icons.fileImage,
  },
  {
    name: "mdi-play",
    title: i18n.t("asset.video"),
    icon: $globals.icons.play,
  },
  {
    name: "mdi-code-json",
    title: i18n.t("asset.code"),
    icon: $globals.icons.codeJson,
  },
  {
    name: "mdi-silverware-fork-knife",
    title: i18n.t("asset.recipe"),
    icon: $globals.icons.primary,
  },
];

const serverBase = useRequestURL().origin;

function getIconDefinition(icon: string) {
  return iconOptions.find(item => item.name === icon) || iconOptions[0];
}

function isImage(fileName?: string | null) {
  if (!fileName) return false;
  return /\.(png|jpe?g|gif|webp|bmp|avif)$/i.test(fileName);
}

function isVideo(fileName?: string | null) {
  if (!fileName) return false;
  return /\.(mp4|webm|mov|m4v|ogv)$/i.test(fileName);
}

function isMediaAsset(asset: RecipeAsset) {
  return (
    isImage(asset.fileName)
    || isVideo(asset.fileName)
    || asset.icon === "mdi-file-image"
    || asset.icon === "mdi-play"
  );
}

function videoMimeType(fileName?: string | null) {
  const extension = fileName?.split(".").pop()?.toLowerCase();
  if (extension === "webm") return "video/webm";
  if (extension === "mov") return "video/quicktime";
  if (extension === "ogv") return "video/ogg";
  return "video/mp4";
}

function videoSizeKey(fileName?: string | null) {
  return `${props.recipeId}:${fileName ?? "video"}`;
}

function videoSize(fileName?: string | null) {
  return videoSizes.value[videoSizeKey(fileName)] ?? 100;
}

function setVideoSize(fileName: string | null | undefined, value: number) {
  const size = Math.min(100, Math.max(45, value));
  videoSizes.value = {
    ...videoSizes.value,
    [videoSizeKey(fileName)]: size,
  };
}

function removeAsset(asset: RecipeAsset) {
  if (isVideo(asset.fileName)) {
    const key = videoSizeKey(asset.fileName);
    videoSizes.value = Object.fromEntries(
      Object.entries(videoSizes.value).filter(([storedKey]) => storedKey !== key),
    );
  }

  model.value = model.value.filter(item => item !== asset);
}

const { recipeAssetPath } = useStaticRoutes();
function assetURL(assetName: string) {
  return recipeAssetPath(props.recipeId, assetName);
}

function assetEmbed(name: string) {
  return `<img src="${serverBase}${assetURL(name)}" height="100%" width="100%" />`;
}

function fileBaseName(fileName: string) {
  const lastDot = fileName.lastIndexOf(".");
  return lastDot > 0 ? fileName.substring(0, lastDot) : fileName;
}

function setFileObject(fileObject: File) {
  state.fileObject = fileObject;
  // If the user didn't provide a name, default to the file base name
  if (!state.newAsset.name?.trim()) {
    state.newAsset.name = fileObject.name.substring(0, fileObject.name.lastIndexOf("."));
  }
  if (fileObject.type.startsWith("video/") || isVideo(fileObject.name)) {
    state.newAsset.icon = "mdi-play";
  }
  else if (fileObject.type.startsWith("image/") || isImage(fileObject.name)) {
    state.newAsset.icon = "mdi-file-image";
  }
}

function validFields() {
  // Only require a file; name will fall back to the file name if empty
  return Boolean(state.fileObject?.name);
}

async function addAsset() {
  if (!validFields()) {
    alert.error(i18n.t("asset.error-submitting-form") as string);
    return;
  }

  const nameToUse = state.newAsset.name?.trim() || state.fileObject.name;

  const { data } = await api.recipes.createAsset(props.slug, {
    name: nameToUse,
    icon: state.newAsset.icon,
    file: state.fileObject,
    extension: state.fileObject.name.split(".").pop() || "",
  });
  if (data) {
    model.value = [...model.value, data];
    emit("asset-uploaded", data);
  }
  state.newAsset = { name: "", icon: "mdi-file" };
  state.fileObject = {} as File;
}

async function addVideoAsset(file: File | File[] | unknown | null) {
  if (!(file instanceof File)) {
    return;
  }

  const { data, error } = await api.recipes.createAsset(props.slug, {
    name: fileBaseName(file.name),
    icon: "mdi-play",
    file,
    extension: file.name.split(".").pop() || "",
  });

  if (error || !data) {
    alert.error(i18n.t("asset.error-submitting-form") as string);
    return;
  }

  model.value = [...model.value, data];
  emit("asset-uploaded", data);
}
</script>

<style scoped>
.recipe-asset-video-wrap {
  max-width: 100%;
}

.recipe-asset-video-frame {
  aspect-ratio: 16 / 9;
  max-width: 100%;
  min-width: min(260px, 100%);
  min-height: 180px;
  max-height: 80vh;
  overflow: auto;
  resize: both;
}

.recipe-asset-video {
  width: 100%;
  height: 100%;
  min-height: 180px;
  display: block;
  border-radius: 8px;
  background: #000;
  object-fit: contain;
}
</style>
