<template>
  <div>
    <RecipeMergeDialog
      v-if="isOwnGroup"
      v-model="recipeMergeDialog"
      @updated="loadRecipePage"
    />
    <RecipeOrganizerDialog
      v-if="isOwnGroup"
      v-model="recipeCategoryDialog"
      item-type="categories"
      recipe-group
      :recipe-group-section="section"
      @created-item="handleRecipeCategoryCreated"
    />
    <RecipeOrganizerDialog
      v-if="isOwnGroup"
      v-model="recipeCategoryEditDialog"
      item-type="categories"
      recipe-group
      :recipe-group-section="section"
      :edit-category="recipeCategoryEditTarget"
      @created-item="handleRecipeCategoryEdited"
    />
    <UploadedBookRenameDialog
      v-model="bookRenameDialog"
      :book="bookRenameTarget"
      @renamed="handleBookRenamed"
    />
    <UploadedBookRecipeDeleteDialog
      v-model="bookRecipeDeleteDialog"
      :book="bookRecipeDeleteTarget"
      @deleted="handleBookRecipesDeleted"
    />
    <BaseDialog
      v-model="recipeCategoryDeleteDialog"
      :title="$t('recipe.delete-recipe-category')"
      :icon="$globals.icons.delete"
      color="error"
      :loading="recipeCategoryDeleteLoading"
      :submit-text="$t('general.delete')"
      :submit-icon="$globals.icons.delete"
      can-submit
      @submit="deleteRecipeCategory"
    >
      <v-card-text>
        <p>{{ $t("recipe.delete-recipe-category-description", { category: recipeCategoryDeleteTarget?.name || "" }) }}</p>
      </v-card-text>
    </BaseDialog>
    <BaseDialog
      v-model="bulkDeleteDialog"
      :title="$t('recipe.delete-selected-recipes', { count: selectedRecipeSlugs.size })"
      color="error"
      :icon="$globals.icons.delete"
      :loading="bulkDeleteLoading"
      :submit-disabled="selectedRecipeSlugs.size === 0"
      :submit-text="$t('recipe.delete-selected-recipes', { count: selectedRecipeSlugs.size })"
      :submit-icon="$globals.icons.delete"
      can-submit
      @submit="deleteSelectedRecipes"
    >
      <v-card-text>
        <p class="mb-3">
          {{ $t("recipe.bulk-delete-confirmation", { count: selectedRecipeSlugs.size }) }}
        </p>
        <v-checkbox
          v-model="bulkDeleteShoppingLists"
          color="error"
          density="compact"
          hide-details
          :label="$t('recipe.bulk-delete-linked-shopping-lists')"
        />
        <v-list
          class="recipe-bulk-delete-preview mt-3"
          density="compact"
          border
        >
          <v-list-item
            v-for="entry in selectedRecipeEntries"
            :key="entry.slug"
            :title="entry.name"
          >
            <template #prepend>
              <v-icon color="error">
                {{ $globals.icons.delete }}
              </v-icon>
            </template>
          </v-list-item>
        </v-list>
      </v-card-text>
    </BaseDialog>
    <v-row
      v-if="!disableToolbar"
      class="align-center pb-2"
    >
      <v-icon
        v-if="title"
        size="large"
        start
      >
        {{ displayTitleIcon }}
      </v-icon>
      <span class="text-headline-small">{{ title }}</span>
      <v-spacer />
      <v-btn
        v-if="isOwnGroup"
        variant="text"
        :icon="$vuetify.display.xs"
        :to="aiCookbookRoute"
        :title="$t('cookbook.create-book-with-ai')"
      >
        <v-icon :start="!$vuetify.display.xs">
          {{ $globals.icons.book }}
        </v-icon>
        {{ $vuetify.display.xs ? null : $t("cookbook.create-book-with-ai") }}
      </v-btn>
      <v-btn
        v-if="isOwnGroup && groupByCategory"
        variant="text"
        :icon="$vuetify.display.xs"
        :title="$t('recipe.create-recipe-category')"
        @click="recipeCategoryDialog = true"
      >
        <v-icon :start="!$vuetify.display.xs">
          {{ $globals.icons.categories }}
        </v-icon>
        {{ $vuetify.display.xs ? null : $t("recipe.create-recipe-category") }}
      </v-btn>
      <v-btn
        v-if="isOwnGroup"
        variant="text"
        :icon="$vuetify.display.xs"
        :title="$t('recipe.merge-recipes')"
        @click="recipeMergeDialog = true"
      >
        <v-icon :start="!$vuetify.display.xs">
          {{ $globals.icons.merge }}
        </v-icon>
        {{ $vuetify.display.xs ? null : $t("recipe.merge-recipes") }}
      </v-btn>
      <v-btn
        :icon="$vuetify.display.xs"
        variant="text"
        :disabled="recipes.length === 0"
        @click="navigateRandom"
      >
        <v-icon :start="!$vuetify.display.xs">
          {{ $globals.icons.diceMultiple }}
        </v-icon>
        {{ $vuetify.display.xs ? null : $t("general.random") }}
      </v-btn>
      <v-menu
        v-if="!disableSort"
        offset-y
        start
      >
        <template #activator="{ props: activatorProps }">
          <v-btn
            variant="text"
            :icon="$vuetify.display.xs"
            v-bind="activatorProps"
            :loading="sortLoading"
          >
            <v-icon :start="!$vuetify.display.xs">
              {{ preferences.sortIcon }}
            </v-icon>
            {{ $vuetify.display.xs ? null : $t("general.sort") }}
          </v-btn>
        </template>
        <v-list>
          <v-list-item @click="sortRecipes(EVENTS.az)">
            <div class="d-flex align-center flex-nowrap">
              <v-icon class="mr-2" inline>
                {{ $globals.icons.orderAlphabeticalAscending }}
              </v-icon>
              <v-list-item-title>{{ $t("general.sort-alphabetically") }}</v-list-item-title>
            </div>
          </v-list-item>
          <v-list-item @click="sortRecipes(EVENTS.rating)">
            <div class="d-flex align-center flex-nowrap">
              <v-icon class="mr-2" inline>
                {{ $globals.icons.star }}
              </v-icon>
              <v-list-item-title>{{ $t("general.rating") }}</v-list-item-title>
            </div>
          </v-list-item>
          <v-list-item @click="sortRecipes(EVENTS.created)">
            <div class="d-flex align-center flex-nowrap">
              <v-icon class="mr-2" inline>
                {{ $globals.icons.newBox }}
              </v-icon>
              <v-list-item-title>{{ $t("general.created") }}</v-list-item-title>
            </div>
          </v-list-item>
          <v-list-item @click="sortRecipes(EVENTS.updated)">
            <div class="d-flex align-center flex-nowrap">
              <v-icon class="mr-2" inline>
                {{ $globals.icons.update }}
              </v-icon>
              <v-list-item-title>{{ $t("general.updated") }}</v-list-item-title>
            </div>
          </v-list-item>
          <v-list-item @click="sortRecipes(EVENTS.lastMade)">
            <div class="d-flex align-center flex-nowrap">
              <v-icon class="mr-2" inline>
                {{ $globals.icons.chefHat }}
              </v-icon>
              <v-list-item-title>{{ $t("general.last-made") }}</v-list-item-title>
            </div>
          </v-list-item>
          <v-list-item @click="sortRecipes(EVENTS.shuffle)">
            <div class="d-flex align-center flex-nowrap">
              <v-icon class="mr-2" inline>
                {{ $globals.icons.diceMultiple }}
              </v-icon>
              <v-list-item-title>{{ $t("general.random") }}</v-list-item-title>
            </div>
          </v-list-item>
        </v-list>
      </v-menu>
      <v-btn
        variant="text"
        :icon="$vuetify.display.xs"
        :color="userExperiencePreferences.showRecipeItemImages ? 'primary' : undefined"
        :title="$t('recipe.toggle-item-images')"
        :aria-label="$t('recipe.toggle-item-images')"
        @click="userExperiencePreferences.showRecipeItemImages = !userExperiencePreferences.showRecipeItemImages"
      >
        <v-icon :start="!$vuetify.display.xs">
          {{ $globals.icons.fileImage }}
        </v-icon>
        {{ $vuetify.display.xs ? null : $t("recipe.item-images") }}
      </v-btn>
      <ContextMenu
        v-if="!$vuetify.display.smAndDown"
        :items="[
          {
            title: $t('general.toggle-view'),
            icon: $globals.icons.eye,
            event: 'toggle-dense-view',
          },
        ]"
        @toggle-dense-view="toggleMobileCards()"
      />
    </v-row>
    <div
      v-if="showRecipeGroups"
      class="recipe-group-expansion-controls d-flex align-center flex-wrap ga-2 mb-2"
    >
      <v-btn
        size="small"
        variant="outlined"
        :icon="$vuetify.display.xs"
        :disabled="nestedRecipeGroupKeys.length === 0"
        :title="$t('recipe.open-subcategories')"
        :aria-label="$t('recipe.open-subcategories')"
        @click="openRecipeSubcategories"
      >
        <v-icon :start="!$vuetify.display.xs">
          {{ $globals.icons.chevronDown }}
        </v-icon>
        {{ $vuetify.display.xs ? null : $t("recipe.open-subcategories") }}
      </v-btn>
      <v-btn
        size="small"
        variant="outlined"
        :icon="$vuetify.display.xs"
        :disabled="nestedRecipeGroupKeys.length === 0"
        :title="$t('recipe.collapse-subcategories')"
        :aria-label="$t('recipe.collapse-subcategories')"
        @click="collapseRecipeSubcategories"
      >
        <v-icon :start="!$vuetify.display.xs">
          {{ $globals.icons.chevronRight }}
        </v-icon>
        {{ $vuetify.display.xs ? null : $t("recipe.collapse-subcategories") }}
      </v-btn>
      <v-btn
        size="small"
        variant="outlined"
        :icon="$vuetify.display.xs"
        :title="$t('recipe.open-all-groups')"
        :aria-label="$t('recipe.open-all-groups')"
        @click="openAllRecipeGroups"
      >
        <v-icon :start="!$vuetify.display.xs">
          {{ $globals.icons.chevronDown }}
        </v-icon>
        {{ $vuetify.display.xs ? null : $t("recipe.open-all-groups") }}
      </v-btn>
      <v-btn
        size="small"
        variant="outlined"
        :icon="$vuetify.display.xs"
        :title="$t('recipe.collapse-all-groups')"
        :aria-label="$t('recipe.collapse-all-groups')"
        @click="collapseAllRecipeGroups"
      >
        <v-icon :start="!$vuetify.display.xs">
          {{ $globals.icons.chevronRight }}
        </v-icon>
        {{ $vuetify.display.xs ? null : $t("recipe.collapse-all-groups") }}
      </v-btn>
    </div>
    <v-sheet
      v-if="bulkDeleteMode"
      class="recipe-bulk-selection-bar d-flex align-center flex-wrap ga-2 pa-2 mb-3"
      border
      rounded
    >
      <v-icon color="error">
        {{ $globals.icons.delete }}
      </v-icon>
      <strong>{{ $t("recipe.recipes-selected", { count: selectedRecipeSlugs.size }) }}</strong>
      <v-spacer />
      <v-btn
        size="small"
        variant="text"
        :disabled="allVisibleRecipesSelected"
        @click="selectAllVisibleRecipes"
      >
        {{ $t("recipe.select-all-visible-recipes") }}
      </v-btn>
      <v-btn
        size="small"
        variant="text"
        :disabled="selectedRecipeSlugs.size === 0"
        @click="clearBulkSelection"
      >
        {{ $t("general.clear-selection") }}
      </v-btn>
      <v-btn
        size="small"
        variant="text"
        @click="cancelBulkDelete"
      >
        {{ $t("general.cancel") }}
      </v-btn>
      <v-btn
        size="small"
        color="error"
        variant="flat"
        :disabled="selectedRecipeSlugs.size === 0"
        @click="openBulkDeleteDialog"
      >
        <v-icon start>
          {{ $globals.icons.delete }}
        </v-icon>
        {{ $t("recipe.delete-selected-recipes", { count: selectedRecipeSlugs.size }) }}
      </v-btn>
    </v-sheet>
    <div v-if="recipes && ready">
      <div class="mt-2">
        <template
          v-for="group in visibleRecipeGroups"
          :key="group.key"
        >
          <div
            v-if="showRecipeGroups && !group.hideHeader"
            class="recipe-book-group-row"
            :class="{ 'recipe-book-group-row--nested': group.depth > 0 }"
            :style="{ '--recipe-group-depth': group.depth }"
          >
            <button
              type="button"
              class="recipe-book-group"
              :aria-expanded="isRecipeGroupExpanded(group.key)"
              @click="toggleRecipeGroup(group.key)"
            >
              <v-icon>
                {{ isRecipeGroupExpanded(group.key) ? $globals.icons.chevronDown : $globals.icons.chevronRight }}
              </v-icon>
              <v-icon>{{ groupIcon(group) }}</v-icon>
              <strong>{{ group.title }}</strong>
              <span>{{ group.recipeCount ?? group.recipes.length }}</span>
            </button>
            <div v-if="group.bookId" class="recipe-book-group-actions">
              <v-btn
                icon
                size="small"
                variant="text"
                :title="$t('cookbook.rename-book')"
                :aria-label="$t('cookbook.rename-book')"
                @click="openBookRenameDialog(group.bookId, group.sourceName || group.title)"
              >
                <v-icon>{{ $globals.icons.edit }}</v-icon>
              </v-btn>
              <v-btn
                icon
                size="small"
                variant="text"
                color="warning"
                :title="$t('cookbook.delete-book-recipes')"
                :aria-label="$t('cookbook.delete-book-recipes')"
                @click="openBookRecipeDeleteDialog(group.bookId, group.sourceName || group.title)"
              >
                <v-icon>{{ $globals.icons.broom }}</v-icon>
              </v-btn>
            </div>
            <div v-else-if="group.categoryId" class="recipe-book-group-actions">
              <v-btn
                icon
                size="small"
                variant="text"
                :title="$t('recipe.rename-recipe-category')"
                :aria-label="$t('recipe.rename-recipe-category')"
                @click="openRecipeCategoryEditDialog(group.categoryId)"
              >
                <v-icon>{{ $globals.icons.edit }}</v-icon>
              </v-btn>
              <v-btn
                icon
                size="small"
                variant="text"
                color="error"
                :title="$t('recipe.delete-recipe-category')"
                :aria-label="$t('recipe.delete-recipe-category')"
                @click="openRecipeCategoryDeleteDialog(group.categoryId)"
              >
                <v-icon>{{ $globals.icons.delete }}</v-icon>
              </v-btn>
            </div>
          </div>
          <div
            v-if="showRecipeGroups && group.isDirectRecipesGroup"
            class="recipe-group-direct-recipes-separator"
          >
            <span>{{ group.title }}</span>
          </div>
          <v-expand-transition>
            <div v-show="!showRecipeGroups || group.hideHeader || isRecipeGroupExpanded(group.key)">
              <v-row v-if="!useMobileCards">
                <v-col
                  v-for="candidate in group.indexCandidates || []"
                  :key="`index-${candidate.id}`"
                  :sm="6"
                  :md="6"
                  :lg="4"
                  :xl="3"
                >
                  <RecipeIndexCandidateCard :candidate="candidate" />
                </v-col>
                <v-col
                  v-for="recipe in group.recipes"
                  :key="recipe.id!"
                  :sm="6"
                  :md="6"
                  :lg="4"
                  :xl="3"
                >
                  <RecipeCard
                    :name="recipe.name!"
                    :description="recipe.description!"
                    :slug="recipe.slug!"
                    :rating="recipe.rating!"
                    :image="recipe.image!"
                    :tags="recipe.tags!"
                    :categories="recipe.recipeCategory!"
                    :recipe-id="recipe.id!"
                    :extras="recipe.extras"
                    :last-made="recipe.lastMade"
                    :recipe-section="recipe.recipeSection"
                    :show-in-recipes="recipe.showInRecipes"
                    :show-in-book="recipe.showInBook"
                    :show-in-sauce="recipe.showInSauce"
                    :bulk-selection-mode="bulkDeleteMode"
                    :bulk-selected="selectedRecipeSlugs.has(recipe.slug!)"
                    @delete="$emit('delete', $event)"
                    @bulk-delete-requested="startBulkDelete"
                    @toggle-bulk-selected="toggleBulkSelected"
                    @renamed="$emit('renamed', $event)"
                    @section-updated="scheduleRecipeRefresh"
                  />
                </v-col>
              </v-row>
              <v-row
                v-else
                density="comfortable"
              >
                <v-col
                  v-for="candidate in group.indexCandidates || []"
                  :key="`index-mobile-${candidate.id}`"
                  cols="12"
                  :sm="singleColumn ? '12' : '12'"
                  :md="singleColumn ? '12' : '6'"
                  :lg="singleColumn ? '12' : '4'"
                  :xl="singleColumn ? '12' : '3'"
                >
                  <RecipeIndexCandidateCard :candidate="candidate" />
                </v-col>
                <v-col
                  v-for="recipe in group.recipes"
                  :key="recipe.id!"
                  cols="12"
                  :sm="singleColumn ? '12' : '12'"
                  :md="singleColumn ? '12' : '6'"
                  :lg="singleColumn ? '12' : '4'"
                  :xl="singleColumn ? '12' : '3'"
                >
                  <RecipeCardMobile
                    :name="recipe.name!"
                    :description="recipe.description!"
                    :slug="recipe.slug!"
                    :rating="recipe.rating!"
                    :image="recipe.image!"
                    :tags="recipe.tags!"
                    :categories="recipe.recipeCategory!"
                    :recipe-id="recipe.id!"
                    :extras="recipe.extras"
                    :last-made="recipe.lastMade"
                    :recipe-section="recipe.recipeSection"
                    :show-in-recipes="recipe.showInRecipes"
                    :show-in-book="recipe.showInBook"
                    :show-in-sauce="recipe.showInSauce"
                    :bulk-selection-mode="bulkDeleteMode"
                    :bulk-selected="selectedRecipeSlugs.has(recipe.slug!)"
                    @delete="$emit('delete', $event)"
                    @bulk-delete-requested="startBulkDelete"
                    @toggle-bulk-selected="toggleBulkSelected"
                    @renamed="$emit('renamed', $event)"
                    @section-updated="scheduleRecipeRefresh"
                  />
                </v-col>
              </v-row>
            </div>
          </v-expand-transition>
        </template>
      </div>
      <BaseListPagination
        :page="page"
        :items-per-page="perPage"
        :total-items="totalRecipes"
        @update:page="changeRecipePage"
        @update:items-per-page="changeRecipePageSize"
      />
    </div>
    <v-fade-transition>
      <AppLoader
        v-if="loading"
        :loading="loading"
      />
    </v-fade-transition>
    <AppScrollToTop />
  </div>
