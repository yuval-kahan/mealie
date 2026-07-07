<template>
  <v-app dark>
    <TheSnackbar />

    <AppHeader>
      <v-btn
        icon
        @click.stop="sidebar = !sidebar"
      >
        <v-icon> {{ $globals.icons.menu }}</v-icon>
      </v-btn>
    </AppHeader>

    <AppSidebar
      v-model="sidebar"
      v-model:organizer-preferences="organizerSidebarPreferences"
      :top-link="topLinks"
      :secondary-links="cookbookLinks || []"
      :organizer-sections="organizerSidebarSections"
    >
      <BaseDialog
        v-model="quickTextRecipeDialog"
        :title="$t('recipe.create-recipe-from-text')"
        :icon="$globals.icons.textBoxCheckOutline"
        width="880"
        max-width="96vw"
        disable-submit-on-enter
      >
        <RecipeCreateFromTextForm
          :show-title="false"
          :rows="10"
          :return-to="route.path"
          @created="quickTextRecipeDialog = false"
        />
      </BaseDialog>
      <v-menu
        offset-y
        nudge-bottom="5"
        close-delay="50"
        nudge-right="15"
      >
        <template #activator="{ props }">
          <v-btn
            v-if="isOwnGroup"
            rounded
            size="large"
            class="ml-2 mt-3"
            v-bind="props"
            variant="elevated"
            elevation="2"
            :color="$vuetify.theme.current.dark ? 'background-lighten-1' : 'background-darken-1'"
          >
            <v-icon
              start
              size="large"
              color="primary"
            >
              {{ $globals.icons.createAlt }}
            </v-icon>
            {{ $t("general.create") }}
          </v-btn>
        </template>
        <v-list
          density="comfortable"
          class="mb-0 mt-1 py-0"
          variant="flat"
        >
          <template v-for="(item, index) in createLinks">
            <div
              v-if="!item.hide"
              :key="item.title"
            >
              <v-divider
                v-if="item.insertDivider"
                :key="index"
                class="mx-2"
              />
              <v-list-item
                v-if="!item.restricted || isOwnGroup"
                :key="item.title"
                :to="item.to"
                exact
                class="my-1"
              >
                <template #prepend>
                  <v-icon
                    size="40"
                    :icon="item.icon"
                  />
                </template>
                <v-list-item-title class="font-weight-medium" style="font-size: small;">
                  {{ item.title }}
                </v-list-item-title>
                <v-list-item-subtitle class="font-weight-medium" style="font-size: small;">
                  {{ item.subtitle }}
                </v-list-item-subtitle>
              </v-list-item>
            </div>
          </template>
        </v-list>
      </v-menu>
      <v-btn
        v-if="isOwnGroup"
        rounded
        size="default"
        class="ml-2 mt-2 mb-2 quick-text-create-btn"
        variant="tonal"
        :color="$vuetify.theme.current.dark ? 'background-lighten-1' : 'background-darken-1'"
        @click="quickTextRecipeDialog = true"
      >
        <v-icon
          start
          color="primary"
        >
          {{ $globals.icons.textBoxCheckOutline }}
        </v-icon>
        {{ $t("recipe.create-from-text") }}
      </v-btn>
    </AppSidebar>
    <v-main class="pt-12">
      <v-scroll-x-transition>
        <div>
          <NuxtPage />
        </div>
      </v-scroll-x-transition>
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
import { useLoggedInState } from "~/composables/use-logged-in-state";
import type { OrganizerSidebarSection, SideBarLink } from "~/types/application-types";
import { useGroupSelf } from "~/composables/use-groups";
import { useCookbookPreferences, useOrganizerSidebarPreferences } from "~/composables/use-users/preferences";
import { useCookbookStore, usePublicCookbookStore } from "~/composables/store/use-cookbook-store";
import { useCategoryStore, usePublicCategoryStore } from "~/composables/store/use-category-store";
import { usePublicTagStore, useTagStore } from "~/composables/store/use-tag-store";
import type { ReadCookBook } from "~/lib/api/types/cookbook";
import type { RecipeCategory, RecipeTag } from "~/lib/api/types/recipe";

const i18n = useI18n();
const { $globals } = useNuxtApp();
const display = useDisplay();
const auth = useMealieAuth();
const { isOwnGroup } = useLoggedInState();
const { group } = useGroupSelf();

const route = useRoute();
const groupSlug = computed(() => route.params.groupSlug as string || auth.user.value?.groupSlug || "");

