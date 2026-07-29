<template>
  <v-container
    v-if="shoppingListChoices && ready"
    class="narrow-container"
  >
    <ShoppingWebsiteLinksDialog
      v-if="shoppingWebsiteLinkTargetId"
      v-model="shoppingWebsiteLinksDialog"
      entity-type="shopping-list"
      :entity-id="shoppingWebsiteLinkTargetId"
    />
    <BaseDialog
      v-model="state.createDialog"
      :title="$t('shopping-list.create-shopping-list')"
      :icon="$globals.icons.formatListCheck"
      can-submit
      keep-open
      :loading="state.createLoading"
      :submit-disabled="!canSubmitCreateShoppingList"
      @submit="createOne"
      @close="closeCreateShoppingListDialog"
    >
      <v-card-text>
        <v-text-field
          v-model="state.createName"
          autofocus
          :label="$t('shopping-list.new-list')"
          :placeholder="selectedCreateRecipe?.name || $t('shopping-list.new-list')"
        />
        <v-autocomplete
          v-model="state.createRecipeSlug"
          v-model:search="state.createRecipeSearch"
          :items="createRecipeOptions"
          item-title="name"
          item-value="slug"
          clearable
          hide-no-data
          :loading="state.createRecipeSearching"
          :label="$t('shopping-list.link-recipe')"
          :placeholder="$t('shopping-list.search-recipe')"
          :prepend-inner-icon="$globals.icons.search"
          @update:search="searchCreateRecipes"
        />
      </v-card-text>
    </BaseDialog>

    <!-- Settings -->
    <BaseDialog
      v-model="state.ownerDialog"
      :icon="$globals.icons.admin"
      :title="$t('user.edit-user')"
      can-confirm
      @confirm="updateOwner"
    >
      <v-container>
        <v-form>
          <v-select
            v-model="updateUserId"
            :items="allUsers"
            item-title="fullName"
            item-value="id"
            :label="$t('general.owner')"
            :prepend-icon="$globals.icons.user"
          />
        </v-form>
      </v-container>
    </BaseDialog>

    <BaseDialog
      v-model="state.deleteDialog"
      :title="deleteTargetIsMerged ? $t('shopping-list.cancel-merge') : $t('general.confirm')"
      :icon="$globals.icons.alertCircle"
      color="error"
      can-confirm
      @confirm="deleteOne"
    >
      <v-card-text>
        {{ deleteTargetIsMerged ? $t('shopping-list.cancel-merge-confirm') : $t('shopping-list.are-you-sure-you-want-to-delete-this-item') }}
        <v-progress-linear v-if="deletePreviewLoading" indeterminate color="primary" class="mt-4" />
        <template v-else>
          <v-divider v-if="deleteRecipeOptions.length || deleteWebsiteOptions.length" class="my-4" />
          <p v-if="deleteRecipeOptions.length" class="font-weight-medium mb-2">
            {{ $t("shopping-list.delete-linked-recipes") }}
          </p>
          <v-checkbox
            v-for="item in deleteRecipeOptions"
            :key="item.id"
            v-model="selectedDeleteRecipeIds"
            :value="item.id"
            :label="item.name"
            density="compact"
            hide-details
          />
          <p v-if="deleteWebsiteOptions.length" class="font-weight-medium mt-4 mb-2">
            {{ $t("shopping-list.delete-linked-websites") }}
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
            v-if="deleteRecipeOptions.length || deleteWebsiteOptions.length"
            type="info"
            variant="tonal"
            density="compact"
            class="mt-4"
          >
            {{ $t("shopping-list.linked-items-remain-by-default") }}
          </v-alert>
        </template>
      </v-card-text>
    </BaseDialog>

    <BaseDialog
      v-model="state.renameDialog"
      :title="$t('shopping-list.rename-shopping-list')"
      :icon="$globals.icons.edit"
      can-submit
      @submit="renameOne"
    >
      <v-card-text>
        <v-text-field
          v-model="state.renameName"
          autofocus
          :label="$t('shopping-list.list-name')"
          @keyup.enter="renameOne"
        />
      </v-card-text>
    </BaseDialog>

    <BaseDialog
      v-model="state.mergeDialog"
      :title="$t('shopping-list.merge-lists')"
      :icon="$globals.icons.merge"
      can-submit
      keep-open
      :loading="state.mergeLoading"
      :submit-disabled="mergeSelectedListIds.length < 2"
      @submit="mergeSelectedShoppingLists"
      @close="resetMergeDialog"
    >
      <v-card-text>
        <v-text-field
          v-model="state.mergeName"
          :label="$t('shopping-list.merged-list-name')"
          :placeholder="suggestedMergedListName"
        />
        <v-text-field
          v-model="mergeListSearch"
          :label="$t('shopping-list.search-shopping-lists')"
          :prepend-inner-icon="$globals.icons.search"
          variant="outlined"
          density="comfortable"
          clearable
          hide-details
          class="mb-3"
        />
        <div class="shopping-list-selection-list">
          <v-checkbox
            v-for="list in filteredMergeCandidateLists"
            :key="list.id"
            v-model="mergeSelectedListIds"
            :value="list.id"
            :label="list.name || ''"
            hide-details
            density="compact"
          />
          <p v-if="!filteredMergeCandidateLists.length" class="text-medium-emphasis pa-3 mb-0">
            {{ $t("search.no-results") }}
          </p>
        </div>
        <v-alert
          v-if="mergeSelectedListIds.length === 1"
          type="info"
          variant="tonal"
          density="compact"
          class="mt-3"
        >
          {{ $t("shopping-list.select-at-least-two-lists") }}
        </v-alert>
      </v-card-text>
    </BaseDialog>

    <BaseDialog
      v-model="state.bulkDeleteDialog"
      :title="$t('shopping-list.delete-shopping-lists')"
      :icon="$globals.icons.delete"
      color="error"
      can-submit
      keep-open
      :loading="state.bulkDeleteLoading"
      :submit-disabled="!bulkDeleteSelectedListIds.length"
      @submit="deleteSelectedShoppingLists"
      @close="resetBulkDeleteDialog"
    >
      <v-card-text>
        <p class="mb-3">
          {{ $t("shopping-list.choose-lists-to-delete") }}
        </p>
        <v-text-field
          v-model="bulkDeleteListSearch"
          :label="$t('shopping-list.search-shopping-lists')"
          :prepend-inner-icon="$globals.icons.search"
          variant="outlined"
          density="comfortable"
          clearable
          hide-details
          class="mb-3"
        />
        <div class="shopping-list-selection-list">
          <v-checkbox
            v-for="list in filteredBulkDeleteLists"
            :key="list.id"
            v-model="bulkDeleteSelectedListIds"
            :value="list.id"
            hide-details
            density="compact"
          >
            <template #label>
              <span>{{ list.name || "" }}</span>
              <LinkedResourcesButton
                v-if="shoppingListLinkedResourcesCount(list)"
                class="ml-1"
                entity-type="shopping-list"
                :entity-id="list.id"
                :count="shoppingListLinkedResourcesCount(list)"
              />
            </template>
          </v-checkbox>
          <p v-if="!filteredBulkDeleteLists.length" class="text-medium-emphasis pa-3 mb-0">
            {{ $t("search.no-results") }}
          </p>
        </div>
      </v-card-text>
    </BaseDialog>

    <BasePageTitle divider>
      <template #header>
        <v-img
          width="100%"
          max-height="100"
          max-width="100"
          src="/svgs/shopping-cart.svg"
        />
      </template>
      <template #title>
        {{ $t('shopping-list.shopping-lists') }}
      </template>
    </BasePageTitle>

    <v-container class="shopping-list-page-controls px-0 pt-0 pb-4">
      <v-text-field
        v-model="shoppingListSearch"
        class="shopping-list-search"
        density="compact"
        hide-details
        clearable
        :label="$t('shopping-list.search-shopping-lists')"
        :prepend-inner-icon="$globals.icons.search"
      />
      <v-menu :close-on-content-click="false">
        <template #activator="{ props: menuProps }">
          <v-btn
            v-bind="menuProps"
            size="small"
            color="primary"
            variant="tonal"
            :prepend-icon="$globals.icons.sort"
          >
            {{ $t("shopping-list.sort-lists") }}
          </v-btn>
        </template>
        <v-card class="shopping-list-sort-menu">
          <v-card-text>
            <v-select
              v-model="preferences.sortBy"
              :items="shoppingListSortOptions"
              item-title="title"
              item-value="value"
              :label="$t('shopping-list.sort-by')"
              density="compact"
            />
            <v-btn-toggle
              v-model="preferences.sortDirection"
              mandatory
              divided
              density="compact"
              class="mb-4"
            >
              <v-btn value="asc" :prepend-icon="$globals.icons.sortAscending">
                {{ $t("general.sort-ascending") }}
              </v-btn>
              <v-btn value="desc" :prepend-icon="$globals.icons.sortDescending">
                {{ $t("general.sort-descending") }}
              </v-btn>
            </v-btn-toggle>
            <v-select
              v-model="preferences.mergedPlacement"
              :items="mergedPlacementOptions"
              item-title="title"
              item-value="value"
              :label="$t('shopping-list.merged-list-placement')"
              density="compact"
            />
            <v-select
              v-model="preferences.mergedPriority"
              :items="mergedPriorityOptions"
              item-title="title"
              item-value="value"
              :label="$t('shopping-list.sort-priority')"
              :disabled="preferences.mergedPlacement === 'normal'"
              density="compact"
              hide-details
            />
          </v-card-text>
        </v-card>
      </v-menu>
      <v-btn
        size="small"
        class="my-0 mr-4 shopping-list-image-toggle"
        :color="preferences.showItemImages ? 'primary' : 'grey'"
        :variant="preferences.showItemImages ? 'tonal' : 'outlined'"
        :prepend-icon="$globals.icons.fileImage"
        @click="preferences.showItemImages = !preferences.showItemImages"
      >
        {{ $t("recipe.toggle-item-images") }}
      </v-btn>
      <v-switch
        v-model="preferences.openListsInline"
        hide-details
        color="primary"
        density="compact"
        :label="$t('shopping-list.open-lists-inline')"
        class="my-0 mr-4"
      />
      <v-checkbox
        v-model="preferences.viewAllLists"
        hide-details
        :label="$t('general.show-all')"
        class="my-0 mr-4"
      />
      <BaseButton
        create
        class="my-0"
        @click="openCreateShoppingListDialog"
      />
      <v-btn
        color="primary"
        variant="tonal"
        :prepend-icon="$globals.icons.merge"
        :disabled="mergeCandidateLists.length < 2"
        @click="openMergeDialog"
      >
        {{ $t("shopping-list.merge-lists") }}
      </v-btn>
      <v-btn
        color="error"
        variant="tonal"
        :prepend-icon="$globals.icons.delete"
        :disabled="!availableShoppingLists.length"
        @click="openBulkDeleteDialog"
      >
        {{ $t("shopping-list.delete-all") }}
      </v-btn>
    </v-container>

    <v-container v-if="!shoppingListChoices.length">
      <BasePageTitle>
        <template #title>
          {{ $t('shopping-list.no-shopping-lists-found') }}
        </template>
      </BasePageTitle>
    </v-container>

    <BaseListPagination
      v-if="shoppingListChoices.length"
      v-model:page="shoppingListPage"
      v-model:items-per-page="shoppingListsPerPage"
      :total-items="shoppingListTotal"
    />

    <section>
      <div
        v-for="list in paginatedShoppingLists"
        :key="list.id"
        class="shopping-list-group"
      >
        <v-card
          class="my-2 left-border"
          :class="{ 'shopping-list-card--expanded': isExpandedShoppingList(list.id) }"
          :to="preferences.openListsInline ? undefined : `/shopping-lists/${list.id}`"
          @click="openShoppingListCard(list)"
        >
          <v-card-title class="shopping-list-card-title">
            <div class="shopping-list-card-identity">
              <v-icon class="shopping-list-card-cart-icon">
                {{ $globals.icons.cartCheck }}
              </v-icon>
              <span class="shopping-list-card-name">
                {{ list.name }}
              </span>
            </div>
            <div class="shopping-list-card-actions">
              <v-chip
                v-if="isMergedShoppingList(list)"
                size="small"
                color="primary"
                variant="tonal"
                class="shopping-list-merged-chip"
              >
                {{ $t("shopping-list.merged-list") }}
              </v-chip>
              <v-chip
                v-if="isShoppingListGroceriesReady(list)"
                size="small"
                color="success"
                variant="tonal"
                class="shopping-list-ready-chip"
              >
                <v-icon start size="small">
                  {{ $globals.icons.cartCheck }}
                </v-icon>
                {{ $t("shopping-list.all-groceries-ready-short") }}
              </v-chip>
              <v-btn
                v-if="isMergedShoppingList(list)"
                icon
                variant="plain"
                :title="$t('shopping-list.source-lists')"
                :aria-label="$t('shopping-list.source-lists')"
                @click.prevent.stop="toggleMergedSources(list.id)"
              >
                <v-icon>
                  {{ mergedSourcesAreVisible(list) ? $globals.icons.chevronDown : $globals.icons.chevronRight }}
                </v-icon>
              </v-btn>
              <v-btn
                icon
                variant="plain"
                :title="$t('shopping-website.link-websites')"
                :aria-label="$t('shopping-website.link-websites')"
                @click.prevent.stop="openShoppingWebsiteLinks(list.id)"
              >
                <v-icon>
                  {{ $globals.icons.web }}
                </v-icon>
              </v-btn>
              <LinkedResourcesButton
                v-if="shoppingListLinkedResourcesCount(list)"
                entity-type="shopping-list"
                :entity-id="list.id"
                :count="shoppingListLinkedResourcesCount(list)"
              />
              <v-btn
                icon
                variant="plain"
                :title="$t('shopping-list.rename-shopping-list')"
                :aria-label="$t('shopping-list.rename-shopping-list')"
                @click.prevent.stop="openRename(list)"
              >
                <v-icon>
                  {{ $globals.icons.edit }}
                </v-icon>
              </v-btn>
              <v-chip
                size="small"
                :color="isShoppingListAiOrganized(list) ? 'success' : 'grey'"
                :variant="isShoppingListAiOrganized(list) ? 'tonal' : 'outlined'"
                class="shopping-list-ai-chip"
                :title="isShoppingListAiOrganized(list) ? $t('shopping-list.ai-organized') : $t('shopping-list.ai-not-organized')"
              >
                <v-icon start size="small">
                  {{ $globals.icons.robot }}
                </v-icon>
                AI
              </v-chip>
              <v-btn
                icon
                variant="plain"
                color="success"
                :title="$t('shopping-list.organize-with-ai')"
                :aria-label="$t('shopping-list.organize-with-ai')"
                :loading="isOrganizingShoppingList(list.id)"
                @click.prevent.stop="organizeShoppingListById(list.id)"
              >
                <v-icon>
                  {{ $globals.icons.robot }}
                </v-icon>
              </v-btn>
              <v-btn
                icon
                variant="plain"
                :title="$t('general.copy')"
                :aria-label="$t('general.copy')"
                :loading="isCopyingShoppingList(list.id)"
                @click.prevent.stop="copyShoppingListById(list.id)"
              >
                <v-icon>
                  {{ $globals.icons.contentCopy }}
                </v-icon>
              </v-btn>
              <v-btn
                icon
                variant="plain"
                :title="$t('general.owner')"
                :aria-label="$t('general.owner')"
                @click.prevent.stop="toggleOwnerDialog(list)"
              >
                <v-icon>
                  {{ $globals.icons.user }}
                </v-icon>
              </v-btn>
              <v-btn
                icon
                variant="plain"
                color="error"
                :title="isMergedShoppingList(list) ? $t('shopping-list.cancel-merge') : $t('general.delete')"
                :aria-label="isMergedShoppingList(list) ? $t('shopping-list.cancel-merge') : $t('general.delete')"
                @click.prevent.stop="openDelete(list.id)"
              >
                <v-icon>
                  {{ $globals.icons.delete }}
                </v-icon>
              </v-btn>
            </div>
          </v-card-title>
          <v-expand-transition>
            <div
              v-if="preferences.openListsInline && isExpandedShoppingList(list.id)"
              class="shopping-list-inline-panel"
              @click.stop
            >
              <v-progress-linear
                v-if="isLoadingExpandedShoppingList(list.id)"
                indeterminate
                color="primary"
                class="my-2"
              />
              <template v-else-if="expandedShoppingLists[list.id]">
                <div class="shopping-list-inline-toolbar">
                  <v-btn
                    size="small"
                    variant="text"
                    :to="`/shopping-lists/${list.id}`"
                  >
                    {{ $t("shopping-list.open-full-list") }}
                  </v-btn>
                  <v-btn
                    size="small"
                    class="shopping-list-ready-action"
                    :class="{ 'shopping-list-ready-action--active': isShoppingListGroceriesReady(expandedShoppingLists[list.id]) }"
                    :color="isShoppingListGroceriesReady(expandedShoppingLists[list.id]) ? 'success' : 'grey'"
                    :variant="isShoppingListGroceriesReady(expandedShoppingLists[list.id]) ? 'tonal' : 'outlined'"
                    :prepend-icon="$globals.icons.cartCheck"
                    :loading="isUpdatingShoppingListReady(list.id)"
                    :disabled="!expandedShoppingLists[list.id].listItems?.length"
                    @click.stop.prevent="setShoppingListGroceriesReady(expandedShoppingLists[list.id], true)"
                  >
                    {{ isShoppingListGroceriesReady(expandedShoppingLists[list.id]) ? $t("shopping-list.all-groceries-ready") : $t("shopping-list.mark-all-groceries-ready") }}
                  </v-btn>
                  <v-btn
                    v-if="isShoppingListGroceriesReady(expandedShoppingLists[list.id])"
                    size="small"
                    class="shopping-list-ready-action shopping-list-ready-action--reset"
                    color="warning"
                    variant="outlined"
                    :prepend-icon="$globals.icons.refresh"
                    :loading="isUpdatingShoppingListReady(list.id)"
                    :disabled="!expandedShoppingLists[list.id].listItems?.length"
                    @click.stop.prevent="setShoppingListGroceriesReady(expandedShoppingLists[list.id], false)"
                  >
                    {{ $t("shopping-list.reset-groceries-ready") }}
                  </v-btn>
                </div>
                <template v-if="!expandedShoppingLists[list.id].listItems?.length">
                  <div class="text-medium-emphasis py-4 text-center">
                    {{ $t("shopping-list.no-items-in-list") }}
                  </div>
                </template>
                <template v-else>
                  <div
                    v-for="group in inlineShoppingListGroups(expandedShoppingLists[list.id])"
                    :key="group.label"
                    class="shopping-list-inline-group"
                  >
                    <div class="shopping-list-inline-group-title">
                      <span>{{ group.label }}</span>
                      <span class="shopping-list-inline-group-count">{{ group.items.length }}</span>
                    </div>
                    <div
                      v-for="item in group.items"
                      :key="item.id"
                      class="shopping-list-inline-item"
                      :class="{ 'shopping-list-inline-item--checked': item.checked }"
                    >
                      <v-checkbox-btn
                        :model-value="item.checked"
                        density="compact"
                        class="shopping-list-inline-checkbox"
                        @click.stop.prevent="toggleInlineShoppingListItem(list.id, item)"
                      />
                      <template v-if="isEditingInlineShoppingListItem(item.id)">
                        <v-text-field
                          v-model="inlineShoppingListItemDrafts[item.id]"
                          density="compact"
                          hide-details
                          class="shopping-list-inline-edit-input"
                          autofocus
                          @keydown.enter.stop.prevent="saveInlineShoppingListItemName(list.id, item)"
                          @keydown.esc.stop.prevent="cancelInlineShoppingListItemEdit(item.id)"
                        />
                        <v-btn
                          icon
                          size="x-small"
                          variant="text"
                          color="success"
                          class="shopping-list-inline-action"
                          :loading="isUpdatingInlineShoppingListItem(item.id)"
                          @click.stop.prevent="saveInlineShoppingListItemName(list.id, item)"
                        >
                          <v-icon>{{ $globals.icons.save }}</v-icon>
                        </v-btn>
                        <v-btn
                          icon
                          size="x-small"
                          variant="text"
                          class="shopping-list-inline-action"
                          :disabled="isUpdatingInlineShoppingListItem(item.id)"
                          @click.stop.prevent="cancelInlineShoppingListItemEdit(item.id)"
                        >
                          <v-icon>{{ $globals.icons.close }}</v-icon>
                        </v-btn>
                      </template>
                      <template v-else>
                        <ItemImageThumb
                          v-if="preferences.showItemImages"
                          :src="itemImage(item.groupId, 'food', inlineShoppingListItemImageName(item))"
                          :alt="formatInlineShoppingListItem(item)"
                        />
                        <span class="shopping-list-inline-item-text">{{ formatInlineShoppingListItem(item) }}</span>
                        <v-spacer />
                        <v-btn
                          icon
                          size="x-small"
                          variant="text"
                          class="shopping-list-inline-action"
                          :title="$t('general.edit')"
                          :aria-label="$t('general.edit')"
                          @click.stop.prevent="startInlineShoppingListItemEdit(item)"
                        >
                          <v-icon>{{ $globals.icons.edit }}</v-icon>
                        </v-btn>
                        <v-btn
                          icon
                          size="x-small"
                          variant="text"
                          color="error"
                          class="shopping-list-inline-action"
                          :loading="isUpdatingInlineShoppingListItem(item.id)"
                          :title="$t('general.delete')"
                          :aria-label="$t('general.delete')"
                          @click.stop.prevent="deleteInlineShoppingListItem(list.id, item)"
                        >
                          <v-icon>{{ $globals.icons.delete }}</v-icon>
                        </v-btn>
                      </template>
                    </div>
                  </div>
                </template>
              </template>
            </div>
          </v-expand-transition>
        </v-card>
        <v-expand-transition>
          <div
            v-if="isMergedShoppingList(list) && mergedSourcesAreVisible(list)"
            class="shopping-list-source-rows"
          >
            <button
              v-for="source in mergedSourceLists(list)"
              :key="source.id"
              type="button"
              class="shopping-list-source-row"
              @click="navigateTo(`/shopping-lists/${source.id}`)"
            >
              <v-icon size="small">
                {{ $globals.icons.cartCheck }}
              </v-icon>
              <span class="shopping-list-source-name">{{ source.name }}</span>
              <v-icon size="small">
                {{ $globals.icons.openInNew }}
              </v-icon>
            </button>
          </div>
        </v-expand-transition>
      </div>
    </section>
  </v-container>
