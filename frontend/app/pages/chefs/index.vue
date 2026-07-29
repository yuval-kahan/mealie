<template>
  <v-container class="narrow-container">
    <ChefCreateDialog
      v-model="dialogOpen"
      :chef="editingChef"
      @saved="handleSaved"
    />
    <ChefProfileDialog
      v-model="profileDialogOpen"
      :chef="selectedChef"
    />

    <BaseDialog
      v-model="deleteDialogOpen"
      :title="$t('general.confirm')"
      :icon="$globals.icons.delete"
      color="error"
      can-confirm
      @confirm="deleteChef"
    >
      <v-card-text>
        {{ $t("chef.delete-confirm", { name: deletingChef?.name || "" }) }}
      </v-card-text>
    </BaseDialog>

    <BasePageTitle divider>
      <template #title>
        {{ $t("chef.chefs") }}
      </template>
      <template #subtitle>
        {{ $t("chef.chefs-description") }}
      </template>
    </BasePageTitle>

    <div class="chef-toolbar mb-6">
      <v-text-field
        v-model="search"
        :label="$t('search.search')"
        :prepend-inner-icon="$globals.icons.search"
        density="compact"
        clearable
        hide-details
      />
      <v-select
        v-model="selectedRank"
        :items="rankFilterOptions"
        item-title="text"
        item-value="value"
        :label="$t('chef.rank')"
        density="compact"
        clearable
        hide-details
      />
      <v-select
        v-model="selectedCuisine"
        :items="cuisineOptions"
        :label="$t('chef.cuisines')"
        density="compact"
        clearable
        hide-details
      />
      <v-checkbox
        v-model="michelinOnly"
        :label="$t('chef.michelin-only')"
        density="compact"
        hide-details
        class="chef-michelin-filter"
      />
      <v-btn color="primary" :prepend-icon="$globals.icons.create" @click="openCreateDialog">
        {{ $t("chef.quick-add") }}
      </v-btn>
    </div>
    <BaseListSortControls
      v-model:sort-by="chefSortBy"
      v-model:sort-direction="chefSortDirection"
      :options="chefSortOptions"
      class="mb-6"
    />

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />
    <template v-else-if="filteredChefs.length">
      <BaseListPagination
        v-model:page="chefPage"
        v-model:items-per-page="chefsPerPage"
        :total-items="chefTotal"
      />
      <section v-for="section in chefSections" :key="section.rank" class="mb-8">
        <div class="d-flex align-center ga-2 mb-3">
          <h2 class="text-h6">
            {{ section.title }}
          </h2>
          <v-chip size="small" color="primary" variant="tonal">
            {{ section.items.length }}
          </v-chip>
        </div>

        <div class="chef-grid">
          <v-card
            v-for="chef in section.items"
            :key="chef.id"
            class="chef-card"
            variant="outlined"
            role="button"
            tabindex="0"
            @click="openProfile(chef)"
            @keydown.enter="openProfile(chef)"
          >
            <div class="chef-portrait">
              <v-img
                v-if="chef.hasImage && !imageErrors.has(chef.id)"
                :src="api.chefs.imageUrl(chef)"
                :alt="chef.name"
                cover
                height="220"
                @error="imageErrors.add(chef.id)"
              />
              <div v-else class="chef-portrait-placeholder">
                <v-icon size="76" color="primary">
                  {{ $globals.icons.chefHat }}
                </v-icon>
              </div>
            </div>

            <v-card-title class="chef-title">
              <span>{{ chef.name }}</span>
              <v-spacer />
              <v-btn
                icon
                size="small"
                variant="text"
                :title="$t('general.edit')"
                @click.stop="openEditDialog(chef)"
              >
                <v-icon>{{ $globals.icons.edit }}</v-icon>
              </v-btn>
            </v-card-title>

            <v-card-subtitle v-if="chef.country">
              {{ chef.country }}
            </v-card-subtitle>

            <v-card-text class="chef-content">
              <div class="d-flex flex-wrap ga-1 mb-3">
                <v-chip
                  v-for="cuisine in chef.cuisines"
                  :key="cuisine"
                  size="small"
                  color="primary"
                  variant="tonal"
                >
                  {{ cuisine }}
                </v-chip>
                <v-chip
                  v-for="specialty in chef.specialties"
                  :key="specialty"
                  size="small"
                  variant="outlined"
                >
                  {{ specialty }}
                </v-chip>
              </div>

              <p v-if="chef.careerSummary" class="chef-summary mb-3">
                {{ chef.careerSummary }}
              </p>
              <p v-else-if="chef.biography" class="chef-summary mb-3">
                {{ chef.biography }}
              </p>

              <v-alert
                v-if="chef.hasMichelinRestaurant || chef.michelinStarCount"
                type="info"
                variant="tonal"
                density="compact"
                class="mb-3"
              >
                <strong>{{ $t("chef.michelin") }}:</strong>
                {{ chef.michelinSummary || $t("chef.michelin-stars", { count: chef.michelinStarCount }) }}
              </v-alert>

              <div v-if="chef.restaurants.length" class="chef-relation mb-2">
                <strong>{{ $t("chef.linked-restaurants") }}:</strong>
                <NuxtLink
                  v-for="restaurant in chef.restaurants"
                  :key="restaurant.id"
                  :to="`/restaurants?search=${encodeURIComponent(restaurant.name)}`"
                >
                  {{ restaurant.name }}
                </NuxtLink>
              </div>
              <div v-if="chef.uploadedBooks.length" class="chef-relation">
                <strong>{{ $t("chef.linked-books") }}:</strong>
                <span v-for="book in chef.uploadedBooks" :key="book.id">
                  {{ book.name }}
                </span>
              </div>
            </v-card-text>

            <v-card-actions class="chef-actions">
              <a
                v-if="chef.websiteUrl"
                :href="chef.websiteUrl"
                target="_blank"
                rel="noopener"
                class="text-decoration-none"
              >
                <v-btn
                  icon
                  size="small"
                  variant="text"
                  :title="$t('chef.website-url')"
                >
                  <v-icon>{{ $globals.icons.web }}</v-icon>
                </v-btn>
              </a>
              <a
                v-if="chef.instagramUrl"
                :href="chef.instagramUrl"
                target="_blank"
                rel="noopener"
                class="text-decoration-none"
              >
                <v-btn
                  icon
                  size="small"
                  variant="text"
                  :title="$t('chef.instagram-url')"
                >
                  <v-icon>{{ $globals.icons.externalLink }}</v-icon>
                </v-btn>
              </a>
              <v-spacer />
              <v-btn
                icon
                size="small"
                variant="text"
                color="error"
                :title="$t('general.delete')"
                @click.stop="openDeleteDialog(chef)"
              >
                <v-icon>{{ $globals.icons.delete }}</v-icon>
              </v-btn>
            </v-card-actions>
          </v-card>
        </div>
      </section>
    </template>
    <v-alert v-else type="info" variant="tonal">
      {{ $t("chef.no-chefs") }}
    </v-alert>
  </v-container>
