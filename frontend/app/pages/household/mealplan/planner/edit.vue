<template>
  <div>
    <!-- Create Meal Dialog -->
    <BaseDialog
      v-model="state.dialog"
      :title="newMeal.existing ? $t('meal-plan.update-this-meal-plan') : $t('meal-plan.create-a-new-meal-plan')"
      :submit-text="newMeal.existing ? $t('general.update') : $t('general.create')"
      color="primary"
      :icon="$globals.icons.foods"
      width="720"
      max-width="96vw"
      keep-open
      :loading="dialog.loading"
      :submit-disabled="isCreateDisabled"
      can-submit
      @submit="submitMealPlan"
      @close="resetDialog()"
    >
      <v-card-text class="pb-2">
        <v-date-picker
          v-model="newMeal.date"
          class="mx-auto"
          hide-header
          show-adjacent-months
          color="primary"
          :first-day-of-week="firstDayOfWeek"
          :local="$i18n.locale"
        />
        <v-card-text class="pb-0">
          <v-select
            v-model="newMeal.entryType"
            :return-object="false"
            :items="planTypeOptions"
            :label="$t('recipe.entry-type')"
            item-title="text"
            item-value="value"
          />
          <template v-if="!dialog.note">
            <v-row dense>
              <v-col cols="12" sm="6">
                <v-autocomplete
                  v-model="selectedMealCategorySlugs"
                  :items="mealPlanCategories"
                  :label="$t('category.categories')"
                  :prepend-inner-icon="$globals.icons.categories"
                  :custom-filter="normalizeFilter"
                  item-title="name"
                  item-value="slug"
                  multiple
                  chips
                  closable-chips
                  clearable
                  hide-details
                  variant="outlined"
                  density="comfortable"
                />
              </v-col>
              <v-col cols="12" sm="6">
                <v-autocomplete
                  v-model="selectedMealTagSlugs"
                  :items="mealPlanTags"
                  :label="$t('tag.tags')"
                  :prepend-inner-icon="$globals.icons.tags"
                  :custom-filter="normalizeFilter"
                  item-title="name"
                  item-value="slug"
                  multiple
                  chips
                  closable-chips
                  clearable
                  hide-details
                  variant="outlined"
                  density="comfortable"
                />
              </v-col>
            </v-row>
            <v-autocomplete
              v-if="newMeal.existing"
              v-model="newMeal.recipeId"
              v-model:search="search.query.value"
              :label="$t('meal-plan.meal-recipe')"
              :items="mealPlanRecipeOptions"
              :custom-filter="normalizeFilter"
              :loading="search.loading.value"
              :prepend-inner-icon="$globals.icons.search"
              :no-data-text="$t('search.no-results')"
              clearable
              item-title="name"
              item-value="id"
              :return-object="false"
              :rules="[requiredRule]"
              @update:model-value="rememberSingleMealRecipe"
            />
            <v-autocomplete
              v-else
              v-model="selectedMealRecipeIds"
              v-model:search="search.query.value"
              :label="$t('meal-plan.meal-recipe')"
              :items="mealPlanRecipeOptions"
              :custom-filter="normalizeFilter"
              :loading="search.loading.value"
              :prepend-inner-icon="$globals.icons.search"
              :no-data-text="$t('search.no-results')"
              clearable
              multiple
              chips
              closable-chips
              hide-selected
              item-title="name"
              item-value="id"
              :return-object="false"
              :rules="[requiredRule]"
              @update:model-value="rememberSelectedMealRecipes"
            />
          </template>
          <template v-else>
            <v-text-field v-model="newMeal.title" :rules="[requiredRule]" :label="$t('meal-plan.meal-title')" />
            <v-textarea v-model="newMeal.text" rows="2" :label="$t('meal-plan.meal-note')" />
          </template>
        </v-card-text>
        <v-card-actions class="py-0 px-4">
          <v-switch v-model="dialog.note" class="mt-n3 mb-n4" :label="$t('meal-plan.note-only')" />
        </v-card-actions>
      </v-card-text>
    </BaseDialog>
    <v-row>
      <v-col
        v-for="(plan, index) in mealplans"
        :key="index"
        cols="12"
        sm="12"
        md="6"
        lg="4"
        xl="3"
        xxl="2"
        class="col-borders my-1 d-flex flex-column"
      >
        <v-card
          class="mb-2 border-left-primary rounded-sm pa-2"
          :class="{ 'meal-plan-today-toggle': isToday(plan.date) }"
          @click="toggleTodayEdit(plan.date)"
        >
          <p class="pl-2 mb-1" :class="{ 'text-primary': isToday(plan.date) }">
            {{ $d(plan.date, "short") }}
          </p>
        </v-card>
        <VueDraggable
          v-model="mealplansByDate[plan.date.toString()]"
          tag="div"
          handle=".handle"
          :delay="250"
          :delay-on-touch-only="true"
          group="meals"
          :data-index="index"
          :data-box="plan.date"
          style="min-height: 150px"
          @end="onMoveCallback"
        >
          <v-card
            v-for="mealplan in mealplansByDate[plan.date.toString()]"
            :key="mealplan.id"
            class="my-1"
            :class="{ handle: $vuetify.display.smAndUp }"
          >
            <v-list-item lines="three" @click="editMeal(mealplan)">
              <template #prepend>
                <v-avatar>
                  <RecipeCardImage
                    v-if="mealplan.recipe"
                    :recipe-id="mealplan.recipe.id!"
                    tiny
                    icon-size="25"
                    :slug="mealplan.recipe ? mealplan.recipe.slug : ''"
                  />
                  <v-icon v-else>
                    {{ $globals.icons.primary }}
                  </v-icon>
                </v-avatar>
              </template>
              <v-list-item-title class="mb-1">
                {{ mealplan.recipe ? mealplan.recipe.name : mealplan.title }}
              </v-list-item-title>
              <v-list-item-subtitle style="min-height: 16px">
                {{ mealplan.recipe ? mealplan.recipe.description + " " : mealplan.text }}
              </v-list-item-subtitle>
            </v-list-item>
            <v-divider class="mx-2" />
            <div class="py-2 px-2 d-flex" style="align-items: center">
              <v-btn size="small" icon variant="text" :class="{ handle: !$vuetify.display.smAndUp }">
                <v-icon>
                  {{ $globals.icons.arrowUpDown }}
                </v-icon>
              </v-btn>
              <v-menu offset-y>
                <template #activator="{ props: menuProps }">
                  <v-chip
                    v-bind="menuProps"
                    label
                    variant="elevated"
                    size="small"
                    color="accent"
                    @click.prevent
                  >
                    <v-icon start>
                      {{ $globals.icons.tags }}
                    </v-icon>
                    {{ getEntryTypeText(mealplan.entryType!) }}
                  </v-chip>
                </template>
                <v-list>
                  <v-list-item
                    v-for="mealType in planTypeOptions"
                    :key="mealType.value"
                    @click="actions.setType(mealplan, mealType.value)"
                  >
                    <v-list-item-title> {{ mealType.text }} </v-list-item-title>
                  </v-list-item>
                </v-list>
              </v-menu>
              <v-btn class="ml-auto" size="small" variant="text" icon @click="actions.deleteOne(mealplan.id)">
                <v-icon>{{ $globals.icons.delete }}</v-icon>
              </v-btn>
            </div>
          </v-card>
        </VueDraggable>
        <!-- Day Column Actions -->
        <div class="d-flex justify-end mt-auto">
          <BaseButtonGroup
            :buttons="[
              {
                icon: $globals.icons.diceMultiple,
                text: $t('meal-plan.random-meal'),
                event: 'random',
                children: [
                  {
                    icon: $globals.icons.diceMultiple,
                    text: $t('meal-plan.breakfast'),
                    event: 'randomBreakfast',
                  },
                  {
                    icon: $globals.icons.diceMultiple,
                    text: $t('meal-plan.lunch'),
                    event: 'randomLunch',
                  },
                  {
                    icon: $globals.icons.diceMultiple,
                    text: $t('meal-plan.side'),
                    event: 'randomSide',
                  },
                  {
                    icon: $globals.icons.diceMultiple,
                    text: $t('meal-plan.snack'),
                    event: 'randomSnack',
                  },
                  {
                    icon: $globals.icons.diceMultiple,
                    text: $t('meal-plan.drink'),
                    event: 'randomDrink',
                  },
                  {
                    icon: $globals.icons.diceMultiple,
                    text: $t('meal-plan.dessert'),
                    event: 'randomDessert',
                  },
                ],
              },
              {
                icon: $globals.icons.potSteam,
                text: $t('meal-plan.random-dinner'),
                event: 'randomDinner',
              },
              {
                icon: $globals.icons.bowlMixOutline,
                text: $t('meal-plan.random-side'),
                event: 'randomSide',
              },
              {
                icon: $globals.icons.createAlt,
                text: $t('general.new'),
                event: 'create',
              },
            ]"
            @create="openDialog(plan.date)"
            @random-breakfast="randomMeal(plan.date, 'breakfast')"
            @random-lunch="randomMeal(plan.date, 'lunch')"
            @random-dinner="randomMeal(plan.date, 'dinner')"
            @random-side="randomMeal(plan.date, 'side')"
            @random-snack="randomMeal(plan.date, 'snack')"
            @random-drink="randomMeal(plan.date, 'drink')"
            @random-dessert="randomMeal(plan.date, 'dessert')"
          />
        </div>
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import { format, isSameDay } from "date-fns";
import type { SortableEvent } from "sortablejs";
import { VueDraggable } from "vue-draggable-plus";
import type { MealsByDate } from "./view.vue";
import type { useMealplans } from "~/composables/use-group-mealplan";
import { usePlanTypeOptions, getEntryTypeText } from "~/composables/use-group-mealplan";
import RecipeCardImage from "~/components/Domain/Recipe/RecipeCardImage.vue";
import type { PlanEntryType, UpdatePlanEntry } from "~/lib/api/types/meal-plan";
import type { Recipe } from "~/lib/api/types/recipe";
import { useUserApi } from "~/composables/api";
import { useHouseholdSelf } from "~/composables/use-households";
import { normalizeFilter } from "~/composables/use-utils";
import { useRecipeSearch } from "~/composables/recipes/use-recipe-search";
import { useCategoryStore, useTagStore } from "~/composables/store";
import { alert } from "~/composables/use-toast";

