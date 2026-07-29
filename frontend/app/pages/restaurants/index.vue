<template>
  <v-container class="narrow-container">
    <RestaurantDiscoverDialog
      v-model="discoverDialogOpen"
      @saved="loadRestaurants"
    />
    <RestaurantCreateDialog
      v-model="dialogOpen"
      :restaurant="editingRestaurant"
      @saved="handleSaved"
    />

    <BaseDialog
      v-model="deleteDialogOpen"
      :title="$t('general.confirm')"
      :icon="$globals.icons.delete"
      color="error"
      can-confirm
      @confirm="deleteRestaurant"
    >
      <v-card-text>
        {{ $t("restaurant.delete-confirm", { name: deletingRestaurant?.name || "" }) }}
      </v-card-text>
    </BaseDialog>

    <BasePageTitle divider>
      <template #title>
        {{ $t("restaurant.restaurants") }}
      </template>
      <template #subtitle>
        {{ $t("restaurant.restaurants-description") }}
      </template>
    </BasePageTitle>

    <div class="restaurants-toolbar mb-6">
      <v-text-field
        v-model="search"
        :label="$t('search.search')"
        :prepend-inner-icon="$globals.icons.search"
        density="compact"
        clearable
        hide-details
      />
      <v-btn color="primary" :prepend-icon="$globals.icons.create" @click="openCreateDialog">
        {{ $t("restaurant.quick-add") }}
      </v-btn>
      <v-btn
        color="primary"
        variant="tonal"
        :prepend-icon="$globals.icons.robot"
        @click="discoverDialogOpen = true"
      >
        {{ $t("restaurant.find-with-ai") }}
      </v-btn>
    </div>
    <div class="restaurants-filters mb-6">
      <v-select
        v-model="recommendationFilter"
        :items="recommendationFilterOptions"
        item-title="text"
        item-value="value"
        :label="$t('restaurant.recommendation')"
        density="compact"
        clearable
        hide-details
      />
      <v-select
        v-model="visitFilter"
        :items="visitFilterOptions"
        item-title="text"
        item-value="value"
        :label="$t('restaurant.visit-status')"
        density="compact"
        clearable
        hide-details
      />
      <v-select
        v-model="cuisineFilter"
        :items="cuisineOptions"
        :label="$t('restaurant.cuisine-types')"
        density="compact"
        clearable
        hide-details
      />
      <v-checkbox
        v-model="michelinOnly"
        :label="$t('restaurant.michelin-only')"
        density="compact"
        hide-details
      />
    </div>
    <BaseListSortControls
      v-model:sort-by="restaurantSortBy"
      v-model:sort-direction="restaurantSortDirection"
      :options="restaurantSortOptions"
      class="mb-6"
    />

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />
    <template v-else-if="filteredRestaurants.length">
      <BaseListPagination
        v-model:page="restaurantPage"
        v-model:items-per-page="restaurantsPerPage"
        :total-items="restaurantTotal"
      />
      <section
        v-for="section in restaurantSections"
        :key="section.status"
        class="restaurant-section mb-8"
      >
        <div class="d-flex align-center ga-2 mb-3">
          <h2 class="text-h6">
            {{ section.title }}
          </h2>
          <v-chip size="small" color="primary" variant="tonal">
            {{ section.items.length }}
          </v-chip>
        </div>
        <div class="restaurants-grid">
          <v-card
            v-for="restaurant in section.items"
            :key="restaurant.id"
            class="restaurant-card"
            variant="outlined"
          >
            <v-card-title class="d-flex align-start ga-2">
              <v-icon color="primary" class="mt-1">
                {{ $globals.icons.chefHat }}
              </v-icon>
              <span class="restaurant-name">{{ restaurant.name }}</span>
              <v-spacer />
              <v-btn
                icon
                size="small"
                variant="text"
                :title="$t('general.edit')"
                @click="openEditDialog(restaurant)"
              >
                <v-icon>{{ $globals.icons.edit }}</v-icon>
              </v-btn>
            </v-card-title>

            <v-card-subtitle v-if="restaurant.websiteUrl">
              <a :href="restaurant.websiteUrl" target="_blank" rel="noopener" class="restaurant-link">
                {{ restaurant.websiteUrl }}
                <v-icon size="x-small">{{ $globals.icons.openInNew }}</v-icon>
              </a>
            </v-card-subtitle>

            <v-card-text>
              <p v-if="restaurant.description" class="mb-3">
                {{ restaurant.description }}
              </p>
              <div v-if="restaurant.cuisineTypes.length" class="d-flex flex-wrap ga-1 mb-3">
                <v-chip
                  v-for="cuisine in restaurant.cuisineTypes"
                  :key="cuisine"
                  size="small"
                  color="primary"
                  variant="tonal"
                >
                  {{ cuisine }}
                </v-chip>
              </div>
              <div v-if="restaurant.addresses.length" class="restaurant-detail mb-2">
                <strong>{{ $t("restaurant.addresses") }}:</strong>
                <div v-for="address in restaurant.addresses" :key="address">
                  <a
                    :href="addressMapUrl(restaurant, address)"
                    target="_blank"
                    rel="noopener"
                    class="restaurant-location-link"
                  >
                    {{ address }}
                    <v-icon size="x-small">{{ $globals.icons.openInNew }}</v-icon>
                  </a>
                </div>
              </div>
              <div v-else-if="restaurant.googleMapsUrl" class="restaurant-detail mb-2">
                <a
                  :href="restaurant.googleMapsUrl"
                  target="_blank"
                  rel="noopener"
                  class="restaurant-location-link"
                >
                  {{ $t("restaurant.open-in-google-maps") }}
                  <v-icon size="x-small">{{ $globals.icons.openInNew }}</v-icon>
                </a>
              </div>
              <div v-if="restaurant.phone" class="restaurant-detail mb-2">
                <strong>{{ $t("restaurant.phone") }}:</strong> {{ restaurant.phone }}
              </div>
              <div v-if="restaurant.priceRange" class="restaurant-detail mb-2">
                <strong>{{ $t("restaurant.price-range") }}:</strong> {{ restaurant.priceRange }}
              </div>
              <v-alert
                v-if="restaurant.michelinInfo || restaurant.isMichelinListed || restaurant.michelinStarCount"
                type="info"
                variant="tonal"
                density="compact"
                class="mt-3"
              >
                <strong>{{ $t("restaurant.michelin-info") }}:</strong>
                {{ restaurant.michelinInfo || $t("restaurant.michelin-stars", { count: restaurant.michelinStarCount }) }}
              </v-alert>
              <div v-if="restaurant.chefNames.length" class="restaurant-detail mt-3">
                <strong>{{ $t("restaurant.linked-chefs") }}:</strong>
                <NuxtLink
                  v-for="chefName in restaurant.chefNames"
                  :key="chefName"
                  :to="`/chefs?search=${encodeURIComponent(chefName)}`"
                  class="restaurant-related-link"
                >
                  {{ chefName }}
                </NuxtLink>
              </div>
              <div v-if="restaurant.bookTitles.length" class="restaurant-detail mt-2">
                <strong>{{ $t("restaurant.linked-books") }}:</strong>
                <span
                  v-for="bookTitle in restaurant.bookTitles"
                  :key="bookTitle"
                  class="restaurant-related-link"
                >
                  {{ bookTitle }}
                </span>
              </div>
              <div v-if="restaurant.googleRating || restaurant.ourRating" class="restaurant-ratings mt-3">
                <a
                  v-if="restaurant.googleRating"
                  :href="restaurantMapUrl(restaurant)"
                  target="_blank"
                  rel="noopener"
                  class="restaurant-google-rating"
                >
                  <v-icon size="small" color="warning">{{ $globals.icons.star }}</v-icon>
                  <strong>{{ $t("restaurant.google-rating") }}:</strong>
                  {{ restaurant.googleRating.toFixed(1) }}
                  <span v-if="restaurant.googleReviewCount">
                    ({{ $t("restaurant.review-count", { count: restaurant.googleReviewCount }) }})
                  </span>
                </a>
                <div v-if="restaurant.ourRating">
                  <strong>{{ $t("restaurant.our-rating") }}:</strong>
                  <v-rating
                    :model-value="restaurant.ourRating"
                    color="warning"
                    active-color="warning"
                    half-increments
                    readonly
                    density="compact"
                    size="small"
                  />
                </div>
              </div>
              <div v-if="restaurant.notes" class="restaurant-notes mt-3">
                <strong>{{ $t("restaurant.notes") }}:</strong> {{ restaurant.notes }}
              </div>
            </v-card-text>

            <v-card-actions class="restaurant-card-actions">
              <v-select
                :model-value="restaurant.visitStatus"
                :items="visitOptions"
                item-title="text"
                item-value="value"
                :label="$t('restaurant.visit-status')"
                density="compact"
                variant="outlined"
                hide-details
                :disabled="updatingIds.has(restaurant.id)"
                @update:model-value="updateVisitStatus(restaurant, $event)"
              />
              <v-select
                :model-value="restaurant.recommendationStatus"
                :items="recommendationOptions"
                item-title="text"
                item-value="value"
                :label="$t('restaurant.recommendation')"
                density="compact"
                variant="outlined"
                hide-details
                :disabled="updatingIds.has(restaurant.id)"
                @update:model-value="updateRecommendationStatus(restaurant, $event)"
              />
              <v-btn
                icon
                variant="text"
                color="error"
                :title="$t('general.delete')"
                @click="openDeleteDialog(restaurant)"
              >
                <v-icon>{{ $globals.icons.delete }}</v-icon>
              </v-btn>
            </v-card-actions>
          </v-card>
        </div>
      </section>
    </template>
    <v-alert v-else type="info" variant="tonal">
      {{ $t("restaurant.no-restaurants") }}
    </v-alert>
  </v-container>
