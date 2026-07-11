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
            <div class="recipe-info-card__details-row">
              <div class="recipe-info-card__meta-column">
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
                      :title="$t('recipe.open-source')"
                    >
                      {{ recipe.source }}
                    </a>
                    <span v-else>{{ recipe.source }}</span>
                  </div>
                </div>
              </div>
              <div
                v-if="hasQuickStats"
                class="recipe-info-card__quick-stats"
              >
                <v-chip
                  v-if="hasAllGroceries"
                  color="success"
                  variant="tonal"
                  class="mb-4 recipe-info-card__ready-chip"
                >
                  <v-icon start size="small">
                    {{ $globals.icons.cartCheck }}
                  </v-icon>
                  {{ $t("recipe.all-ingredients-available") }}
                </v-chip>
                <RecipeYield
                  v-if="recipe.recipeYieldQuantity || recipe.recipeYield"
                  :yield-quantity="recipe.recipeYieldQuantity"
                  :yield-text="recipe.recipeYield"
                  :scale="recipeScale"
                  class="mb-4"
                />
                <RecipeLastMade
                  v-if="isOwnGroup"
                  :recipe="recipe"
                  class="mb-4"
                />
              </div>
              <div
                v-if="hasTimeStats"
                class="recipe-info-card__time-stats"
              >
                <RecipeTimeCard
                  container-class="d-flex flex-wrap justify-start"
                  :prep-time="recipe.prepTime"
                  :total-time="recipe.totalTime"
                  :perform-time="recipe.performTime"
                  class="mb-4"
                />
              </div>
            </div>
            <v-divider v-if="hasInfoDetails" />
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
import { useShoppingListAvailability } from "~/composables/shopping-list-page/use-shopping-list-availability";

interface Props {
  recipe: NoUndefinedField<Recipe>;
  recipeScale?: number;
  landscape: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  recipeScale: 1,
});

const api = useUserApi();
const { isOwnGroup } = useLoggedInState();
const { ensureAvailability, hasAllGroceriesForRecipe } = useShoppingListAvailability();
const hasAllGroceries = computed(() => hasAllGroceriesForRecipe(props.recipe.name));
const hasQuickStats = computed(() => Boolean(
  props.recipe.recipeYieldQuantity
  || props.recipe.recipeYield
  || isOwnGroup.value
  || hasAllGroceries.value,
));
const hasTimeStats = computed(() => Boolean(props.recipe.prepTime || props.recipe.totalTime || props.recipe.performTime));
const hasInfoDetails = computed(() => Boolean(
  props.recipe.description
  || props.recipe.source
  || props.recipe.createdBy
  || hasQuickStats.value
  || hasTimeStats.value,
));

onMounted(() => {
  void ensureAvailability();
});

const recipeSourceUrl = computed(() => {
  const externalUrl = externalUrlFromSource(props.recipe.source);
  if (externalUrl) {
    return externalUrl;
  }

  const source = props.recipe.source?.trim();
  if (!source) {
    return null;
  }

  const extras = props.recipe.extras || {};
  const bookId = typeof extras.uploadedBookSourceId === "string"
    ? extras.uploadedBookSourceId.trim()
    : "";
  const storedPage = Number(extras.uploadedBookSourcePageStart);
  const page = Number.isInteger(storedPage) && storedPage > 0
    ? storedPage
    : pageFromBookSource(source);

  if (bookId) {
    return api.uploadedBooks.openUrl(bookId, page);
  }
  return page ? api.uploadedBooks.openSourceUrl(source, page) : null;
});

function pageFromBookSource(source: string) {
  const match = source.match(/(?:pages?|p\.?|עמוד(?:ים)?|עמ[׳'])\s*[:#]?\s*(\d{1,5})/i);
  const page = Number(match?.[1]);
  return Number.isInteger(page) && page > 0 ? page : null;
}

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

.recipe-info-card__details-row {
  display: flex;
  flex-direction: column;
  gap: 12px 48px;
}

.recipe-info-card__meta-column {
  min-width: 0;
}

.recipe-info-card__quick-stats {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  min-width: min(100%, 240px);
}

.recipe-info-card__time-stats {
  display: flex;
  align-items: flex-start;
  justify-content: flex-start;
  min-width: min(100%, 240px);
}

.recipe-info-card__ready-chip {
  font-weight: 700;
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

.recipe-origin-meta__link {
  color: rgb(var(--v-theme-primary));
  text-decoration: underline;
  text-underline-offset: 2px;
  overflow-wrap: anywhere;
}

@media (min-width: 960px) {
  .recipe-info-card__details {
    width: min(100%, 1140px);
    margin-inline: auto;
  }

  .recipe-info-card__details-row {
    display: grid;
    grid-template-columns: minmax(360px, 1fr) minmax(220px, max-content) minmax(240px, max-content);
    justify-content: stretch;
    align-items: flex-start;
  }

  .recipe-info-card__meta-column {
    max-width: 560px;
    min-width: 0;
  }

  .recipe-info-card__quick-stats {
    align-items: center;
    padding-top: 12px;
  }

  .recipe-info-card__time-stats {
    justify-content: center;
    padding-top: 12px;
  }
}
</style>
