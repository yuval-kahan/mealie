<template>
  <!-- Wrap v-hover with a div to provide a proper DOM element for the transition -->
  <div>
    <RecipeShoppingListQuickDialog
      v-model="shoppingListQuickDialog"
      :recipe-slug="slug"
      @resolved="handleShoppingListResolved"
      @failed="shoppingListOverlayLoading = false"
    />
    <RecipeAICookbooksDialog
      v-model="aiCookbooksDialog"
      :recipe-slug="slug"
    />
    <RecipeQuickEditDialog
      v-model="quickEditDialog"
      :recipe-slug="slug"
      @saved="handleQuickEditSaved"
    />
    <v-hover v-slot="{ isHovering, props: hoverProps }" :open-delay="50">
      <v-card
        v-bind="hoverProps"
        class="recipe-card"
        :class="{ 'on-hover': isHovering }"
        :style="{ cursor }"
        :elevation="isHovering ? 12 : 2"
        :to="recipeRoute"
        :min-height="imageHeight + 75"
        @click.self="$emit('click')"
      >
        <RecipeCardImage
          small
          :icon-size="imageHeight"
          :height="imageHeight"
          :slug="slug"
          :recipe-id="recipeId"
          :image-version="localImageVersion"
          @image-status="handleImageStatus"
        >
          <v-chip
            v-if="localLastMade"
            class="recipe-card-done-badge"
            color="success"
            variant="flat"
            size="small"
          >
            <v-icon start size="small">
              {{ $globals.icons.checkBold }}
            </v-icon>
            DONE
          </v-chip>
          <v-expand-transition v-if="description">
            <div
              v-if="isHovering"
              class="d-flex transition-fast-in-fast-out bg-secondary v-card--reveal"
              style="height: 100%"
            >
              <v-card-text class="v-card--text-show white--text">
                <div class="descriptionWrapper">
                  <SafeMarkdown :source="description" />
                </div>
              </v-card-text>
            </div>
          </v-expand-transition>
        </RecipeCardImage>
        <v-btn
          v-if="showAiImageButton"
          icon
          variant="flat"
          size="x-small"
          class="recipe-card-ai-image-btn"
          color="primary"
          :loading="aiImageLoading"
          :title="$t('recipe.add-ai-image')"
          :aria-label="$t('recipe.add-ai-image')"
          @click.stop.prevent="createAIImageFromCard"
        >
          <v-icon>{{ $globals.icons.fileImage }}</v-icon>
        </v-btn>
        <v-btn
          v-if="showAiItemImagesButton"
          icon
          variant="flat"
          size="x-small"
          class="recipe-card-ai-item-images-btn"
          color="success"
          :loading="itemImagesLoading"
          :title="$t('recipe.create-item-images')"
          :aria-label="$t('recipe.create-item-images')"
          @click.stop.prevent="ensureItemImagesFromCard"
        >
          <v-icon>{{ $globals.icons.fileImage }}</v-icon>
        </v-btn>
        <v-btn
          v-if="showCreateShoppingListOverlay"
          icon
          variant="flat"
          size="x-small"
          class="recipe-card-ai-shopping-list-btn"
          color="success"
          :loading="shoppingListOverlayLoading"
          :title="$t('recipe.create-ai-shopping-list')"
          :aria-label="$t('recipe.create-ai-shopping-list')"
          @click.stop.prevent="createShoppingListFromCardImage"
        >
          <v-icon>{{ $globals.icons.cartCheck }}</v-icon>
        </v-btn>
        <v-card-title class="recipe-card-title px-4">
          {{ displayName }}
        </v-card-title>
        <div class="recipe-card-tags px-4">
          <v-chip
            v-if="hasAllGroceries"
            size="x-small"
            color="success"
            variant="tonal"
            class="recipe-card-ready-chip"
            :title="$t('recipe.all-ingredients-available')"
          >
            <v-icon start size="x-small">
              {{ $globals.icons.cartCheck }}
            </v-icon>
            {{ $t("recipe.all-ingredients-available-short") }}
          </v-chip>
          <RecipeChips
            :truncate="true"
            :items="categories"
            :title="false"
            small
            color="primary"
            url-prefix="categories"
            v-bind="$attrs"
          />
          <RecipeChips
            :truncate="true"
            :items="tags"
            :title="false"
            small
            url-prefix="tags"
            v-bind="$attrs"
          />
        </div>

        <slot name="actions">
          <v-card-actions v-if="showRecipeContent" class="recipe-card-actions px-1">
            <RecipeFavoriteBadge v-if="isOwnGroup" :recipe-id="recipeId" show-always />
            <div v-else class="px-1" />
            <!-- Empty div to keep the layout consistent -->

            <RecipeCardRating :model-value="rating" :recipe-id="recipeId" />
            <v-spacer />

            <div v-if="isOwnGroup" class="recipe-card-quick-actions">
              <v-btn
                icon
                variant="text"
                size="x-small"
                class="recipe-card-action-btn"
                color="primary"
                :title="$t('recipe.quick-edit')"
                :aria-label="$t('recipe.quick-edit')"
                @click.stop.prevent="quickEditDialog = true"
              >
                <v-icon>{{ $globals.icons.manageData }}</v-icon>
              </v-btn>
              <v-btn
                icon
                variant="text"
                size="x-small"
                class="recipe-card-action-btn"
                color="primary"
                :loading="copyLoading"
                :title="$t('recipe.copy-recipe')"
                :aria-label="$t('recipe.copy-recipe')"
                @click.stop.prevent="copyRecipeFromCard"
              >
                <v-icon>{{ $globals.icons.contentCopy }}</v-icon>
              </v-btn>
              <v-btn
                icon
                variant="text"
                size="x-small"
                class="recipe-card-action-btn"
                color="primary"
                :loading="copyShoppingListLoading"
                :title="$t('recipe.copy-shopping-list')"
                :aria-label="$t('recipe.copy-shopping-list')"
                @click.stop.prevent="copyShoppingListFromCard"
              >
                <v-icon>{{ $globals.icons.formatListCheck }}</v-icon>
              </v-btn>
              <v-btn
                icon
                variant="text"
                size="x-small"
                class="recipe-card-action-btn"
                color="primary"
                :title="$t('recipe.add-to-plan')"
                :aria-label="$t('recipe.add-to-plan')"
                @click.stop.prevent="openMealplannerFromCard"
              >
                <v-icon>{{ $globals.icons.calendar }}</v-icon>
              </v-btn>
              <v-btn
                icon
                variant="text"
                size="x-small"
                class="recipe-card-action-btn"
                color="primary"
                :title="$t('recipe.add-to-list')"
                :aria-label="$t('recipe.add-to-list')"
                @click.stop.prevent="openShoppingListFromCard"
              >
                <v-icon>{{ $globals.icons.cartCheck }}</v-icon>
              </v-btn>
              <v-btn
                icon
                variant="text"
                size="x-small"
                class="recipe-card-action-btn"
                color="primary"
                :title="$t('recipe.open-or-create-shopping-list')"
                :aria-label="$t('recipe.open-or-create-shopping-list')"
                @click.stop.prevent="shoppingListQuickDialog = true"
              >
                <v-icon>{{ $globals.icons.clipboardCheck }}</v-icon>
              </v-btn>
              <v-btn
                icon
                variant="text"
                size="x-small"
                class="recipe-card-action-btn"
                color="primary"
                :title="$t('cookbook.ai-generated-books')"
                :aria-label="$t('cookbook.ai-generated-books')"
                @click.stop.prevent="aiCookbooksDialog = true"
              >
                <v-icon>{{ $globals.icons.book }}</v-icon>
              </v-btn>
              <LinkedResourcesButton
                v-if="linkedResourcesCount"
                class="recipe-card-linked-resources"
                entity-type="recipe"
                :entity-id="recipeId"
                :count="linkedResourcesCount"
              />
            </div>

            <!-- If we're not logged-in, no items display, so we hide this menu -->
            <RecipeContextMenu
              v-if="isOwnGroup && showRecipeContent"
              ref="recipeContextMenu"
              color="grey-darken-2"
              :slug="slug"
              :menu-icon="$globals.icons.dotsVertical"
              :name="displayName"
              :recipe-id="recipeId"
              :rating="rating"
              :last-made="localLastMade"
              :recipe-section="recipeSection"
              :redirect-on-delete="false"
              :use-items="{
                edit: false,
                rename: true,
                copy: false,
                rating: true,
                download: true,
                mealplanner: true,
                shoppingList: true,
                aiShoppingList: true,
                aiImage: true,
                imageUpload: true,
                aiEdit: true,
                print: false,
                printPreferences: false,
                share: true,
                shoppingWebsites: true,
                delete: true,
                section: true,
                markDone: true,
              }"
              @deleted="$emit('delete', slug)"
              @image-updated="handleImageUpdated"
              @renamed="handleRenamed"
              @made="handleMade"
              @section-updated="handleSectionUpdated"
            />
          </v-card-actions>
        </slot>
        <slot />
      </v-card>
    </v-hover>
  </div>
