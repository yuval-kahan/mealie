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
    <BaseDialog
      v-model="aiMeal.dialog"
      :title="$t('meal-plan.create-ai-meal')"
      :submit-text="aiMeal.result ? $t('meal-plan.add-ai-meal-to-plan') : $t('meal-plan.suggest-meal')"
      color="primary"
      :icon="$globals.icons.robot"
      width="760"
      max-width="96vw"
      keep-open
      can-submit
      :loading="aiMeal.loading"
      :submit-disabled="isAIMealSubmitDisabled"
      @submit="handleAIMealSubmit"
      @close="resetAIMealDialog"
    >
      <v-card-text class="pt-4">
        <v-text-field
          :model-value="aiMealDateString"
          :label="$t('meal-plan.selected-date')"
          :prepend-inner-icon="$globals.icons.calendar"
          readonly
          variant="outlined"
          density="comfortable"
        />
        <v-select
          v-model="aiMeal.mealPeriod"
          :items="aiMealPeriodOptions"
          :label="$t('meal-plan.meal-type')"
          item-title="text"
          item-value="value"
          :rules="[requiredRule]"
          variant="outlined"
          density="comfortable"
          @update:model-value="clearAIMealResult"
        />
        <v-textarea
          v-model="aiMeal.request"
          :label="$t('meal-plan.ai-meal-request')"
          :placeholder="$t('meal-plan.ai-meal-request-example')"
          :rules="[requiredRule]"
          rows="3"
          maxlength="1000"
          counter
          variant="outlined"
          @update:model-value="clearAIMealResult"
        />
        <div class="text-subtitle-2 mb-2">
          {{ $t("meal-plan.course-quantities") }}
        </div>
        <v-row dense class="mb-2">
          <v-col
            v-for="course in aiMealCourseOptions"
            :key="course.value"
            cols="12"
            sm="6"
          >
            <div class="d-flex ga-2">
              <v-select
                v-model="aiMealCountSelections[course.value]"
                :items="aiMealCountOptions"
                :label="course.text"
                item-title="text"
                item-value="value"
                hide-details
                variant="outlined"
                density="comfortable"
                class="flex-grow-1"
                @update:model-value="clearAIMealResult"
              />
              <v-text-field
                v-if="aiMealCountSelections[course.value] === 'custom'"
                v-model.number="aiMealCustomCourseCounts[course.value]"
                :label="$t('meal-plan.custom-count')"
                type="number"
                min="0"
                max="100"
                step="1"
                hide-details
                variant="outlined"
                density="comfortable"
                class="ai-meal-custom-count"
                @update:model-value="clearAIMealResult"
              />
            </div>
          </v-col>
        </v-row>
        <div class="text-subtitle-2 mb-2">
          {{ $t("meal-plan.filter-ai-meal-recipes") }}
        </div>
        <v-row dense class="mb-2">
          <v-col cols="12" sm="6">
            <v-autocomplete
              v-model="aiMealCategorySlugs"
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
              @update:model-value="clearAIMealResult"
            />
          </v-col>
          <v-col cols="12" sm="6">
            <v-autocomplete
              v-model="aiMealTagSlugs"
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
              @update:model-value="clearAIMealResult"
            />
          </v-col>
        </v-row>
        <v-row dense>
          <v-col cols="12" sm="8">
            <v-autocomplete
              v-model="aiMeal.anchorRecipeId"
              v-model:search="aiRecipeSearch.query.value"
              :items="aiRecipeSearch.data.value"
              :label="$t('meal-plan.anchor-recipe')"
              :hint="$t('meal-plan.anchor-recipe-hint')"
              :prepend-inner-icon="$globals.icons.foods"
              :loading="aiRecipeSearch.loading.value"
              :custom-filter="normalizeFilter"
              :no-data-text="$t('search.no-results')"
              item-title="name"
              item-value="id"
              clearable
              persistent-hint
              variant="outlined"
              density="comfortable"
              @update:model-value="clearAIMealResult"
            />
          </v-col>
          <v-col cols="12" sm="4">
            <v-select
              v-model="aiMeal.anchorCourse"
              :items="aiMealCourseOptions"
              :label="$t('meal-plan.anchor-course')"
              item-title="text"
              item-value="value"
              :disabled="!aiMeal.anchorRecipeId"
              variant="outlined"
              density="comfortable"
              @update:model-value="clearAIMealResult"
            />
          </v-col>
        </v-row>

        <template v-if="aiMeal.result">
          <v-divider class="my-3" />
          <h3 class="text-h6 mb-1">
            {{ aiMeal.result.title || $t('meal-plan.ai-meal-suggestion') }}
          </h3>
          <p v-if="aiMeal.result.explanation" class="text-body-2 text-medium-emphasis mb-3">
            {{ aiMeal.result.explanation }}
          </p>
          <div
            v-for="item in aiMeal.result.items || []"
            :key="aiMealSuggestionKey(item)"
            class="ai-meal-suggestion-row"
          >
            <v-checkbox-btn
              v-model="aiMeal.selectedKeys"
              :value="aiMealSuggestionKey(item)"
              color="primary"
            />
            <div class="ai-meal-suggestion-image mx-2">
              <RecipeCardImage
                :recipe-id="item.recipe.id!"
                :slug="item.recipe.slug"
                :image-version="recipeImageVersion(item.recipe)"
                tiny
                icon-size="30"
                height="56"
              />
            </div>
            <div class="min-width-0 flex-grow-1">
              <div class="d-flex align-center ga-2 flex-wrap">
                <v-chip size="x-small" color="accent" label>
                  {{ aiMealCourseText(item.course) }}
                </v-chip>
                <strong>{{ item.recipe.name }}</strong>
              </div>
              <div v-if="item.reason" class="text-caption text-medium-emphasis mt-1">
                {{ item.reason }}
              </div>
            </div>
          </div>
        </template>
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
          class="mb-2 border-left-primary rounded-sm pa-2 meal-plan-day-toggle"
          @click="toggleDayView"
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
                icon: $globals.icons.robot,
                text: $t('meal-plan.ai-meal'),
                event: 'aiMeal',
              },
              {
                icon: $globals.icons.createAlt,
                text: $t('general.new'),
                event: 'create',
              },
            ]"
            @ai-meal="openAIMealDialog(plan.date)"
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
import type {
  AIMealCourse,
  AIMealCourseCounts,
  AIMealPeriod,
  AIMealSuggestionItem,
  AIMealSuggestResponse,
  PlanEntryType,
  UpdatePlanEntry,
} from "~/lib/api/types/meal-plan";
import type { Recipe } from "~/lib/api/types/recipe";
import { useUserApi } from "~/composables/api/api-client";
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