</template>

<script setup lang="ts">
import type { ShoppingListItemOut, ShoppingListOut } from "~/lib/api/types/household";
import type { Recipe } from "~/lib/api/types/recipe";
import ItemImageThumb from "~/components/Domain/ItemImages/ItemImageThumb.vue";
import { useStaticRoutes } from "~/composables/api";
import { useUserApi } from "~/composables/api/api-client";
import { useAsyncKey } from "~/composables/use-utils";
import { useShoppingListPreferences } from "~/composables/use-users/preferences";
import { alert } from "~/composables/use-toast";
import { useShoppingListCopy } from "~/composables/shopping-list-page/sub-composables/use-shopping-list-copy";
import {
  buildShoppingListReadyExtras,
  isShoppingListGroceriesReady,
  useShoppingListAvailability,
} from "~/composables/shopping-list-page/use-shopping-list-availability";
import type { UserOut } from "~/lib/api/types/user";
import type { ShoppingListDeletePreview } from "~/lib/api/user/group-shopping-lists";
import LinkedResourcesButton from "~/components/Domain/LinkedResources/LinkedResourcesButton.vue";

const auth = useMealieAuth();
const i18n = useI18n();
const ready = ref(false);
const userApi = useUserApi();
const route = useRoute();
const router = useRouter();
const { itemImage } = useStaticRoutes();
const { copyShoppingList } = useShoppingListCopy();
const copyingShoppingListIds = ref<Set<string>>(new Set());
const organizingShoppingListIds = ref<Set<string>>(new Set());
const expandedShoppingListIds = ref<Set<string>>(new Set());
const expandedMergedSourceIds = ref<Set<string>>(new Set());
const loadingExpandedShoppingListIds = ref<Set<string>>(new Set());
const updatingReadyShoppingListIds = ref<Set<string>>(new Set());
const editingInlineShoppingListItemIds = ref<Set<string>>(new Set());
const updatingInlineShoppingListItemIds = ref<Set<string>>(new Set());
const inlineShoppingListItemDrafts = ref<Record<string, string>>({});
const expandedShoppingLists = ref<Record<string, ShoppingListOut>>({});
const shoppingListSearch = ref("");
const mergeListSearch = ref("");
const bulkDeleteListSearch = ref("");
const shoppingWebsiteLinksDialog = ref(false);
const shoppingWebsiteLinkTargetId = ref("");
const mergeSelectedListIds = ref<string[]>([]);
const bulkDeleteSelectedListIds = ref<string[]>([]);
const deletePreview = ref<ShoppingListDeletePreview>();
const deletePreviewLoading = ref(false);
const selectedDeleteRecipeIds = ref<string[]>([]);
const selectedDeleteWebsiteIds = ref<string[]>([]);
const { updateAvailabilityForListName } = useShoppingListAvailability();