</template>

<script setup lang="ts">
import type {
  Restaurant,
  RestaurantCreate,
  RestaurantRecommendationStatus,
  RestaurantVisitStatus,
} from "~/lib/api/types/restaurant";
import { useUserApi } from "~/composables/api/api-client";
import { alert } from "~/composables/use-toast";

const i18n = useI18n();
const api = useUserApi();
const route = useRoute();
const restaurants = ref<Restaurant[]>([]);
const loading = ref(true);
const search = ref(typeof route.query.search === "string" ? route.query.search : "");
const recommendationFilter = ref<RestaurantRecommendationStatus | null>(null);
const visitFilter = ref<RestaurantVisitStatus | null>(null);
const cuisineFilter = ref<string | null>(null);
const michelinOnly = ref(false);
const dialogOpen = ref(false);
const discoverDialogOpen = ref(false);
const deleteDialogOpen = ref(false);
const editingRestaurant = ref<Restaurant | null>(null);
const deletingRestaurant = ref<Restaurant | null>(null);
const updatingIds = reactive(new Set<string>());

useSeoMeta({ title: i18n.t("restaurant.restaurants") });

const recommendationOptions = computed<{ text: string; value: RestaurantRecommendationStatus }[]>(() => [
  { text: i18n.t("restaurant.strongly-recommended"), value: "strongly_recommended" },
  { text: i18n.t("restaurant.recommended"), value: "recommended" },
  { text: i18n.t("restaurant.neutral"), value: "neutral" },
  { text: i18n.t("restaurant.not-recommended"), value: "not_recommended" },
  { text: i18n.t("restaurant.strongly-not-recommended"), value: "strongly_not_recommended" },
]);