const aiMeal = reactive({
  dialog: false,
  loading: false,
  date: new Date(Date.now() - new Date().getTimezoneOffset() * 60000),
  mealPeriod: null as AIMealPeriod | null,
  request: "",
  anchorRecipeId: null as string | null,
  anchorCourse: "main" as AIMealCourse,
  result: null as AIMealSuggestResponse | null,
  selectedKeys: [] as string[],
});
const aiMealCategorySlugs = ref<string[]>([]);
const aiMealTagSlugs = ref<string[]>([]);
type AIMealCountSelection = number | "custom";

const aiMealCountSelections = reactive<Record<AIMealCourse, AIMealCountSelection>>({
  starter: 1,
  main: 1,
  side: 1,
  dessert: 1,
});
const aiMealCustomCourseCounts = reactive<Record<AIMealCourse, number>>({
  starter: 1,
  main: 1,
  side: 1,
  dessert: 1,
});

const aiMealDateString = computed(() => format(aiMeal.date, "yyyy-MM-dd"));
const aiMealPeriodOptions = computed(() => [
  { value: "breakfast" as AIMealPeriod, text: i18n.t("meal-plan.breakfast") },
  { value: "lunch" as AIMealPeriod, text: i18n.t("meal-plan.lunch") },
  { value: "dinner" as AIMealPeriod, text: i18n.t("meal-plan.dinner") },
]);
const aiMealCourseOptions = computed(() => [
  { value: "starter" as AIMealCourse, text: i18n.t("meal-plan.starter") },
  { value: "main" as AIMealCourse, text: i18n.t("meal-plan.main-course") },
  { value: "side" as AIMealCourse, text: i18n.t("meal-plan.side") },
  { value: "dessert" as AIMealCourse, text: i18n.t("meal-plan.dessert") },
]);
const aiMealCountOptions = computed(() => [
  ...Array.from({ length: 21 }, (_, value) => ({ value, text: String(value) })),
  { value: "custom" as const, text: i18n.t("general.custom") },
]);
const resolvedAIMealCourseCounts = computed<AIMealCourseCounts>(() => {
  const result = {} as AIMealCourseCounts;
  for (const course of Object.keys(aiMealCountSelections) as AIMealCourse[]) {
    const selected = aiMealCountSelections[course];
    const value = selected === "custom" ? aiMealCustomCourseCounts[course] : selected;
    result[course] = Math.max(0, Math.min(100, Math.trunc(Number(value) || 0)));
  }
  return result;
});

