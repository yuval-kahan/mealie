<template>
  <v-container
    v-if="shoppingList"
    class="md-container"
  >
    <BaseDialog
      v-model="state.checkAllDialog"
      :title="$t('general.confirm')"
      :icon="$globals.icons.checkboxOutline"
      can-confirm
      @confirm="checkAll"
    >
      <v-card-text>
        {{ $t('shopping-list.are-you-sure-you-want-to-check-all-items') }}
      </v-card-text>
    </BaseDialog>

    <BaseDialog
      v-model="state.uncheckAllDialog"
      :title="$t('general.confirm')"
      :icon="$globals.icons.checkboxBlankOutline"
      can-confirm
      @confirm="uncheckAll"
    >
      <v-card-text>
        {{ $t('shopping-list.are-you-sure-you-want-to-uncheck-all-items') }}
      </v-card-text>
    </BaseDialog>

    <BaseDialog
      v-model="state.deleteCheckedDialog"
      :title="$t('general.confirm')"
      :icon="$globals.icons.alertCircle"
      can-confirm
      @confirm="deleteChecked"
    >
      <v-card-text>
        {{ $t('shopping-list.are-you-sure-you-want-to-delete-checked-items') }}
      </v-card-text>
    </BaseDialog>

    <!-- Reorder Labels -->
    <BaseDialog
      v-model="reorderLabelsDialog"
      :icon="$globals.icons.tagArrowUp"
      :title="$t('shopping-list.reorder-labels')"
      :submit-icon="$globals.icons.save"
      :submit-text="$t('general.save')"
      can-submit
      @submit="saveLabelOrder"
      @close="cancelLabelOrder"
    >
      <v-card height="fit-content" max-height="70vh" style="overflow-y: auto;">
        <VueDraggable
          v-if="localLabels"
          v-model="localLabels"
          handle=".handle"
          :delay="250"
          :delay-on-touch-only="true"
          class="my-2"
          @update:model-value="updateLabelOrder"
        >
          <div v-for="(labelSetting, index) in localLabels" :key="labelSetting.id">
            <MultiPurposeLabelSection v-model="localLabels[index]" use-color />
          </div>
        </VueDraggable>
      </v-card>
    </BaseDialog>

    <BasePageTitle divider class="shopping-list-title-block">
      <template #header>
        <div class="shopping-list-header">
          <div class="shopping-list-header-nav">
            <ButtonLink
              :to="`/shopping-lists?disableRedirect=true`"
              :text="$t('shopping-list.all-lists')"
              :icon="$globals.icons.backArrow"
            />
          </div>
          <div
            v-if="mdAndUp"
            class="shopping-list-header-hero"
          >
            <v-img
              max-height="100"
              max-width="100"
              src="/svgs/shopping-cart.svg"
            />
          </div>
          <div class="shopping-list-header-actions">
            <v-chip
              size="small"
              :color="shoppingListAiOrganized ? 'success' : 'grey'"
              :variant="shoppingListAiOrganized ? 'tonal' : 'outlined'"
              class="shopping-list-ai-chip"
            >
              <v-icon start size="small">
                {{ $globals.icons.robot }}
              </v-icon>
              {{ shoppingListAiOrganized ? $t("shopping-list.ai-organized") : $t("shopping-list.ai-not-organized") }}
            </v-chip>
            <v-btn
              color="success"
              variant="tonal"
              :prepend-icon="$globals.icons.robot"
              :loading="aiOrganizing"
              :disabled="!hasShoppingListItems || isOffline"
              @click="organizeShoppingListWithAI"
            >
              {{ $t("shopping-list.organize-with-ai") }}
            </v-btn>
            <v-btn
              :color="shoppingListGroceriesReady ? 'success' : 'grey'"
              :variant="shoppingListGroceriesReady ? 'tonal' : 'outlined'"
              :prepend-icon="$globals.icons.cartCheck"
              :disabled="!hasShoppingListItems || isOffline"
              @click="toggleShoppingListGroceriesReady"
            >
              {{ shoppingListGroceriesReady ? $t("shopping-list.all-groceries-ready") : $t("shopping-list.mark-all-groceries-ready") }}
            </v-btn>
            <v-btn
              color="primary"
              variant="tonal"
              :prepend-icon="$globals.icons.contentCopy"
              :disabled="!hasShoppingListItems"
              @click="copyListItems('plain')"
            >
              {{ $t("general.copy") }}
            </v-btn>
            <BaseButtonGroup
              class="d-flex"
              :buttons="[
                {
                  icon: $globals.icons.contentCopy,
                  text: '',
                  event: 'edit',
                  children: [
                    {
                      icon: $globals.icons.contentCopy,
                      text: $t('shopping-list.copy-as-text'),
                      event: 'copy-plain',
                    },
                    {
                      icon: $globals.icons.contentCopy,
                      text: $t('shopping-list.copy-as-markdown'),
                      event: 'copy-markdown',
                    },
                  ],
                },
                {
                  icon: $globals.icons.checkboxOutline,
                  text: $t('shopping-list.check-all-items'),
                  event: 'check',
                },
                {
                  icon: $globals.icons.dotsVertical,
                  text: '',
                  event: 'three-dot',
                  children: [
                    {
                      icon: $globals.icons.tags,
                      text: $t('shopping-list.reorder-labels'),
                      event: 'reorder-labels',
                    },
                    {
                      icon: $globals.icons.tags,
                      text: $t('shopping-list.manage-labels'),
                      event: 'manage-labels',
                    },
                  ],
                },
              ]"
              @edit="edit = true"
              @three-dot="threeDot = true"
              @check="openCheckAll"
              @copy-plain="copyListItems('plain')"
              @copy-markdown="copyListItems('markdown')"
              @reorder-labels="toggleReorderLabelsDialog()"
              @manage-labels="$router.push(`/group/data/labels`)"
            />
          </div>
        </div>
      </template>
      <template #title>
        <span class="shopping-list-page-title">{{ shoppingList.name }}</span>
      </template>
    </BasePageTitle>
    <BannerWarning
      v-if="isOffline"
      :title="$t('shopping-list.you-are-offline')"
      :description="$t('shopping-list.you-are-offline-description')"
    />

    <!-- Viewer -->
    <section v-if="!edit" class="py-2 d-flex flex-column ga-4">
      <!-- Create Item -->
      <ShoppingListAddItemForm
        v-if="$vuetify.display.smAndDown"
        v-model="createListItemData"
        class="my-4"
        :labels="allLabels || []"
        :units="allUnits || []"
        :foods="allFoods || []"
        @cancel="createEditorOpen = false"
        @save="createListItem"
      />

      <div v-else>
        <ShoppingListItemEditor
          v-if="createEditorOpen"
          v-model="createListItemData"
          class="my-4"
          :labels="allLabels || []"
          :units="allUnits || []"
          :foods="allFoods || []"
          :allow-delete="false"
          @delete="createEditorOpen = false"
          @cancel="createEditorOpen = false"
          @save="createListItem"
        />
        <InputLabelType
          v-else
          :items="allFoods"
          :label="$t('shopping-list.add-item')"
          :icon="$globals.icons.foods"
          search
          @focus="createEditorOpen = true"
        />
      </div>

      <v-sheet class="shopping-list-items-sheet border-solid border-thin rounded">
        <TransitionGroup name="scroll-x-transition">
          <section
            v-for="(value, key) in itemsByLabel"
            :key="key"
            class="shopping-list-section"
          >
            <div
              class="shopping-list-section-title body-1 font-weight-bold"
              :style="{ backgroundColor: getLabelColor(key) }"
            >
              {{ key }}
            </div>
            <VueDraggable
              :model-value="value"
              handle=".handle"
              :delay="250"
              :delay-on-touch-only="true"
              @start="loadingCounter += 1"
              @end="loadingCounter -= 1"
              @update:model-value="updateIndexUncheckedByLabel(key.toString(), $event)"
            >
              <TransitionGroup name="scroll-x-transition">
                <ShoppingListItem
                  v-for="(item, index) in value"
                  :key="item.id"
                  v-model="value[index]"
                  class="shopping-list-section-item ml-2 my-2 w-auto"
                  :labels="allLabels || []"
                  :units="allUnits || []"
                  :foods="allFoods || []"
                  :recipes="recipeMap"
                  @checked="(item) => {
                    saveListItem(item);
                    if (item.checked) {
                      itemCheckedToast(item);
                    }
                  }"
                  @save="saveListItem"
                  @delete="deleteListItem(item)"
                />
              </TransitionGroup>
            </VueDraggable>
          </section>
        </TransitionGroup>
      </v-sheet>
      <v-sheet
        v-if="listItems.checked && listItems.checked.length > 0"
        class="checked-items-actions border-solid border-thin rounded pa-2"
      >
        <div class="d-flex align-center flex-wrap ga-2">
          <div class="flex-1-0">
            {{ $t('shopping-list.items-checked-count', listItems.checked ? listItems.checked.length : 0) }}
          </div>
          <BaseButtonGroup
            :buttons="[
              {
                icon: $globals.icons.checkboxBlankOutline,
                text: $t('shopping-list.uncheck-all-items'),
                event: 'uncheck',
              },
              {
                icon: $globals.icons.delete,
                text: $t('shopping-list.delete-checked'),
                event: 'delete',
              },
            ]"
            @uncheck="openUncheckAll"
            @delete="openDeleteChecked"
          />
        </div>
      </v-sheet>
    </section>

    <!-- Recipe References -->
    <v-lazy
      v-if="shoppingList.recipeReferences && shoppingList.recipeReferences.length > 0"
      class="mt-6"
    >
      <section>
        <div>
          <span>
            <v-icon start class="mb-1">
              {{ $globals.icons.primary }}
            </v-icon>
          </span>
          {{ $t('shopping-list.linked-recipes-count', shoppingList.recipeReferences
            ? shoppingList.recipeReferences.length
            : 0) }}
        </div>
        <v-divider />
        <RecipeList
          :recipes="recipeList"
          show-description
          :disabled="isOffline"
        >
          <template
            v-for="(recipe, index) in recipeList"
            #[`actions-${recipe.id}`]
            :key="'item-actions-decrease' + recipe.id"
          >
            <v-list-item-action>
              <v-btn
                v-if="recipe"
                icon
                flat
                class="bg-transparent"
                :disabled="isOffline"
                @click.prevent="removeRecipeReferenceToList(recipe.id!)"
              >
                <v-icon color="grey-lighten-1">
                  {{ $globals.icons.minus }}
                </v-icon>
              </v-btn>
            </v-list-item-action>
            <div class="pl-3">
              {{ shoppingList.recipeReferences[index].recipeQuantity }}
            </div>
            <v-list-item-action>
              <v-btn
                icon
                :disabled="isOffline"
                flat
                class="bg-transparent"
                @click.prevent="addRecipeReferenceToList(recipe.id!)"
              >
                <v-icon color="grey-lighten-1">
                  {{ $globals.icons.createAlt }}
                </v-icon>
              </v-btn>
            </v-list-item-action>
          </template>
        </RecipeList>
      </section>
    </v-lazy>
    <WakelockSwitch />
  </v-container>