</template>

<script setup lang="ts">
import type { Chef, ChefRank } from "~/lib/api/types/chef";
import { useUserApi } from "~/composables/api/api-client";
import { alert } from "~/composables/use-toast";

const i18n = useI18n();
const route = useRoute();
const api = useUserApi();
const chefs = ref<Chef[]>([]);
const loading = ref(true);
const search = ref(typeof route.query.search === "string" ? route.query.search : "");
const selectedRank = ref<ChefRank | null>(null);
const selectedCuisine = ref<string | null>(null);
const michelinOnly = ref(false);
const dialogOpen = ref(false);
const deleteDialogOpen = ref(false);
const editingChef = ref<Chef | null>(null);
const deletingChef = ref<Chef | null>(null);
const selectedChef = ref<Chef | null>(null);
const profileDialogOpen = ref(false);
const imageErrors = reactive(new Set<string>());
const CHEF_SORT_KEYS = ["name", "rank", "michelin", "country", "created"] as const;
const {
  sortBy: chefSortBy,
  sortDirection: chefSortDirection,
} = usePersistedListSort(CHEF_SORT_KEYS, "name", "asc", "chefs");

useSeoMeta({ title: i18n.t("chef.chefs") });

const rankOptions = computed<{ text: string; value: ChefRank }[]>(() => [
  { text: i18n.t("chef.rank-world-class"), value: "world_class" },
  { text: i18n.t("chef.rank-excellent"), value: "excellent" },
  { text: i18n.t("chef.rank-good"), value: "good" },
  { text: i18n.t("chef.rank-medium"), value: "medium" },
  { text: i18n.t("chef.rank-emerging"), value: "emerging" },
]);

const rankFilterOptions = computed(() => rankOptions.value);
const chefSortOptions = computed(() => [
  { title: i18n.t("general.name"), value: "name" },
  { title: i18n.t("chef.rank"), value: "rank" },
  { title: i18n.t("chef.michelin-star-count"), value: "michelin" },
  { title: i18n.t("chef.country"), value: "country" },
  { title: i18n.t("general.created"), value: "created" },
]);