</template>

<script setup lang="ts">
import RecipeCard from "./RecipeCard.vue";
import RecipeCardMobile from "./RecipeCardMobile.vue";
import RecipeIndexCandidateCard from "./RecipeIndexCandidateCard.vue";
import { useLoggedInState } from "~/composables/use-logged-in-state";
import { useLazyRecipes } from "~/composables/recipes";
import type { Recipe, RecipeCategory } from "~/lib/api/types/recipe";
import { useUserExperiencePreferences, useUserSortPreferences } from "~/composables/use-users/preferences";
import type { RecipeSearchQuery } from "~/lib/api/user/recipes/recipe";
import { useUserApi } from "~/composables/api/api-client";
import type { UploadedBook, UploadedBookRecipeCandidate, UploadedBookRecipeSource } from "~/lib/api/types/uploaded-book";
import { usePersistedListPageSize } from "~/composables/use-list-pagination";
import { alert } from "~/composables/use-toast";
import { useCategoryStore } from "~/composables/store/use-category-store";
import { useLocalStorage } from "@vueuse/core";

const REPLACE_RECIPES_EVENT = "replaceRecipes";

interface Props {
  disableToolbar?: boolean;
  disableSort?: boolean;
  icon?: string | null;
  title?: string | null;
  singleColumn?: boolean;
  recipes?: Recipe[];
  query?: RecipeSearchQuery | null;
  section?: string;
  groupByBook?: boolean;
  groupByCategory?: boolean;
}
const props = withDefaults(defineProps<Props>(), {
  disableToolbar: false,
  disableSort: false,
  icon: null,
  title: null,
  singleColumn: false,
  recipes: () => [],
  query: null,
  section: "recipes",
  groupByBook: false,
  groupByCategory: false,
});

