<template>
  <div :style="`height: ${height}px;`">
    <v-expand-transition>
      <v-card
        :ripple="false"
        :class="[isFlat ? 'mx-auto flat' : 'mx-auto', { 'disable-highlight': disableHighlight }]"
        :style="{ cursor }"
        hover
        height="100%"
        :to="$attrs.selected ? undefined : recipeRoute"
        @click="$emit('selected')"
      >
        <v-img v-if="vertical" class="rounded-sm" cover>
          <RecipeCardImage
            tiny
            :icon-size="100"
            :slug="slug"
            :recipe-id="recipeId"
            :image-version="image"
            :height="height"
          />
        </v-img>
        <v-list-item
          lines="three"
          class="py-0"
          :class="vertical ? 'px-2' : 'px-0'"
          item-props
          height="100%"
          density="compact"
        >
          <template #prepend>
            <slot v-if="!vertical" name="avatar">
              <RecipeCardImage
                tiny
                :icon-size="100"
                :slug="slug"
                :recipe-id="recipeId"
                :image-version="image"
                width="125"
                :height="height"
              />
            </slot>
          </template>
          <div class="pl-4 d-flex flex-column justify-space-between align-stretch pr-2">
            <v-list-item-title class="recipe-mobile-card-title mt-3 mb-1 text-top w-100">
              {{ displayName }}
            </v-list-item-title>
            <v-list-item-subtitle class="ma-0 text-top">
              <SafeMarkdown v-if="description" :source="description" />
              <p v-else>
                <br>
                <br>
                <br>
              </p>
            </v-list-item-subtitle>
            <div
              class="recipe-mobile-card-tags d-flex flex-nowrap justify-start ma-0 pt-2 pb-0"
            >
              <v-chip
                v-if="hasAllGroceries"
                size="x-small"
                color="success"
                variant="tonal"
                class="recipe-mobile-card-ready-chip"
                :title="$t('recipe.all-ingredients-available')"
              >
                <v-icon start size="x-small">
                  {{ $globals.icons.cartCheck }}
                </v-icon>
                {{ $t("recipe.all-ingredients-available-short") }}
              </v-chip>
              <RecipeChips
                class="recipe-mobile-card-tags-list"
                :truncate="true"
                :items="tags"
                :title="false"
                small
                url-prefix="tags"
                v-bind="$attrs"
              />
            </div>
          </div>
          <slot name="actions">
            <v-card-actions class="w-100 my-0 px-1 py-0">
              <RecipeFavoriteBadge
                v-if="isOwnGroup && showRecipeContent"
                :recipe-id="recipeId"
                show-always
                class="ma-0 pa-0"
              />
              <div v-else class="my-0 px-1 py-0" />
              <!-- Empty div to keep the layout consistent -->
              <RecipeCardRating
                v-if="showRecipeContent"
                :class="[{ 'pb-2': !isOwnGroup }, 'ml-n2']"
                :model-value="rating"
                :recipe-id="recipeId"
              />

              <div v-if="isOwnGroup && showRecipeContent" class="recipe-mobile-card-quick-actions ml-auto">
                <v-btn
                  icon
                  variant="text"
                  size="x-small"
                  class="recipe-mobile-card-action-btn"
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
                  class="recipe-mobile-card-action-btn"
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
                  class="recipe-mobile-card-action-btn"
                  color="primary"
                  :title="$t('recipe.add-to-list')"
                  :aria-label="$t('recipe.add-to-list')"
                  @click.stop.prevent="openShoppingListFromCard"
                >
                  <v-icon>{{ $globals.icons.cartCheck }}</v-icon>
                </v-btn>
              </div>

              <!-- If we're not logged-in, no items display, so we hide this menu -->
              <!-- We also add padding to the v-rating above to compensate -->
              <RecipeContextMenu
                v-if="isOwnGroup && showRecipeContent"
                ref="recipeContextMenu"
                :slug="slug"
                :menu-icon="$globals.icons.dotsHorizontal"
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
                  print: false,
                  printPreferences: false,
                  share: true,
                  delete: true,
                }"
                @deleted="$emit('delete', slug)"
                @renamed="handleRenamed"
              />
            </v-card-actions>
          </slot>
        </v-list-item>
        <slot />
      </v-card>
    </v-expand-transition>
  </div>