</template>

<script setup lang="ts">
import RecipeFavoriteBadge from "./RecipeFavoriteBadge.vue";
import RecipeChips from "./RecipeChips.vue";
import RecipeContextMenu from "./RecipeContextMenu/RecipeContextMenu.vue";
import RecipeCardImage from "./RecipeCardImage.vue";
import RecipeCardRating from "./RecipeCardRating.vue";
import RecipeShoppingListQuickDialog from "./RecipeShoppingListQuickDialog.vue";
import RecipeAICookbooksDialog from "./RecipeAICookbooksDialog.vue";
import RecipeQuickEditDialog from "./RecipeQuickEditDialog.vue";
import LinkedResourcesButton from "~/components/Domain/LinkedResources/LinkedResourcesButton.vue";
import { useUserApi } from "~/composables/api/api-client";
import { useRecipeCopy } from "~/composables/recipes/use-recipe-copy";
import { recipeItemImagesEnsured, useRecipeItemImages } from "~/composables/recipes/use-recipe-item-images";
import { useRecipeShoppingListCopy } from "~/composables/recipes/use-recipe-shopping-list-copy";
import { useLoggedInState } from "~/composables/use-logged-in-state";
import { useShoppingListAvailability } from "~/composables/shopping-list-page/use-shopping-list-availability";
import { alert } from "~/composables/use-toast";