const emit = defineEmits<{
  replaceRecipes: [recipes: Recipe[]];
  appendRecipes: [recipes: Recipe[]];
  delete: [slug: string];
  renamed: [{ slug: string; name: string; recipe?: Recipe }];
}>();

const display = useDisplay();
const preferences = useUserSortPreferences();
const userExperiencePreferences = useUserExperiencePreferences();

const EVENTS = {
  az: "az",
  rating: "rating",
  created: "created",
  updated: "updated",
  lastMade: "lastMade",
  shuffle: "shuffle",
};

const { $globals } = useNuxtApp();
const { isOwnGroup, groupSlug } = useLoggedInState();
const i18n = useI18n();
const api = useUserApi();
const categoryStore = useCategoryStore();
const recipeLocationCategories = ref<RecipeCategory[]>([]);
const uploadedBooks = ref<UploadedBook[]>([]);
const expandedRecipeGroups = ref<Set<string>>(new Set());
const aiCookbookRoute = computed(() => `/g/${groupSlug.value}/cookbooks?generate=true`);
const groupByCategory = computed(() => props.groupByCategory);
const useMobileCards = computed(() => {
  return display.smAndDown.value || preferences.value.useMobileCards;
});

const displayTitleIcon = computed(() => {
  return props.icon || $globals.icons.tags;
});