</template>

<script setup lang="ts">
import { VueDraggable } from "vue-draggable-plus";
import RecipeList from "~/components/Domain/Recipe/RecipeList.vue";
import MultiPurposeLabelSection from "~/components/Domain/ShoppingList/MultiPurposeLabelSection.vue";
import ShoppingListAddItemForm from "~/components/Domain/ShoppingList/ShoppingListAddItemForm.vue";
import ShoppingListItem from "~/components/Domain/ShoppingList/ShoppingListItem.vue";
import ShoppingListItemEditor from "~/components/Domain/ShoppingList/ShoppingListItemEditor.vue";
import { useShoppingListPage } from "~/composables/shopping-list-page/use-shopping-list-page";
import { useLabelStore, useUnitStore, useFoodStore } from "~/composables/store";
import { alert } from "~/composables/use-toast";
import type { ShoppingListItemOut } from "~/lib/api/types/household";

const { mdAndUp } = useDisplay();
const i18n = useI18n();

useSeoMeta({
  title: i18n.t("shopping-list.shopping-list"),
});

const route = useRoute();
const id = route.params.id as string;

const shoppingListPage = useShoppingListPage(id);
const { store: allLabels } = useLabelStore();
const { store: allUnits } = useUnitStore();
const { store: allFoods } = useFoodStore();

