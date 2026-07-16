<template>
  <v-toolbar
    class="fixed-bar mt-0"
    :class="{ 'fixed-bar--inline': inline }"
    style="z-index: 2; position: sticky; background: transparent; box-shadow: none"
    density="compact"
    elevation="0"
  >
    <BaseDialog
      v-model="deleteDialog"
      :title="$t('recipe.delete-recipe')"
      color="error"
      :icon="$globals.icons.alertCircle"
      can-confirm
      @confirm="emitDelete()"
    >
      <v-card-text>
        {{ $t("recipe.delete-confirmation") }}
        <v-progress-linear v-if="deletePreviewLoading" indeterminate color="primary" class="mt-4" />
        <template v-else>
          <v-divider v-if="deleteShoppingListOptions.length || deleteWebsiteOptions.length" class="my-4" />
          <p v-if="deleteShoppingListOptions.length" class="font-weight-medium mb-2">
            {{ $t("recipe.delete-linked-shopping-lists") }}
          </p>
          <v-checkbox
            v-for="item in deleteShoppingListOptions"
            :key="item.id"
            v-model="selectedDeleteShoppingListIds"
            :value="item.id"
            :label="item.name"
            density="compact"
            hide-details
          />
          <p v-if="deleteWebsiteOptions.length" class="font-weight-medium mt-4 mb-2">
            {{ $t("recipe.delete-linked-websites") }}
          </p>
          <v-checkbox
            v-for="item in deleteWebsiteOptions"
            :key="item.id"
            v-model="selectedDeleteWebsiteIds"
            :value="item.id"
            :label="item.name"
            density="compact"
            hide-details
          />
          <v-alert
            v-if="deleteShoppingListOptions.length || deleteWebsiteOptions.length"
            type="info"
            variant="tonal"
            density="compact"
            class="mt-4"
          >
            {{ $t("recipe.linked-items-remain-by-default") }}
          </v-alert>
        </template>
      </v-card-text>
    </BaseDialog>
    <RecipeShoppingListQuickDialog
      v-model="shoppingListQuickDialog"
      :recipe-slug="recipe.slug"
    />
    <ShoppingWebsiteLinksDialog
      v-model="shoppingWebsiteLinksDialog"
      entity-type="recipe"
      :entity-id="recipe.id!"
    />

    <v-spacer v-if="!inline" />
    <div v-if="!open" class="custom-btn-group ma-1">
      <RecipeFavoriteBadge v-if="loggedIn" color="info" button-style :recipe-id="recipe.id!" show-always />
      <RecipeTimelineBadge
        v-if="loggedIn"
        class="ml-1"
        color="info"
        button-style
        :slug="recipe.slug"
        :recipe-name="recipe.name!"
      />
      <v-tooltip v-if="loggedIn" location="bottom" color="info">
        <template #activator="{ props: tooltipProps }">
          <v-btn
            icon
            variant="flat"
            rounded="circle"
            size="small"
            color="info"
            class="ml-1"
            v-bind="tooltipProps"
            @click="shoppingListQuickDialog = true"
          >
            <v-icon size="x-large">
              {{ $globals.icons.cartCheck }}
            </v-icon>
          </v-btn>
        </template>
        <span>{{ $t("recipe.open-or-create-shopping-list") }}</span>
      </v-tooltip>
      <v-tooltip v-if="loggedIn" location="bottom" color="info">
        <template #activator="{ props: tooltipProps }">
          <v-btn
            icon
            variant="flat"
            rounded="circle"
            size="small"
            color="info"
            class="ml-1"
            v-bind="tooltipProps"
            @click="shoppingWebsiteLinksDialog = true"
          >
            <v-icon size="x-large">
              {{ $globals.icons.web }}
            </v-icon>
          </v-btn>
        </template>
        <span>{{ $t("shopping-website.link-websites") }}</span>
      </v-tooltip>
      <div v-if="loggedIn">
        <v-tooltip v-if="canEdit && !quickEditing" location="bottom" color="info">
          <template #activator="{ props: tooltipProps }">
            <v-btn
              icon
              variant="flat"
              rounded="circle"
              size="small"
              color="info"
              class="ml-1"
              v-bind="tooltipProps"
              @click="$emit('edit', true)"
            >
              <v-icon size="x-large">
                {{ $globals.icons.edit }}
              </v-icon>
            </v-btn>
          </template>
          <span>{{ $t("general.edit") }}</span>
        </v-tooltip>
      </div>

      <v-tooltip v-if="loggedIn && canEdit" location="bottom" color="info">
        <template #activator="{ props: tooltipProps }">
          <v-btn
            icon
            variant="flat"
            rounded="circle"
            size="small"
            color="info"
            class="ml-1"
            v-bind="tooltipProps"
            @click="quickEditing ? $emit('quick-save') : $emit('quick-edit')"
          >
            <v-icon size="x-large">
              {{ quickEditing ? $globals.icons.save : $globals.icons.manageData }}
            </v-icon>
          </v-btn>
        </template>
        <span>{{ $t(quickEditing ? "recipe.save-quick-edit" : "recipe.quick-edit") }}</span>
      </v-tooltip>
      <v-tooltip v-if="loggedIn && canEdit && quickEditing" location="bottom" color="info">
        <template #activator="{ props: tooltipProps }">
          <v-btn
            icon
            variant="flat"
            rounded="circle"
            size="small"
            color="info"
            class="ml-1"
            v-bind="tooltipProps"
            @click="$emit('quick-close')"
          >
            <v-icon size="x-large">
              {{ $globals.icons.close }}
            </v-icon>
          </v-btn>
        </template>
        <span>{{ $t("general.close") }}</span>
      </v-tooltip>

      <RecipeContextMenu
        show-print
        :menu-top="false"
        :name="recipe.name!"
        :slug="recipe.slug!"
        :menu-icon="$globals.icons.dotsVertical"
        fab
        color="info"
        :card-menu="false"
        :recipe="recipe"
        :recipe-id="recipe.id!"
        :rating="recipe.rating ?? 0"
        :recipe-scale="recipeScale"
        :use-items="{
          edit: false,
          rename: loggedIn,
          copy: true,
          rating: loggedIn,
          download: loggedIn,
          duplicate: loggedIn,
          mealplanner: loggedIn,
          shoppingList: loggedIn,
          print: true,
          printPreferences: true,
          share: loggedIn,
          recipeActions: true,
          shoppingWebsites: true,
          delete: loggedIn,
        }"
        class="ml-1"
        @print="$emit('print')"
        @renamed="$emit('renamed', $event)"
      />
    </div>
    <div v-if="open" class="custom-btn-group gapped ma-1">
      <v-btn
        v-for="(btn, index) in editorButtons"
        :key="index"
        :class="{ 'rounded-circle': $vuetify.display.xs }"
        :size="$vuetify.display.xs ? 'small' : undefined"
        :color="btn.color"
        variant="elevated"
        :icon="$vuetify.display.xs"
        @click="emitHandler(btn.event)"
      >
        <v-icon :left="!$vuetify.display.xs">
          {{ btn.icon }}
        </v-icon>
        {{ $vuetify.display.xs ? "" : btn.text }}
      </v-btn>
    </div>
  </v-toolbar>
