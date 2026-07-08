<template>
  <div>
    <div class="d-flex justify-center flex-wrap align-stretch">
      <v-card
        width="100%"
        flat
        class="d-flex flex-column justify-center align-center"
      >
        <v-card-text class="w-100">
          <div class="d-flex flex-column align-center">
            <v-card-title class="text-h5 font-weight-regular pa-0 text-wrap text-center opacity-80">
              {{ recipe.name }}
            </v-card-title>
            <RecipeRating
              :key="recipe.slug"
              :model-value="recipe.rating"
              :recipe-id="recipe.id"
              :slug="recipe.slug"
              edit-button
            />
          </div>
          <div class="recipe-info-card__action-line my-2">
            <v-divider />
            <div class="recipe-info-card__action-slot">
              <slot name="actions" />
            </div>
          </div>
          <div class="recipe-info-card__details">
            <SafeMarkdown
              :source="recipe.description"
              class="recipe-info-card__description my-3"
            />
            <div
              v-if="recipe.source || recipe.createdBy"
              class="recipe-origin-meta my-3"
            >
              <div
                v-if="recipe.createdBy"
                class="recipe-origin-meta__item"
              >
                <v-icon
                  size="small"
                  color="primary"
                >
                  {{ $globals.icons.chefHat }}
                </v-icon>
                <span class="font-weight-medium">{{ $t("recipe.created-by") }}:</span>
                <span>{{ recipe.createdBy }}</span>
              </div>
              <div
                v-if="recipe.source"
                class="recipe-origin-meta__item"
              >
                <v-icon
                  size="small"
                  color="primary"
                >
                  {{ $globals.icons.book }}
                </v-icon>
                <span class="font-weight-medium">{{ $t("recipe.source") }}:</span>
                <a
                  v-if="recipeSourceUrl"
                  :href="recipeSourceUrl"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="recipe-origin-meta__link"
                >
                  {{ recipe.source }}
                </a>
                <span v-else>{{ recipe.source }}</span>
              </div>
            </div>
            <v-divider v-if="recipe.description || recipe.source || recipe.createdBy" />
            <v-container class="recipe-info-card__stats px-0">
              <div class="recipe-info-card__stat-group">
                <v-row no-gutters>
                  <v-col
                    v-if="recipe.recipeYieldQuantity || recipe.recipeYield"
                    cols="12"
                    class="d-flex flex-wrap justify-start"
                  >
                    <RecipeYield
                      :yield-quantity="recipe.recipeYieldQuantity"
                      :yield-text="recipe.recipeYield"
                      :scale="recipeScale"
                      class="mb-4"
                    />
                  </v-col>
                </v-row>
                <v-row no-gutters>
                  <v-col
                    cols="12"
                    class="d-flex flex-wrap justify-start"
                  >
                    <RecipeLastMade
                      v-if="isOwnGroup"
                      :recipe="recipe"
                      class="mb-4"
                    />
                  </v-col>
                </v-row>
              </div>
              <div
                v-if="recipe.prepTime || recipe.totalTime || recipe.performTime"
                class="recipe-info-card__stat-group"
              >
                <RecipeTimeCard
                  container-class="d-flex flex-wrap justify-start"
                  :prep-time="recipe.prepTime"
                  :total-time="recipe.totalTime"
                  :perform-time="recipe.performTime"
                  class="mb-4"
                />
              </div>
            </v-container>
          </div>
        </v-card-text>
      </v-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useLoggedInState } from "~/composables/use-logged-in-state";
import RecipeRating from "~/components/Domain/Recipe/RecipeRating.vue";
import RecipeLastMade from "~/components/Domain/Recipe/RecipeLastMade.vue";
import RecipeTimeCard from "~/components/Domain/Recipe/RecipeTimeCard.vue";
import RecipeYield from "~/components/Domain/Recipe/RecipeYield.vue";
import type { Recipe } from "~/lib/api/types/recipe";
import type { NoUndefinedField } from "~/lib/api/types/non-generated";

interface Props {
  recipe: NoUndefinedField<Recipe>;
  recipeScale?: number;
  landscape: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  recipeScale: 1,
});

const { isOwnGroup } = useLoggedInState();

const recipeSourceUrl = computed(() => {
  return externalUrlFromSource(props.recipe.source);
});

function externalUrlFromSource(source?: string | null) {
  const value = source?.trim();
  if (!value) {
    return null;
  }

  const normalizedValue = value.replace(/^<(.+)>$/, "$1");
  const explicitUrl = normalizedValue.match(/https?:\/\/[^\s<>"']+/i)?.[0];
  const candidate = explicitUrl || normalizedValue;
  const withProtocol = candidate.startsWith("www.")
    ? `https://${candidate}`
    : /^[^\s]+\.[^\s]+$/i.test(candidate)
      ? `https://${candidate}`
      : candidate;

  try {
    const url = new URL(withProtocol);
    return url.protocol === "http:" || url.protocol === "https:" ? url.toString() : null;
  }
  catch {
    return null;
  }
}
</script>

<style scoped>
.recipe-info-card__details {
  width: min(100%, 920px);
  margin-inline: auto;
  text-align: start;
}

.recipe-info-card__description {
  color: rgba(var(--v-theme-on-surface), 0.78);
}

.recipe-info-card__action-line {
  position: relative;
  display: flex;
  align-items: center;
  min-height: 48px;
}

.recipe-info-card__action-line .v-divider {
  width: 100%;
}

.recipe-info-card__action-slot {
  position: absolute;
  left: 0;
  top: 50%;
  z-index: 1;
  display: flex;
  align-items: center;
  transform: translateY(-50%);
}

.recipe-origin-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  color: rgba(var(--v-theme-on-surface), 0.75);
}

.recipe-origin-meta__item {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  width: 100%;
}

.recipe-info-card__stats {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-start;
  gap: 16px 48px;
}

.recipe-info-card__stat-group {
  min-width: min(100%, 260px);
}

.recipe-origin-meta__link {
  color: rgb(var(--v-theme-primary));
  text-decoration: underline;
  text-underline-offset: 2px;
  overflow-wrap: anywhere;
}

@media (min-width: 960px) {
  .recipe-info-card__details {
    width: calc(33.333333% - 8px);
    margin-inline-start: 0;
    margin-inline-end: auto;
  }
}
</style>