interface Props {
  name: string;
  slug: string;
  description?: string | null;
  rating?: number;
  ratingColor?: string;
  image?: string;
  tags?: Array<any>;
  categories?: Array<any>;
  recipeId: string;
  imageHeight?: number;
  extras?: Record<string, unknown> | null;
  lastMade?: string | null;
  recipeSection?: string;
}
const props = withDefaults(defineProps<Props>(), {
  description: null,
  rating: 0,
  ratingColor: "secondary",
  image: "abc123",
  tags: () => [],
  categories: () => [],
  imageHeight: 200,
  extras: null,
  lastMade: null,
  recipeSection: "recipes",
});

const emit = defineEmits<{
  click: [];
  delete: [slug: string];
  renamed: [{ slug: string; name: string; recipe?: any }];
  sectionUpdated: [{ slug: string; recipeSection: string }];
}>();

const api = useUserApi();
const { copyRecipeText } = useRecipeCopy();
const { copyRecipeShoppingList } = useRecipeShoppingListCopy();
const { ensureRecipeItemImages } = useRecipeItemImages();
const i18n = useI18n();
const { isOwnGroup, groupSlug } = useLoggedInState();
const { ensureAvailability, hasAllGroceriesForRecipe } = useShoppingListAvailability();
const displayName = ref(props.name);
const copyLoading = ref(false);
const copyShoppingListLoading = ref(false);
const aiImageLoading = ref(false);
const itemImagesLoading = ref(false);
const itemImagesEnsured = ref(recipeItemImagesEnsured(props.extras));
const shoppingListStatusKnown = ref(hasShoppingListStatus(props.extras));
const hasLinkedShoppingList = ref(Boolean(props.extras?.shoppingListLinked));
const imageLoadFailed = ref(false);
const localImageVersion = ref<string | null>(props.image ?? null);
const localLastMade = ref<string | null>(props.lastMade ?? null);
const shoppingListQuickDialog = ref(false);
const shoppingListOverlayLoading = ref(false);
const aiCookbooksDialog = ref(false);
const quickEditDialog = ref(false);
const linkedResourcesCount = computed(() => Number(props.extras?.linkedResourcesCount || 0));
const recipeContextMenu = ref<{
  openMealplannerDialog: () => Promise<void>;
  openShoppingListDialog: () => Promise<void>;
} | null>(null);

watch(
  () => props.name,
  (name) => {
    displayName.value = name;
  },
);

watch(
  () => props.image,
  (image) => {
    localImageVersion.value = image ?? null;
    imageLoadFailed.value = false;
  },
);

watch(
  () => props.lastMade,
  value => localLastMade.value = value ?? null,
);