function itemCheckedToast(item: ShoppingListItemOut) {
  setTimeout(() => {
    alert.info(
      i18n.t("shopping-list.item-checked-off", { item: item.food?.name || item.note || i18n.t("recipe.ingredient") }),
      undefined,
      {
        timeout: 4000,
        action: {
          message: i18n.t("general.undo"),
          onClick: () => {
            item.checked = false;
            shoppingListPage.saveListItem(item);
          },
        },
      },
    );
  }, 500);
}

const {
  shoppingList,
  state,
  checkAll,
  uncheckAll,
  deleteChecked,
  reorderLabelsDialog,
  localLabels,
  saveLabelOrder,
  cancelLabelOrder,
  updateLabelOrder,
  edit,
  threeDot,
  openCheckAll,
  copyListItems,
  organizeShoppingListWithAI,
  aiOrganizing,
  shoppingListAiOrganized,
  shoppingListGroceriesReady,
  toggleShoppingListGroceriesReady,
  toggleReorderLabelsDialog,
  isOffline,
  createEditorOpen,
  createListItemData,
  createListItem,
  itemsByLabel,
  getLabelColor,
  loadingCounter,
  updateIndexUncheckedByLabel,
  recipeMap,
  saveListItem,
  deleteListItem,
  listItems,
  openUncheckAll,
  openDeleteChecked,
  recipeList,
  removeRecipeReferenceToList,
  addRecipeReferenceToList,
} = shoppingListPage;