const sortLoading = ref(false);
const recipeMergeDialog = ref(false);
const recipeCategoryDialog = ref(false);
const recipeCategoryEditDialog = ref(false);
const recipeCategoryEditTarget = ref<{
  id?: string | null;
  name: string;
  isRecipeGroup?: boolean | null;
  recipeGroupSection?: string | null;
  parentCategoryId?: string | null;
} | null>(null);
const recipeCategoryDeleteDialog = ref(false);
const recipeCategoryDeleteLoading = ref(false);
const recipeCategoryDeleteTarget = ref<{ id: string; name: string } | null>(null);
const bookRenameDialog = ref(false);
const bookRenameTarget = ref<{ id: string; name: string } | null>(null);
const bookRecipeDeleteDialog = ref(false);
const bookRecipeDeleteTarget = ref<{ id: string; name: string } | null>(null);
const bulkDeleteMode = ref(false);
const bulkDeleteDialog = ref(false);
const bulkDeleteLoading = ref(false);
const bulkDeleteShoppingLists = ref(true);
const selectedRecipeSlugs = ref<Set<string>>(new Set());
const selectedRecipeNames = ref<Map<string, string>>(new Map());
const randomSeed = ref(Date.now().toString());

const page = ref(1);
const perPage = usePersistedListPageSize();
const totalRecipes = ref(0);
const ready = ref(false);
const loading = ref(false);
let recipeRequestId = 0;
let organizerRefreshTimer: ReturnType<typeof setTimeout> | null = null;
let recipeRefreshTimer: ReturnType<typeof setTimeout> | null = null;

interface RecipeDisplayGroup {
  key: string;
  bookId: string | null;
  categoryId: string | null;
  title: string;
  sourceName: string | null;
  recipes: Recipe[];
  indexCandidates?: UploadedBookRecipeCandidate[];
  parentCategoryId?: string | null;
  children: RecipeDisplayGroup[];
  depth: number;
  hideHeader?: boolean;
  isDirectRecipesGroup?: boolean;
  recipeCount?: number;
}

const recipeGroupCategories = computed(() => recipeLocationCategories.value.filter(category => category.isRecipeGroup
  && (category.recipeGroupSection || "recipes") === props.section));

const recipeGroups = computed<RecipeDisplayGroup[]>(() => {
  if (!props.groupByBook && !props.groupByCategory) {
    return [{ key: "all", bookId: null, categoryId: null, title: props.title || "", sourceName: null, recipes: props.recipes, children: [], depth: 0 }];
  }

  if (props.groupByCategory && recipeGroupCategories.value.length) {
    const groups = recipeGroupCategories.value.map(category => ({
      key: `category:${category.id || category.slug}`,
      bookId: null,
      categoryId: category.id || null,
      title: i18n.t("recipe.recipes-in-category", { category: category.name }),
      sourceName: null,
      recipes: [] as Recipe[],
      parentCategoryId: category.parentCategoryId || null,
      children: [] as RecipeDisplayGroup[],
      depth: 0,
    }));
    const groupsById = new Map(groups.filter(group => group.categoryId).map(group => [group.categoryId!, group]));
    const groupsByName = new Map<string, RecipeDisplayGroup>();
    for (const category of recipeGroupCategories.value) {
      const group = category.id ? groupsById.get(category.id) : null;
      if (group) groupsByName.set(category.name.trim().toLocaleLowerCase(), group);
    }
    const categoryDepth = (group: { parentCategoryId?: string | null }) => {
      let depth = 0;
      let parentId = group.parentCategoryId || null;
      const visited = new Set<string>();
      while (parentId && !visited.has(parentId)) {
        visited.add(parentId);
        const parent = groupsById.get(parentId);
        if (!parent) break;
        depth++;
        parentId = parent.parentCategoryId || null;
      }
      return depth;
    };
    const rootGroups: RecipeDisplayGroup[] = [];
    for (const group of groups) {
      const parent = group.parentCategoryId ? groupsById.get(group.parentCategoryId) : null;
      if (parent && parent !== group) parent.children.push(group);
      else rootGroups.push(group);
    }
    const sortGroups = (items: RecipeDisplayGroup[]) => {
      items.sort((left, right) => left.title.localeCompare(right.title));
      for (const item of items) sortGroups(item.children);
    };
    sortGroups(rootGroups);
    const ungrouped: Recipe[] = [];

    for (const recipe of props.recipes) {
      const matchingGroups = (recipe.recipeCategory || [])
        .map((category) => {
          const categoryName = category.name.trim().toLocaleLowerCase();
          // A freshly-created group can briefly have a different serialized
          // id between the recipe response and the group index. The name is
          // the stable fallback during that synchronization window.
          return (category.id ? groupsById.get(category.id) : null)
            || groupsByName.get(categoryName)
            || null;
        })
        .filter((group): group is RecipeDisplayGroup => Boolean(group));
      const deepestDepth = matchingGroups.length
        ? Math.max(...matchingGroups.map(group => categoryDepth(group)))
        : -1;
      const deepestGroups = matchingGroups.filter(group => categoryDepth(group) === deepestDepth);
      if (deepestGroups.length) {
        // A recipe may intentionally remain in its old group while also being
        // moved/copied to a new group. Show it in every selected group at the
        // same depth, while still keeping a child category exclusive of its
        // parent category.
        for (const group of deepestGroups) {
          if (!group.recipes.some(item => item.id === recipe.id || item.slug === recipe.slug)) {
            group.recipes.push(recipe);
          }
        }
      }
      else {
        ungrouped.push(recipe);
      }
    }

    if (ungrouped.length) {
      rootGroups.push({
        key: "category:unassigned",
        bookId: null,
        categoryId: null,
        title: i18n.t("recipe.recipes-without-custom-category"),
        sourceName: null,
        recipes: ungrouped,
        children: [],
        depth: 0,
      });
    }
    return rootGroups;
  }

  if (!props.groupByBook) {
    return [{ key: "all", bookId: null, categoryId: null, title: props.title || "", sourceName: null, recipes: props.recipes, children: [], depth: 0 }];
  }

  const bookNames = new Map(uploadedBooks.value.map(book => [book.id, book.name]));
  const bookIndexCandidates = new Map(
    uploadedBooks.value.map(book => [book.id, bookRecipeIndexCandidates(book)]),
  );
  const groups = new Map<string, RecipeDisplayGroup>();
  const unlinked: Recipe[] = [];

  for (const recipe of props.recipes) {
    const rawBookId = recipe.extras?.uploadedBookSourceId;
    const bookId = typeof rawBookId === "string" ? rawBookId.trim() : "";
    if (!bookId) {
      unlinked.push(recipe);
      continue;
    }
    let group = groups.get(bookId);
    if (!group) {
      const storedSourceName = typeof recipe.extras?.uploadedBookSourceName === "string"
        ? recipe.extras.uploadedBookSourceName.trim()
        : "";
      const sourceName = storedSourceName || bookNames.get(bookId) || recipe.source?.split(/,\s*(?:pages?|עמ(?:וד|ודים)?)/i)[0]?.trim() || i18n.t("cookbook.cookbook");
      group = {
        key: `book:${bookId}`,
        bookId,
        categoryId: null,
        title: i18n.t("recipe.recipes-from-book", {
          book: sourceName,
        }),
        sourceName,
        recipes: [],
        indexCandidates: [],
        children: [],
        depth: 0,
      };
      groups.set(bookId, group);
    }
    group.recipes.push(recipe);
  }

  // Catalog entries are persisted in uploaded-book metadata. They remain
  // index-only records until the user imports the recipe pages, so they must
  // never be represented as fake Recipe entities.
  for (const [bookId, candidates] of bookIndexCandidates) {
    if (!candidates.length) continue;
    let group = groups.get(bookId);
    if (!group) {
      const sourceName = bookNames.get(bookId) || i18n.t("cookbook.cookbook");
      group = {
        key: `book:${bookId}`,
        bookId,
        categoryId: null,
        title: i18n.t("recipe.recipes-from-book", { book: sourceName }),
        sourceName,
        recipes: [],
        indexCandidates: [],
        children: [],
        depth: 0,
      };
      groups.set(bookId, group);
    }
    group.indexCandidates = candidates;
  }

  const result = Array.from(groups.values());
  if (unlinked.length) {
    result.push({
      key: "unlinked",
      bookId: null,
      categoryId: null,
      title: i18n.t("recipe.recipes-not-from-book"),
      sourceName: null,
      recipes: unlinked,
      children: [],
      depth: 0,
    });
  }
  return result;
});
const showRecipeGroups = computed(() => {
  return (props.groupByBook || (props.groupByCategory && recipeGroupCategories.value.length > 0))
    && recipeGroups.value.length > 0;
});
function flattenVisibleRecipeGroups(groups: RecipeDisplayGroup[], depth = 0): RecipeDisplayGroup[] {
  const visible: RecipeDisplayGroup[] = [];
  for (const group of groups) {
    const hasChildren = group.children.length > 0;
    visible.push({
      ...group,
      recipes: hasChildren ? [] : group.recipes,
      recipeCount: group.recipes.length + (group.indexCandidates?.length || 0),
      depth,
    });
    if (group.children.length && isRecipeGroupExpanded(group.key)) {
      visible.push(...flattenVisibleRecipeGroups(group.children, depth + 1));
      // Keep recipes assigned directly to a parent category after all of its children.
      if (group.recipes.length) {
        visible.push({
          ...group,
          key: `${group.key}:direct`,
          title: i18n.t("recipe.recipes-without-subcategory"),
          recipes: group.recipes,
          children: [],
          depth: depth + 1,
          hideHeader: true,
          isDirectRecipesGroup: true,
          recipeCount: group.recipes.length,
        });
      }
    }
  }
  return visible;
}
const visibleRecipeGroups = computed(() => showRecipeGroups.value
  ? flattenVisibleRecipeGroups(recipeGroups.value)
  : recipeGroups.value);