watch(
  () => props.extras,
  (extras) => {
    itemImagesEnsured.value = recipeItemImagesEnsured(extras);
    shoppingListStatusKnown.value = hasShoppingListStatus(extras);
    if (shoppingListStatusKnown.value) {
      hasLinkedShoppingList.value = Boolean(extras?.shoppingListLinked);
    }
  },
);

watch(shoppingListQuickDialog, (open) => {
  if (!open) {
    shoppingListOverlayLoading.value = false;
  }
});

const showRecipeContent = computed(() => props.recipeId && props.slug);
const recipeRoute = computed<string>(() => {
  return showRecipeContent.value ? `/g/${groupSlug.value}/r/${props.slug}` : "";
});
const cursor = computed(() => (showRecipeContent.value ? "pointer" : "auto"));
const hasAllGroceries = computed(() => hasAllGroceriesForRecipe(displayName.value));
const showAiImageButton = computed(() => isOwnGroup.value && showRecipeContent.value && (!localImageVersion.value || imageLoadFailed.value));
const showAiItemImagesButton = computed(() => isOwnGroup.value && showRecipeContent.value && !itemImagesEnsured.value);
const showCreateShoppingListOverlay = computed(() => {
  return isOwnGroup.value
    && showRecipeContent.value
    && shoppingListStatusKnown.value
    && !hasLinkedShoppingList.value;
});

onMounted(() => {
  void ensureAvailability();
});

function handleRenamed(payload: { slug: string; name: string; recipe?: any }) {
  displayName.value = payload.name;
  emit("renamed", payload);
}

function handleQuickEditSaved(payload: { slug: string; name: string; recipe: any }) {
  displayName.value = payload.name;
  emit("renamed", payload);
}

function handleImageStatus(hasImage: boolean) {
  imageLoadFailed.value = !hasImage;
}

function handleImageUpdated(payload: { slug: string; image: string }) {
  localImageVersion.value = payload.image;
  imageLoadFailed.value = false;
}

function handleMade(payload: { slug: string; lastMade: string }) {
  localLastMade.value = payload.lastMade;
}

function handleSectionUpdated(payload: { slug: string; recipeSection: string }) {
  emit("sectionUpdated", payload);
}

function hasShoppingListStatus(extras: Record<string, unknown> | null | undefined) {
  return Boolean(extras && Object.prototype.hasOwnProperty.call(extras, "shoppingListLinked"));
}

function createShoppingListFromCardImage() {
  if (shoppingListOverlayLoading.value) {
    return;
  }
  shoppingListOverlayLoading.value = true;
  shoppingListQuickDialog.value = true;
}

function handleShoppingListResolved() {
  shoppingListStatusKnown.value = true;
  hasLinkedShoppingList.value = true;
  shoppingListOverlayLoading.value = false;
}

async function createAIImageFromCard() {
  if (aiImageLoading.value || !showRecipeContent.value) {
    return;
  }

  aiImageLoading.value = true;
  try {
    const { data, error } = await api.recipes.createAIImage(props.slug);
    if (error || !data?.image) {
      alert.error(i18n.t("recipe.ai-image-create-failed"));
      return;
    }

    handleImageUpdated({ slug: props.slug, image: data.image });
    alert.success(i18n.t("recipe.recipe-image-updated"));
  }
  finally {
    aiImageLoading.value = false;
  }
}

async function copyRecipeFromCard() {
  if (copyLoading.value || !showRecipeContent.value) {
    return;
  }

  copyLoading.value = true;
  try {
    const { data } = await api.recipes.getOne(props.slug);
    if (!data) {
      alert.error(i18n.t("events.something-went-wrong"));
      return;
    }

    copyRecipeText(data, displayName.value);
  }
  finally {
    copyLoading.value = false;
  }
}

async function copyShoppingListFromCard() {
  if (copyShoppingListLoading.value || !showRecipeContent.value) {
    return;
  }

  copyShoppingListLoading.value = true;
  try {
    await copyRecipeShoppingList(props.slug);
  }
  finally {
    copyShoppingListLoading.value = false;
  }
}

async function ensureItemImagesFromCard() {
  if (itemImagesLoading.value || !showRecipeContent.value) {
    return;
  }

  itemImagesLoading.value = true;
  try {
    const result = await ensureRecipeItemImages(props.slug);
    if (result) {
      itemImagesEnsured.value = true;
    }
  }
  finally {
    itemImagesLoading.value = false;
  }
}