function openShoppingWebsiteLinks(id: string) {
  shoppingWebsiteLinkTargetId.value = id;
  shoppingWebsiteLinksDialog.value = true;
}

function shoppingListLinkedResourcesCount(list: ShoppingListOut) {
  return Number(list.extras?.linkedResourcesCount || 0);
}

useSeoMeta({
  title: i18n.t("shopping-list.shopping-list"),
});

const overrideDisableRedirect = ref(false);
const disableRedirect = computed(() => route.query.disableRedirect === "true" || overrideDisableRedirect.value);
const preferences = useShoppingListPreferences();

const shoppingListSortOptions = computed(() => [
  { title: i18n.t("general.created"), value: "createdAt" },
  { title: i18n.t("general.name"), value: "name" },
  { title: i18n.t("shopping-list.item-count"), value: "itemCount" },
]);
const mergedPlacementOptions = computed(() => [
  { title: i18n.t("shopping-list.merged-sort-normal"), value: "normal" },
  { title: i18n.t("shopping-list.merged-sort-first"), value: "first" },
  { title: i18n.t("shopping-list.merged-sort-last"), value: "last" },
]);
const mergedPriorityOptions = computed(() => [
  { title: i18n.t("shopping-list.primary-priority"), value: "primary" },
  { title: i18n.t("shopping-list.secondary-priority"), value: "secondary" },
]);