function flattenRecipeGroupKeys(groups: RecipeDisplayGroup[]): string[] {
  return groups.flatMap(group => [group.key, ...flattenRecipeGroupKeys(group.children)]);
}
const recipeGroupKeys = computed(() => flattenRecipeGroupKeys(recipeGroups.value));
function flattenNestedRecipeGroupKeys(groups: RecipeDisplayGroup[]): string[] {
  return groups.flatMap(group => [
    ...group.children.flatMap(child => [child.key, ...flattenNestedRecipeGroupKeys(child.children)]),
  ]);
}
const nestedRecipeGroupKeys = computed(() => flattenNestedRecipeGroupKeys(recipeGroups.value));
function flattenSubcategoryExpansionKeys(groups: RecipeDisplayGroup[]): string[] {
  return groups.flatMap(group => group.children.length
    ? [group.key, ...flattenRecipeGroupKeys(group.children)]
    : []);
}
const subcategoryExpansionKeys = computed(() => flattenSubcategoryExpansionKeys(recipeGroups.value));
const allVisibleRecipesSelected = computed(() => {
  return props.recipes.length > 0 && props.recipes.every(recipe => Boolean(recipe.slug) && selectedRecipeSlugs.value.has(recipe.slug!));
});
const selectedRecipeEntries = computed(() => {
  return [...selectedRecipeSlugs.value].map(slug => ({
    slug,
    name: selectedRecipeNames.value.get(slug) || slug,
  }));
});

const expandedRecipeGroupStorage = useLocalStorage<Record<string, string[]>>("recipe-group-expanded-v2", {});
const MAX_EXPANSION_STORAGE_SCOPES = 40;
const MAX_EXPANDED_GROUPS_PER_SCOPE = 250;
const expansionStorageScope = computed(() => `${groupSlug.value || "public"}:${props.section}:${props.groupByBook ? "books" : "categories"}`);
const collapseBehavior = computed(() => props.groupByBook
  ? userExperiencePreferences.value.bookGroupCollapseBehavior
  : props.section === "sauce"
    ? userExperiencePreferences.value.sauceGroupCollapseBehavior
    : userExperiencePreferences.value.recipeGroupCollapseBehavior);
let loadedExpansionScope = "";

watch(
  [expansionStorageScope, collapseBehavior],
  ([scope, behavior]) => {
    loadedExpansionScope = scope;
    if (behavior === "collapsed") {
      expandedRecipeGroups.value = new Set();
      return;
    }
    if (behavior === "expanded") {
      expandedRecipeGroups.value = new Set(recipeGroupKeys.value);
      return;
    }
    // Keep saved keys even while the async recipe/category request is still empty.
    // Filtering at that point used to erase the remembered open state on navigation.
    expandedRecipeGroups.value = new Set(expandedRecipeGroupStorage.value[scope] || []);
  },
  { immediate: true },
);

watch(
  () => recipeGroupKeys.value.join("|"),
  () => {
    if (loadedExpansionScope !== expansionStorageScope.value) return;
    if (collapseBehavior.value === "expanded") {
      expandedRecipeGroups.value = new Set(recipeGroupKeys.value);
    }
    else if (collapseBehavior.value === "collapsed") {
      expandedRecipeGroups.value = new Set();
    }
  },
);

const { fetchPage, getRandom } = useLazyRecipes(isOwnGroup.value ? null : groupSlug.value);
const router = useRouter();