const cuisineOptions = computed(() => [...new Set(chefs.value.flatMap(chef => chef.cuisines))]
  .sort((left, right) => left.localeCompare(right, i18n.locale.value)));

const filteredChefs = computed(() => {
  const query = search.value.trim().toLocaleLowerCase();
  return chefs.value.filter((chef) => {
    if (selectedRank.value && chef.rank !== selectedRank.value) return false;
    if (selectedCuisine.value && !chef.cuisines.includes(selectedCuisine.value)) return false;
    if (michelinOnly.value && !chef.hasMichelinRestaurant) return false;
    if (!query) return true;
    return [
      chef.name,
      chef.country || "",
      chef.biography || "",
      chef.careerSummary || "",
      chef.michelinSummary || "",
      ...chef.aliases,
      ...chef.cuisines,
      ...chef.specialties,
      ...chef.awards,
      ...chef.notableRestaurants,
      ...chef.bookTitles,
    ].join(" ").toLocaleLowerCase().includes(query);
  });
});
const rankWeights: Record<ChefRank, number> = {
  world_class: 5,
  excellent: 4,
  good: 3,
  medium: 2,
  emerging: 1,
};
const sortedChefs = sortListItems(
  filteredChefs,
  chef => ({
    name: chef.name,
    rank: rankWeights[chef.rank],
    michelin: chef.michelinStarCount,
    country: chef.country,
    created: chef.createdAt ? Date.parse(chef.createdAt) : null,
  })[chefSortBy.value],
  chefSortDirection,
  i18n.locale,
);
const {
  page: chefPage,
  itemsPerPage: chefsPerPage,
  totalItems: chefTotal,
  paginatedItems: paginatedChefs,
} = useListPagination(sortedChefs);

const chefSections = computed(() => {
  const sections = rankOptions.value
    .map(option => ({
      rank: option.value,
      title: option.text,
      items: paginatedChefs.value.filter(chef => chef.rank === option.value),
    }))
    .filter(section => section.items.length);
  return chefSortBy.value === "rank" && chefSortDirection.value === "asc"
    ? [...sections].reverse()
    : sections;
});

onMounted(loadChefs);

async function loadChefs() {
  loading.value = true;
  const { data, error } = await api.chefs.getAll();
  chefs.value = data || [];
  if (error) alert.error(i18n.t("events.something-went-wrong"));
  loading.value = false;
}

function openCreateDialog() {
  editingChef.value = null;
  dialogOpen.value = true;
}

function openProfile(chef: Chef) {
  selectedChef.value = chef;
  profileDialogOpen.value = true;
}

function openEditDialog(chef: Chef) {
  editingChef.value = chef;
  dialogOpen.value = true;
}

function openDeleteDialog(chef: Chef) {
  deletingChef.value = chef;
  deleteDialogOpen.value = true;
}

async function handleSaved() {
  editingChef.value = null;
  imageErrors.clear();
  await loadChefs();
}

async function deleteChef() {
  if (!deletingChef.value) return;
  const { error } = await api.chefs.deleteOne(deletingChef.value.id);
  if (error) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }
  deletingChef.value = null;
  await loadChefs();
}
</script>

<style scoped>
.chef-toolbar {
  align-items: center;
  display: grid;
  gap: 12px;
  grid-template-columns:
    minmax(240px, 1fr)
    minmax(180px, 220px)
    minmax(180px, 220px)
    minmax(150px, max-content)
    max-content;
}

.chef-michelin-filter {
  min-width: 150px;
  white-space: nowrap;
}

.chef-grid {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 330px), 1fr));
}

.chef-card {
  display: flex;
  flex-direction: column;
  min-height: 480px;
}

.chef-portrait {
  background: rgb(var(--v-theme-surface-variant));
  height: 220px;
  overflow: hidden;
}

.chef-portrait-placeholder {
  align-items: center;
  display: flex;
  height: 100%;
  justify-content: center;
}

.chef-title {
  align-items: flex-start;
  display: flex;
  font-size: 1.1rem;
  line-height: 1.35;
}

.chef-content {
  flex: 1;
}

.chef-summary {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 5;
}

.chef-relation {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 8px;
}

.chef-actions {
  min-height: 48px;
}

@media (max-width: 1180px) {
  .chef-toolbar {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .chef-toolbar > :first-child {
    grid-column: 1 / -1;
  }
}

@media (max-width: 650px) {
  .chef-toolbar {
    grid-template-columns: 1fr;
  }

  .chef-toolbar > :first-child {
    grid-column: auto;
  }
}
</style>