const visitOptions = computed<{ text: string; value: RestaurantVisitStatus }[]>(() => [
  { text: i18n.t("restaurant.not-tried"), value: "not_tried" },
  { text: i18n.t("restaurant.tried"), value: "tried" },
]);

const recommendationFilterOptions = computed(() => [
  { text: i18n.t("catalog.all"), value: null },
  ...recommendationOptions.value,
]);

const visitFilterOptions = computed(() => [
  { text: i18n.t("catalog.all"), value: null },
  ...visitOptions.value,
]);

const cuisineOptions = computed(() => [...new Set(restaurants.value.flatMap(item => item.cuisineTypes))]
  .sort((left, right) => left.localeCompare(right, i18n.locale.value, { sensitivity: "base" })));

const RESTAURANT_SORT_KEYS = [
  "name",
  "recommendation",
  "googleRating",
  "ourRating",
  "michelin",
  "created",
] as const;
type RestaurantSortKey = typeof RESTAURANT_SORT_KEYS[number];
const {
  sortBy: restaurantSortBy,
  sortDirection: restaurantSortDirection,
} = usePersistedListSort(RESTAURANT_SORT_KEYS, "name", "asc", "restaurants");
const restaurantSortOptions = computed<{ title: string; value: RestaurantSortKey }[]>(() => [
  { title: i18n.t("general.name"), value: "name" },
  { title: i18n.t("restaurant.recommendation"), value: "recommendation" },
  { title: i18n.t("restaurant.google-rating"), value: "googleRating" },
  { title: i18n.t("restaurant.our-rating"), value: "ourRating" },
  { title: i18n.t("restaurant.michelin-info"), value: "michelin" },
  { title: i18n.t("catalog.created-at"), value: "created" },
]);
const recommendationWeights: Record<RestaurantRecommendationStatus, number> = {
  strongly_recommended: 5,
  recommended: 4,
  neutral: 3,
  not_recommended: 2,
  strongly_not_recommended: 1,
};