const props = defineProps<{
  mealplans: MealsByDate[];
  actions: ReturnType<typeof useMealplans>["actions"];
}>();

const api = useUserApi();
const auth = useMealieAuth();
const route = useRoute();
const router = useRouter();
const i18n = useI18n();
const { household } = useHouseholdSelf();
const requiredRule = (value: any) => !!value || "Required.";

const state = ref({
  dialog: false,
});

const firstDayOfWeek = computed(() => {
  return household.value?.preferences?.firstDayOfWeek || 0;
});

// Local mutable meals object
const mealplansByDate = reactive<{ [date: string]: UpdatePlanEntry[] }>({});
watch(
  () => props.mealplans,
  (plans) => {
    for (const plan of plans) {
      mealplansByDate[plan.date.toString()] = plan.meals ? [...plan.meals] : [];
    }
    // Remove any dates that no longer exist
    Object.keys(mealplansByDate).forEach((date) => {
      if (!plans.find(p => p.date.toString() === date)) {
        mealplansByDate[date] = [];
      }
    });
  },
  { immediate: true, deep: true },
);

function onMoveCallback(evt: SortableEvent) {
  const supportedEvents = ["drop", "touchend"];

  // Adapted From https://github.com/SortableJS/Vue.Draggable/issues/1029
  const ogEvent: DragEvent = (evt as any).originalEvent;

  if (ogEvent && ogEvent.type in supportedEvents) {
    // The drop was cancelled, unsure if anything needs to be done?
    console.log("Cancel Move Event");
  }
  else {
    // A Meal was moved, set the new date value and make an update request and refresh the meals
    const fromMealsByIndex = parseInt(evt.from.getAttribute("data-index") ?? "");
    const toMealsByIndex = parseInt(evt.to.getAttribute("data-index") ?? "");

    if (!isNaN(fromMealsByIndex) && !isNaN(toMealsByIndex)) {
      const destDate = props.mealplans[toMealsByIndex].date;
      const mealData = mealplansByDate[destDate.toString()][evt.newIndex as number];

      mealData.date = format(destDate, "yyyy-MM-dd");

      props.actions.updateOne(mealData);
    }
  }
}

