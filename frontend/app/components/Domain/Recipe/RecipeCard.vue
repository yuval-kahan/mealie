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
          :image-version="image"
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
        <v-card-title class="recipe-card-title px-4">
          {{ displayName }}
        </v-card-title>

        <slot name="actions">
          <v-card-actions v-if="showRecipeContent" class="recipe-card-actions px-1">
            <RecipeFavoriteBadge v-if="isOwnGroup" :recipe-id="recipeId" show-always />
            <div v-else class="px-1" />
            <!-- Empty div to keep the layout consistent -->

            <RecipeCardRating :model-value="rating" :recipe-id="recipeId" />
            <v-spacer />
            <RecipeChips
              :truncate="true"
              :items="tags"
              :title="false"
              :limit="2"
              small
              url-prefix="tags"
              v-bind="$attrs"
            />

            <!-- If we're not logged-in, no items display, so we hide this menu -->
            <RecipeContextMenu
              v-if="isOwnGroup && showRecipeContent"
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
import { useLoggedInState } from "~/composables/use-logged-in-state";

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
const { isOwnGroup } = useLoggedInState();
const displayName = ref(props.name);

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

function handleRenamed(payload: { slug: string; name: string; recipe?: any }) {
  displayName.value = payload.name;
  emit("renamed", payload);
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
.recipe-card-actions {
  align-items: center;
  flex-wrap: nowrap;
  height: 52px;
  min-height: 52px;
  overflow: hidden;
}
.descriptionWrapper {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 8;
  line-clamp: 8;
  overflow: hidden;
}
</style>