const cookbookPreferences = useCookbookPreferences();
const organizerSidebarPreferences = useOrganizerSidebarPreferences();
const ownCookbookStore = computed(() => isOwnGroup.value ? useCookbookStore(i18n) : null);
const ownCategoryStore = computed(() => isOwnGroup.value ? useCategoryStore(i18n) : null);
const ownTagStore = computed(() => isOwnGroup.value ? useTagStore(i18n) : null);
const publicCookbookStoreCache = ref<Record<string, ReturnType<typeof usePublicCookbookStore>>>({});
const publicCategoryStoreCache = ref<Record<string, ReturnType<typeof usePublicCategoryStore>>>({});
const publicTagStoreCache = ref<Record<string, ReturnType<typeof usePublicTagStore>>>({});

function getPublicCookbookStore(slug: string) {
  if (!publicCookbookStoreCache.value[slug]) {
    publicCookbookStoreCache.value[slug] = usePublicCookbookStore(slug, i18n);
  }
  return publicCookbookStoreCache.value[slug];
}

function getPublicCategoryStore(slug: string) {
  if (!publicCategoryStoreCache.value[slug]) {
    publicCategoryStoreCache.value[slug] = usePublicCategoryStore(slug, i18n);
  }
  return publicCategoryStoreCache.value[slug];
}

function getPublicTagStore(slug: string) {
  if (!publicTagStoreCache.value[slug]) {
    publicTagStoreCache.value[slug] = usePublicTagStore(slug, i18n);
  }
  return publicTagStoreCache.value[slug];
}

const cookbooks = computed(() => {
  if (ownCookbookStore.value) {
    return ownCookbookStore.value.store.value;
  }
  else if (groupSlug.value) {
    const publicStore = getPublicCookbookStore(groupSlug.value);
    return unref(publicStore.store);
  }
  return [];
});

const categories = computed(() => {
  if (ownCategoryStore.value) {
    return ownCategoryStore.value.store.value;
  }
  else if (groupSlug.value) {
    const publicStore = getPublicCategoryStore(groupSlug.value);
    return unref(publicStore.store);
  }
  return [];
});

const tags = computed(() => {
  if (ownTagStore.value) {
    return ownTagStore.value.store.value;
  }
  else if (groupSlug.value) {
    const publicStore = getPublicTagStore(groupSlug.value);
    return unref(publicStore.store);
  }
  return [];
});

const showImageImport = computed(() => group.value?.aiProviderSettings?.imageProviderEnabled);

const sidebar = ref<boolean>(false);
const quickTextRecipeDialog = ref(false);
onMounted(() => {
  sidebar.value = display.lgAndUp.value;
});

function cookbookAsLink(cookbook: ReadCookBook): SideBarLink {
  return {
    key: cookbook.slug || "",
    icon: $globals.icons.pages,
    title: cookbook.name,
    to: `/g/${groupSlug.value}/cookbooks/${cookbook.slug || ""}`,
    restricted: false,
  };
}

function organizerItemAsLink(item: RecipeCategory | RecipeTag, queryKey: "categories" | "tags", icon: string): SideBarLink | null {
  if (!item.id) {
    return null;
  }

  return {
    key: item.id,
    icon,
    title: item.name,
    to: `/g/${groupSlug.value}?${queryKey}=${encodeURIComponent(item.id)}`,
    restricted: false,
  };
}

function sortByName<T extends { name: string }>(items: T[]) {
  return [...items].sort((a, b) => a.name.localeCompare(b.name));
}

const currentUserHouseholdId = computed(() => auth.user.value?.householdId);
const cookbookLinks = computed<SideBarLink[]>(() => {
  if (!cookbooks.value?.length) {
    return [];
  }

  const sortedCookbooks = [...cookbooks.value].sort((a, b) => (a.position || 0) - (b.position || 0));

  const ownLinks: SideBarLink[] = [];
  const links: SideBarLink[] = [];
  const cookbooksByHousehold = sortedCookbooks.reduce((acc, cookbook) => {
    const householdName = cookbook.household?.name || "";
    (acc[householdName] ||= []).push(cookbook);
    return acc;
  }, {} as Record<string, ReadCookBook[]>);

  Object.entries(cookbooksByHousehold).forEach(([householdName, cookbooks]) => {
    if (!cookbooks.length) {
      return;
    }
    if (cookbooks[0].householdId === currentUserHouseholdId.value) {
      ownLinks.push(...cookbooks.map(cookbookAsLink));
    }
    else {
      links.push({
        key: householdName,
        icon: $globals.icons.book,
        title: householdName,
        children: cookbooks.map(cookbookAsLink),
        restricted: false,
      });
    }
  });

  links.sort((a, b) => a.title.localeCompare(b.title));
  if (auth.user.value && cookbookPreferences.value.hideOtherHouseholds) {
    return ownLinks;
  }
  else {
    return [...ownLinks, ...links];
  }
});

