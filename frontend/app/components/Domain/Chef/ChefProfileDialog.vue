<template>
  <BaseDialog
    v-model="dialogOpen"
    :title="chef?.name || $t('chef.profile')"
    :icon="$globals.icons.chefHat"
    width="1120"
    max-width="96vw"
  >
    <v-card-text v-if="chef" class="chef-profile pa-0">
      <header class="chef-profile-header">
        <v-img
          v-if="chef.hasImage && !imageFailed"
          :src="api.chefs.imageUrl(chef)"
          :alt="chef.name"
          class="chef-profile-image"
          cover
          @error="imageFailed = true"
        />
        <div v-else class="chef-profile-image chef-profile-placeholder">
          <v-icon size="88" color="primary">
            {{ $globals.icons.chefHat }}
          </v-icon>
        </div>
        <div class="chef-profile-heading">
          <h2>{{ chef.name }}</h2>
          <p v-if="chef.country" class="text-medium-emphasis">
            {{ chef.country }}
          </p>
          <div class="d-flex flex-wrap ga-2 mt-3">
            <v-chip color="primary" variant="tonal" size="small">
              {{ rankLabel }}
            </v-chip>
            <v-chip
              v-if="chef.hasMichelinRestaurant || chef.michelinStarCount"
              color="amber-darken-3"
              variant="tonal"
              size="small"
              :prepend-icon="$globals.icons.star"
            >
              {{ chef.michelinSummary || $t("chef.michelin-stars", { count: chef.michelinStarCount }) }}
            </v-chip>
          </div>
        </div>
      </header>

      <div class="chef-profile-layout">
        <main class="chef-profile-main">
          <section v-if="chef.biography">
            <h3>{{ $t("chef.biography") }}</h3>
            <p>{{ chef.biography }}</p>
          </section>
          <section v-if="chef.careerSummary">
            <h3>{{ $t("chef.career-summary") }}</h3>
            <p>{{ chef.careerSummary }}</p>
          </section>
          <section v-if="chef.michelinSummary">
            <h3>{{ $t("chef.michelin-summary") }}</h3>
            <p>{{ chef.michelinSummary }}</p>
          </section>
          <section v-if="chef.notes">
            <h3>{{ $t("chef.notes") }}</h3>
            <p>{{ chef.notes }}</p>
          </section>
        </main>

        <aside class="chef-profile-facts">
          <section v-if="chef.cuisines.length">
            <h3>{{ $t("chef.cuisines") }}</h3>
            <div class="d-flex flex-wrap ga-1">
              <v-chip v-for="item in chef.cuisines" :key="item" size="small">
                {{ item }}
              </v-chip>
            </div>
          </section>
          <section v-if="chef.specialties.length">
            <h3>{{ $t("chef.specialties") }}</h3>
            <ul>
              <li v-for="item in chef.specialties" :key="item">
                {{ item }}
              </li>
            </ul>
          </section>
          <section v-if="allRestaurants.length">
            <h3>{{ $t("chef.linked-restaurants") }}</h3>
            <ul>
              <li v-for="item in allRestaurants" :key="item">
                {{ item }}
              </li>
            </ul>
          </section>
          <section v-if="allBooks.length">
            <h3>{{ $t("chef.linked-books") }}</h3>
            <ul>
              <li v-for="item in allBooks" :key="item">
                {{ item }}
              </li>
            </ul>
          </section>
          <section v-if="chef.awards.length">
            <h3>{{ $t("chef.awards") }}</h3>
            <ul>
              <li v-for="item in chef.awards" :key="item">
                {{ item }}
              </li>
            </ul>
          </section>
          <section v-if="chef.wikipediaUrl || chef.websiteUrl || chef.instagramUrl">
            <h3>{{ $t("chef.sources") }}</h3>
            <a
              v-if="chef.wikipediaUrl"
              :href="chef.wikipediaUrl"
              target="_blank"
              rel="noopener"
            >
              {{ $t("chef.wikipedia-url") }}
            </a>
            <a
              v-if="chef.websiteUrl"
              :href="chef.websiteUrl"
              target="_blank"
              rel="noopener"
            >
              {{ $t("chef.website-url") }}
            </a>
            <a
              v-if="chef.instagramUrl"
              :href="chef.instagramUrl"
              target="_blank"
              rel="noopener"
            >
              {{ $t("chef.instagram-url") }}
            </a>
          </section>
        </aside>
      </div>
    </v-card-text>
  </BaseDialog>
</template>

<script setup lang="ts">
import type { Chef, ChefRank } from "~/lib/api/types/chef";
import { useUserApi } from "~/composables/api/api-client";

const props = defineProps<{ chef?: Chef | null }>();
const dialogOpen = defineModel<boolean>({ default: false });
const api = useUserApi();
const i18n = useI18n();
const imageFailed = ref(false);

const rankKeys: Record<ChefRank, string> = {
  world_class: "chef.rank-world-class",
  excellent: "chef.rank-excellent",
  good: "chef.rank-good",
  medium: "chef.rank-medium",
  emerging: "chef.rank-emerging",
};
const rankLabel = computed(() => i18n.t(rankKeys[props.chef?.rank || "good"]));
const allRestaurants = computed(() => [...new Set([
  ...(props.chef?.restaurants.map(item => item.name) || []),
  ...(props.chef?.notableRestaurants || []),
])]);
const allBooks = computed(() => [...new Set([
  ...(props.chef?.uploadedBooks.map(item => item.name) || []),
  ...(props.chef?.bookTitles || []),
])]);

watch(() => [dialogOpen.value, props.chef?.id], () => {
  imageFailed.value = false;
});
</script>

<style scoped>
.chef-profile {
  color: rgb(var(--v-theme-on-surface));
}

.chef-profile-header {
  align-items: center;
  background: rgba(var(--v-theme-primary), 0.06);
  display: grid;
  gap: 24px;
  grid-template-columns: 190px minmax(0, 1fr);
  padding: 24px;
}

.chef-profile-image {
  aspect-ratio: 1;
  border-radius: 4px;
  width: 190px;
}

.chef-profile-placeholder {
  align-items: center;
  background: rgba(var(--v-theme-on-surface), 0.06);
  display: flex;
  justify-content: center;
}

.chef-profile-heading h2 {
  font-size: 2rem;
  line-height: 1.2;
}

.chef-profile-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(250px, 32%);
}

.chef-profile-main,
.chef-profile-facts {
  display: grid;
  gap: 24px;
  padding: 28px;
}

.chef-profile-main section,
.chef-profile-facts section {
  border-block-end: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  padding-block-end: 20px;
}

.chef-profile-main h3,
.chef-profile-facts h3 {
  font-size: 1rem;
  margin-block-end: 10px;
}

.chef-profile-main p {
  line-height: 1.8;
  white-space: pre-line;
}

.chef-profile-facts {
  background: rgba(var(--v-theme-on-surface), 0.025);
  border-inline-start: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.chef-profile-facts ul {
  margin: 0;
  padding-inline-start: 20px;
}

.chef-profile-facts a {
  display: block;
  margin-block: 6px;
}

@media (max-width: 700px) {
  .chef-profile-header {
    grid-template-columns: 96px minmax(0, 1fr);
    padding: 16px;
  }

  .chef-profile-image {
    width: 96px;
  }

  .chef-profile-heading h2 {
    font-size: 1.35rem;
  }

  .chef-profile-layout {
    grid-template-columns: 1fr;
  }

  .chef-profile-facts {
    border-inline-start: 0;
    border-block-start: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  }
}
</style>
