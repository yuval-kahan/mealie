<template>
  <div v-if="value && value.length > 0">
    <div
      v-if="!isCookMode"
      class="d-flex justify-start"
    >
      <h2 class="mt-1 text-h5 font-weight-medium opacity-80">
        {{ $t("recipe.ingredients") }}
      </h2>
      <v-btn
        icon
        size="small"
        variant="text"
        class="ml-2"
        :color="userExperiencePreferences.showRecipeItemImages ? 'primary' : undefined"
        :title="$t('recipe.toggle-item-images')"
        :aria-label="$t('recipe.toggle-item-images')"
        @click.stop="toggleItemImages"
      >
        <v-icon>{{ $globals.icons.fileImage }}</v-icon>
      </v-btn>
      <v-btn
        v-if="showEnsureItemImagesButton"
        icon
        size="small"
        variant="text"
        color="success"
        class="ml-1"
        :loading="itemImagesLoading"
        :title="$t('recipe.create-item-images')"
        :aria-label="$t('recipe.create-item-images')"
        @click.stop="ensureItemImages"
      >
        <v-icon>{{ $globals.icons.robot }}</v-icon>
      </v-btn>
      <AppButtonCopy
        btn-class="ml-auto"
        :copy-text="ingredientCopyText"
      />
    </div>
    <div>
      <div
        v-for="(ingredient, index) in value"
        :key="'ingredient' + index"
      >
        <h3
          v-if="showTitleEditor[index]"
          class="mt-4 mb-0"
        >
          {{ ingredient.title }}
        </h3>
        <v-divider v-if="showTitleEditor[index]" class="my-2" />
        <v-list-item
          density="compact"
          class="pa-0"
          @click.stop="toggleChecked(index)"
        >
          <template #prepend>
            <v-checkbox
              v-model="checked[index]"
              hide-details
              class="pt-0 my-auto py-auto"
              color="secondary"
              density="comfortable"
            />
          </template>
          <v-list-item-title
            :class="{ 'recipe-completed-item': checked[index] && userExperiencePreferences.strikeCompletedRecipeItems }"
          >
            <RecipeIngredientListItem
              :ingredient="ingredient"
              :scale="scale"
              :show-image="userExperiencePreferences.showRecipeItemImages"
              :image-url="ingredientImageUrl(ingredient)"
            />
          </v-list-item-title>
        </v-list-item>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import RecipeIngredientListItem from "./RecipeIngredientListItem.vue";
import { useStaticRoutes } from "~/composables/api";
import { useIngredientTextParser } from "~/composables/recipes";
import { recipeItemImagesEnsured, useRecipeItemImages } from "~/composables/recipes/use-recipe-item-images";
import { useUserExperiencePreferences } from "~/composables/use-users/preferences";
import type { RecipeIngredient } from "~/lib/api/types/recipe";

interface Props {
  value?: RecipeIngredient[];
  scale?: number;
  isCookMode?: boolean;
  groupId?: string | null;
  recipeSlug?: string | null;
  itemImagesEnsured?: boolean;
}
const props = withDefaults(defineProps<Props>(), {
  value: () => [],
  scale: 1,
  isCookMode: false,
  groupId: null,
  recipeSlug: null,
  itemImagesEnsured: false,
});

const emit = defineEmits<{
  itemImagesEnsured: [];
}>();

const { parseIngredientText } = useIngredientTextParser();
const userExperiencePreferences = useUserExperiencePreferences();
const { ensureRecipeItemImages } = useRecipeItemImages();
const { itemImage } = useStaticRoutes();
const itemImagesLoading = ref(false);
const localItemImagesEnsured = ref(props.itemImagesEnsured);

function validateTitle(title?: string | null) {
  return !(title === undefined || title === "" || title === null);
}

const checked = ref(props.value.map(() => false));
const showTitleEditor = computed(() => props.value.map(x => validateTitle(x.title)));
const showEnsureItemImagesButton = computed(() => {
  return !props.isCookMode && !!props.recipeSlug && !localItemImagesEnsured.value;
});

watch(
  () => props.itemImagesEnsured,
  (value) => {
    localItemImagesEnsured.value = recipeItemImagesEnsured({ itemImagesEnsured: value });
  },
);

const ingredientCopyText = computed(() => {
  const components: string[] = [];
  props.value.forEach((ingredient) => {
    if (ingredient.title) {
      if (components.length) {
        components.push("");
      }

      components.push(`[${ingredient.title}]`);
    }

    components.push(parseIngredientText(ingredient, props.scale, false));
  });

  return components.join("\n");
});

function toggleItemImages() {
  userExperiencePreferences.value.showRecipeItemImages = !userExperiencePreferences.value.showRecipeItemImages;
}

async function ensureItemImages() {
  if (!props.recipeSlug || itemImagesLoading.value) {
    return;
  }

  itemImagesLoading.value = true;
  try {
    const result = await ensureRecipeItemImages(props.recipeSlug);
    if (result) {
      localItemImagesEnsured.value = true;
      emit("itemImagesEnsured");
    }
  }
  finally {
    itemImagesLoading.value = false;
  }
}

function ingredientImageName(ingredient: RecipeIngredient) {
  if (ingredient.title) {
    return "";
  }

  return ingredient.food?.name || ingredient.display || ingredient.note || "";
}

function ingredientImageUrl(ingredient: RecipeIngredient) {
  return itemImage(props.groupId, "food", ingredientImageName(ingredient));
}

function toggleChecked(index: number) {
  // TODO Find a better way to do this - $set is not available, and
  // direct array modifications are not propagated for some reason
  checked.value.splice(index, 1, !checked.value[index]);
}
</script>

<style>
.dense-markdown p {
  margin: auto !important;
}

.recipe-completed-item,
.recipe-completed-item * {
  text-decoration: line-through;
}
</style>