const state = reactive({
  createName: "",
  createRecipeSlug: null as string | null,
  createRecipeSearch: "",
  createRecipeSearching: false,
  createLoading: false,
  createDialog: false,
  deleteDialog: false,
  deleteTarget: "",
  renameDialog: false,
  renameName: "",
  renameTarget: null as ShoppingListOut | null,
  mergeDialog: false,
  mergeLoading: false,
  mergeName: "",
  bulkDeleteDialog: false,
  bulkDeleteLoading: false,
  ownerDialog: false,
  ownerTarget: ref<ShoppingListOut | null>(null),
});
const createRecipeOptions = ref<Recipe[]>([]);
let createRecipeSearchTimer: ReturnType<typeof setTimeout> | null = null;
let createRecipeSearchRequest = 0;

const selectedCreateRecipe = computed(() => {
  return createRecipeOptions.value.find(recipe => recipe.slug === state.createRecipeSlug) || null;
});

const canSubmitCreateShoppingList = computed(() => {
  return Boolean(state.createName.trim() || selectedCreateRecipe.value);
});

const { data: shoppingLists } = useAsyncData(useAsyncKey(), async () => {
  return await fetchShoppingLists();
});

const availableShoppingLists = computed(() => {
  if (!shoppingLists.value) {
    return [];
  }

  return shoppingLists.value.filter(list => preferences.value.viewAllLists || list.userId === auth.user.value?.id);
});
const availableShoppingListsById = computed(() => new Map(
  availableShoppingLists.value.map(list => [list.id, list]),
));

const mergedSourceIds = computed(() => {
  const sourceIds = new Set<string>();
  availableShoppingLists.value.forEach((list) => {
    if (!isMergedShoppingList(list)) {
      return;
    }
    parseMergedSourceIds(list).forEach(sourceId => sourceIds.add(sourceId));
  });
  return sourceIds;
});

const mergeCandidateLists = computed(() => {
  return availableShoppingLists.value.filter(list => !isMergedShoppingList(list));
});

function shoppingListMatchesSearch(list: ShoppingListOut, searchValue: string) {
  const query = searchValue.trim().toLocaleLowerCase();
  if (!query) {
    return true;
  }

  return (list.name || "").toLocaleLowerCase().includes(query);
}

const filteredMergeCandidateLists = computed(() =>
  mergeCandidateLists.value.filter(list => shoppingListMatchesSearch(list, mergeListSearch.value)),
);

const filteredBulkDeleteLists = computed(() =>
  availableShoppingLists.value.filter(list => shoppingListMatchesSearch(list, bulkDeleteListSearch.value)),
);

const shoppingListChoices = computed(() => {
  const search = shoppingListSearch.value.trim().toLocaleLowerCase();
  const matches = availableShoppingLists.value.filter((list) => {
    if (mergedSourceIds.value.has(list.id)) {
      return false;
    }
    if (!search) {
      return true;
    }

    const matchesName = (list.name || "").toLocaleLowerCase().includes(search);
    const matchesSource = isMergedShoppingList(list)
      && mergedSourceLists(list).some(source => (source.name || "").toLocaleLowerCase().includes(search));
    return matchesName || matchesSource;
  });

  return matches.sort(compareShoppingLists);
});
const {
  page: shoppingListPage,
  itemsPerPage: shoppingListsPerPage,
  totalItems: shoppingListTotal,
  paginatedItems: paginatedShoppingLists,
} = useListPagination(shoppingListChoices);

function shoppingListItemCount(list: ShoppingListOut) {
  return Number(list.itemCount ?? list.listItems?.length ?? 0);
}

function compareMergedPlacement(left: ShoppingListOut, right: ShoppingListOut) {
  if (preferences.value.mergedPlacement === "normal") {
    return 0;
  }

  const leftMerged = isMergedShoppingList(left) ? 1 : 0;
  const rightMerged = isMergedShoppingList(right) ? 1 : 0;
  const direction = preferences.value.mergedPlacement === "first" ? -1 : 1;
  return (leftMerged - rightMerged) * direction;
}

function compareShoppingListField(left: ShoppingListOut, right: ShoppingListOut) {
  const direction = preferences.value.sortDirection === "asc" ? 1 : -1;
  let comparison = 0;

  if (preferences.value.sortBy === "name") {
    comparison = (left.name || "").localeCompare(right.name || "", i18n.locale.value, { sensitivity: "base" });
  }
  else if (preferences.value.sortBy === "itemCount") {
    comparison = shoppingListItemCount(left) - shoppingListItemCount(right);
  }
  else {
    comparison = new Date(left.createdAt || 0).getTime() - new Date(right.createdAt || 0).getTime();
  }

  return comparison * direction;
}

function compareShoppingLists(left: ShoppingListOut, right: ShoppingListOut) {
  const mergedComparison = compareMergedPlacement(left, right);
  const fieldComparison = compareShoppingListField(left, right);
  const comparisons = preferences.value.mergedPriority === "primary"
    ? [mergedComparison, fieldComparison]
    : [fieldComparison, mergedComparison];

  return comparisons.find(value => value !== 0)
    ?? (left.name || "").localeCompare(right.name || "", i18n.locale.value, { sensitivity: "base" });
}

const suggestedMergedListName = computed(() => {
  const sourceNames = mergeSelectedListIds.value
    .map(id => availableShoppingListsById.value.get(id)?.name)
    .filter(Boolean)
    .join(" + ");
  return sourceNames
    ? i18n.t("shopping-list.merged-list-name-with-sources", { sources: sourceNames })
    : i18n.t("shopping-list.merged-list");
});

const deleteTargetIsMerged = computed(() => {
  const target = availableShoppingListsById.value.get(state.deleteTarget);
  return Boolean(target && isMergedShoppingList(target));
});
const deleteRecipeOptions = computed(() => (deletePreview.value?.recipeIds || []).map((id, index) => ({
  id,
  name: deletePreview.value?.recipeNames[index] || id,
})));
const deleteWebsiteOptions = computed(() => (deletePreview.value?.websiteIds || []).map((id, index) => ({
  id,
  name: deletePreview.value?.websiteNames[index] || id,
})));

