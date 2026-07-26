<template>
  <div class="text-center">
    <v-menu
      offset-y
      start
      :eager="isMenuContentLoaded"
      :bottom="!menuTop"
      :nudge-bottom="!menuTop ? '5' : '0'"
      :top="menuTop"
      :nudge-top="menuTop ? '5' : '0'"
      allow-overflow
      close-delay="125"
      content-class="d-print-none"
      @update:model-value="onMenuToggle"
    >
      <template #activator="{ props: activatorProps }">
        <v-btn
          icon
          class="recipe-context-menu__activator"
          :variant="fab ? 'flat' : undefined"
          :rounded="fab ? 'circle' : undefined"
          :size="fab ? 'small' : undefined"
          :color="fab ? 'info' : 'secondary'"
          :fab="fab"
          v-bind="activatorProps"
          @click.prevent
        >
          <v-icon :size="!fab ? undefined : 'x-large'" :color="fab ? 'white' : 'secondary'">
            {{ icon }}
          </v-icon>
        </v-btn>
      </template>

      <RecipeContextMenuContent
        v-if="isMenuContentLoaded"
        ref="menuContent"
        v-bind="contentProps"
        @print="$emit('print')"
        @deleted="$emit('deleted', $event)"
        @image-updated="$emit('imageUpdated', $event)"
        @renamed="$emit('renamed', $event)"
      />
    </v-menu>
  </div>
</template>

<script setup lang="ts">
import type { Recipe } from "~/lib/api/types/recipe";

interface ContextMenuIncludes {
  delete?: boolean;
  edit?: boolean;
  rename?: boolean;
  copy?: boolean;
  rating?: boolean;
  download?: boolean;
  duplicate?: boolean;
  mealplanner?: boolean;
  shoppingList?: boolean;
  aiShoppingList?: boolean;
  aiImage?: boolean;
  imageUpload?: boolean;
  aiEdit?: boolean;
  print?: boolean;
  printPreferences?: boolean;
  share?: boolean;
  recipeActions?: boolean;
  shoppingWebsites?: boolean;
}

interface ContextMenuItem {
  title: string;
  icon: string;
  color?: string;
  event: string;
  isPublic: boolean;
}

interface Props {
  useItems?: ContextMenuIncludes;
  appendItems?: ContextMenuItem[];
  leadingItems?: ContextMenuItem[];
  menuTop?: boolean;
  fab?: boolean;
  color?: string;
  slug: string;
  menuIcon?: string | null;
  name: string;
  recipe?: Recipe;
  recipeId: string;
  rating?: number;
  recipeScale?: number;
  redirectOnDelete?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  useItems: () => ({
    delete: true,
    edit: true,
    rename: true,
    copy: true,
    rating: true,
    download: true,
    duplicate: false,
    mealplanner: true,
    shoppingList: true,
    aiShoppingList: true,
    aiImage: true,
    imageUpload: true,
    aiEdit: true,
    print: true,
    printPreferences: true,
    share: true,
    recipeActions: true,
    shoppingWebsites: true,
  }),
  appendItems: () => [],
  leadingItems: () => [],
  menuTop: true,
  fab: false,
  color: "primary",
  menuIcon: null,
  recipe: undefined,
  rating: 0,
  recipeScale: 1,
  redirectOnDelete: true,
});

defineEmits<{
  [key: string]: any;
  print: [];
  deleted: [slug: string];
  renamed: [{ slug: string; name: string; recipe?: Recipe }];
  imageUpdated: [{ slug: string; image: string }];
}>();

const { $globals } = useNuxtApp();

const isMenuContentLoaded = ref(false);
const menuContent = ref<{
  openMealplannerDialog: () => void;
  openShoppingListDialog: () => Promise<void>;
} | null>(null);

const icon = computed(() => {
  return props.menuIcon || $globals.icons.dotsVertical;
});

// Props to pass to the content component (excluding internal wrapper props)
const contentProps = computed(() => {
  const { ...rest } = props;
  return rest;
});

function onMenuToggle(isOpen: boolean) {
  if (isOpen && !isMenuContentLoaded.value) {
    isMenuContentLoaded.value = true;
  }
}

async function ensureMenuContentLoaded() {
  if (!isMenuContentLoaded.value) {
    isMenuContentLoaded.value = true;
    await nextTick();
  }

  for (let attempt = 0; attempt < 10 && !menuContent.value; attempt++) {
    await new Promise(resolve => setTimeout(resolve, 10));
    await nextTick();
  }
}

async function openMealplannerDialog() {
  await ensureMenuContentLoaded();
  menuContent.value?.openMealplannerDialog();
}

async function openShoppingListDialog() {
  await ensureMenuContentLoaded();
  await menuContent.value?.openShoppingListDialog();
}

defineExpose({
  openMealplannerDialog,
  openShoppingListDialog,
});

const RecipeContextMenuContent = defineAsyncComponent(() => import("./RecipeContextMenuContent.vue"));
</script>

<style scoped>
.recipe-context-menu__activator {
  transition:
    background-color 0.15s ease,
    box-shadow 0.15s ease,
    color 0.15s ease;
}

.recipe-context-menu__activator:not(.v-btn--variant-flat):hover,
.recipe-context-menu__activator:not(.v-btn--variant-flat):focus-visible {
  background-color: rgba(var(--v-theme-primary), 0.14) !important;
  box-shadow: inset 0 0 0 1px rgba(var(--v-theme-primary), 0.28);
  color: rgb(var(--v-theme-primary)) !important;
}
</style>