const isAIMealSubmitDisabled = computed(() => {
  if (aiMeal.result) {
    return !aiMeal.selectedKeys.length;
  }
  const requestedCourses = Object.values(resolvedAIMealCourseCounts.value).reduce((sum, count) => sum + count, 0);
  return !aiMeal.mealPeriod || aiMeal.request.trim().length < 2 || requestedCourses < 1;
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

function toggleDayView() {
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

function aiMealSuggestionKey(item: AIMealSuggestionItem) {
  return `${item.course}:${item.recipe.slug}`;
}

function aiMealCourseText(course: AIMealCourse) {
  return i18n.t(course === "main" ? "meal-plan.main-course" : `meal-plan.${course}`);
}

function recipeImageVersion(recipe: Recipe) {
  return typeof recipe.image === "string" ? recipe.image : null;
}

function clearAIMealResult() {
  aiMeal.result = null;
  aiMeal.selectedKeys = [];
}

function openAIMealDialog(date: Date) {
  resetAIMealDialog();
  aiMeal.date = date;
  aiMeal.dialog = true;
}

function resetAIMealDialog() {
  aiMeal.dialog = false;
  aiMeal.loading = false;
  aiMeal.date = new Date(Date.now() - new Date().getTimezoneOffset() * 60000);
  aiMeal.mealPeriod = null;
  aiMeal.request = "";
  aiMeal.anchorRecipeId = null;
  aiMeal.anchorCourse = "main";
  aiMeal.result = null;
  aiMeal.selectedKeys = [];
  aiMealCategorySlugs.value = [];
  aiMealTagSlugs.value = [];
  for (const course of Object.keys(aiMealCountSelections) as AIMealCourse[]) {
    aiMealCountSelections[course] = 1;
    aiMealCustomCourseCounts[course] = 1;
  }
  aiRecipeSearch.query.value = "";
}

async function suggestAIMeal() {
  if (!aiMeal.mealPeriod || aiMeal.request.trim().length < 2) return;

  const { data, error } = await api.mealplans.suggestWithAI({
    mealPeriod: aiMeal.mealPeriod,
    request: aiMeal.request.trim(),
    anchorRecipeId: aiMeal.anchorRecipeId,
    anchorCourse: aiMeal.anchorCourse,
    courseCounts: resolvedAIMealCourseCounts.value,
    categoryNames: organizerNames(mealPlanCategories.value, aiMealCategorySlugs.value),
    tagNames: organizerNames(mealPlanTags.value, aiMealTagSlugs.value),
  });
  if (error || !data?.items?.length) {
    alert.error(i18n.t("meal-plan.ai-meal-suggestion-failed"));
    return;
  }

  aiMeal.result = data;
  aiMeal.selectedKeys = data.items.map(aiMealSuggestionKey);
}

async function addAIMealToPlan() {
  if (!aiMeal.result?.items?.length) return;

  const selectedKeys = new Set(aiMeal.selectedKeys);
  const selectedItems = aiMeal.result.items.filter(item => selectedKeys.has(aiMealSuggestionKey(item)));
  let failed = false;
  for (const item of selectedItems) {
    if (!item.recipe.id) {
      failed = true;
      continue;
    }
    const { error } = await api.mealplans.createOne({
      date: aiMealDateString.value,
      entryType: item.entryType,
      recipeId: item.recipe.id,
    });
    failed ||= !!error;
  }

  await props.actions.refreshAll();
  if (failed) {
    alert.error(i18n.t("meal-plan.mealplan-creation-failed"));
    return;
  }

  alert.success(i18n.t("meal-plan.ai-meal-added"));
  resetAIMealDialog();
}

async function handleAIMealSubmit() {
  if (aiMeal.loading || isAIMealSubmitDisabled.value) return;
  aiMeal.loading = true;
  try {
    if (aiMeal.result) {
      await addAIMealToPlan();
    }
    else {
      await suggestAIMeal();
    }
  }
  finally {
    aiMeal.loading = false;
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
const aiRecipeSearch = useRecipeSearch(api, {
  categories: aiMealCategorySlugs,
  tags: aiMealTagSlugs,
  perPage: 100,
});

function organizerNames(items: Array<{ name: string; slug: string }>, selectedSlugs: string[]) {
  const selected = new Set(selectedSlugs);
  return items.filter(item => selected.has(item.slug)).map(item => item.name);
}
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
  await Promise.all([search.trigger(), aiRecipeSearch.trigger()]);
});
</script>

<style scoped>
.meal-plan-day-toggle {
  cursor: pointer;
  transition:
    box-shadow 0.15s ease,
    transform 0.15s ease;
}

.meal-plan-day-toggle:hover,
.meal-plan-day-toggle:focus-within {
  box-shadow: 0 2px 10px rgba(var(--v-theme-primary), 0.18);
  transform: translateY(-1px);
}

.ai-meal-suggestion-row {
  display: flex;
  align-items: center;
  min-height: 64px;
  padding: 8px 4px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.ai-meal-suggestion-row:last-child {
  border-bottom: 0;
}

.ai-meal-suggestion-image {
  flex: 0 0 72px;
  width: 72px;
  height: 56px;
  overflow: hidden;
  border-radius: 4px;
}

.ai-meal-suggestion-image :deep(.v-img),
.ai-meal-suggestion-image :deep(.icon-slot) {
  width: 100%;
  height: 56px;
  min-height: 56px !important;
}

.ai-meal-suggestion-image :deep(.v-img__img) {
  object-fit: contain !important;
}

.ai-meal-custom-count {
  flex: 0 0 120px;
}

.min-width-0 {
  min-width: 0;
}
</style>