const queryFilter = computed(() => {
  const baseFilter = props.query?.queryFilter?.trim();
  const membershipField = props.section === "book"
    ? "show_in_book"
    : props.section === "sauce"
      ? "show_in_sauce"
      : "show_in_recipes";
  const sectionFilter = `${membershipField} = true`;
  return baseFilter ? `(${baseFilter}) AND (${sectionFilter})` : sectionFilter;

  // TODO: allow user to filter out null values when ordering by a value that may be null (such as lastMade)

  // const orderBy = props.query?.orderBy || preferences.value.orderBy;
  // const orderByFilter = preferences.value.filterNull && orderBy ? `${orderBy} IS NOT NULL` : null;

  // if (props.query.queryFilter && orderByFilter) {
  //   return `(${props.query.queryFilter}) AND ${orderByFilter}`;
  // } else if (props.query.queryFilter) {
  //   return props.query.queryFilter;
  // } else {
  //   return orderByFilter;
  // }
});

async function fetchRecipes() {
  const orderDir = props.query?.orderDirection || preferences.value.orderDirection;
  const orderByNullPosition = props.query?.orderByNullPosition || orderDir === "asc" ? "first" : "last";
  const orderBy = props.query?.orderBy || preferences.value.orderBy;
  const localQuery = { ...props.query };
  if (orderBy === "random") {
    localQuery._searchSeed = randomSeed.value;
  }
  return await fetchPage(
    page.value,
    perPage.value,
    orderBy,
    orderDir,
    orderByNullPosition,
    localQuery,
    // we use a computed queryFilter to filter out recipes that have a null value for the property we're sorting by
    queryFilter.value,
  );
}

onMounted(async () => {
  if (import.meta.client && isOwnGroup.value) {
    window.addEventListener("mealie:recipes-updated", scheduleRecipeRefresh);
  }
  if (import.meta.client && isOwnGroup.value && props.groupByCategory) {
    window.addEventListener("mealie:organizers-updated", scheduleOrganizerRefresh);
  }
  if (isOwnGroup.value && props.groupByBook) {
    void loadUploadedBooks();
  }
  if (isOwnGroup.value && props.groupByCategory) {
    await loadRecipeGroupCategories();
  }
  loading.value = true;
  try {
    await initRecipes();
  }
  catch (error) {
    console.error("Failed to load recipe cards", error);
    emit(REPLACE_RECIPES_EVENT, []);
  }
  finally {
    ready.value = true;
    loading.value = false;
  }
});

// The auth state can finish hydrating after this component mounts. In that
// case the initial request is public and the private recipe-group index is
// never loaded unless we react to the transition explicitly.
watch(isOwnGroup, async (own) => {
  if (!own) return;
  if (import.meta.client) {
    window.addEventListener("mealie:recipes-updated", scheduleRecipeRefresh);
  }
  if (!props.groupByCategory) return;
  if (import.meta.client) {
    window.addEventListener("mealie:organizers-updated", scheduleOrganizerRefresh);
  }
  await loadRecipeGroupCategories();
  await loadRecipePage();
});

onBeforeUnmount(() => {
  if (organizerRefreshTimer) {
    clearTimeout(organizerRefreshTimer);
    organizerRefreshTimer = null;
  }
  if (recipeRefreshTimer) {
    clearTimeout(recipeRefreshTimer);
    recipeRefreshTimer = null;
  }
  if (import.meta.client) {
    window.removeEventListener("mealie:recipes-updated", scheduleRecipeRefresh);
    window.removeEventListener("mealie:organizers-updated", scheduleOrganizerRefresh);
  }
});

async function loadRecipeGroupCategories() {
  const { data, error } = await api.categories.getRecipeGroups();
  if (!error && data?.length) {
    recipeLocationCategories.value = data;
    mergeRecipeGroupCategoriesFromRecipes();
    return;
  }

  // Keep the category view working with older API images that do not yet
  // expose /categories/recipe-groups. The regular categories endpoint still
  // contains the recipe-group metadata and is a safe compatibility fallback.
  const { data: allCategories } = await api.categories.getAll(1, -1);
  const recipeGroups = (allCategories?.items || []).filter(category => category.isRecipeGroup);
  if (recipeGroups.length) {
    recipeLocationCategories.value = recipeGroups;
    mergeRecipeGroupCategoriesFromRecipes();
    return;
  }

  await categoryStore.actions.refresh();
  recipeLocationCategories.value = [...categoryStore.store.value];
  mergeRecipeGroupCategoriesFromRecipes();
}

watch(
  () => props.recipes,
  (recipes) => {
    if (props.groupByCategory) mergeRecipeGroupCategoriesFromRecipes(recipes);
  },
);

function mergeRecipeGroupCategoriesFromRecipes(recipes: Recipe[] = props.recipes) {
  if (!props.groupByCategory) return;

  const categoriesById = new Map(
    recipeLocationCategories.value
      .filter(category => category.id)
      .map(category => [category.id!, category]),
  );
  for (const recipe of recipes) {
    for (const category of recipe.recipeCategory || []) {
      if (!category.id || !category.isRecipeGroup) continue;
      if ((category.recipeGroupSection || "recipes") !== props.section) continue;
      if (!categoriesById.has(category.id)) categoriesById.set(category.id, category);
    }
  }
  recipeLocationCategories.value = [...categoriesById.values()];
}

function scheduleOrganizerRefresh() {
  if (!import.meta.client || !isOwnGroup.value || !props.groupByCategory) return;
  if (organizerRefreshTimer) clearTimeout(organizerRefreshTimer);
  organizerRefreshTimer = setTimeout(() => {
    organizerRefreshTimer = null;
    void (async () => {
      await loadRecipeGroupCategories();
      await loadRecipePage();
    })();
  }, 0);
}

function scheduleRecipeRefresh() {
  if (!import.meta.client || !isOwnGroup.value) return;
  if (recipeRefreshTimer) clearTimeout(recipeRefreshTimer);
  recipeRefreshTimer = setTimeout(() => {
    recipeRefreshTimer = null;
    void loadRecipePage();
  }, 0);
}

async function loadUploadedBooks() {
  try {
    const { data } = await api.uploadedBooks.getAll();
    uploadedBooks.value = data || [];
  }
  catch (error) {
    console.error("Failed to load uploaded books for recipe grouping", error);
    uploadedBooks.value = [];
  }
}

function isRecipeGroupExpanded(key: string) {
  return expandedRecipeGroups.value.has(key);
}

function rememberRecipeGroupExpansion(next: Set<string>) {
  if (collapseBehavior.value === "remember") {
    const scope = expansionStorageScope.value;
    const entries = Object.entries(expandedRecipeGroupStorage.value)
      .filter(([storedScope]) => storedScope !== scope);
    entries.push([scope, [...next].slice(0, MAX_EXPANDED_GROUPS_PER_SCOPE)]);
    expandedRecipeGroupStorage.value = Object.fromEntries(entries.slice(-MAX_EXPANSION_STORAGE_SCOPES));
  }
}

function setExpandedRecipeGroups(keys: Iterable<string>) {
  const validKeys = new Set(recipeGroupKeys.value);
  const next = new Set([...keys].filter(key => validKeys.has(key)));
  expandedRecipeGroups.value = next;
  rememberRecipeGroupExpansion(next);
}