const filteredRestaurants = computed(() => {
  const query = search.value.trim().toLocaleLowerCase();
  return restaurants.value.filter((restaurant) => {
    if (
      recommendationFilter.value
      && restaurant.recommendationStatus !== recommendationFilter.value
    ) return false;
    if (visitFilter.value && restaurant.visitStatus !== visitFilter.value) return false;
    if (cuisineFilter.value && !restaurant.cuisineTypes.includes(cuisineFilter.value)) return false;
    if (
      michelinOnly.value
      && !restaurant.isMichelinListed
      && restaurant.michelinStarCount <= 0
    ) return false;
    if (!query) return true;
    return [
      restaurant.name,
      restaurant.websiteUrl || "",
      restaurant.description || "",
      restaurant.notes || "",
      restaurant.michelinInfo || "",
      ...restaurant.chefNames,
      ...restaurant.bookTitles,
      ...restaurant.cuisineTypes,
      ...restaurant.addresses,
    ].join(" ").toLocaleLowerCase().includes(query);
  });
});
const sortedRestaurants = sortListItems(
  filteredRestaurants,
  restaurant => ({
    name: restaurant.name,
    recommendation: recommendationWeights[restaurant.recommendationStatus],
    googleRating: restaurant.googleRating,
    ourRating: restaurant.ourRating,
    michelin: restaurant.michelinStarCount,
    created: restaurant.createdAt,
  })[restaurantSortBy.value],
  restaurantSortDirection,
  i18n.locale,
);
const {
  page: restaurantPage,
  itemsPerPage: restaurantsPerPage,
  totalItems: restaurantTotal,
  paginatedItems: paginatedRestaurants,
} = useListPagination(sortedRestaurants);

const orderedRecommendationOptions = computed(() => (
  restaurantSortBy.value === "recommendation" && restaurantSortDirection.value === "asc"
    ? [...recommendationOptions.value].reverse()
    : recommendationOptions.value
));
const restaurantSections = computed(() => orderedRecommendationOptions.value
  .map(option => ({
    status: option.value,
    title: option.text,
    items: paginatedRestaurants.value.filter(item => item.recommendationStatus === option.value),
  }))
  .filter(section => section.items.length));

onMounted(loadRestaurants);

async function loadRestaurants() {
  loading.value = true;
  const { data, error } = await api.restaurants.getAll();
  restaurants.value = data || [];
  if (error) alert.error(i18n.t("events.something-went-wrong"));
  loading.value = false;
}

function openCreateDialog() {
  editingRestaurant.value = null;
  dialogOpen.value = true;
}

function openEditDialog(restaurant: Restaurant) {
  editingRestaurant.value = restaurant;
  dialogOpen.value = true;
}

function openDeleteDialog(restaurant: Restaurant) {
  deletingRestaurant.value = restaurant;
  deleteDialogOpen.value = true;
}

async function handleSaved() {
  editingRestaurant.value = null;
  await loadRestaurants();
}

function mapsSearchUrl(query: string) {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
}