</template>

<script setup lang="ts">
import RecipeFavoriteBadge from "./RecipeFavoriteBadge.vue";
import RecipeContextMenu from "./RecipeContextMenu/RecipeContextMenu.vue";
import RecipeCardImage from "./RecipeCardImage.vue";
import RecipeCardRating from "./RecipeCardRating.vue";
import RecipeChips from "./RecipeChips.vue";
import { useUserApi } from "~/composables/api/api-client";
import { useRecipeCopy } from "~/composables/recipes/use-recipe-copy";
import { useLoggedInState } from "~/composables/use-logged-in-state";
import { useShoppingListAvailability } from "~/composables/shopping-list-page/use-shopping-list-availability";
import { alert } from "~/composables/use-toast";

interface Props {
  name: string;
  slug: string;
  description: string;
  rating?: number;
  image?: string;
  tags?: Array<any>;
  recipeId: string;
  vertical?: boolean;
  isFlat?: boolean;
  height?: number;
  disableHighlight?: boolean;
}
const props = withDefaults(defineProps<Props>(), {
  rating: 0,
  image: "abc123",
  tags: () => [],
  vertical: false,
  isFlat: false,
  height: 150,
  disableHighlight: false,
});

const emit = defineEmits<{
  selected: [];
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

const route = useRoute();
const groupSlug = computed(() => route.params.groupSlug || auth.user.value?.groupSlug || "");
const showRecipeContent = computed(() => props.recipeId && props.slug);
const recipeRoute = computed<string>(() => {
  return showRecipeContent.value ? `/g/${groupSlug.value}/r/${props.slug}` : "";
});
const cursor = computed(() => (showRecipeContent.value ? "pointer" : "auto"));
const hasAllGroceries = computed(() => hasAllGroceriesForRecipe(displayName.value));

onMounted(() => {
  void ensureAvailability();
});

function handleRenamed(payload: { slug: string; name: string; recipe?: any }) {
  displayName.value = payload.name;
  emit("renamed", payload);
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

<style scoped>
:deep(.v-list-item__prepend) {
  height: 100%;
}
.v-mobile-img {
  padding-top: 0;
  padding-bottom: 0;
  padding-left: 0;
}
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

.recipe-mobile-card-title {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  white-space: normal;
  word-break: break-word;
  overflow: hidden;
  line-height: 1.25;
  max-height: 3.75em;
}

.recipe-mobile-card-quick-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 0;
  max-width: 96px;
  overflow: hidden;
}

.recipe-mobile-card-action-btn {
  flex: 0 0 32px;
  height: 32px !important;
  min-width: 32px !important;
  transition:
    background-color 0.15s ease,
    box-shadow 0.15s ease,
    color 0.15s ease;
  width: 32px !important;
}

.recipe-mobile-card-action-btn:hover,
.recipe-mobile-card-action-btn:focus-visible {
  background-color: rgba(var(--v-theme-primary), 0.14) !important;
  box-shadow: inset 0 0 0 1px rgba(var(--v-theme-primary), 0.28);
  color: rgb(var(--v-theme-primary)) !important;
}

.recipe-mobile-card-tags {
  overflow: hidden;
  white-space: nowrap;
}

.recipe-mobile-card-tags :deep(.recipe-mobile-card-tags-list) {
  display: flex;
  flex-wrap: nowrap;
  min-width: 0;
  overflow: hidden;
}

.recipe-mobile-card-tags :deep(.v-chip) {
  flex: 0 0 auto;
  margin-top: 0 !important;
}

.recipe-mobile-card-ready-chip {
  font-weight: 700;
  margin-inline-end: 4px;
}

.text-top {
  align-self: start !important;
}

.flat,
.theme--dark .flat {
  box-shadow: none !important;
  background-color: transparent !important;
}

.disable-highlight :deep(.v-card__overlay) {
  opacity: 0 !important;
}
</style>
