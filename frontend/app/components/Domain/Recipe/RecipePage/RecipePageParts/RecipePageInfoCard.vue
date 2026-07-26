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
                  v-if="recipeSourceName || recipeSourceUrl || recipe.createdBy"
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
                    v-if="recipeSourceName"
                    class="recipe-origin-meta__item"
                  >
                    <v-icon
                      size="small"
                      color="primary"
                    >
                      {{ $globals.icons.book }}
                    </v-icon>
                    <span class="font-weight-medium">{{ $t("recipe.source") }}:</span>
                    <span>{{ recipeSourceName }}</span>
                  </div>
                  <div
                    v-if="recipeSourceUrl"
                    class="recipe-origin-meta__item"
                  >
                    <v-icon size="small" color="primary">
                      {{ $globals.icons.link }}
                    </v-icon>
                    <span class="font-weight-medium">{{ $t("recipe.source-link") }}:</span>
                    <a
                      :href="recipeSourceUrl"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="recipe-origin-meta__link"
                      :title="$t('recipe.open-source')"
                    >
                      {{ recipeSourceUrl }}
                    </a>
                  </div>
                </div>
                <div
                  v-if="mealSuitability.length"
                  class="recipe-meal-suitability my-3"
                >
                  <div class="recipe-meal-suitability__title">
                    <v-icon size="small" color="primary">
                      {{ $globals.icons.calendar }}
                    </v-icon>
                    <span>{{ $t("recipe.suitable-meals") }}</span>
                  </div>
                  <div class="d-flex flex-wrap ga-2">
                    <v-chip
                      v-for="period in mealSuitability"
                      :key="period"
                      size="small"
                      color="primary"
                      variant="tonal"
                      label
                    >
                      {{ $t(`meal-plan.${period}`) }}
                    </v-chip>
                  </div>
                </div>
                <div
                  v-if="miseEnPlaceFood || miseEnPlaceTools"
                  class="recipe-mise-en-place my-3"
                >
                  <div class="recipe-mise-en-place__title">
                    <v-icon size="small" color="primary">
                      {{ $globals.icons.formatListCheck }}
                    </v-icon>
                    <span>{{ $t("recipe.mise-en-place") }}</span>
                  </div>
                  <div v-if="miseEnPlaceFood" class="recipe-mise-en-place__group">
                    <div class="recipe-mise-en-place__subtitle">
                      {{ $t("recipe.mise-en-place-food") }}
                    </div>
                    <SafeMarkdown :source="miseEnPlaceFood" />
                  </div>
                  <div v-if="miseEnPlaceTools" class="recipe-mise-en-place__group">
                    <div class="recipe-mise-en-place__subtitle">
                      {{ $t("recipe.mise-en-place-tools") }}
                    </div>
                    <SafeMarkdown :source="miseEnPlaceTools" />
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
import { useUserApi } from "~/composables/api/api-client";
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
  || mealSuitability.value.length
  || miseEnPlaceFood.value
  || miseEnPlaceTools.value
  || hasQuickStats.value
  || hasTimeStats.value,
));

const miseEnPlaceFood = computed(() => {
  const extras = props.recipe.extras || {};
  const value = extras.miseEnPlaceFood || extras.miseEnPlace;
  return typeof value === "string" ? value.trim() : "";
});

const miseEnPlaceTools = computed(() => {
  const value = props.recipe.extras?.miseEnPlaceTools;
  return typeof value === "string" ? value.trim() : "";
});

const mealSuitability = computed(() => {
  const value = props.recipe.extras?.mealSuitability;
  if (typeof value !== "string") {
    return [];
  }

  const allowedPeriods = new Set(["breakfast", "lunch", "dinner"]);
  return [...new Set(value.split(",").map(period => period.trim()).filter(period => allowedPeriods.has(period)))];
});

onMounted(() => {
  void ensureAvailability();
});

const recipeSourceName = computed(() => {
  const storedTitle = props.recipe.extras?.sourceTitle;
  if (typeof storedTitle === "string" && storedTitle.trim()) {
    return storedTitle.trim();
  }

  const source = props.recipe.source?.trim() || "";
  const sourceWithoutUrl = source
    .replace(/\[([^\]]+)\]\(https?:\/\/[^)]+\)/gi, "$1")
    .replace(/https?:\/\/[^\s<>"']+/gi, "")
    .replace(/^[\s|,:;\-–—]+|[\s|,:;\-–—]+$/g, "")
    .trim();
  if (sourceWithoutUrl && !externalUrlFromSource(sourceWithoutUrl)) {
    return sourceWithoutUrl;
  }

  const externalUrl = externalUrlFromSource(source);
  if (externalUrl) {
    try {
      return new URL(externalUrl).hostname.replace(/^www\./, "");
    }
    catch {
      return source;
    }
  }

  return source || null;
});

const recipeSourceUrl = computed(() => {
  const storedUrl = props.recipe.extras?.sourceUrl;
  const externalUrl = externalUrlFromSource(typeof storedUrl === "string" ? storedUrl : null)
    || externalUrlFromSource(props.recipe.source);
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

  const normalizedValue = value
    .replace(/^<(.+)>$/, "$1")
    .replace(/^https?:\/\/https?\/\//i, "https://");
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

.recipe-mise-en-place {
  border-inline-start: 3px solid rgb(var(--v-theme-primary));
  padding-inline-start: 12px;
}

.recipe-meal-suitability__title {
  align-items: center;
  display: flex;
  font-weight: 700;
  gap: 6px;
  margin-bottom: 8px;
}

.recipe-mise-en-place__title {
  align-items: center;
  display: flex;
  font-weight: 700;
  gap: 6px;
  margin-bottom: 6px;
}

.recipe-mise-en-place__group + .recipe-mise-en-place__group {
  margin-top: 12px;
}

.recipe-mise-en-place__subtitle {
  font-weight: 700;
  margin-bottom: 4px;
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