function addressMapUrl(restaurant: Restaurant, address: string) {
  return mapsSearchUrl(`${restaurant.name} ${address}`.trim());
}

function restaurantMapUrl(restaurant: Restaurant) {
  return restaurant.googleMapsUrl
    || mapsSearchUrl([restaurant.name, restaurant.addresses[0] || "ישראל"].filter(Boolean).join(" "));
}

function restaurantPayload(restaurant: Restaurant): RestaurantCreate {
  return {
    name: restaurant.name,
    websiteUrl: restaurant.websiteUrl,
    cuisineTypes: [...restaurant.cuisineTypes],
    addresses: [...restaurant.addresses],
    phone: restaurant.phone,
    priceRange: restaurant.priceRange,
    description: restaurant.description,
    notes: restaurant.notes,
    michelinInfo: restaurant.michelinInfo,
    michelinStarCount: restaurant.michelinStarCount,
    isMichelinListed: restaurant.isMichelinListed,
    chefNames: [...restaurant.chefNames],
    bookTitles: [...restaurant.bookTitles],
    chefIds: [...restaurant.chefIds],
    uploadedBookIds: [...restaurant.uploadedBookIds],
    googleRating: restaurant.googleRating,
    googleReviewCount: restaurant.googleReviewCount,
    googleMapsUrl: restaurant.googleMapsUrl,
    ourRating: restaurant.ourRating,
    recommendationStatus: restaurant.recommendationStatus,
    visitStatus: restaurant.visitStatus,
  };
}

async function updateRestaurantStatus(restaurant: Restaurant, update: Partial<RestaurantCreate>) {
  updatingIds.add(restaurant.id);
  const { data, error } = await api.restaurants.updateOne(restaurant.id, {
    ...restaurantPayload(restaurant),
    ...update,
  });
  updatingIds.delete(restaurant.id);
  if (!data || error) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }
  const index = restaurants.value.findIndex(item => item.id === data.id);
  if (index >= 0) restaurants.value[index] = data;
}

async function updateVisitStatus(restaurant: Restaurant, visitStatus: RestaurantVisitStatus) {
  await updateRestaurantStatus(restaurant, { visitStatus });
}

async function updateRecommendationStatus(
  restaurant: Restaurant,
  recommendationStatus: RestaurantRecommendationStatus,
) {
  await updateRestaurantStatus(restaurant, { recommendationStatus });
}

async function deleteRestaurant() {
  if (!deletingRestaurant.value) return;
  const { error } = await api.restaurants.deleteOne(deletingRestaurant.value.id);
  if (error) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }
  deletingRestaurant.value = null;
  await loadRestaurants();
}
</script>

<style scoped>
.restaurants-toolbar {
  align-items: center;
  display: grid;
  gap: 12px;
  grid-template-columns: minmax(220px, 1fr) auto auto;
}

.restaurants-filters {
  align-items: center;
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(3, minmax(160px, 1fr)) auto;
}

.restaurants-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 340px), 1fr));
}

.restaurant-card {
  display: flex;
  flex-direction: column;
  min-height: 300px;
}

.restaurant-card .v-card-text {
  flex: 1;
}

.restaurant-name {
  line-height: 1.35;
  overflow-wrap: anywhere;
  white-space: normal;
}

.restaurant-link,
.restaurant-google-rating,
.restaurant-location-link,
.restaurant-detail,
.restaurant-notes {
  overflow-wrap: anywhere;
}

.restaurant-related-link {
  margin-inline-start: 8px;
}

.restaurant-ratings {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.restaurant-google-rating {
  align-items: center;
  color: inherit;
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  text-decoration: none;
}

.restaurant-location-link {
  color: inherit;
  text-decoration: underline;
  text-decoration-thickness: 1px;
  text-underline-offset: 2px;
}

.restaurant-card-actions {
  align-items: center;
  display: grid;
  gap: 8px;
  grid-template-columns: minmax(125px, 1fr) minmax(145px, 1fr) auto;
}

@media (max-width: 700px) {
  .restaurants-toolbar,
  .restaurants-filters,
  .restaurant-card-actions {
    grid-template-columns: 1fr;
  }

  .restaurant-card-actions .v-btn {
    justify-self: end;
  }
}
</style>