// This has to appear before the shoppingListChoices watcher, otherwise that runs first and the redirect is not disabled
watch(
  () => preferences.value.viewAllLists,
  () => {
    overrideDisableRedirect.value = true;
  },
);

watch(
  () => preferences.value.openListsInline,
  () => {
    overrideDisableRedirect.value = true;
    if (!preferences.value.openListsInline) {
      clearExpandedShoppingLists();
    }
  },
);

watch(
  () => route.query.create,
  () => {
    openCreateDialogFromRoute();
  },
);

watch(
  () => state.createRecipeSlug,
  () => {
    if (!state.createName.trim() && selectedCreateRecipe.value?.name) {
      state.createName = selectedCreateRecipe.value.name;
    }
  },
);

onMounted(() => {
  openCreateDialogFromRoute();
});

onUnmounted(() => {
  if (createRecipeSearchTimer) {
    clearTimeout(createRecipeSearchTimer);
    createRecipeSearchTimer = null;
  }
  createRecipeSearchRequest += 1;
  createRecipeOptions.value = [];
  clearExpandedShoppingLists();
  expandedMergedSourceIds.value = new Set();
  updatingReadyShoppingListIds.value = new Set();
  editingInlineShoppingListItemIds.value = new Set();
  updatingInlineShoppingListItemIds.value = new Set();
  inlineShoppingListItemDrafts.value = {};
});

watch(
  () => shoppingListChoices.value,
  () => {
    if (!preferences.value.openListsInline && !disableRedirect.value && availableShoppingLists.value.length === 1) {
      navigateTo(`/shopping-lists/${availableShoppingLists.value[0].id}`);
    }
    else {
      ready.value = true;
    }
  },
  {
    deep: true,
  },
);

async function fetchShoppingLists() {
  const { data } = await userApi.shopping.lists.getAll(1, -1, { orderBy: "name", orderDirection: "asc" });

  if (!data) {
    return [];
  }

  return data.items;
}

async function refresh() {
  shoppingLists.value = await fetchShoppingLists();
  pruneExpandedShoppingLists();
}

function parseStringArrayExtra(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map(String).filter(Boolean);
  }
  if (typeof value !== "string" || !value.trim()) {
    return [];
  }

  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed.map(String).filter(Boolean) : [];
  }
  catch {
    return [];
  }
}

function isMergedShoppingList(list: ShoppingListOut) {
  const value = list.extras?.isMergedList;
  return value === true || value === "true";
}

function parseMergedSourceIds(list: ShoppingListOut) {
  return parseStringArrayExtra(list.extras?.mergedFromListIds);
}

function mergedSourceLists(list: ShoppingListOut) {
  return parseMergedSourceIds(list)
    .map(sourceId => availableShoppingListsById.value.get(sourceId))
    .filter((source): source is ShoppingListOut => Boolean(source));
}

function toggleMergedSources(id: string) {
  const next = new Set(expandedMergedSourceIds.value);
  if (next.has(id)) {
    next.delete(id);
  }
  else {
    next.add(id);
  }
  expandedMergedSourceIds.value = next;
}

function mergedSourcesAreVisible(list: ShoppingListOut) {
  if (expandedMergedSourceIds.value.has(list.id)) {
    return true;
  }

  const search = shoppingListSearch.value.trim().toLocaleLowerCase();
  return Boolean(search && mergedSourceLists(list).some(
    source => (source.name || "").toLocaleLowerCase().includes(search),
  ));
}

function resetMergeDialog() {
  state.mergeDialog = false;
  state.mergeLoading = false;
  state.mergeName = "";
  mergeListSearch.value = "";
  mergeSelectedListIds.value = [];
}

function openMergeDialog() {
  resetMergeDialog();
  state.mergeDialog = true;
}

async function mergeSelectedShoppingLists() {
  if (mergeSelectedListIds.value.length < 2 || state.mergeLoading) {
    return;
  }

  state.mergeLoading = true;
  try {
    const { data, error } = await userApi.shopping.lists.merge({
      sourceListIds: [...mergeSelectedListIds.value],
      name: state.mergeName.trim() || suggestedMergedListName.value,
    });
    if (error || !data) {
      alert.error(i18n.t("shopping-list.merge-lists-failed"));
      return;
    }

    const mergedId = data.id;
    resetMergeDialog();
    expandedMergedSourceIds.value = new Set([...expandedMergedSourceIds.value, mergedId]);
    await refresh();
    window.dispatchEvent(new CustomEvent("mealie:organizers-updated"));
    alert.success(i18n.t("shopping-list.merge-lists-complete"));
  }
  finally {
    state.mergeLoading = false;
  }
}

function resetBulkDeleteDialog() {
  state.bulkDeleteDialog = false;
  state.bulkDeleteLoading = false;
  bulkDeleteListSearch.value = "";
  bulkDeleteSelectedListIds.value = [];
}

function openBulkDeleteDialog() {
  resetBulkDeleteDialog();
  bulkDeleteSelectedListIds.value = availableShoppingLists.value.map(list => list.id);
  state.bulkDeleteDialog = true;
}

async function deleteSelectedShoppingLists() {
  if (!bulkDeleteSelectedListIds.value.length || state.bulkDeleteLoading) {
    return;
  }

  state.bulkDeleteLoading = true;
  try {
    const selectedIds = new Set(bulkDeleteSelectedListIds.value);
    const listsToDelete = availableShoppingLists.value.filter(list => selectedIds.has(list.id));
    const { data, error } = await userApi.shopping.lists.deleteMany(bulkDeleteSelectedListIds.value);
    if (error || !data) {
      alert.error(i18n.t("shopping-list.delete-lists-failed"));
      return;
    }

    listsToDelete.forEach(list => updateAvailabilityForListName(list.name, false));
    resetBulkDeleteDialog();
    clearExpandedShoppingLists();
    expandedMergedSourceIds.value = new Set();
    await refresh();
    window.dispatchEvent(new CustomEvent("mealie:organizers-updated"));
  }
  finally {
    state.bulkDeleteLoading = false;
  }
}

function setShoppingListCopying(id: string, copying: boolean) {
  const next = new Set(copyingShoppingListIds.value);
  if (copying) {
    next.add(id);
  }
  else {
    next.delete(id);
  }
  copyingShoppingListIds.value = next;
}

function isCopyingShoppingList(id: string) {
  return copyingShoppingListIds.value.has(id);
}

function setShoppingListOrganizing(id: string, organizing: boolean) {
  const next = new Set(organizingShoppingListIds.value);
  if (organizing) {
    next.add(id);
  }
  else {
    next.delete(id);
  }
  organizingShoppingListIds.value = next;
}

function isOrganizingShoppingList(id: string) {
  return organizingShoppingListIds.value.has(id);
}

function isShoppingListAiOrganized(list: ShoppingListOut) {
  const value = list.extras?.aiOrganized;
  return value === true || value === "true";
}

function replaceShoppingList(updatedList: ShoppingListOut) {
  if (shoppingLists.value) {
    shoppingLists.value = shoppingLists.value.map(list => list.id === updatedList.id ? { ...list, ...updatedList } : list);
  }

  if (expandedShoppingLists.value[updatedList.id]) {
    expandedShoppingLists.value = {
      ...expandedShoppingLists.value,
      [updatedList.id]: updatedList,
    };
  }
}

function setExpandedShoppingListLoading(id: string, loading: boolean) {
  const next = new Set(loadingExpandedShoppingListIds.value);
  if (loading) {
    next.add(id);
  }
  else {
    next.delete(id);
  }
  loadingExpandedShoppingListIds.value = next;
}

function setShoppingListReadyUpdating(id: string, updating: boolean) {
  const next = new Set(updatingReadyShoppingListIds.value);
  if (updating) {
    next.add(id);
  }
  else {
    next.delete(id);
  }
  updatingReadyShoppingListIds.value = next;
}

function isExpandedShoppingList(id: string) {
  return expandedShoppingListIds.value.has(id);
}

function isLoadingExpandedShoppingList(id: string) {
  return loadingExpandedShoppingListIds.value.has(id);
}