function toggleRecipeGroup(key: string) {
  const next = new Set(expandedRecipeGroups.value);
  if (next.has(key)) next.delete(key);
  else next.add(key);
  setExpandedRecipeGroups(next);
}

function openRecipeSubcategories() {
  setExpandedRecipeGroups(new Set([...expandedRecipeGroups.value, ...subcategoryExpansionKeys.value]));
}

function collapseRecipeSubcategories() {
  const nestedKeys = new Set(nestedRecipeGroupKeys.value);
  setExpandedRecipeGroups([...expandedRecipeGroups.value].filter(key => !nestedKeys.has(key)));
}

function openAllRecipeGroups() {
  setExpandedRecipeGroups(recipeGroupKeys.value);
}

function collapseAllRecipeGroups() {
  setExpandedRecipeGroups([]);
}

function groupIcon(group: RecipeDisplayGroup) {
  if (group.bookId) return $globals.icons.book;
  if (group.categoryId) return $globals.icons.categories;
  return $globals.icons.silverwareForkKnife;
}

function bookRecipeIndexCandidates(book: UploadedBook): UploadedBookRecipeCandidate[] {
  const raw = book.bookMetadata?.recipe_catalog_candidates;
  if (!Array.isArray(raw)) return [];

  const optionalPage = (value: unknown) => {
    const page = Number(value);
    return Number.isFinite(page) && page >= 1 ? Math.floor(page) : null;
  };

  return raw
    .map((candidate) => {
      const value = candidate as unknown as Record<string, unknown>;
      const id = String(value.id || "").trim();
      const title = String(value.title || "").trim();
      const importedRecipeSlug = String(value.imported_recipe_slug || value.importedRecipeSlug || "").trim();
      if (!id || !title || importedRecipeSlug) return null;
      return {
        id,
        title,
        sourceTitle: String(value.source_title || value.sourceTitle || title),
        chapter: value.chapter ? String(value.chapter) : null,
        source: value.source === "internet" ? "internet" : "book",
        sourceUrl: String(value.source_url || value.sourceUrl || "").trim() || null,
        pageStart: optionalPage(value.page_start ?? value.pageStart),
        pageEnd: optionalPage(value.page_end ?? value.pageEnd),
        reason: value.reason ? String(value.reason) : null,
        importedRecipeSlug: null,
      } satisfies UploadedBookRecipeCandidate;
    })
    .filter((candidate): candidate is UploadedBookRecipeCandidate => Boolean(candidate));
}

async function handleRecipeCategoryCreated() {
  await loadRecipeGroupCategories();
  window.dispatchEvent(new CustomEvent("mealie:organizers-updated"));
}

function openRecipeCategoryEditDialog(categoryId: string) {
  recipeCategoryEditTarget.value = recipeGroupCategories.value.find(category => category.id === categoryId) || null;
  recipeCategoryEditDialog.value = Boolean(recipeCategoryEditTarget.value);
}

function openRecipeCategoryDeleteDialog(categoryId: string) {
  const category = recipeGroupCategories.value.find(item => item.id === categoryId);
  if (!category?.id) return;
  recipeCategoryDeleteTarget.value = { id: category.id, name: category.name };
  recipeCategoryDeleteDialog.value = true;
}

async function deleteRecipeCategory() {
  const target = recipeCategoryDeleteTarget.value;
  if (!target || recipeCategoryDeleteLoading.value) return;
  recipeCategoryDeleteLoading.value = true;
  try {
    const { error } = await api.categories.deleteOne(target.id);
    if (error) {
      alert.error(i18n.t("recipe.delete-recipe-category-failed"));
      return;
    }
    recipeCategoryDeleteDialog.value = false;
    recipeCategoryDeleteTarget.value = null;
    await loadRecipeGroupCategories();
    window.dispatchEvent(new CustomEvent("mealie:organizers-updated"));
    await loadRecipePage();
    alert.success(i18n.t("recipe.delete-recipe-category-success"));
  }
  finally {
    recipeCategoryDeleteLoading.value = false;
  }
}

async function handleRecipeCategoryEdited() {
  recipeCategoryEditTarget.value = null;
  await loadRecipeGroupCategories();
  window.dispatchEvent(new CustomEvent("mealie:organizers-updated"));
}

function uploadedBookById(bookId: string) {
  return uploadedBooks.value.find(book => book.id === bookId) || null;
}

function openBookRenameDialog(bookId: string, sourceName: string) {
  const book = uploadedBookById(bookId);
  bookRenameTarget.value = book || { id: bookId, name: sourceName };
  bookRenameDialog.value = true;
}

function openBookRecipeDeleteDialog(bookId: string, fallbackName: string) {
  bookRecipeDeleteTarget.value = uploadedBookById(bookId) || { id: bookId, name: fallbackName };
  bookRecipeDeleteDialog.value = true;
}

function handleBookRenamed(book: UploadedBookRecipeSource) {
  const index = uploadedBooks.value.findIndex(item => item.id === book.id);
  if (index >= 0) uploadedBooks.value[index].name = book.name;
  bookRenameTarget.value = null;
  void loadRecipePage();
}

async function handleBookRecipesDeleted(bookId: string, _deletedCount: number, remainingCount: number) {
  const book = uploadedBookById(bookId);
  if (book) book.extractionRecipesCreated = remainingCount;
  bookRecipeDeleteTarget.value = null;
  window.dispatchEvent(new CustomEvent("mealie:organizers-updated"));
  await loadRecipePage();
}

function setBulkSelected(slug: string, selected: boolean) {
  const nextSlugs = new Set(selectedRecipeSlugs.value);
  const nextNames = new Map(selectedRecipeNames.value);
  if (selected) {
    nextSlugs.add(slug);
    const recipe = props.recipes.find(item => item.slug === slug);
    nextNames.set(slug, recipe?.name || slug);
  }
  else {
    nextSlugs.delete(slug);
    nextNames.delete(slug);
  }
  selectedRecipeSlugs.value = nextSlugs;
  selectedRecipeNames.value = nextNames;
}

function startBulkDelete(slug: string) {
  bulkDeleteMode.value = true;
  setBulkSelected(slug, true);
}

function toggleBulkSelected(slug: string) {
  setBulkSelected(slug, !selectedRecipeSlugs.value.has(slug));
}

function selectAllVisibleRecipes() {
  const nextSlugs = new Set(selectedRecipeSlugs.value);
  const nextNames = new Map(selectedRecipeNames.value);
  for (const recipe of props.recipes) {
    if (!recipe.slug) continue;
    nextSlugs.add(recipe.slug);
    nextNames.set(recipe.slug, recipe.name || recipe.slug);
  }
  selectedRecipeSlugs.value = nextSlugs;
  selectedRecipeNames.value = nextNames;
}

function clearBulkSelection() {
  selectedRecipeSlugs.value = new Set();
  selectedRecipeNames.value = new Map();
}

function cancelBulkDelete() {
  bulkDeleteDialog.value = false;
  bulkDeleteMode.value = false;
  bulkDeleteShoppingLists.value = true;
  clearBulkSelection();
}

function openBulkDeleteDialog() {
  if (!selectedRecipeSlugs.value.size) return;
  bulkDeleteShoppingLists.value = true;
  bulkDeleteDialog.value = true;
}