const hasShoppingListItems = computed(() => {
  return Boolean(listItems.unchecked.length || listItems.checked.length);
});
</script>

<style>
.number-input-container {
  max-width: 50px;
}

.shopping-list-header {
  align-items: start;
  direction: ltr;
  display: grid;
  grid-template-areas:
    "nav hero spacer"
    "actions actions actions";
  grid-template-columns: minmax(0, 1fr) 120px minmax(0, 1fr);
  row-gap: 12px;
}

.shopping-list-header-nav {
  direction: rtl;
  grid-area: nav;
  justify-self: start;
}

.shopping-list-header-hero {
  display: flex;
  grid-area: hero;
  justify-content: center;
  min-height: 104px;
  pointer-events: none;
}

.shopping-list-header-actions {
  align-items: center;
  direction: rtl;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  grid-area: actions;
  justify-content: flex-end;
  min-height: 40px;
  position: relative;
  z-index: 1;
}

.shopping-list-header-actions > * {
  direction: rtl;
}

.shopping-list-title-block :deep(h2) {
  font-size: 4rem !important;
  line-height: 1;
  margin: 2px 0 0 !important;
}

.shopping-list-title-block :deep(.subtitle-1) {
  display: none;
  margin: 0 !important;
}

.shopping-list-title-block :deep(.v-divider) {
  margin-top: 0 !important;
}

.shopping-list-page-title {
  font-weight: 700;
}

.shopping-list-ai-chip {
  font-weight: 700;
}

@media (max-width: 600px) {
  .shopping-list-header {
    grid-template-areas:
      "nav"
      "actions";
    grid-template-columns: minmax(0, 1fr);
  }

  .shopping-list-header-actions {
    justify-content: flex-end;
  }

  .shopping-list-title-block :deep(h2) {
    font-size: 2.6rem !important;
  }
}

.shopping-list-items-sheet {
  background-color: rgb(var(--v-theme-surface));
  overflow: hidden;
}

.shopping-list-section + .shopping-list-section {
  border-top: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.shopping-list-section-title {
  align-items: center;
  display: flex;
  font-size: 1rem;
  justify-content: flex-start;
  justify-content: start;
  min-height: 44px;
  padding: 0 16px;
  text-align: start;
}

.shopping-list-section-item {
  border-bottom: thin solid rgba(var(--v-border-color), 0.08);
}

.shopping-list-section-item:last-child {
  border-bottom: 0;
}

.checked-items-actions {
  background-color: rgb(var(--v-theme-surface));
}
</style>
