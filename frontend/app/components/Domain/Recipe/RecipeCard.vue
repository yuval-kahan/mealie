<template>
  <!-- Wrap v-hover with a div to provide a proper DOM element for the transition -->
  <div>
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
                print: false,
                printPreferences: false,
                share: true,
                delete: true,
              }"
              @deleted="$emit('delete', slug)"
              @image-updated="handleImageUpdated"
              @renamed="handleRenamed"
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
import { useUserApi } from "~/composables/api/api-client";
import { useRecipeCopy } from "~/composables/recipes/use-recipe-copy";
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
  recipeId: string;
  imageHeight?: number;
}
const props = withDefaults(defineProps<Props>(), {
  description: null,
  rating: 0,
  ratingColor: "secondary",
  image: "abc123",
  tags: () => [],
  imageHeight: 200,
});

const emit = defineEmits<{
  click: [];
  delete: [slug: string];
  renamed: [{ slug: string; name: string; recipe?: any }];
}>();

const auth = useMealieAuth();
const api = useUserApi();
const { copyRecipeText } = useRecipeCopy();
const i18n = useI18n();
const { isOwnGroup } = useLoggedInState();
const { ensureAvailability, hasAllGroceriesForRecipe } = useShoppingListAvailability();
const displayName = ref(props.name);
const copyLoading = ref(false);
const aiImageLoading = ref(false);
const imageLoadFailed = ref(false);
const localImageVersion = ref<string | null>(props.image ?? null);
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

const route = useRoute();
const groupSlug = computed(() => route.params.groupSlug || auth.user.value?.groupSlug || "");
const showRecipeContent = computed(() => props.recipeId && props.slug);
const recipeRoute = computed<string>(() => {
  return showRecipeContent.value ? `/g/${groupSlug.value}/r/${props.slug}` : "";
});
const cursor = computed(() => (showRecipeContent.value ? "pointer" : "auto"));
const hasAllGroceries = computed(() => hasAllGroceriesForRecipe(displayName.value));
const showAiImageButton = computed(() => isOwnGroup.value && showRecipeContent.value && (!localImageVersion.value || imageLoadFailed.value));

onMounted(() => {
  void ensureAvailability();
});

function handleRenamed(payload: { slug: string; name: string; recipe?: any }) {
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
.recipe-card-actions {
  align-items: center;
  flex-wrap: nowrap;
  height: 52px;
  min-height: 52px;
  overflow: hidden;
}
.recipe-card-quick-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 0;
  max-width: 96px;
  overflow: hidden;
}
.recipe-card-action-btn {
  flex: 0 0 32px;
  height: 32px !important;
  min-width: 32px !important;
  transition:
    background-color 0.15s ease,
    box-shadow 0.15s ease,
    color 0.15s ease;
  width: 32px !important;
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