function isUpdatingShoppingListReady(id: string) {
  return updatingReadyShoppingListIds.value.has(id);
}

function setInlineShoppingListItemUpdating(id: string, updating: boolean) {
  const next = new Set(updatingInlineShoppingListItemIds.value);
  if (updating) {
    next.add(id);
  }
  else {
    next.delete(id);
  }
  updatingInlineShoppingListItemIds.value = next;
}

function isUpdatingInlineShoppingListItem(id: string) {
  return updatingInlineShoppingListItemIds.value.has(id);
}

function isEditingInlineShoppingListItem(id: string) {
  return editingInlineShoppingListItemIds.value.has(id);
}

function startInlineShoppingListItemEdit(item: ShoppingListItemOut) {
  const next = new Set(editingInlineShoppingListItemIds.value);
  next.add(item.id);
  editingInlineShoppingListItemIds.value = next;
  inlineShoppingListItemDrafts.value = {
    ...inlineShoppingListItemDrafts.value,
    [item.id]: formatInlineShoppingListItem(item),
  };
}

function cancelInlineShoppingListItemEdit(id: string) {
  const next = new Set(editingInlineShoppingListItemIds.value);
  next.delete(id);
  editingInlineShoppingListItemIds.value = next;
  inlineShoppingListItemDrafts.value = Object.fromEntries(
    Object.entries(inlineShoppingListItemDrafts.value).filter(([itemId]) => itemId !== id),
  );
}

function removeExpandedShoppingList(id: string) {
  const nextExpanded = new Set(expandedShoppingListIds.value);
  nextExpanded.delete(id);
  expandedShoppingListIds.value = nextExpanded;

  if (expandedShoppingLists.value[id]) {
    expandedShoppingLists.value = Object.fromEntries(
      Object.entries(expandedShoppingLists.value).filter(([listId]) => listId !== id),
    );
  }
}

function clearExpandedShoppingLists() {
  expandedShoppingListIds.value = new Set();
  loadingExpandedShoppingListIds.value = new Set();
  expandedShoppingLists.value = {};
}

function pruneExpandedShoppingLists() {
  const currentIds = new Set(shoppingLists.value?.map(list => list.id) || []);
  expandedShoppingListIds.value.forEach((id) => {
    if (!currentIds.has(id)) {
      removeExpandedShoppingList(id);
    }
  });
}

async function openShoppingListCard(list: ShoppingListOut) {
  if (!preferences.value.openListsInline) {
    return;
  }

  const nextExpanded = new Set(expandedShoppingListIds.value);
  if (nextExpanded.has(list.id)) {
    removeExpandedShoppingList(list.id);
    return;
  }

  nextExpanded.add(list.id);
  expandedShoppingListIds.value = nextExpanded;

  if (!expandedShoppingLists.value[list.id]) {
    await loadExpandedShoppingList(list.id);
  }
}

async function loadExpandedShoppingList(id: string) {
  if (isLoadingExpandedShoppingList(id)) {
    return;
  }

  setExpandedShoppingListLoading(id, true);
  try {
    const { data } = await userApi.shopping.lists.getOne(id);
    if (data) {
      expandedShoppingLists.value = {
        ...expandedShoppingLists.value,
        [id]: data,
      };
      replaceShoppingList(data);
    }
    else {
      alert.error(i18n.t("events.something-went-wrong"));
    }
  }
  finally {
    setExpandedShoppingListLoading(id, false);
  }
}

function inlineShoppingListGroups(list?: ShoppingListOut) {
  const noLabelText = i18n.t("shopping-list.no-label");
  const labelOrder = list?.labelSettings?.map(labelSetting => labelSetting.label.name).filter(Boolean) || [];
  const grouped = new Map<string, ShoppingListItemOut[]>();

  (list?.listItems || []).forEach((item) => {
    const label = item.label?.name || noLabelText;
    const labelItems = grouped.get(label) || [];
    labelItems.push(item);
    grouped.set(label, labelItems);
  });

  const groups: Array<{ label: string; items: ShoppingListItemOut[] }> = [];
  if (grouped.has(noLabelText)) {
    groups.push({ label: noLabelText, items: [...grouped.get(noLabelText)!].sort(sortInlineShoppingListItems) });
    grouped.delete(noLabelText);
  }

  labelOrder.forEach((label) => {
    if (grouped.has(label)) {
      groups.push({ label, items: [...grouped.get(label)!].sort(sortInlineShoppingListItems) });
      grouped.delete(label);
    }
  });

  grouped.forEach((items, label) => {
    groups.push({ label, items: [...items].sort(sortInlineShoppingListItems) });
  });

  return groups;
}

function sortInlineShoppingListItems(a: ShoppingListItemOut, b: ShoppingListItemOut) {
  if (Boolean(a.checked) !== Boolean(b.checked)) {
    return a.checked ? 1 : -1;
  }

  const posA = a.position ?? 0;
  const posB = b.position ?? 0;
  if (posA !== posB) {
    return posA - posB;
  }

  return formatInlineShoppingListItem(a).localeCompare(formatInlineShoppingListItem(b));
}

function formatInlineShoppingListItem(item: ShoppingListItemOut) {
  if (item.display) {
    return item.display;
  }

  const amount = item.quantity ? String(item.quantity) : "";
  return [amount, item.unit?.name, item.food?.name, item.note].filter(Boolean).join(" ");
}

function inlineShoppingListItemImageName(item: ShoppingListItemOut) {
  return item.food?.name || item.display || item.note || "";
}

function replaceInlineShoppingListItem(listId: string, item: ShoppingListItemOut) {
  const list = expandedShoppingLists.value[listId];
  if (!list?.listItems) {
    return;
  }

  const nextList = {
    ...list,
    listItems: list.listItems.map(existingItem => existingItem.id === item.id ? item : existingItem),
  };
  expandedShoppingLists.value = {
    ...expandedShoppingLists.value,
    [listId]: nextList,
  };
}

function removeInlineShoppingListItem(listId: string, itemId: string) {
  const list = expandedShoppingLists.value[listId];
  if (!list?.listItems) {
    return;
  }

  const nextList = {
    ...list,
    listItems: list.listItems.filter(existingItem => existingItem.id !== itemId),
  };
  expandedShoppingLists.value = {
    ...expandedShoppingLists.value,
    [listId]: nextList,
  };
}

async function saveInlineShoppingListItemName(listId: string, item: ShoppingListItemOut) {
  if (isUpdatingInlineShoppingListItem(item.id)) {
    return;
  }

  const draft = (inlineShoppingListItemDrafts.value[item.id] || "").trim();
  if (!draft) {
    return;
  }

  const originalItem = { ...item };
  const optimisticItem = {
    ...item,
    display: draft,
    food: null,
    foodId: null,
    note: draft,
    quantity: 0,
    unit: null,
    unitId: null,
    updatedAt: new Date().toISOString(),
  };

  setInlineShoppingListItemUpdating(item.id, true);
  replaceInlineShoppingListItem(listId, optimisticItem);
  try {
    const { data, error } = await userApi.shopping.items.updateOne(item.id, optimisticItem);
    if (error || !data) {
      replaceInlineShoppingListItem(listId, originalItem);
      alert.error(i18n.t("events.something-went-wrong"));
      return;
    }

    replaceInlineShoppingListItem(listId, data);
    cancelInlineShoppingListItemEdit(item.id);
  }
  finally {
    setInlineShoppingListItemUpdating(item.id, false);
  }
}

async function deleteInlineShoppingListItem(listId: string, item: ShoppingListItemOut) {
  if (isUpdatingInlineShoppingListItem(item.id)) {
    return;
  }

  const list = expandedShoppingLists.value[listId];
  const originalItems = [...(list?.listItems || [])];
  setInlineShoppingListItemUpdating(item.id, true);
  removeInlineShoppingListItem(listId, item.id);
  cancelInlineShoppingListItemEdit(item.id);
  try {
    const { error } = await userApi.shopping.items.deleteOne(item.id);
    if (error) {
      if (list) {
        expandedShoppingLists.value = {
          ...expandedShoppingLists.value,
          [listId]: { ...list, listItems: originalItems },
        };
      }
      alert.error(i18n.t("events.something-went-wrong"));
    }
  }
  finally {
    setInlineShoppingListItemUpdating(item.id, false);
  }
}