async function openMealplannerFromCard() {
  await recipeContextMenu.value?.openMealplannerDialog();
}

async function openShoppingListFromCard() {
  await recipeContextMenu.value?.openShoppingListDialog();
}
</script>

<style>
.v-card--reveal {
  align-items: center;
  bottom: 0;
  justify-content: center;
  opacity: 0.8;
  position: absolute;
  width: 100%;
}
.v-card--text-show {
  opacity: 1 !important;
}
.headerClass {
  white-space: nowrap;
  word-break: normal;
  overflow: hidden;
  text-overflow: ellipsis;
}
.recipe-card-title {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  white-space: normal;
  word-break: break-word;
  overflow: hidden;
  line-height: 1.3;
  font-size: 1.25rem;
  height: 3.9em;
  min-height: 3.9em;
  max-height: 3.9em;
}
.recipe-card {
  position: relative;
}

.recipe-card-done-badge {
  bottom: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.28);
  font-weight: 800;
  left: 50%;
  letter-spacing: 0;
  pointer-events: none;
  position: absolute;
  transform: translateX(-50%) rotate(-2deg);
  z-index: 6;
}
.recipe-card-ai-image-btn {
  position: absolute !important;
  right: 8px;
  top: 8px;
  z-index: 4;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.22);
  transition:
    background-color 0.15s ease,
    box-shadow 0.15s ease,
    transform 0.15s ease;
}
.recipe-card-ai-image-btn:hover,
.recipe-card-ai-image-btn:focus-visible {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.28);
  transform: translateY(-1px);
}
.recipe-card-ai-item-images-btn {
  position: absolute !important;
  left: 8px;
  top: 8px;
  z-index: 4;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.22);
  transition:
    background-color 0.15s ease,
    box-shadow 0.15s ease,
    transform 0.15s ease;
}
.recipe-card-ai-item-images-btn:hover,
.recipe-card-ai-item-images-btn:focus-visible {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.28);
  transform: translateY(-1px);
}
.recipe-card-ai-shopping-list-btn {
  left: 50%;
  position: absolute !important;
  top: 8px;
  transform: translateX(-50%);
  z-index: 4;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.22);
  transition:
    background-color 0.15s ease,
    box-shadow 0.15s ease,
    transform 0.15s ease;
}
.recipe-card-ai-shopping-list-btn:hover,
.recipe-card-ai-shopping-list-btn:focus-visible {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.28);
  transform: translate(-50%, -1px);
}
.recipe-card-actions {
  align-items: center;
  flex-wrap: nowrap;
  height: 52px;
  min-height: 52px;
  gap: 0;
  overflow: visible;
}
.recipe-card-quick-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 0;
  max-width: none;
  overflow: visible;
}
.recipe-card-action-btn {
  flex: 0 0 22px;
  height: 28px !important;
  min-width: 22px !important;
  transition:
    background-color 0.15s ease,
    box-shadow 0.15s ease,
    color 0.15s ease;
  width: 22px !important;
}
.recipe-card-linked-resources {
  flex: 0 0 22px;
  width: 22px;
}
.recipe-card-linked-resources .linked-resources-button {
  height: 28px !important;
  min-width: 22px !important;
  width: 22px !important;
}
.recipe-card-actions > .v-btn,
.recipe-card-actions > div:not(.recipe-card-quick-actions) > .v-btn {
  height: 28px !important;
  min-width: 28px !important;
  width: 28px !important;
}
.recipe-card-actions .rating-display .star {
  font-size: 14px !important;
}
.recipe-card-action-btn:hover,
.recipe-card-action-btn:focus-visible {
  background-color: rgba(var(--v-theme-primary), 0.14) !important;
  box-shadow: inset 0 0 0 1px rgba(var(--v-theme-primary), 0.28);
  color: rgb(var(--v-theme-primary)) !important;
}
.recipe-card-tags {
  align-items: center;
  display: flex;
  flex-wrap: nowrap;
  height: 32px;
  min-height: 32px;
  overflow: hidden;
}
.recipe-card-tags > div {
  display: flex;
  flex-wrap: nowrap;
  min-width: 0;
  overflow: hidden;
}
.recipe-card-tags .v-chip {
  flex: 0 0 auto;
  margin-top: 0 !important;
}
.recipe-card-ready-chip {
  font-weight: 700;
  margin-inline-end: 4px;
}
.descriptionWrapper {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 8;
  line-clamp: 8;
  overflow: hidden;
}
</style>