// =====================================================
// New Meal Dialog

const dialog = reactive({
  loading: false,
  error: false,
  note: false,
});

const selectedMealRecipeIds = ref<string[]>([]);
const selectedMealRecipeCache = ref<Record<string, Recipe>>({});
const selectedMealCategorySlugs = ref<string[]>([]);
const selectedMealTagSlugs = ref<string[]>([]);

watch(dialog, () => {
  if (dialog.note) {
    newMeal.recipeId = undefined;
    selectedMealRecipeIds.value = [];
    selectedMealRecipeCache.value = {};
  }
});

const newMeal = reactive({
  date: new Date(Date.now() - new Date().getTimezoneOffset() * 60000),
  title: "",
  text: "",
  recipeId: undefined as string | undefined,
  entryType: "dinner" as PlanEntryType,
  existing: false,
  id: 0,
  groupId: "",
  userId: auth.user.value?.id || "",
});

const newMealDateString = computed(() => {
  return format(newMeal.date, "yyyy-MM-dd");
});

const isCreateDisabled = computed(() => {
  if (dialog.note) {
    return !newMeal.title.trim();
  }
  return newMeal.existing ? !newMeal.recipeId : !selectedMealRecipeIds.value.length;
});

async function submitMealPlan() {
  if (dialog.loading || isCreateDisabled.value) {
    return;
  }

  dialog.loading = true;
  try {
    if (newMeal.existing) {
      await props.actions.updateOne({ ...newMeal, date: newMealDateString.value });
    }
    else if (dialog.note) {
      const { error } = await api.mealplans.createOne({
        date: newMealDateString.value,
        entryType: newMeal.entryType,
        title: newMeal.title,
        text: newMeal.text,
      });
      if (error) {
        alert.error(i18n.t("meal-plan.mealplan-creation-failed"));
        return;
      }
      await props.actions.refreshAll();
    }
    else {
      const failedRecipeIds: string[] = [];
      let created = false;

      for (const recipeId of selectedMealRecipeIds.value) {
        const { error } = await api.mealplans.createOne({
          date: newMealDateString.value,
          entryType: newMeal.entryType,
          recipeId,
        });
        if (error) {
          failedRecipeIds.push(recipeId);
        }
        else {
          created = true;
        }
      }

      if (created) {
        await props.actions.refreshAll();
      }
      if (failedRecipeIds.length) {
        selectedMealRecipeIds.value = failedRecipeIds;
        alert.error(i18n.t("meal-plan.mealplan-creation-failed"));
        return;
      }
    }

    state.value.dialog = false;
    resetDialog();
  }
  finally {
    dialog.loading = false;
  }
}