async function toggleInlineShoppingListItem(listId: string, item: ShoppingListItemOut) {
  const originalItem = { ...item };
  const optimisticItem = {
    ...item,
    checked: !item.checked,
    updatedAt: new Date().toISOString(),
  };

  replaceInlineShoppingListItem(listId, optimisticItem);
  const { data, error } = await userApi.shopping.items.updateOne(item.id, optimisticItem);
  if (error || !data) {
    replaceInlineShoppingListItem(listId, originalItem);
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }

  replaceInlineShoppingListItem(listId, data);
}

async function setShoppingListGroceriesReady(list: ShoppingListOut, nextReady: boolean) {
  if (isUpdatingShoppingListReady(list.id)) {
    return;
  }

  setShoppingListReadyUpdating(list.id, true);
  try {
    const { data: fullList } = await userApi.shopping.lists.getOne(list.id);
    const sourceList = fullList || list;
    if (isShoppingListGroceriesReady(sourceList) === nextReady) {
      return;
    }

    const { data, error } = await userApi.shopping.lists.updateOne(
      list.id,
      {
        ...sourceList,
        extras: buildShoppingListReadyExtras(sourceList, nextReady),
      },
    );

    if (error || !data) {
      alert.error(i18n.t("events.something-went-wrong"));
      return;
    }

    replaceShoppingList(data);
    updateAvailabilityForListName(data.name, nextReady);
    window.dispatchEvent(new CustomEvent("mealie:organizers-updated"));
  }
  finally {
    setShoppingListReadyUpdating(list.id, false);
  }
}

async function copyShoppingListById(id: string) {
  if (isCopyingShoppingList(id)) {
    return;
  }

  setShoppingListCopying(id, true);
  try {
    const { data } = await userApi.shopping.lists.getOne(id);
    if (data) {
      copyShoppingList(data);
    }
    else {
      alert.error(i18n.t("general.clipboard-copy-failure"));
    }
  }
  finally {
    setShoppingListCopying(id, false);
  }
}

async function organizeShoppingListById(id: string) {
  if (isOrganizingShoppingList(id)) {
    return;
  }

  setShoppingListOrganizing(id, true);
  try {
    const { data: shoppingList, error: shoppingListError } = await userApi.shopping.lists.getOne(id);
    if (shoppingListError || !shoppingList) {
      alert.error(i18n.t("shopping-list.ai-organize-failed"));
      return;
    }

    if (!shoppingList.listItems?.length) {
      alert.error(i18n.t("shopping-list.ai-organize-empty"));
      return;
    }

    const { data, error } = await userApi.shopping.lists.organizeWithAi(id);
    if (error || !data) {
      alert.error(i18n.t("shopping-list.ai-organize-failed"));
      return;
    }

    const { error: itemImagesError } = await userApi.shopping.lists.ensureItemImages(id);
    if (itemImagesError) {
      console.error("Failed to ensure shopping list item images", itemImagesError);
    }
    window.dispatchEvent(new CustomEvent("mealie:organizers-updated"));
    replaceShoppingList(data);
    alert.success(i18n.t("shopping-list.ai-organize-complete"));
  }
  catch {
    alert.error(i18n.t("shopping-list.ai-organize-failed"));
  }
  finally {
    setShoppingListOrganizing(id, false);
  }
}

function resetCreateShoppingListDialog() {
  if (createRecipeSearchTimer) {
    clearTimeout(createRecipeSearchTimer);
    createRecipeSearchTimer = null;
  }
  createRecipeSearchRequest += 1;
  state.createName = "";
  state.createRecipeSlug = null;
  state.createRecipeSearch = "";
  state.createRecipeSearching = false;
  createRecipeOptions.value = [];
}

function openCreateShoppingListDialog() {
  resetCreateShoppingListDialog();
  state.createDialog = true;
  searchCreateRecipes("");
}

function closeCreateShoppingListDialog() {
  resetCreateShoppingListDialog();
  clearCreateQuery();
}

function openCreateDialogFromRoute() {
  if (route.query.create === "1" || route.query.create === "true") {
    openCreateShoppingListDialog();
  }
}

function clearCreateQuery() {
  if (!route.query.create) {
    return;
  }

  const nextQuery = { ...route.query };
  delete nextQuery.create;
  void router.replace({ path: route.path, query: nextQuery });
}

function searchCreateRecipes(query: string | null) {
  if (createRecipeSearchTimer) {
    clearTimeout(createRecipeSearchTimer);
  }

  createRecipeSearchTimer = setTimeout(() => {
    void loadCreateRecipeOptions(query || "");
  }, 220);
}

async function loadCreateRecipeOptions(query: string) {
  const requestId = ++createRecipeSearchRequest;
  state.createRecipeSearching = true;
  try {
    const { data } = await userApi.recipes.search({
      search: query.trim(),
      page: 1,
      perPage: 20,
      orderBy: "name",
      orderDirection: "asc",
    });

    if (requestId !== createRecipeSearchRequest) {
      return;
    }

    createRecipeOptions.value = data?.items || [];
  }
  finally {
    if (requestId === createRecipeSearchRequest) {
      state.createRecipeSearching = false;
    }
  }
}

async function addSelectedRecipeToShoppingList(listId: string, recipeSlug: string) {
  const { data: recipe, error } = await userApi.recipes.getOne(recipeSlug);
  if (error || !recipe?.id) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }

  const { error: addError } = await userApi.shopping.lists.addRecipes(listId, [
    {
      recipeId: recipe.id,
      recipeIncrementQuantity: 1,
      recipeIngredients: recipe.recipeIngredient || null,
    },
  ]);

  if (addError) {
    alert.error(i18n.t("events.something-went-wrong"));
  }
}

async function createOne() {
  const recipeSlug = state.createRecipeSlug;
  const name = state.createName.trim() || selectedCreateRecipe.value?.name?.trim() || "";
  if (!name) {
    return;
  }

  state.createLoading = true;
  try {
    const existingList = shoppingLists.value?.find(list => (list.name || "").trim().toLocaleLowerCase() === name.toLocaleLowerCase());
    if (existingList) {
      alert.error(i18n.t("shopping-list.list-name-already-exists"));
      return;
    }

    const { data } = await userApi.shopping.lists.createOne({ name });

    if (data) {
      if (recipeSlug) {
        await addSelectedRecipeToShoppingList(data.id, recipeSlug);
      }
      state.createDialog = false;
      closeCreateShoppingListDialog();
      await refresh();
      window.dispatchEvent(new CustomEvent("mealie:organizers-updated"));
    }
  }
  finally {
    state.createLoading = false;
  }
}

function openRename(list: ShoppingListOut) {
  state.renameTarget = list;
  state.renameName = list.name || "";
  state.renameDialog = true;
}

async function renameOne() {
  const target = state.renameTarget;
  const name = state.renameName.trim();
  if (!target || !name) {
    return;
  }

  if ((target.name || "").trim() === name) {
    state.renameDialog = false;
    return;
  }

  const existingList = shoppingLists.value?.find(list =>
    list.id !== target.id && (list.name || "").trim().toLocaleLowerCase() === name.toLocaleLowerCase(),
  );
  if (existingList) {
    alert.error(i18n.t("shopping-list.list-name-already-exists"));
    return;
  }

  const { data: fullList } = await userApi.shopping.lists.getOne(target.id);
  if (!fullList) {
    alert.error(i18n.t("shopping-list.rename-shopping-list-failed"));
    return;
  }

  const { data } = await userApi.shopping.lists.updateOne(target.id, { ...fullList, name });
  if (!data) {
    alert.error(i18n.t("shopping-list.rename-shopping-list-failed"));
    return;
  }

  state.renameDialog = false;
  state.renameTarget = null;
  state.renameName = "";
  updateAvailabilityForListName(target.name, false);
  updateAvailabilityForListName(data.name, isShoppingListGroceriesReady(data));
  window.dispatchEvent(new CustomEvent("mealie:organizers-updated"));
  await refresh();
}

async function toggleOwnerDialog(list: ShoppingListOut) {
  if (!state.ownerDialog) {
    state.ownerTarget = list;
    await fetchAllUsers();
  }
  state.ownerDialog = !state.ownerDialog;
}