</template>

<script setup lang="ts">
import RecipeContextMenu from "./RecipeContextMenu/RecipeContextMenu.vue";
import RecipeFavoriteBadge from "./RecipeFavoriteBadge.vue";
import RecipeTimelineBadge from "./RecipeTimelineBadge.vue";
import { useUserApi } from "~/composables/api/api-client";
import type { Recipe } from "~/lib/api/types/recipe";
import type { RecipeDeletePreview } from "~/lib/api/user/recipes/recipe";

const SAVE_EVENT = "save";
const DELETE_EVENT = "delete";
const CLOSE_EVENT = "close";
const JSON_EVENT = "json";

interface Props {
  recipe: Recipe;
  slug: string;
  recipeScale?: number;
  open: boolean;
  name: string;
  loggedIn?: boolean;
  recipeId: string;
  canEdit?: boolean;
  inline?: boolean;
  quickEditing?: boolean;
}
const props = withDefaults(defineProps<Props>(), {
  recipeScale: 1,
  loggedIn: false,
  canEdit: false,
  inline: false,
  quickEditing: false,
});

const emit = defineEmits(["print", "input", "save", "delete", "close", "json", "edit", "renamed", "quick-edit", "quick-save", "quick-close"]);

const deleteDialog = ref(false);
const deletePreviewLoading = ref(false);
const deletePreview = ref<RecipeDeletePreview>();
const selectedDeleteShoppingListIds = ref<string[]>([]);
const selectedDeleteWebsiteIds = ref<string[]>([]);