async function deleteSelectedRecipes() {
  if (!selectedRecipeSlugs.value.size || bulkDeleteLoading.value) return;

  bulkDeleteLoading.value = true;
  const slugs = [...selectedRecipeSlugs.value];
  try {
    const { error } = await api.bulk.bulkDelete({
      recipes: slugs,
      deleteShoppingLists: bulkDeleteShoppingLists.value,
    });
    if (error) {
      alert.error(i18n.t("recipe.bulk-delete-failed"));
      return;
    }

    const remainingCount = Math.max(0, totalRecipes.value - slugs.length);
    page.value = Math.min(page.value, Math.max(1, Math.ceil(remainingCount / perPage.value)));
    cancelBulkDelete();
    window.dispatchEvent(new CustomEvent("mealie:organizers-updated"));
    await loadRecipePage();
    alert.success(i18n.t("recipe.bulk-delete-success", { count: slugs.length }));
  }
  finally {
    bulkDeleteLoading.value = false;
  }
}

let lastQuery: string | undefined = JSON.stringify(props.query);
watch(
  () => props.query,
  async (newValue: RecipeSearchQuery | undefined | null) => {
    const newValueString = JSON.stringify(newValue);
    if (lastQuery !== newValueString) {
      lastQuery = newValueString;
      ready.value = false;
      try {
        await initRecipes();
      }
      catch (error) {
        console.error("Failed to refresh recipe cards", error);
        emit(REPLACE_RECIPES_EVENT, []);
      }
      finally {
        ready.value = true;
      }
    }
  },
);

async function initRecipes() {
  cancelBulkDelete();
  if (preferences.value.orderBy === "random") {
    randomSeed.value = Date.now().toString();
  }
  page.value = 1;
  await loadRecipePage();
}

async function loadRecipePage() {
  const requestId = ++recipeRequestId;
  loading.value = true;
  try {
    const result = await fetchRecipes();
    if (requestId !== recipeRequestId) return;
    totalRecipes.value = result?.total ?? 0;
    const items = result?.items ?? [];
    mergeRecipeGroupCategoriesFromRecipes(items);
    emit(REPLACE_RECIPES_EVENT, items);
  }
  finally {
    if (requestId === recipeRequestId) {
      loading.value = false;
    }
  }
}

async function changeRecipePage(nextPage: number) {
  if (nextPage === page.value || loading.value) return;
  page.value = nextPage;
  await loadRecipePage();
}

async function changeRecipePageSize(nextPageSize: number) {
  if (nextPageSize === perPage.value || loading.value) return;
  perPage.value = nextPageSize;
  page.value = 1;
  await loadRecipePage();
}

async function sortRecipes(sortType: string) {
  if (sortLoading.value || loading.value) {
    return;
  }

  function setter(
    orderBy: string,
    ascIcon: string,
    descIcon: string,
    defaultOrderDirection = "asc",
    filterNull = false,
  ) {
    if (preferences.value.orderBy !== orderBy) {
      preferences.value.orderBy = orderBy;
      preferences.value.orderDirection = defaultOrderDirection;
      preferences.value.filterNull = filterNull;
    }
    else {
      preferences.value.orderDirection = preferences.value.orderDirection === "asc" ? "desc" : "asc";
    }
    preferences.value.sortIcon = preferences.value.orderDirection === "asc" ? ascIcon : descIcon;
  }

  switch (sortType) {
    case EVENTS.az:
      setter(
        "name",
        $globals.icons.sortAlphabeticalAscending,
        $globals.icons.sortAlphabeticalDescending,
        "asc",
        false,
      );
      break;
    case EVENTS.rating:
      setter("rating", $globals.icons.sortAscending, $globals.icons.sortDescending, "desc", true);
      break;
    case EVENTS.created:
      setter(
        "created_at",
        $globals.icons.sortCalendarAscending,
        $globals.icons.sortCalendarDescending,
        "desc",
        false,
      );
      break;
    case EVENTS.updated:
      setter("updated_at", $globals.icons.sortClockAscending, $globals.icons.sortClockDescending, "desc", false);
      break;
    case EVENTS.lastMade:
      setter(
        "last_made",
        $globals.icons.sortCalendarAscending,
        $globals.icons.sortCalendarDescending,
        "desc",
        true,
      );
      break;
    case EVENTS.shuffle:
      setter(
        "random",
        $globals.icons.diceMultiple,
        $globals.icons.diceMultiple, // icon in asc and desc is the same for random
      );
      // We update the seed value to have a different order
      randomSeed.value = Date.now().toString();
      break;
    default:
      console.log("Unknown Event", sortType);
      return;
  }

  page.value = 1;

  sortLoading.value = true;
  await loadRecipePage();
  sortLoading.value = false;
}

async function navigateRandom() {
  const recipe = await getRandom(props.query, queryFilter.value);
  if (!recipe?.slug) {
    return;
  }

  router.push(`/g/${groupSlug.value}/r/${recipe.slug}`);
}

function toggleMobileCards() {
  preferences.value.useMobileCards = !preferences.value.useMobileCards;
}
</script>

<style scoped>
.transparent {
  opacity: 1;
}

.recipe-book-group-row {
  align-items: center;
  background: rgb(var(--v-theme-surface));
  border-block: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  display: flex;
  margin: 12px 0 4px;
  min-height: 44px;
  width: 100%;
}

.recipe-book-group-row--nested {
  border-block-start: 0;
  margin-block-start: 0;
  margin-inline-start: calc(var(--recipe-group-depth, 0) * 24px);
  width: calc(100% - (var(--recipe-group-depth, 0) * 24px));
}

.recipe-book-group {
  align-items: center;
  background: transparent;
  border: 0;
  color: inherit;
  cursor: pointer;
  display: flex;
  flex: 1 1 auto;
  gap: 8px;
  min-height: 44px;
  padding: 8px 4px;
  text-align: start;
  width: auto;
}

.recipe-book-group:hover,
.recipe-book-group:focus-visible {
  background: rgba(var(--v-theme-primary), 0.06);
}

.recipe-book-group span {
  color: rgb(var(--v-theme-on-surface-variant));
  margin-inline-start: auto;
}

.recipe-book-group-actions {
  align-items: center;
  display: flex;
  flex: 0 0 auto;
  padding-inline: 2px;
}

.recipe-group-expansion-controls {
  border-block-start: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  padding-block-start: 8px;
}

.recipe-group-direct-recipes-separator {
  align-items: center;
  color: rgba(var(--v-theme-on-surface), 0.58);
  display: flex;
  font-size: 0.82rem;
  gap: 12px;
  margin: 10px 0 4px;
}

.recipe-group-direct-recipes-separator::before,
.recipe-group-direct-recipes-separator::after {
  background: rgba(var(--v-theme-on-surface), 0.16);
  content: "";
  flex: 1 1 auto;
  height: 1px;
}

.recipe-bulk-selection-bar {
  position: sticky;
  top: 8px;
  z-index: 9;
}

.recipe-bulk-delete-preview {
  max-height: min(320px, 45vh);
  overflow-y: auto;
}
</style>