// ===============================================================
// Shopping List Edit User/Owner

const allUsers = ref<UserOut[]>([]);
const updateUserId = ref<string | undefined>();
async function fetchAllUsers() {
  const { data } = await userApi.households.fetchMembers();
  if (!data) {
    return;
  }

  // update current user
  allUsers.value = data.items.sort((a, b) => ((a.fullName || "") < (b.fullName || "") ? -1 : 1));
  updateUserId.value = state.ownerTarget?.userId;
}

async function updateOwner() {
  if (!state.ownerTarget || !updateUserId.value) {
    return;
  }
  // user has not changed, so we should not update
  if (state.ownerTarget.userId === updateUserId.value) {
    return;
  }
  // get full list, so the move does not delete shopping list items
  const { data: fullList } = await userApi.shopping.lists.getOne(state.ownerTarget.id);
  if (!fullList) {
    return;
  }
  const { data } = await userApi.shopping.lists.updateOne(
    state.ownerTarget.id,
    { ...fullList, userId: updateUserId.value },
  );

  if (data) {
    window.dispatchEvent(new CustomEvent("mealie:organizers-updated"));
    refresh();
  }
}

async function openDelete(id: string) {
  selectedDeleteRecipeIds.value = [];
  selectedDeleteWebsiteIds.value = [];
  deletePreview.value = undefined;
  state.deleteDialog = true;
  state.deleteTarget = id;
  deletePreviewLoading.value = true;
  try {
    const { data } = await userApi.shopping.lists.getDeletePreview(id);
    if (data) deletePreview.value = data;
  }
  finally {
    deletePreviewLoading.value = false;
  }
}

async function deleteOne() {
  const targetList = shoppingLists.value?.find(list => list.id === state.deleteTarget);
  const { data } = await userApi.shopping.lists.deleteWithLinks(
    state.deleteTarget,
    selectedDeleteRecipeIds.value,
    selectedDeleteWebsiteIds.value,
  );
  if (data) {
    updateAvailabilityForListName(targetList?.name, false);
    const nextMergedSources = new Set(expandedMergedSourceIds.value);
    nextMergedSources.delete(state.deleteTarget);
    expandedMergedSourceIds.value = nextMergedSources;
    await refresh();
    window.dispatchEvent(new CustomEvent("mealie:organizers-updated"));
  }
}
</script>

<style scoped>
.shopping-list-page-controls {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
}

.shopping-list-search {
  flex: 1 1 260px;
  margin-inline-end: auto;
  max-width: 420px;
  min-width: 220px;
}

.shopping-list-sort-menu {
  max-width: min(92vw, 440px);
  min-width: min(92vw, 380px);
}

.shopping-list-selection-list {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  max-height: min(52vh, 440px);
  overflow-y: auto;
  padding: 8px 12px;
}

.shopping-list-card-title {
  align-items: center;
  display: flex;
  gap: 12px;
  min-height: 64px;
  white-space: normal;
}

.shopping-list-card-identity {
  align-items: center;
  display: flex;
  flex: 1 1 220px;
  gap: 8px;
  min-width: 0;
}

.shopping-list-card-cart-icon {
  flex: 0 0 auto;
}

.shopping-list-card-name,
.shopping-list-source-name {
  display: -webkit-box;
  letter-spacing: 0;
  line-height: 1.35;
  min-width: 0;
  overflow: hidden;
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.shopping-list-card-actions {
  align-items: center;
  display: flex;
  flex: 0 0 auto;
  flex-wrap: wrap;
  gap: 2px;
  justify-content: flex-end;
  max-width: 62%;
}

.shopping-list-card-actions :deep(.v-btn) {
  height: 36px;
  width: 36px;
}

.shopping-list-ready-chip,
.shopping-list-merged-chip,
.shopping-list-ai-chip {
  flex: 0 0 auto;
}

.shopping-list-source-rows {
  border-inline-start: 3px solid rgba(var(--v-theme-primary), 0.42);
  margin: -2px 18px 12px;
  padding: 4px 0;
}

.shopping-list-source-row {
  align-items: center;
  background: transparent;
  border: 0;
  border-bottom: 1px solid rgba(var(--v-border-color), 0.18);
  color: inherit;
  cursor: pointer;
  display: flex;
  font: inherit;
  gap: 10px;
  min-height: 44px;
  padding: 6px 14px;
  text-align: start;
  width: 100%;
}

.shopping-list-source-row:hover,
.shopping-list-source-row:focus-visible {
  background-color: rgba(var(--v-theme-primary), 0.08);
  outline: none;
}

.shopping-list-source-name {
  flex: 1 1 auto;
}

.shopping-list-ready-chip {
  font-weight: 700;
  margin-inline: 6px;
}

.shopping-list-card--expanded {
  cursor: default;
}

.shopping-list-inline-panel {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  padding: 8px 20px 16px;
}

.shopping-list-inline-toolbar {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: space-between;
  margin-bottom: 8px;
}

.shopping-list-ready-action {
  transition:
    background-color 0.15s ease,
    box-shadow 0.15s ease,
    transform 0.15s ease;
}

.shopping-list-ready-action:hover,
.shopping-list-ready-action:focus-visible {
  box-shadow: 0 2px 8px rgba(var(--v-theme-on-surface), 0.18);
  transform: translateY(-1px);
}

.shopping-list-ready-action--active {
  box-shadow: inset 0 0 0 1px rgba(var(--v-theme-success), 0.28);
}

.shopping-list-ready-action--reset:hover,
.shopping-list-ready-action--reset:focus-visible {
  background-color: rgba(var(--v-theme-warning), 0.12) !important;
}

.shopping-list-image-toggle {
  transition:
    background-color 0.15s ease,
    box-shadow 0.15s ease,
    transform 0.15s ease;
}

.shopping-list-image-toggle:hover,
.shopping-list-image-toggle:focus-visible {
  box-shadow: 0 2px 8px rgba(var(--v-theme-on-surface), 0.16);
  transform: translateY(-1px);
}

.shopping-list-inline-group + .shopping-list-inline-group {
  margin-top: 10px;
}

.shopping-list-inline-group {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 6px;
  overflow: hidden;
}

.shopping-list-inline-group-title {
  align-items: center;
  background: rgba(var(--v-theme-primary), 0.09);
  color: rgb(var(--v-theme-on-surface));
  display: flex;
  font-size: 0.85rem;
  font-weight: 700;
  justify-content: space-between;
  min-height: 38px;
  padding: 8px 14px;
  text-align: start;
}

.shopping-list-inline-group-count {
  color: rgba(var(--v-theme-on-surface), 0.72);
  font-size: 0.75rem;
  font-weight: 500;
}

.shopping-list-inline-item {
  align-items: center;
  border-bottom: 1px solid rgba(var(--v-border-color), 0.18);
  display: flex;
  gap: 8px;
  min-height: 34px;
  padding: 4px 10px;
}

.shopping-list-inline-item:last-child {
  border-bottom: 0;
}

.shopping-list-inline-item--checked {
  color: rgba(var(--v-theme-on-surface), 0.52);
}

.shopping-list-inline-item--checked .shopping-list-inline-item-text {
  text-decoration: line-through;
}

.shopping-list-inline-checkbox {
  flex: 0 0 auto;
}

.shopping-list-inline-item-text {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.shopping-list-inline-edit-input {
  flex: 1 1 auto;
  min-width: 140px;
}

.shopping-list-inline-action {
  flex: 0 0 auto;
  opacity: 0.68;
  transition:
    background-color 0.15s ease,
    box-shadow 0.15s ease,
    opacity 0.15s ease;
}

.shopping-list-inline-action:hover,
.shopping-list-inline-action:focus-visible {
  background-color: rgba(var(--v-theme-primary), 0.1) !important;
  box-shadow: inset 0 0 0 1px rgba(var(--v-theme-primary), 0.24);
  opacity: 1;
}

@media (max-width: 760px) {
  .shopping-list-card-title {
    align-items: stretch;
    flex-direction: column;
  }

  .shopping-list-card-identity {
    flex-basis: auto;
    width: 100%;
  }

  .shopping-list-card-actions {
    max-width: none;
    width: 100%;
  }

  .shopping-list-search {
    max-width: none;
    width: 100%;
  }
}
</style>