function openDialog(date: Date) {
  newMeal.date = date;
  state.value.dialog = true;
}

function isToday(date: Date) {
  return isSameDay(date, new Date());
}

function toggleTodayEdit(date: Date) {
  if (!isToday(date)) {
    return;
  }

  void router.push({
    name: "household-mealplan-planner-view",
    query: route.query,
  });
}

function editMeal(mealplan: UpdatePlanEntry) {
  const { date, title, text, entryType, recipeId, id, groupId, userId } = mealplan;
  const mealRecipe = (mealplan as any).recipe;
  if (!entryType) return;

  const [year, month, day] = date.split("-").map(Number);
  newMeal.date = new Date(year, month - 1, day);
  newMeal.title = title || "";
  newMeal.text = text || "";
  newMeal.recipeId = recipeId || undefined;
  newMeal.entryType = entryType;
  newMeal.existing = true;
  newMeal.id = id;
  newMeal.groupId = groupId;
  newMeal.userId = userId || auth.user.value?.id || "";
  selectedMealRecipeIds.value = [];

  selectedMealRecipeCache.value = mealRecipe?.id
    ? { [mealRecipe.id]: mealRecipe as Recipe }
    : {};

  state.value.dialog = true;
  dialog.note = !recipeId;
}

function resetDialog() {
  newMeal.date = new Date(Date.now() - new Date().getTimezoneOffset() * 60000);
  newMeal.title = "";
  newMeal.text = "";
  newMeal.entryType = "dinner";
  newMeal.recipeId = undefined;
  newMeal.existing = false;
  selectedMealRecipeIds.value = [];
  selectedMealRecipeCache.value = {};
  selectedMealCategorySlugs.value = [];
  selectedMealTagSlugs.value = [];
  search.query.value = "";
  dialog.note = false;
  dialog.error = false;
}

async function randomMeal(date: Date, type: PlanEntryType) {
  const { data } = await api.mealplans.setRandom({
    date: format(date, "yyyy-MM-dd"),
    entryType: type,
  });

  if (data) {
    props.actions.refreshAll();
  }
}

// =====================================================
// Search

const { store: mealPlanCategories } = useCategoryStore();
const { store: mealPlanTags } = useTagStore();
const search = useRecipeSearch(api, {
  categories: selectedMealCategorySlugs,
  tags: selectedMealTagSlugs,
  perPage: 100,
});
const mealPlanRecipeOptions = computed(() => {
  const recipesById = new Map<string, Recipe>();
  Object.values(selectedMealRecipeCache.value).forEach(recipe => recipesById.set(recipe.id, recipe));
  search.data.value.forEach(recipe => recipesById.set(recipe.id, recipe));
  return [...recipesById.values()];
});

function rememberSingleMealRecipe(recipeId: string | null) {
  if (!recipeId) {
    selectedMealRecipeCache.value = {};
    return;
  }

  const recipe = mealPlanRecipeOptions.value.find(candidate => candidate.id === recipeId);
  if (recipe) {
    selectedMealRecipeCache.value = { [recipe.id]: recipe };
  }
}

function rememberSelectedMealRecipes(recipeIds: string[] | null) {
  const activeIds = new Set(recipeIds || []);
  const nextCache: Record<string, Recipe> = {};
  mealPlanRecipeOptions.value.forEach((recipe) => {
    if (activeIds.has(recipe.id)) {
      nextCache[recipe.id] = recipe;
    }
  });
  selectedMealRecipeCache.value = nextCache;
}
const planTypeOptions = usePlanTypeOptions();

onMounted(async () => {
  await search.trigger();
});
</script>

<style scoped>
.meal-plan-today-toggle {
  cursor: pointer;
  transition:
    box-shadow 0.15s ease,
    transform 0.15s ease;
}

.meal-plan-today-toggle:hover,
.meal-plan-today-toggle:focus-within {
  box-shadow: 0 2px 10px rgba(var(--v-theme-primary), 0.18);
  transform: translateY(-1px);
}
</style>