const categoryLinks = computed<SideBarLink[]>(() => {
  return sortByName(categories.value)
    .map(category => organizerItemAsLink(category, "categories", $globals.icons.categories))
    .filter((link): link is SideBarLink => !!link);
});

const tagLinks = computed<SideBarLink[]>(() => {
  return sortByName(tags.value)
    .map(tag => organizerItemAsLink(tag, "tags", $globals.icons.tags))
    .filter((link): link is SideBarLink => !!link);
});

const organizerSidebarSections = computed<OrganizerSidebarSection[]>(() => [
  {
    key: "cookbooks",
    icon: $globals.icons.book,
    title: i18n.t("cookbook.cookbooks"),
    links: cookbookLinks.value,
  },
  {
    key: "categories",
    icon: $globals.icons.categories,
    title: i18n.t("category.categories"),
    links: categoryLinks.value,
  },
  {
    key: "tags",
    icon: $globals.icons.tags,
    title: i18n.t("tag.tags"),
    links: tagLinks.value,
  },
]);

const createLinks = computed(() => [
  {
    insertDivider: false,
    icon: $globals.icons.link,
    title: i18n.t("general.import"),
    subtitle: i18n.t("new-recipe.import-by-url"),
    to: `/g/${groupSlug.value}/r/create/url`,
    restricted: true,
    hide: false,
  },
  {
    insertDivider: false,
    icon: $globals.icons.fileImage,
    title: i18n.t("recipe.create-from-images"),
    subtitle: i18n.t("recipe.create-recipe-from-images"),
    to: `/g/${groupSlug.value}/r/create/image`,
    restricted: true,
    hide: !showImageImport.value,
  },
  {
    insertDivider: true,
    icon: $globals.icons.edit,
    title: i18n.t("general.create"),
    subtitle: i18n.t("new-recipe.create-manually"),
    to: `/g/${groupSlug.value}/r/create/new`,
    restricted: true,
    hide: false,
  },
]);

const topLinks = computed<SideBarLink[]>(() => [
  {
    icon: $globals.icons.silverwareForkKnife,
    to: `/g/${groupSlug.value}`,
    title: i18n.t("general.recipes"),
    restricted: false,
  },
  {
    icon: $globals.icons.search,
    to: `/g/${groupSlug.value}/recipes/finder`,
    title: i18n.t("recipe-finder.recipe-finder"),
    restricted: false,
  },
  {
    icon: $globals.icons.calendarMultiselect,
    title: i18n.t("meal-plan.meal-planner"),
    to: "/household/mealplan/planner/view",
    restricted: true,
  },
  {
    icon: $globals.icons.formatListCheck,
    title: i18n.t("shopping-list.shopping-lists"),
    to: "/shopping-lists",
    restricted: true,
  },
  {
    icon: $globals.icons.timelineText,
    title: i18n.t("recipe.timeline"),
    to: `/g/${groupSlug.value}/recipes/timeline`,
    restricted: true,
  },
  {
    icon: $globals.icons.book,
    to: `/g/${groupSlug.value}/cookbooks`,
    title: i18n.t("cookbook.cookbooks"),
    restricted: true,
  },
  {
    icon: $globals.icons.organizers,
    title: i18n.t("general.organizers"),
    restricted: true,
    children: [
      {
        icon: $globals.icons.categories,
        to: `/g/${groupSlug.value}/recipes/categories`,
        title: i18n.t("sidebar.categories"),
        restricted: true,
      },
      {
        icon: $globals.icons.tags,
        to: `/g/${groupSlug.value}/recipes/tags`,
        title: i18n.t("sidebar.tags"),
        restricted: true,
      },
      {
        icon: $globals.icons.potSteam,
        to: `/g/${groupSlug.value}/recipes/tools`,
        title: i18n.t("tool.tools"),
        restricted: true,
      },
    ],
  },
]);
</script>

<style scoped>
.quick-text-create-btn {
  min-width: 170px;
}

.quick-text-create-btn :deep(.v-btn__content) {
  color: rgba(var(--v-theme-on-surface), var(--v-high-emphasis-opacity));
}
</style>