const i18n = useI18n();
const { $globals } = useNuxtApp();
const api = useUserApi();
const shoppingListQuickDialog = ref(false);
const shoppingWebsiteLinksDialog = ref(false);
const deleteShoppingListOptions = computed(() => (deletePreview.value?.shoppingListIds || []).map((id, index) => ({
  id,
  name: deletePreview.value?.shoppingListNames[index] || id,
})));
const deleteWebsiteOptions = computed(() => (deletePreview.value?.websiteIds || []).map((id, index) => ({
  id,
  name: deletePreview.value?.websiteNames[index] || id,
})));

const editorButtons = [
  {
    text: i18n.t("general.delete"),
    icon: $globals.icons.delete,
    event: DELETE_EVENT,
    color: "error",
  },
  {
    text: i18n.t("general.json"),
    icon: $globals.icons.codeBraces,
    event: JSON_EVENT,
    color: "accent",
  },
  {
    text: i18n.t("general.close"),
    icon: $globals.icons.close,
    event: CLOSE_EVENT,
    color: "",
  },
  {
    text: i18n.t("general.save"),
    icon: $globals.icons.save,
    event: SAVE_EVENT,
    color: "success",
  },
];

function emitHandler(event: string) {
  switch (event) {
    case CLOSE_EVENT:
      emit("close");
      emit("input", false);
      break;
    case DELETE_EVENT:
      void openDeleteDialog();
      break;
    default:
      emit(event as any);
      break;
  }
}

async function openDeleteDialog() {
  selectedDeleteShoppingListIds.value = [];
  selectedDeleteWebsiteIds.value = [];
  deletePreview.value = undefined;
  deleteDialog.value = true;
  deletePreviewLoading.value = true;
  try {
    const { data } = await api.recipes.getDeletePreview(props.recipe.slug);
    if (data) deletePreview.value = data;
  }
  finally {
    deletePreviewLoading.value = false;
  }
}

function emitDelete() {
  emit("delete", {
    shoppingListIds: selectedDeleteShoppingListIds.value,
    websiteIds: selectedDeleteWebsiteIds.value,
  });
  emit("input", false);
}
</script>

<style scoped>
.custom-btn-group {
  flex: 0 1 auto;
  display: inline-flex;
  flex-wrap: wrap;
  gap: 2px;
  max-width: 100%;
}

.gapped {
  gap: 0.25rem;
}

.vertical {
  flex-direction: column !important;
}

.sticky {
  margin-left: auto;
  position: fixed !important;
  margin-top: 4.25rem;
}

.fixed-bar {
  align-items: center;
  display: flex;
  position: sticky;
  top: 4.5em;
  z-index: 2;
  background: transparent !important;
  box-shadow: none !important;
  min-height: 0 !important;
  height: 48px;
  padding: 0 8px;
}

.fixed-bar-mobile {
  top: 1.5em !important;
}

.fixed-bar--inline {
  display: flex !important;
  position: static !important;
  top: auto !important;
  width: 100% !important;
  max-width: 100%;
  height: auto;
  min-height: 0 !important;
  padding: 0;
  overflow: visible;
}

.fixed-bar--inline .custom-btn-group {
  flex: 0 0 auto;
  min-width: max-content;
}
</style>
