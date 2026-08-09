<template>
  <div>
    <!-- Create Dialog -->
    <BaseDialog
      v-if="createTarget"
      v-model="dialogStates.create"
      width="100%"
      max-width="1100px"
      :icon="$globals.icons.pages"
      :title="$t('cookbook.create-a-cookbook')"
      :submit-icon="$globals.icons.save"
      :submit-text="$t('general.save')"
      :submit-disabled="!createTarget.queryFilterString"
      can-submit
      @submit="actions.updateOne(createTarget)"
      @cancel="deleteCreateTarget()"
    >
      <v-card-text>
        <CookbookEditor :key="createTargetKey" v-model="createTarget" />
      </v-card-text>
    </BaseDialog>

    <!-- Delete Dialog -->
    <BaseDialog
      v-model="dialogStates.delete"
      :title="$t('general.delete-with-name', { name: $t('cookbook.cookbook') })"
      :icon="$globals.icons.alertCircle"
      color="error"
      can-confirm
      @confirm="deleteCookbook()"
    >
      <v-card-text>
        <p>{{ $t("general.confirm-delete-generic-with-name", { name: $t("cookbook.cookbook") }) }}</p>
        <p v-if="deleteTarget" class="mt-4 ml-4">
          {{ deleteTarget.name }}
        </p>
      </v-card-text>
    </BaseDialog>

    <BaseDialog
      v-model="aiBookDialog"
      :title="$t('cookbook.create-book-with-ai')"
      :icon="$globals.icons.robot"
      width="680"
      max-width="96vw"
      can-submit
      keep-open
      :loading="aiBookCreating"
      :submit-disabled="aiBookSubmitDisabled"
      @submit="createAIBook"
    >
      <v-card-text class="pt-4">
        <v-btn-toggle v-model="aiBookMode" mandatory divided color="primary" class="mb-4">
          <v-btn value="preset" :prepend-icon="$globals.icons.formatListCheck">
            {{ $t("cookbook.ai-book-preset") }}
          </v-btn>
          <v-btn value="prompt" :prepend-icon="$globals.icons.messageText">
            {{ $t("cookbook.ai-book-free-definition") }}
          </v-btn>
        </v-btn-toggle>
        <v-select
          v-if="aiBookMode === 'preset'"
          v-model="aiBookPreset"
          :items="aiBookPresetOptions"
          item-title="title"
          item-value="value"
          variant="outlined"
          :label="$t('cookbook.ai-book-preset')"
        />
        <v-textarea
          v-else
          v-model="aiBookPrompt"
          variant="outlined"
          rows="4"
          auto-grow
          maxlength="2000"
          counter
          :label="$t('cookbook.ai-book-free-definition')"
          :placeholder="$t('cookbook.ai-book-prompt-placeholder')"
        />
        <v-text-field
          v-model="aiBookTitle"
          variant="outlined"
          :label="$t('cookbook.ai-book-title-optional')"
        />
        <v-row dense>
          <v-col cols="12" sm="6">
            <v-number-input
              v-model="aiBookMaxRecipes"
              :min="5"
              :max="200"
              variant="outlined"
              control-variant="stacked"
              :label="$t('cookbook.recipes-per-volume')"
            />
          </v-col>
          <v-col cols="12" sm="6">
            <v-number-input
              v-model="aiBookMaxPages"
              :min="40"
              :max="1000"
              variant="outlined"
              control-variant="stacked"
              :label="$t('cookbook.estimated-pages-per-volume')"
            />
          </v-col>
        </v-row>
        <v-alert density="compact" variant="tonal" type="info">
          {{ $t("cookbook.ai-book-volume-description") }}
        </v-alert>
      </v-card-text>
    </BaseDialog>

    <BaseDialog
      v-model="uploadedBookDeleteDialog"
      :title="$t('cookbook.delete-book')"
      :icon="$globals.icons.delete"
      color="error"
      can-confirm
      :loading="uploadedBookDeleting"
      @confirm="deleteUploadedBook"
    >
      <v-card-text>
        {{ $t("cookbook.delete-uploaded-book-confirm") }}
        <strong v-if="uploadedBookDeleteTarget" class="d-block mt-3">{{ uploadedBookDeleteTarget.name }}</strong>
        <v-progress-linear v-if="uploadedBookDeletePreviewLoading" indeterminate color="primary" class="mt-4" />
        <template v-else-if="uploadedBookDeletePreview">
          <v-checkbox
            v-if="uploadedBookDeletePreview.recipeIds.length"
            v-model="uploadedBookDeleteRecipes"
            :label="$t('cookbook.delete-linked-recipes', { count: uploadedBookDeletePreview.recipeIds.length })"
            density="compact"
            hide-details
            class="mt-4"
          />
          <v-checkbox
            v-if="uploadedBookDeletePreview.shoppingListIds.length"
            v-model="uploadedBookDeleteShoppingLists"
            :label="$t('cookbook.delete-linked-shopping-lists', { count: uploadedBookDeletePreview.shoppingListIds.length })"
            density="compact"
            hide-details
          />
          <v-alert
            v-if="uploadedBookDeletePreview.recipeIds.length || uploadedBookDeletePreview.shoppingListIds.length"
            type="info"
            variant="tonal"
            density="compact"
            class="mt-4"
          >
            {{ $t('cookbook.linked-items-remain-by-default') }}
          </v-alert>
        </template>
      </v-card-text>
    </BaseDialog>

    <BaseDialog
      v-model="bookCoverDialog"
      :title="$t('cookbook.change-book-cover')"
      :icon="$globals.icons.fileImage"
      :loading="bookCoverSaving"
      @close="resetBookCoverDialog"
    >
      <v-card-text>
        <p v-if="bookCoverTarget" class="font-weight-medium mb-4">
          {{ bookCoverTarget.name }}
        </p>
        <v-btn-toggle v-model="bookCoverMode" mandatory divided density="comfortable" class="mb-4">
          <v-btn value="upload" :prepend-icon="$globals.icons.upload">
            {{ $t("cookbook.upload-cover") }}
          </v-btn>
          <v-btn value="url" :prepend-icon="$globals.icons.link">
            {{ $t("cookbook.cover-address") }}
          </v-btn>
          <v-btn value="auto" :prepend-icon="$globals.icons.robot">
            {{ $t("cookbook.find-cover") }}
          </v-btn>
        </v-btn-toggle>
        <v-file-input
          v-if="bookCoverMode === 'upload'"
          v-model="bookCoverFile"
          accept="image/*"
          show-size
          :label="$t('cookbook.choose-cover')"
          :prepend-icon="$globals.icons.fileImage"
        />
        <v-text-field
          v-else-if="bookCoverMode === 'url'"
          v-model="bookCoverAddress"
          type="url"
          variant="outlined"
          :label="$t('cookbook.cover-address')"
          :prepend-inner-icon="$globals.icons.link"
        />
        <v-alert v-else type="info" variant="tonal" density="compact">
          {{ $t("cookbook.find-cover-help") }}
        </v-alert>
      </v-card-text>
      <template #custom-card-action>
        <v-btn
          color="primary"
          :prepend-icon="$globals.icons.save"
          :disabled="!canSaveBookCover"
          :loading="bookCoverSaving"
          @click="saveBookCover"
        >
          {{ $t("general.save") }}
        </v-btn>
      </template>
    </BaseDialog>

    <UploadedBookRecipeDeleteDialog
      v-model="bookRecipeDeleteDialog"
      :book="bookRecipeDeleteTarget"
      @deleted="handleBookRecipesDeleted"
    />

    <UploadedBookRenameDialog
      v-model="bookRenameDialog"
      :book="bookRenameTarget"
      @renamed="handleBookRenamed"
    />

    <BaseDialog
      v-model="bookExtractionDialog"
      :title="$t('cookbook.extract-recipes-with-ai')"
      :icon="$globals.icons.robot"
      width="680"
      max-width="96vw"
      can-submit
      keep-open
      :loading="bookExtractionStarting"
      :submit-disabled="!bookExtractionTarget || bookExtractionRangeInvalid"
      @submit="startBookExtraction"
    >
      <v-card-text v-if="bookExtractionTarget">
        <p class="font-weight-medium mb-4">
          {{ bookExtractionTarget.name }}
        </p>
        <v-checkbox
          v-model="bookExtractionAllPages"
          :label="$t('cookbook.all-pages')"
          density="compact"
          hide-details
          class="mb-3"
        />
        <v-row v-if="!bookExtractionAllPages" dense>
          <v-col cols="12" sm="6">
            <v-number-input
              v-model="bookExtractionPageStart"
              :min="1"
              :label="$t('cookbook.page-start')"
              variant="outlined"
              control-variant="stacked"
            />
          </v-col>
          <v-col cols="12" sm="6">
            <v-number-input
              v-model="bookExtractionPageEnd"
              :min="1"
              :label="$t('cookbook.page-end')"
              variant="outlined"
              control-variant="stacked"
            />
          </v-col>
        </v-row>
        <v-number-input
          v-model="bookExtractionPagesPerChunk"
          :min="1"
          :max="100"
          :label="$t('cookbook.pages-per-ai-chunk')"
          variant="outlined"
          control-variant="stacked"
        />
        <v-checkbox v-model="bookExtractionCreateLists" :label="$t('cookbook.extraction-shopping-lists')" density="compact" hide-details />
        <v-checkbox
          v-model="bookExtractionOrganizeLists"
          :disabled="!bookExtractionCreateLists"
          :label="$t('cookbook.extraction-organize-shopping-lists')"
          density="compact"
          hide-details
        />
        <v-checkbox v-model="bookExtractionRecipeImages" :label="$t('cookbook.extraction-recipe-images')" density="compact" hide-details />
        <v-checkbox v-model="bookExtractionItemImages" :label="$t('cookbook.extraction-item-images')" density="compact" hide-details />
        <v-checkbox v-model="bookExtractionTips" :label="$t('cookbook.extraction-ai-tips')" density="compact" hide-details />
        <v-alert
          v-if="bookExtractionTarget.extractionRecipesCreated > 0"
          type="warning"
          variant="tonal"
          density="compact"
          class="mt-4"
        >
          {{ $t('cookbook.extraction-existing-recipes', { count: bookExtractionTarget.extractionRecipesCreated }) }}
          <v-checkbox
            v-model="bookExtractionAllowDuplicates"
            :label="$t('cookbook.extraction-create-new-copies')"
            density="compact"
            hide-details
            class="mt-2"
          />
        </v-alert>
      </v-card-text>
    </BaseDialog>

    <BaseDialog
      v-model="bookRecipeCatalogDialog"
      :title="$t('cookbook.choose-recipes-from-book')"
      :icon="$globals.icons.formatListCheck"
      width="820"
      max-width="96vw"
      can-submit
      keep-open
      :loading="bookRecipeCatalogImporting"
      :submit-text="$t('cookbook.import-selected-recipes')"
      :submit-disabled="!bookRecipeCatalogTarget || !bookRecipeCatalogSelected.length"
      @submit="importSelectedBookRecipes"
    >
      <v-card-text v-if="bookRecipeCatalogTarget" class="pt-4">
        <p class="font-weight-medium mb-4">
          {{ bookRecipeCatalogTarget.name }}
        </p>
        <div class="book-recipe-catalog__search">
          <v-text-field
            v-model="bookRecipeCatalogQuery"
            variant="outlined"
            density="comfortable"
            hide-details
            clearable
            :prepend-inner-icon="$globals.icons.search"
            :label="$t('cookbook.book-recipe-search')"
            :placeholder="$t('cookbook.book-recipe-search-placeholder')"
            @keydown.enter.prevent="discoverBookRecipes"
          />
          <v-select
            v-model="bookRecipeCatalogLanguage"
            :items="bookTranslationLanguageOptions"
            variant="outlined"
            density="comfortable"
            hide-details
            :label="$t('cookbook.recipe-language')"
          />
          <v-btn
            color="primary"
            :prepend-icon="$globals.icons.robot"
            :loading="bookRecipeCatalogLoading"
            @click="discoverBookRecipes"
          >
            {{ $t("cookbook.find-recipes") }}
          </v-btn>
        </div>
        <v-alert
          v-if="bookRecipeCatalog?.warning"
          type="warning"
          variant="tonal"
          density="compact"
          class="mt-4"
        >
          {{ bookRecipeCatalog.warning }}
        </v-alert>
        <template v-if="bookRecipeCatalog">
          <div class="d-flex align-center mt-4">
            <v-checkbox
              :model-value="allCatalogRecipesSelected"
              :indeterminate="someCatalogRecipesSelected"
              :label="$t('cookbook.select-all-recipes')"
              density="compact"
              hide-details
              @update:model-value="toggleAllCatalogRecipes"
            />
            <v-spacer />
            <v-chip size="small" variant="tonal">
              {{ $t(`cookbook.recipe-catalog-source-${bookRecipeCatalog.source}`) }}
            </v-chip>
          </div>
          <div v-if="bookRecipeCatalog.candidates.length" class="book-recipe-catalog__list">
            <label
              v-for="candidate in bookRecipeCatalog.candidates"
              :key="candidate.id"
              class="book-recipe-catalog__row"
            >
              <v-checkbox-btn
                v-model="bookRecipeCatalogSelected"
                :value="candidate.id"
                :disabled="Boolean(candidate.importedRecipeSlug)"
              />
              <span class="book-recipe-catalog__details">
                <strong>{{ candidate.title }}</strong>
                <small>
                  <span v-if="candidate.chapter">{{ candidate.chapter }} · </span>
                  {{ $t("cookbook.pages") }} {{ candidate.pageStart }}–{{ candidate.pageEnd }}
                </small>
                <small v-if="candidate.reason">{{ candidate.reason }}</small>
              </span>
              <v-chip v-if="candidate.importedRecipeSlug" color="success" size="x-small">
                {{ $t("cookbook.already-imported") }}
              </v-chip>
            </label>
          </div>
          <v-alert v-else type="info" variant="tonal" density="compact" class="mt-4">
            {{ $t("cookbook.no-matching-book-recipes") }}
          </v-alert>
          <v-expansion-panels class="mt-4" variant="accordion">
            <v-expansion-panel>
              <v-expansion-panel-title>{{ $t("cookbook.import-options") }}</v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-checkbox v-model="bookRecipeCatalogCreateLists" :label="$t('cookbook.extraction-shopping-lists')" density="compact" hide-details />
                <v-checkbox
                  v-model="bookRecipeCatalogOrganizeLists"
                  :disabled="!bookRecipeCatalogCreateLists"
                  :label="$t('cookbook.extraction-organize-shopping-lists')"
                  density="compact"
                  hide-details
                />
                <v-checkbox v-model="bookRecipeCatalogRecipeImages" :label="$t('cookbook.extraction-recipe-images')" density="compact" hide-details />
                <v-checkbox v-model="bookRecipeCatalogItemImages" :label="$t('cookbook.extraction-item-images')" density="compact" hide-details />
                <v-checkbox v-model="bookRecipeCatalogTips" :label="$t('cookbook.extraction-ai-tips')" density="compact" hide-details />
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </template>
        <v-alert v-else type="info" variant="tonal" density="compact" class="mt-4">
          {{ $t("cookbook.book-recipe-search-help") }}
        </v-alert>
      </v-card-text>
    </BaseDialog>

    <BaseDialog
      v-model="bookTranslationDialog"
      :title="$t('cookbook.translate-book-with-ai')"
      :icon="$globals.icons.translate"
      width="720"
      max-width="96vw"
      can-submit
      keep-open
      :loading="bookTranslationStarting"
      :submit-disabled="!bookTranslationTarget || bookTranslationRangeInvalid"
      :submit-text="$t('cookbook.start-translation')"
      @submit="startBookTranslation"
    >
      <v-card-text v-if="bookTranslationTarget">
        <p class="font-weight-medium mb-4">
          {{ bookTranslationTarget.name }}
        </p>
        <v-combobox
          v-model="bookTranslationLanguage"
          :items="bookTranslationLanguageOptions"
          :label="$t('cookbook.translation-language')"
          variant="outlined"
        />
        <v-checkbox
          v-model="bookTranslationAllPages"
          :label="$t('cookbook.all-pages')"
          density="compact"
          hide-details
          class="mb-3"
        />
        <v-row v-if="!bookTranslationAllPages" dense>
          <v-col cols="12" sm="6">
            <v-number-input
              v-model="bookTranslationPageStart"
              :min="1"
              :label="$t('cookbook.page-start')"
              variant="outlined"
              control-variant="stacked"
            />
          </v-col>
          <v-col cols="12" sm="6">
            <v-number-input
              v-model="bookTranslationPageEnd"
              :min="1"
              :label="$t('cookbook.page-end')"
              variant="outlined"
              control-variant="stacked"
            />
          </v-col>
        </v-row>
        <v-number-input
          v-model="bookTranslationPagesPerChunk"
          :min="1"
          :max="100"
          :label="$t('cookbook.pages-per-ai-chunk')"
          variant="outlined"
          control-variant="stacked"
        />
        <v-checkbox
          v-model="bookTranslationIncludeLinkedRecipes"
          :label="$t('cookbook.translation-include-linked-recipes')"
          density="compact"
          hide-details
        />
        <v-checkbox
          v-model="bookTranslationExtractRecipes"
          :label="$t('cookbook.translation-extract-recipes')"
          density="compact"
          hide-details
        />
        <div v-if="bookTranslationExtractRecipes" class="mt-2 ps-3 border-s-sm">
          <v-checkbox v-model="bookTranslationCreateLists" :label="$t('cookbook.extraction-shopping-lists')" density="compact" hide-details />
          <v-checkbox
            v-model="bookTranslationOrganizeLists"
            :disabled="!bookTranslationCreateLists"
            :label="$t('cookbook.extraction-organize-shopping-lists')"
            density="compact"
            hide-details
          />
          <v-checkbox v-model="bookTranslationRecipeImages" :label="$t('cookbook.extraction-recipe-images')" density="compact" hide-details />
          <v-checkbox v-model="bookTranslationItemImages" :label="$t('cookbook.extraction-item-images')" density="compact" hide-details />
          <v-checkbox v-model="bookTranslationTips" :label="$t('cookbook.extraction-ai-tips')" density="compact" hide-details />
        </div>
        <v-alert type="info" variant="tonal" density="compact" class="mt-4">
          {{ $t('cookbook.translation-professional-contents-hint') }}
        </v-alert>
        <v-alert
          v-if="bookTranslationTarget.translationStatus === 'partial_failed'"
          type="warning"
          variant="tonal"
          density="compact"
          class="mt-4"
        >
          {{ $t("cookbook.translation-partial-saved") }}
          <div v-if="bookTranslationFailedChunks.length" class="mt-2">
            <strong>{{ $t("cookbook.translation-missing-ranges") }}</strong>
            <v-chip
              v-for="chunk in bookTranslationFailedChunks"
              :key="chunk.range"
              size="small"
              class="ma-1"
              @click="selectManualTranslationPage(chunk.startPage)"
            >
              {{ chunk.startPage }}–{{ chunk.endPage }}
            </v-chip>
          </div>
          <p class="mt-2 mb-0">
            {{ $t("cookbook.translation-retry-hint") }}
          </p>
        </v-alert>
        <v-expansion-panels
          v-if="bookTranslationTarget.translationStatus === 'partial_failed'"
          class="mt-4"
          variant="accordion"
        >
          <v-expansion-panel>
            <v-expansion-panel-title>
              {{ $t("cookbook.add-manual-translation-page") }}
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-number-input
                v-model="bookTranslationManualPage"
                :min="1"
                variant="outlined"
                control-variant="stacked"
                :label="$t('cookbook.page-number')"
              />
              <v-textarea
                v-model="bookTranslationManualText"
                variant="outlined"
                auto-grow
                rows="6"
                maxlength="200000"
                :label="$t('cookbook.translated-page-text')"
              />
              <v-btn
                color="primary"
                :prepend-icon="$globals.icons.save"
                :loading="bookTranslationManualSaving"
                :disabled="!bookTranslationManualPage || !bookTranslationManualText.trim()"
                @click="saveManualTranslationPage"
              >
                {{ $t("cookbook.save-translated-page") }}
              </v-btn>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card-text>
    </BaseDialog>

    <!-- Cookbook Page -->
    <!-- Page Title -->
    <v-container class="lg-container">
      <BasePageTitle divider>
        <template #header>
          <v-img width="100%" max-height="100" max-width="100" src="/svgs/manage-cookbooks.svg" />
        </template>
        <template #title>
          {{ $t("cookbook.cookbooks") }}
        </template>
        {{ $t("cookbook.description") }}
      </BasePageTitle>

      <div class="my-6">
        <v-checkbox
          v-model="cookbookPreferences.hideOtherHouseholds"
          :label="$t('cookbook.hide-cookbooks-from-other-households')"
          hide-details
          color="primary"
        />
        <div class="ml-10 mt-n3">
          <p class="text-subtitle-2 my-0 py-0">
            {{ $t("cookbook.hide-cookbooks-from-other-households-description") }}
          </p>
        </div>
      </div>

      <!-- Create New -->
      <BaseButton create @click="createCookbook" />

      <!-- Cookbook List -->
      <v-expansion-panels class="mt-2">
        <VueDraggable
          v-model="myCookbooks"
          handle=".handle"
          :delay="250"
          :delay-on-touch-only="true"
          style="width: 100%"
          @end="updateAll(myCookbooks)"
        >
          <v-expansion-panel
            v-for="(cookbook, index) in myCookbooks"
            :key="cookbook.id"
            class="my-2 left-border rounded"
          >
            <v-expansion-panel-title disable-icon-rotate class="text-h6 opacity-80">
              <div class="d-flex align-center">
                <v-icon size="large" start>
                  {{ $globals.icons.pages }}
                </v-icon>
                {{ cookbook.name }}
              </div>
              <template #actions>
                <div class="d-flex align-center">
                  <v-btn icon variant="text" class="ml-2">
                    <v-icon>
                      {{ $globals.icons.edit }}
                    </v-icon>
                  </v-btn>
                  <v-icon class="handle" :size="40">
                    {{ $globals.icons.arrowUpDown }}
                  </v-icon>
                </div>
              </template>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <CookbookEditor
                v-model="myCookbooks[index]"
                :collapsable="false"
              />
              <v-card-actions>
                <v-spacer />
                <BaseButtonGroup
                  :buttons="[
                    {
                      icon: $globals.icons.delete,
                      text: $t('general.delete'),
                      event: 'delete',
                    },
                    {
                      icon: $globals.icons.save,
                      text: $t('general.save'),
                      event: 'save',
                      disabled: !cookbook.queryFilterString,
                    },
                  ]"
                  @delete="deleteEventHandler(myCookbooks[index])"
                  @save="actions.updateOne(myCookbooks[index])"
                />
              </v-card-actions>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </VueDraggable>
      </v-expansion-panels>

      <section class="cookbook-library mt-12 pt-8">
        <div class="d-flex flex-wrap align-center ga-3 mb-5">
          <div>
            <h2 class="text-h5 font-weight-medium">
              {{ $t("cookbook.book-library") }}
            </h2>
            <p class="text-body-2 text-medium-emphasis mb-0">
              {{ $t("cookbook.book-library-description") }}
            </p>
          </div>
          <v-spacer />
          <v-btn
            color="primary"
            variant="tonal"
            :prepend-icon="$globals.icons.robot"
            @click="aiBookDialog = true"
          >
            {{ $t("cookbook.create-book-with-ai") }}
          </v-btn>
          <v-btn
            icon
            variant="text"
            :loading="uploadedBooksLoading"
            :title="$t('general.refresh')"
            @click="loadUploadedBooks"
          >
            <v-icon :icon="$globals.icons.refresh" />
          </v-btn>
        </div>

        <div class="cookbook-library__filters mb-6">
          <v-text-field
            v-model="bookSearch"
            variant="outlined"
            density="comfortable"
            hide-details
            clearable
            :prepend-inner-icon="$globals.icons.search"
            :label="$t('search.search')"
          />
          <v-select
            v-model="bookTypeFilter"
            :items="bookTypeOptions"
            item-title="title"
            item-value="value"
            variant="outlined"
            density="comfortable"
            hide-details
            :label="$t('cookbook.book-type')"
          />
          <v-autocomplete
            v-model="bookMetadataFilters"
            :items="bookMetadataOptions"
            multiple
            chips
            closable-chips
            clearable
            variant="outlined"
            density="comfortable"
            hide-details
            :label="$t('cookbook.categories-and-tags')"
          />
          <v-select
            v-model="uploadedBookGroupBy"
            :items="uploadedBookGroupOptions"
            item-title="title"
            item-value="value"
            variant="outlined"
            density="comfortable"
            hide-details
            :label="$t('cookbook.group-books-by')"
          />
        </div>
        <BaseListSortControls
          v-model:sort-by="uploadedBookSortBy"
          v-model:sort-direction="uploadedBookSortDirection"
          :options="uploadedBookSortOptions"
          class="mb-6"
        />

        <BaseListPagination
          v-if="filteredUploadedBooks.length"
          v-model:page="uploadedBookPage"
          v-model:items-per-page="uploadedBooksPerPage"
          :total-items="uploadedBookTotal"
        />

        <v-alert v-if="!uploadedBooksLoading && !filteredUploadedBooks.length" type="info" variant="tonal">
          {{ $t("cookbook.no-library-books") }}
        </v-alert>
        <div v-else class="cookbook-library__grid">
          <template v-for="(book, bookIndex) in paginatedUploadedBooks" :key="book.id">
            <div
              v-if="isFirstBookGroupItem(bookIndex)"
              class="cookbook-library__group-divider"
            >
              <span>{{ bookGroupLabel(book) }}</span>
            </div>
            <v-card
              variant="outlined"
              class="cookbook-library__book"
              :class="{ 'cookbook-library__book--complete': isBookCompleted(book) }"
            >
              <div
                class="cookbook-library__cover cookbook-library__cover--interactive"
                role="button"
                tabindex="0"
                :title="$t('cookbook.open-book')"
                :aria-label="`${$t('cookbook.open-book')}: ${book.name}`"
                @click="openUploadedBook(book)"
                @keydown.enter.prevent="openUploadedBook(book)"
                @keydown.space.prevent="openUploadedBook(book)"
              >
                <v-img
                  v-if="book.bookMetadata?.cover_file_name"
                  :src="api.uploadedBooks.coverUrl(book.id, book.updatedAt)"
                  :alt="book.name"
                  cover
                  height="260"
                >
                  <template #error>
                    <div class="cookbook-library__cover-fallback">
                      <v-icon :icon="bookIcon(book)" size="72" />
                    </div>
                  </template>
                </v-img>
                <div v-else class="cookbook-library__cover-fallback">
                  <v-icon :icon="bookIcon(book)" size="72" />
                </div>
                <div class="cookbook-library__cover-action" aria-hidden="true">
                  <v-icon :icon="$globals.icons.openInNew" size="36" />
                </div>
                <div v-if="isBookCompleted(book)" class="cookbook-library__complete-mark" :title="$t('cookbook.book-completed')">
                  <v-icon :icon="$globals.icons.check" size="22" />
                </div>
                <v-btn
                  class="cookbook-library__cover-edit"
                  icon
                  size="small"
                  color="primary"
                  :title="$t('cookbook.change-book-cover')"
                  @click.stop="openBookCoverDialog(book)"
                  @keydown.enter.stop.prevent="openBookCoverDialog(book)"
                >
                  <v-icon :icon="$globals.icons.fileImage" />
                </v-btn>
                <v-btn
                  class="cookbook-library__cover-delete"
                  icon
                  size="small"
                  color="error"
                  :title="$t('cookbook.delete-book')"
                  @click.stop="confirmUploadedBookDelete(book)"
                  @keydown.enter.stop.prevent="confirmUploadedBookDelete(book)"
                  @keydown.space.stop.prevent="confirmUploadedBookDelete(book)"
                >
                  <v-icon :icon="$globals.icons.delete" />
                </v-btn>
              </div>
              <v-card-item>
                <template #prepend>
                  <v-avatar color="surface-variant" rounded="sm">
                    <v-icon :icon="bookIcon(book)" />
                  </v-avatar>
                </template>
                <v-card-title class="text-subtitle-1 text-wrap">
                  {{ book.name }}
                </v-card-title>
                <v-card-subtitle>
                  {{ bookTypeLabel(book) }} · {{ book.extension.toUpperCase() }}
                </v-card-subtitle>
              </v-card-item>
              <v-card-text class="pt-0">
                <p v-if="bookClassification(book)?.summary" class="book-summary mb-3">
                  {{ bookClassification(book)?.summary }}
                </p>
                <div class="d-flex flex-wrap ga-1">
                  <v-chip
                    v-for="label in bookLabels(book).slice(0, 8)"
                    :key="label"
                    size="x-small"
                    variant="tonal"
                  >
                    {{ label }}
                  </v-chip>
                </div>
                <v-progress-linear
                  v-if="book.classificationStatus === 'processing'"
                  indeterminate
                  color="primary"
                  class="mt-3"
                />
                <v-alert
                  v-else-if="book.classificationStatus === 'failed'"
                  density="compact"
                  type="warning"
                  variant="tonal"
                  class="mt-3"
                >
                  {{ $t("cookbook.book-classification-failed") }}
                </v-alert>
                <div
                  v-if="book.isTranslatedBook && bookTranslationAudit(book)"
                  class="cookbook-library__translation mt-3"
                >
                  <div class="cookbook-library__reading-row">
                    <span>{{ $t("cookbook.translation-completeness") }}</span>
                    <strong>{{ bookTranslationPercent(book) }}%</strong>
                  </div>
                  <v-progress-linear
                    :model-value="bookTranslationPercent(book)"
                    :color="bookTranslationPercent(book) >= 100 ? 'success' : 'warning'"
                    height="5"
                    rounded
                  />
                  <div class="cookbook-library__translation-footer mt-1">
                    <small>
                      {{ $t("cookbook.translated-pages-count", {
                        translated: bookTranslatedPageCount(book),
                        total: bookTranslationAudit(book)?.source_pages || 0,
                      }) }}
                    </small>
                    <v-btn
                      v-if="bookTranslationPercent(book) < 100 && sourceBookForTranslation(book)"
                      size="x-small"
                      variant="text"
                      color="warning"
                      :prepend-icon="$globals.icons.translate"
                      :disabled="sourceBookForTranslation(book)?.translationStatus === 'processing'
                        || sourceBookForTranslation(book)?.translationStatus === 'retrying'"
                      @click="finishBookTranslation(book)"
                    >
                      {{ $t("cookbook.finish-translation") }}
                    </v-btn>
                  </div>
                </div>
                <div v-if="bookReadingState(book)" class="cookbook-library__reading mt-3">
                  <div class="cookbook-library__reading-row">
                    <span>{{ $t("cookbook.current-reading-position") }}</span>
                    <strong>{{ Math.round(bookReadingState(book)?.readingPercent || 0) }}%</strong>
                  </div>
                  <v-progress-linear
                    :model-value="bookReadingState(book)?.readingPercent || 0"
                    color="primary"
                    height="5"
                    rounded
                  />
                  <div class="cookbook-library__reading-row mt-2">
                    <span>{{ $t("cookbook.chapters-read") }}</span>
                    <strong>{{ bookChapterPercent(book) }}%</strong>
                  </div>
                  <v-progress-linear
                    :model-value="bookChapterPercent(book)"
                    color="success"
                    height="5"
                    rounded
                  />
                </div>
              </v-card-text>
              <v-card-actions>
                <v-btn variant="text" color="primary" :prepend-icon="$globals.icons.openInNew" @click="openUploadedBook(book)">
                  {{ $t("cookbook.open-book") }}
                </v-btn>
                <v-spacer />
                <v-btn
                  icon
                  variant="text"
                  :title="$t('cookbook.rename-book')"
                  @click="openBookRenameDialog(book)"
                >
                  <v-icon :icon="$globals.icons.edit" />
                </v-btn>
                <v-btn
                  v-if="isGeneratedBook(book)"
                  icon
                  variant="text"
                  :loading="refreshingBookIds.has(book.id)"
                  :title="$t('cookbook.refresh-ai-book')"
                  @click="refreshAIBook(book)"
                >
                  <v-icon :icon="$globals.icons.refresh" />
                </v-btn>
                <v-btn
                  v-else
                  icon
                  variant="text"
                  :loading="book.classificationStatus === 'processing'"
                  :title="$t('cookbook.organize-book-with-ai')"
                  @click="classifyUploadedBook(book)"
                >
                  <v-icon :icon="$globals.icons.robot" />
                </v-btn>
                <v-btn
                  v-if="!isGeneratedBook(book) && !book.isTranslatedBook"
                  icon
                  variant="text"
                  :disabled="book.translationStatus === 'processing' || book.translationStatus === 'retrying'"
                  :title="$t('cookbook.translate-book-with-ai')"
                  @click="openBookTranslationDialog(book)"
                >
                  <v-icon :icon="$globals.icons.translate" />
                </v-btn>
                <v-btn
                  v-if="!isGeneratedBook(book)"
                  icon
                  variant="text"
                  :disabled="book.extractionStatus === 'processing' || book.extractionStatus === 'retrying'"
                  :title="$t('cookbook.extract-recipes-with-ai')"
                  @click="openBookExtractionDialog(book)"
                >
                  <v-icon :icon="$globals.icons.potSteam" />
                </v-btn>
                <v-btn
                  v-if="!isGeneratedBook(book)"
                  icon
                  variant="text"
                  :disabled="bookRecipeSource(book)?.extractionStatus === 'processing' || bookRecipeSource(book)?.extractionStatus === 'retrying'"
                  :title="$t('cookbook.choose-recipes-from-book')"
                  @click="openBookRecipeCatalogDialog(book)"
                >
                  <v-icon :icon="$globals.icons.formatListCheck" />
                </v-btn>
                <v-btn
                  v-if="bookRecipeSource(book)?.extractionRecipesCreated"
                  icon
                  variant="text"
                  color="warning"
                  :title="$t('cookbook.delete-book-recipes')"
                  @click="openBookRecipeDeleteDialog(book)"
                >
                  <v-icon :icon="$globals.icons.broom" />
                </v-btn>
              </v-card-actions>
            </v-card>
          </template>
        </div>
      </section>
    </v-container>
  </div>
</template>

<script setup lang="ts">
import { VueDraggable } from "vue-draggable-plus";
import { useLocalStorage } from "@vueuse/core";
import { useCookbookStore } from "~/composables/store/use-cookbook-store";
import { useHouseholdSelf } from "@/composables/use-households";
import CookbookEditor from "~/components/Domain/Cookbook/CookbookEditor.vue";
import type { CreateCookBook, ReadCookBook } from "~/lib/api/types/cookbook";
import { useCookbookPreferences } from "~/composables/use-users/preferences";
import type {
  AICookbookGenerateRequest,
  UploadedBook,
  UploadedBookClassification,
  UploadedBookDeletePreview,
  UploadedBookReadingState,
  UploadedBookRecipeCatalog,
} from "~/lib/api/types/uploaded-book";
import { useUserApi } from "~/composables/api/api-client";
import { alert } from "~/composables/use-toast";

definePageMeta({
  middleware: ["group-only"],
});

const dialogStates = reactive({
  create: false,
  delete: false,
});

const i18n = useI18n();
const route = useRoute();
const api = useUserApi();
const { $globals } = useNuxtApp();

// Set page title
useSeoMeta({
  title: i18n.t("cookbook.cookbooks"),
});

const auth = useMealieAuth();
const { store: allCookbooks, actions, updateAll } = useCookbookStore();

// Make a local reactive copy of myCookbooks
const myCookbooks = ref<ReadCookBook[]>([]);
watch(
  allCookbooks,
  (cookbooks) => {
    myCookbooks.value
      = cookbooks?.filter(
        cookbook => cookbook.householdId === auth.user.value?.householdId,
      ).sort((a, b) => a.position > b.position) ?? [];
  },
  { immediate: true },
);

const { household } = useHouseholdSelf();
const cookbookPreferences = useCookbookPreferences();

const uploadedBooks = ref<UploadedBook[]>([]);
const uploadedBooksById = computed(() =>
  new Map(uploadedBooks.value.map(book => [book.id, book])),
);
const uploadedBookReadingStates = ref<Record<string, UploadedBookReadingState>>({});
const uploadedBooksLoading = ref(false);
const bookSearch = ref("");
const bookTypeFilter = ref("all");
const bookMetadataFilters = ref<string[]>([]);
const UPLOADED_BOOK_GROUP_KEYS = ["none", "difficulty", "michelin", "cuisine", "teaching", "type"] as const;
type UploadedBookGroupKey = typeof UPLOADED_BOOK_GROUP_KEYS[number];
const uploadedBookGroupPreferences = useLocalStorage<Record<string, UploadedBookGroupKey>>(
  "mealie-uploaded-book-grouping",
  {},
  { deep: true },
);
const uploadedBookGroupPreferenceKey = computed(() => `${auth.user.value?.id || "anonymous"}:uploaded-books`);
const uploadedBookGroupBy = computed<UploadedBookGroupKey>({
  get() {
    const stored = uploadedBookGroupPreferences.value[uploadedBookGroupPreferenceKey.value];
    return stored && UPLOADED_BOOK_GROUP_KEYS.includes(stored) ? stored : "none";
  },
  set(value) {
    if (!UPLOADED_BOOK_GROUP_KEYS.includes(value)) return;
    uploadedBookGroupPreferences.value = {
      ...uploadedBookGroupPreferences.value,
      [uploadedBookGroupPreferenceKey.value]: value,
    };
  },
});
const UPLOADED_BOOK_SORT_KEYS = ["name", "created", "size", "readingProgress", "type"] as const;
type UploadedBookSortKey = typeof UPLOADED_BOOK_SORT_KEYS[number];
const {
  sortBy: uploadedBookSortBy,
  sortDirection: uploadedBookSortDirection,
} = usePersistedListSort(UPLOADED_BOOK_SORT_KEYS, "name", "asc", "uploaded-books");
const uploadedBookSortOptions = computed<{ title: string; value: UploadedBookSortKey }[]>(() => [
  { title: i18n.t("general.name"), value: "name" },
  { title: i18n.t("catalog.created-at"), value: "created" },
  { title: i18n.t("catalog.book-size"), value: "size" },
  { title: i18n.t("catalog.reading-progress"), value: "readingProgress" },
  { title: i18n.t("cookbook.book-type"), value: "type" },
]);
const uploadedBookGroupOptions = computed<{ title: string; value: UploadedBookGroupKey }[]>(() => [
  { title: i18n.t("cookbook.group-none"), value: "none" },
  { title: i18n.t("cookbook.difficulty"), value: "difficulty" },
  { title: i18n.t("cookbook.michelin-connection"), value: "michelin" },
  { title: i18n.t("cookbook.cuisine"), value: "cuisine" },
  { title: i18n.t("cookbook.teaching-level"), value: "teaching" },
  { title: i18n.t("cookbook.book-type"), value: "type" },
]);
const aiBookDialog = ref(route.query.generate === "true");
const aiBookCreating = ref(false);
const aiBookMode = ref<"preset" | "prompt">("preset");
const aiBookPreset = ref("Italian food");
const aiBookPrompt = ref("");
const aiBookTitle = ref("");
const aiBookMaxRecipes = ref(100);
const aiBookMaxPages = ref(300);
const refreshingBookIds = ref(new Set<string>());
const uploadedBookDeleteDialog = ref(false);
const bookCoverDialog = ref(false);
const bookCoverSaving = ref(false);
const bookCoverTarget = ref<UploadedBook | null>(null);
const bookCoverMode = ref<"upload" | "url" | "auto">("upload");
const bookCoverFile = ref<File | null>(null);
const bookCoverAddress = ref("");
const uploadedBookDeleteTarget = ref<UploadedBook | null>(null);
const uploadedBookDeleting = ref(false);
const uploadedBookDeletePreview = ref<UploadedBookDeletePreview>();
const uploadedBookDeletePreviewLoading = ref(false);
const uploadedBookDeleteRecipes = ref(false);
const uploadedBookDeleteShoppingLists = ref(false);
const bookRecipeDeleteDialog = ref(false);
const bookRecipeDeleteTarget = ref<UploadedBook | null>(null);
const bookRenameDialog = ref(false);
const bookRenameTarget = ref<UploadedBook | null>(null);
const bookExtractionDialog = ref(false);
const bookExtractionTarget = ref<UploadedBook | null>(null);
const bookExtractionStarting = ref(false);
const bookExtractionAllPages = ref(true);
const bookExtractionPageStart = ref<number | null>(null);
const bookExtractionPageEnd = ref<number | null>(null);
const bookExtractionPagesPerChunk = ref(10);
const bookExtractionCreateLists = ref(true);
const bookExtractionOrganizeLists = ref(true);
const bookExtractionRecipeImages = ref(true);
const bookExtractionItemImages = ref(true);
const bookExtractionTips = ref(true);
const bookExtractionAllowDuplicates = ref(false);
const bookRecipeCatalogDialog = ref(false);
const bookRecipeCatalogTarget = ref<UploadedBook | null>(null);
const bookRecipeCatalog = ref<UploadedBookRecipeCatalog | null>(null);
const bookRecipeCatalogQuery = ref("");
const bookRecipeCatalogLanguage = ref("Hebrew");
const bookRecipeCatalogSelected = ref<string[]>([]);
const bookRecipeCatalogLoading = ref(false);
const bookRecipeCatalogImporting = ref(false);
const bookRecipeCatalogCreateLists = ref(true);
const bookRecipeCatalogOrganizeLists = ref(true);
const bookRecipeCatalogRecipeImages = ref(true);
const bookRecipeCatalogItemImages = ref(true);
const bookRecipeCatalogTips = ref(true);
const bookTranslationDialog = ref(false);
const bookTranslationTarget = ref<UploadedBook | null>(null);
const bookTranslationStarting = ref(false);
const bookTranslationAllPages = ref(true);
const bookTranslationPageStart = ref<number | null>(null);
const bookTranslationPageEnd = ref<number | null>(null);
const bookTranslationPagesPerChunk = ref(10);
const bookTranslationLanguage = ref("Hebrew");
const bookTranslationIncludeLinkedRecipes = ref(true);
const bookTranslationExtractRecipes = ref(false);
const bookTranslationCreateLists = ref(true);
const bookTranslationOrganizeLists = ref(true);
const bookTranslationRecipeImages = ref(true);
const bookTranslationItemImages = ref(true);
const bookTranslationTips = ref(true);
const bookTranslationManualPage = ref<number | null>(null);
const bookTranslationManualText = ref("");
const bookTranslationManualSaving = ref(false);
let classificationRefreshTimer: number | null = null;

const aiBookPresetOptions = computed(() => [
  { title: i18n.t("cookbook.preset-italian"), value: "Italian food" },
  { title: i18n.t("cookbook.preset-dinner"), value: "Dinner recipes" },
  { title: i18n.t("cookbook.preset-michelin"), value: "Michelin-level chef recipes" },
  { title: i18n.t("cookbook.preset-baking"), value: "Baking and pastry" },
  { title: i18n.t("cookbook.preset-quick"), value: "Quick recipes" },
  { title: i18n.t("cookbook.preset-vegetarian"), value: "Vegetarian recipes" },
]);
const bookTypeOptions = computed(() => [
  { title: i18n.t("cookbook.all-books"), value: "all" },
  { title: i18n.t("cookbook.uploaded-books"), value: "uploaded" },
  { title: i18n.t("cookbook.translated-books"), value: "translated" },
  { title: i18n.t("cookbook.ai-generated-books"), value: "generated" },
]);
const aiBookSubmitDisabled = computed(() =>
  aiBookMode.value === "preset" ? !aiBookPreset.value.trim() : !aiBookPrompt.value.trim(),
);
const canSaveBookCover = computed(() => Boolean(
  bookCoverTarget.value
  && (bookCoverMode.value === "auto"
    || (bookCoverMode.value === "upload" && bookCoverFile.value)
    || (bookCoverMode.value === "url" && bookCoverAddress.value.trim())),
));
const bookExtractionRangeInvalid = computed(() => !bookExtractionAllPages.value && (
  !bookExtractionPageStart.value
  || !bookExtractionPageEnd.value
  || bookExtractionPageEnd.value < bookExtractionPageStart.value
));
const bookTranslationRangeInvalid = computed(() => !bookTranslationAllPages.value && (
  !bookTranslationPageStart.value
  || !bookTranslationPageEnd.value
  || bookTranslationPageEnd.value < bookTranslationPageStart.value
));
const bookTranslationLanguageOptions = computed(() => [
  { title: i18n.t("cookbook.language-hebrew"), value: "Hebrew" },
  { title: i18n.t("cookbook.language-english"), value: "English" },
]);
const selectableCatalogRecipeIds = computed(() =>
  (bookRecipeCatalog.value?.candidates || [])
    .filter(candidate => !candidate.importedRecipeSlug)
    .map(candidate => candidate.id),
);
const allCatalogRecipesSelected = computed(() =>
  selectableCatalogRecipeIds.value.length > 0
  && selectableCatalogRecipeIds.value.every(id => bookRecipeCatalogSelected.value.includes(id)),
);
const someCatalogRecipesSelected = computed(() =>
  !allCatalogRecipesSelected.value
  && selectableCatalogRecipeIds.value.some(id => bookRecipeCatalogSelected.value.includes(id)),
);
const bookTranslationFailedChunks = computed(() => {
  const raw = bookTranslationTarget.value?.translationChunkStatus;
  if (!raw) return [];
  try {
    const states = JSON.parse(raw) as Array<Record<string, unknown>>;
    return states
      .filter(state => state.status !== "completed")
      .map(state => ({
        range: String(state.range || `${state.startPage}-${state.endPage}`),
        startPage: Math.max(1, Number(state.startPage) || 1),
        endPage: Math.max(1, Number(state.endPage) || Number(state.startPage) || 1),
      }))
      .sort((a, b) => a.startPage - b.startPage);
  }
  catch {
    return [];
  }
});

function bookClassification(book: UploadedBook): UploadedBookClassification | undefined {
  return book.bookMetadata?.classification;
}

function isGeneratedBook(book: UploadedBook) {
  return book.bookMetadata?.generated_by_ai === true;
}

function bookRecipeSource(book: UploadedBook) {
  if (!book.isTranslatedBook) {
    return book;
  }
  return book.translatedFromBookId
    ? uploadedBooksById.value.get(book.translatedFromBookId) || null
    : null;
}

function bookLabels(book: UploadedBook) {
  const classification = bookClassification(book);
  return Array.from(new Set([
    ...(classification?.cuisines || []),
    ...(classification?.categories || []),
    ...(classification?.tags || []),
    classification?.difficulty,
    classification?.teaching_level,
    classification?.book_type,
    classification?.michelin_related ? i18n.t("cookbook.michelin-related") : undefined,
  ].filter((value): value is string => Boolean(value && value !== "unspecified"))));
}

const bookMetadataOptions = computed(() =>
  Array.from(new Set(uploadedBooks.value.flatMap(bookLabels))).sort((a, b) => a.localeCompare(b)),
);

function matchesBookType(book: UploadedBook) {
  if (bookTypeFilter.value === "generated") return isGeneratedBook(book);
  if (bookTypeFilter.value === "translated") return book.isTranslatedBook;
  if (bookTypeFilter.value === "uploaded") return !book.isTranslatedBook && !isGeneratedBook(book);
  return true;
}

const filteredUploadedBooks = computed(() => {
  const query = bookSearch.value.trim().toLocaleLowerCase();
  return uploadedBooks.value.filter((book) => {
    if (!matchesBookType(book)) return false;
    const labels = bookLabels(book);
    if (bookMetadataFilters.value.some(filter => !labels.includes(filter))) return false;
    if (!query) return true;
    return `${book.name} ${book.originalFileName} ${labels.join(" ")} ${bookClassification(book)?.summary || ""}`
      .toLocaleLowerCase()
      .includes(query);
  });
});
const baseSortedUploadedBooks = sortListItems(
  filteredUploadedBooks,
  book => ({
    name: book.name,
    created: book.createdAt,
    size: book.size,
    readingProgress: bookReadingState(book)?.readingPercent,
    type: bookTypeLabel(book),
  })[uploadedBookSortBy.value],
  uploadedBookSortDirection,
  i18n.locale,
);
function bookGroupLabel(book: UploadedBook) {
  const classification = bookClassification(book);
  switch (uploadedBookGroupBy.value) {
    case "difficulty":
      return classification?.difficulty || i18n.t("cookbook.unspecified");
    case "michelin":
      return classification?.michelin_related
        ? i18n.t("cookbook.michelin-related")
        : i18n.t("cookbook.not-michelin-related");
    case "cuisine":
      return classification?.cuisines?.[0] || i18n.t("cookbook.unspecified");
    case "teaching":
      return classification?.teaching_level || i18n.t("cookbook.unspecified");
    case "type":
      return bookTypeLabel(book);
    default:
      return "";
  }
}
const sortedUploadedBooks = computed(() => {
  if (uploadedBookGroupBy.value === "none") return baseSortedUploadedBooks.value;
  return baseSortedUploadedBooks.value
    .map((book, index) => ({ book, index, group: bookGroupLabel(book) }))
    .sort((left, right) => left.group.localeCompare(right.group, i18n.locale.value, {
      numeric: true,
      sensitivity: "base",
    }) || left.index - right.index)
    .map(entry => entry.book);
});
const {
  page: uploadedBookPage,
  itemsPerPage: uploadedBooksPerPage,
  totalItems: uploadedBookTotal,
  paginatedItems: paginatedUploadedBooks,
} = useListPagination(sortedUploadedBooks);

function isFirstBookGroupItem(index: number) {
  if (uploadedBookGroupBy.value === "none") return false;
  const current = paginatedUploadedBooks.value[index];
  const previous = paginatedUploadedBooks.value[index - 1];
  return !previous || bookGroupLabel(previous) !== bookGroupLabel(current);
}

async function loadUploadedBooks() {
  uploadedBooksLoading.value = true;
  try {
    const [booksResponse, statesResponse] = await Promise.all([
      api.uploadedBooks.getAll(),
      api.uploadedBooks.getReadingStates(),
    ]);
    uploadedBooks.value = booksResponse.data || [];
    uploadedBookReadingStates.value = Object.fromEntries(
      (statesResponse.data || []).map(state => [state.bookId, state]),
    );
  }
  finally {
    uploadedBooksLoading.value = false;
  }
}

async function loadUploadedBookReadingStates() {
  const { data } = await api.uploadedBooks.getReadingStates();
  if (data) {
    uploadedBookReadingStates.value = Object.fromEntries(data.map(state => [state.bookId, state]));
  }
}

function bookReadingState(book: UploadedBook) {
  const direct = uploadedBookReadingStates.value[book.id];
  if (direct) return direct;
  if (book.translatedBookId) return uploadedBookReadingStates.value[book.translatedBookId];
  return undefined;
}

function translatedVersionOfBook(book: UploadedBook) {
  if (book.isTranslatedBook) return book;
  if (!book.translatedBookId) return undefined;
  return uploadedBooksById.value.get(book.translatedBookId);
}

function bookTranslationAudit(book: UploadedBook) {
  return translatedVersionOfBook(book)?.bookMetadata?.translation_audit;
}

function bookTranslationPercent(book: UploadedBook) {
  const audit = bookTranslationAudit(book);
  const total = Number(audit?.source_pages || 0);
  if (!total) return 0;
  const verified = bookTranslatedPageCount(book);
  return Math.min(100, Math.max(0, Math.round((verified / total) * 100)));
}

function bookTranslatedPageCount(book: UploadedBook) {
  const audit = bookTranslationAudit(book);
  return audit?.verified_translated_pages
    ?? Math.max(0, Number(audit?.translated_pages || 0) - (audit?.suspicious_pages?.length || 0));
}

function sourceBookForTranslation(book: UploadedBook) {
  if (!book.isTranslatedBook) return book;
  return book.translatedFromBookId
    ? uploadedBooksById.value.get(book.translatedFromBookId)
    : undefined;
}

function finishBookTranslation(book: UploadedBook) {
  const sourceBook = sourceBookForTranslation(book);
  if (sourceBook) openBookTranslationDialog(sourceBook);
}

function bookChapterPercent(book: UploadedBook) {
  const state = bookReadingState(book);
  if (!state?.totalChapters) return 0;
  return Math.min(100, Math.round((new Set(state.completedChapters).size / state.totalChapters) * 100));
}

function isBookCompleted(book: UploadedBook) {
  const state = bookReadingState(book);
  return Boolean(state?.totalChapters && bookChapterPercent(book) >= 100);
}

function openUploadedBook(book: UploadedBook) {
  window.open(api.uploadedBooks.fileUrl(book.id), "_blank", "noopener");
}

function resetBookCoverDialog() {
  bookCoverTarget.value = null;
  bookCoverMode.value = "upload";
  bookCoverFile.value = null;
  bookCoverAddress.value = "";
}

function openBookCoverDialog(book: UploadedBook) {
  resetBookCoverDialog();
  bookCoverTarget.value = book;
  bookCoverDialog.value = true;
}

async function saveBookCover() {
  if (!bookCoverTarget.value || bookCoverSaving.value || !canSaveBookCover.value) return;
  bookCoverSaving.value = true;
  try {
    const response = bookCoverMode.value === "upload"
      ? await api.uploadedBooks.uploadCover(bookCoverTarget.value.id, bookCoverFile.value!)
      : bookCoverMode.value === "url"
        ? await api.uploadedBooks.saveCoverUrl(bookCoverTarget.value.id, bookCoverAddress.value.trim())
        : await api.uploadedBooks.findCover(bookCoverTarget.value.id);
    if (!response.data || response.error) {
      alert.error(i18n.t("cookbook.cover-save-failed"));
      return;
    }
    const index = uploadedBooks.value.findIndex(book => book.id === response.data!.id);
    if (index >= 0) uploadedBooks.value[index] = response.data;
    bookCoverDialog.value = false;
    resetBookCoverDialog();
    alert.success(i18n.t("cookbook.cover-saved"));
  }
  finally {
    bookCoverSaving.value = false;
  }
}

async function classifyUploadedBook(book: UploadedBook) {
  const { data, error } = await api.uploadedBooks.classify(book.id);
  if (error || !data) {
    alert.error(i18n.t("cookbook.book-classification-failed"));
    return;
  }
  const index = uploadedBooks.value.findIndex(item => item.id === book.id);
  if (index >= 0) uploadedBooks.value[index] = data;
  if (classificationRefreshTimer !== null) {
    window.clearTimeout(classificationRefreshTimer);
  }
  if (!pageMounted) {
    return;
  }
  classificationRefreshTimer = window.setTimeout(() => {
    classificationRefreshTimer = null;
    if (!pageMounted) {
      return;
    }
    void loadUploadedBooks();
  }, 5000);
}

async function createAIBook() {
  const payload: AICookbookGenerateRequest = {
    mode: aiBookMode.value,
    preset: aiBookMode.value === "preset" ? aiBookPreset.value : null,
    prompt: aiBookMode.value === "prompt" ? aiBookPrompt.value.trim() : null,
    title: aiBookTitle.value.trim() || null,
    maxRecipesPerVolume: aiBookMaxRecipes.value,
    maxEstimatedPagesPerVolume: aiBookMaxPages.value,
  };
  aiBookCreating.value = true;
  try {
    const { data, error } = await api.uploadedBooks.generate(payload);
    if (error || !data?.length) {
      alert.error(i18n.t("cookbook.ai-book-create-failed"));
      return;
    }
    aiBookDialog.value = false;
    alert.success(i18n.t("cookbook.ai-book-created", { count: data.length }));
    await loadUploadedBooks();
  }
  finally {
    aiBookCreating.value = false;
  }
}

async function refreshAIBook(book: UploadedBook) {
  refreshingBookIds.value = new Set(refreshingBookIds.value).add(book.id);
  try {
    const { error } = await api.uploadedBooks.refreshAi(book.id);
    if (error) alert.error(i18n.t("cookbook.ai-book-refresh-failed"));
    else alert.success(i18n.t("cookbook.ai-book-refreshed"));
    await loadUploadedBooks();
  }
  finally {
    const next = new Set(refreshingBookIds.value);
    next.delete(book.id);
    refreshingBookIds.value = next;
  }
}

async function confirmUploadedBookDelete(book: UploadedBook) {
  uploadedBookDeleteTarget.value = book;
  uploadedBookDeletePreview.value = undefined;
  uploadedBookDeleteRecipes.value = false;
  uploadedBookDeleteShoppingLists.value = false;
  uploadedBookDeleteDialog.value = true;
  uploadedBookDeletePreviewLoading.value = true;
  try {
    const { data } = await api.uploadedBooks.deletePreview(book.id);
    if (data) uploadedBookDeletePreview.value = data;
  }
  finally {
    uploadedBookDeletePreviewLoading.value = false;
  }
}

function openBookRecipeDeleteDialog(book: UploadedBook) {
  bookRecipeDeleteTarget.value = bookRecipeSource(book) || book;
  bookRecipeDeleteDialog.value = true;
}

function openBookRenameDialog(book: UploadedBook) {
  bookRenameTarget.value = book;
  bookRenameDialog.value = true;
}

function handleBookRenamed(book: UploadedBook) {
  const index = uploadedBooks.value.findIndex(item => item.id === book.id);
  if (index >= 0) uploadedBooks.value[index] = book;
  bookRenameTarget.value = null;
}

function openBookExtractionDialog(book: UploadedBook) {
  bookExtractionTarget.value = book;
  bookExtractionAllPages.value = true;
  bookExtractionPageStart.value = null;
  bookExtractionPageEnd.value = null;
  bookExtractionPagesPerChunk.value = book.extractionPagesPerChunk || 10;
  bookExtractionCreateLists.value = true;
  bookExtractionOrganizeLists.value = true;
  bookExtractionRecipeImages.value = true;
  bookExtractionItemImages.value = true;
  bookExtractionTips.value = true;
  bookExtractionAllowDuplicates.value = false;
  bookExtractionDialog.value = true;
}

function openBookRecipeCatalogDialog(book: UploadedBook) {
  bookRecipeCatalogTarget.value = bookRecipeSource(book) || book;
  bookRecipeCatalog.value = null;
  bookRecipeCatalogQuery.value = "";
  bookRecipeCatalogLanguage.value = String(i18n.locale.value || "").toLowerCase().startsWith("he")
    ? "Hebrew"
    : "English";
  bookRecipeCatalogSelected.value = [];
  bookRecipeCatalogCreateLists.value = true;
  bookRecipeCatalogOrganizeLists.value = true;
  bookRecipeCatalogRecipeImages.value = true;
  bookRecipeCatalogItemImages.value = true;
  bookRecipeCatalogTips.value = true;
  bookRecipeCatalogDialog.value = true;
}

function toggleAllCatalogRecipes(value: boolean | null) {
  bookRecipeCatalogSelected.value = value ? [...selectableCatalogRecipeIds.value] : [];
}

async function discoverBookRecipes() {
  if (!bookRecipeCatalogTarget.value || bookRecipeCatalogLoading.value) return;
  bookRecipeCatalogLoading.value = true;
  try {
    const { data, error } = await api.uploadedBooks.discoverRecipeCatalog(
      bookRecipeCatalogTarget.value.id,
      {
        query: bookRecipeCatalogQuery.value.trim(),
        targetLanguage: bookRecipeCatalogLanguage.value,
      },
    );
    if (error || !data) {
      alert.error(i18n.t("cookbook.book-recipe-search-failed"));
      return;
    }
    bookRecipeCatalog.value = data;
    bookRecipeCatalogSelected.value = data.candidates
      .filter(candidate => !candidate.importedRecipeSlug)
      .map(candidate => candidate.id);
  }
  finally {
    bookRecipeCatalogLoading.value = false;
  }
}

async function importSelectedBookRecipes() {
  if (
    !bookRecipeCatalogTarget.value
    || !bookRecipeCatalogSelected.value.length
    || bookRecipeCatalogImporting.value
  ) return;
  bookRecipeCatalogImporting.value = true;
  try {
    const { data, error } = await api.uploadedBooks.importRecipeCatalog(
      bookRecipeCatalogTarget.value.id,
      {
        candidateIds: bookRecipeCatalogSelected.value,
        targetLanguage: bookRecipeCatalogLanguage.value,
        autoRecipeImages: bookRecipeCatalogRecipeImages.value,
        includeItemImages: bookRecipeCatalogItemImages.value,
        includeAiTips: bookRecipeCatalogTips.value,
        createShoppingLists: bookRecipeCatalogCreateLists.value,
        organizeShoppingListsWithAi:
          bookRecipeCatalogCreateLists.value && bookRecipeCatalogOrganizeLists.value,
      },
    );
    if (error || !data) {
      alert.error(i18n.t("cookbook.book-recipe-import-failed"));
      return;
    }
    const index = uploadedBooks.value.findIndex(book => book.id === data.id);
    if (index >= 0) uploadedBooks.value[index] = data;
    bookRecipeCatalogDialog.value = false;
    alert.success(i18n.t("cookbook.book-recipe-import-started"));
  }
  finally {
    bookRecipeCatalogImporting.value = false;
  }
}

function openBookTranslationDialog(book: UploadedBook) {
  const options = book.bookMetadata?.translation_options as Record<string, unknown> | undefined;
  bookTranslationTarget.value = book;
  bookTranslationAllPages.value = !book.translationPageStart && !book.translationPageEnd;
  bookTranslationPageStart.value = book.translationPageStart || null;
  bookTranslationPageEnd.value = book.translationPageEnd || null;
  bookTranslationPagesPerChunk.value = book.translationPagesPerChunk || 10;
  bookTranslationLanguage.value = book.translationLanguage
    || (String(i18n.locale.value || "").toLowerCase().startsWith("he") ? "Hebrew" : "English");
  bookTranslationIncludeLinkedRecipes.value = options?.include_linked_recipes !== false;
  bookTranslationExtractRecipes.value = options?.extract_recipes === true;
  bookTranslationCreateLists.value = options?.create_shopping_lists !== false;
  bookTranslationOrganizeLists.value = options?.organize_shopping_lists_with_ai !== false;
  bookTranslationRecipeImages.value = options?.auto_recipe_images !== false;
  bookTranslationItemImages.value = options?.include_item_images !== false;
  bookTranslationTips.value = options?.include_ai_tips !== false;
  bookTranslationManualPage.value = null;
  bookTranslationManualText.value = "";
  bookTranslationDialog.value = true;
}

function selectManualTranslationPage(page: number) {
  bookTranslationManualPage.value = page;
}

async function saveManualTranslationPage() {
  if (
    !bookTranslationTarget.value
    || !bookTranslationManualPage.value
    || !bookTranslationManualText.value.trim()
    || bookTranslationManualSaving.value
  ) return;
  bookTranslationManualSaving.value = true;
  try {
    const { data, error } = await api.uploadedBooks.saveManualTranslationPage(
      bookTranslationTarget.value.id,
      {
        page: bookTranslationManualPage.value,
        text: bookTranslationManualText.value.trim(),
      },
    );
    if (error || !data) {
      alert.error(i18n.t("cookbook.manual-translation-save-failed"));
      return;
    }
    const index = uploadedBooks.value.findIndex(book => book.id === data.id);
    if (index >= 0) uploadedBooks.value[index] = data;
    bookTranslationTarget.value = data;
    bookTranslationManualText.value = "";
    alert.success(i18n.t("cookbook.manual-translation-saved"));
  }
  finally {
    bookTranslationManualSaving.value = false;
  }
}

async function startBookExtraction() {
  if (!bookExtractionTarget.value || bookExtractionRangeInvalid.value || bookExtractionStarting.value) return;
  bookExtractionStarting.value = true;
  try {
    const { data, error } = await api.uploadedBooks.extractRecipes(bookExtractionTarget.value.id, {
      pagesPerChunk: Math.min(100, Math.max(1, Number(bookExtractionPagesPerChunk.value) || 10)),
      translateLanguage: String(i18n.locale.value || "en-US"),
      pageStart: bookExtractionAllPages.value ? null : bookExtractionPageStart.value,
      pageEnd: bookExtractionAllPages.value ? null : bookExtractionPageEnd.value,
      autoRecipeImages: bookExtractionRecipeImages.value,
      includeItemImages: bookExtractionItemImages.value,
      includeAiTips: bookExtractionTips.value,
      createShoppingLists: bookExtractionCreateLists.value,
      organizeShoppingListsWithAi: bookExtractionCreateLists.value && bookExtractionOrganizeLists.value,
      allowDuplicateRecipes: bookExtractionAllowDuplicates.value,
    });
    if (error || !data) {
      alert.error(i18n.t("cookbook.extraction-start-failed"));
      return;
    }
    const index = uploadedBooks.value.findIndex(book => book.id === data.id);
    if (index >= 0) uploadedBooks.value[index] = data;
    bookExtractionDialog.value = false;
    alert.success(i18n.t("cookbook.extraction-started"));
  }
  finally {
    bookExtractionStarting.value = false;
  }
}

async function startBookTranslation() {
  if (!bookTranslationTarget.value || bookTranslationRangeInvalid.value || bookTranslationStarting.value) return;
  bookTranslationStarting.value = true;
  try {
    const { data, error } = await api.uploadedBooks.translate(bookTranslationTarget.value.id, {
      pagesPerChunk: Math.min(100, Math.max(1, Number(bookTranslationPagesPerChunk.value) || 10)),
      targetLanguage: bookTranslationLanguage.value,
      pageStart: bookTranslationAllPages.value ? null : bookTranslationPageStart.value,
      pageEnd: bookTranslationAllPages.value ? null : bookTranslationPageEnd.value,
      includeLinkedRecipes: bookTranslationIncludeLinkedRecipes.value,
      extractRecipes: bookTranslationExtractRecipes.value,
      autoRecipeImages: bookTranslationRecipeImages.value,
      includeItemImages: bookTranslationItemImages.value,
      includeAiTips: bookTranslationTips.value,
      createShoppingLists: bookTranslationCreateLists.value,
      organizeShoppingListsWithAi: bookTranslationCreateLists.value && bookTranslationOrganizeLists.value,
    });
    if (error || !data) {
      alert.error(i18n.t("cookbook.translation-start-failed"));
      return;
    }
    const index = uploadedBooks.value.findIndex(book => book.id === data.id);
    if (index >= 0) uploadedBooks.value[index] = data;
    bookTranslationDialog.value = false;
    alert.success(i18n.t("cookbook.translation-started"));
  }
  finally {
    bookTranslationStarting.value = false;
  }
}

function handleBookRecipesDeleted(bookId: string, _deletedCount: number, remainingCount: number) {
  const book = uploadedBooks.value.find(item => item.id === bookId);
  if (book) {
    book.extractionRecipesCreated = remainingCount;
  }
  bookRecipeDeleteTarget.value = null;
  window.dispatchEvent(new CustomEvent("mealie:organizers-updated"));
}

async function deleteUploadedBook() {
  if (!uploadedBookDeleteTarget.value) return;
  uploadedBookDeleting.value = true;
  try {
    const { error } = await api.uploadedBooks.delete(uploadedBookDeleteTarget.value.id, {
      deleteRecipes: uploadedBookDeleteRecipes.value,
      deleteShoppingLists: uploadedBookDeleteShoppingLists.value,
    });
    if (error) alert.error(i18n.t("cookbook.delete-book-failed"));
    else uploadedBooks.value = uploadedBooks.value.filter(book => book.id !== uploadedBookDeleteTarget.value?.id);
    uploadedBookDeleteDialog.value = false;
    uploadedBookDeleteTarget.value = null;
  }
  finally {
    uploadedBookDeleting.value = false;
  }
}

function bookTypeLabel(book: UploadedBook) {
  if (isGeneratedBook(book)) return i18n.t("cookbook.ai-generated-book");
  if (book.isTranslatedBook) return i18n.t("cookbook.translated-book");
  return i18n.t("cookbook.uploaded-book");
}

function bookIcon(book: UploadedBook) {
  if (isGeneratedBook(book)) return $globals.icons.robot;
  if (book.isTranslatedBook) return $globals.icons.translate;
  return book.extension === ".pdf" ? $globals.icons.filePDF : $globals.icons.book;
}

// create
const createTargetKey = ref(0);
const createTarget = ref<ReadCookBook | null>(null);
async function createCookbook() {
  const name = i18n.t("cookbook.household-cookbook-name", [
    household.value?.name || "",
    String((myCookbooks.value?.length ?? 0) + 1),
  ]) as string;

  const data = { name } as CreateCookBook;
  await actions.createOne(data).then((cookbook) => {
    if (!cookbook) {
      return;
    }

    myCookbooks.value.push(cookbook);
    createTarget.value = cookbook as ReadCookBook;
    createTargetKey.value++;
  });
  dialogStates.create = true;
}

// delete
const deleteTarget = ref<ReadCookBook | null>(null);
function deleteEventHandler(item: ReadCookBook) {
  deleteTarget.value = item;
  dialogStates.delete = true;
}
async function deleteCookbook() {
  if (!deleteTarget.value) {
    return;
  }
  await actions.deleteOne(deleteTarget.value.id);
  myCookbooks.value = myCookbooks.value.filter(c => c.id !== deleteTarget.value?.id);
  dialogStates.delete = false;
  deleteTarget.value = null;
}

async function deleteCreateTarget() {
  if (!createTarget.value?.id) {
    return;
  }
  await actions.deleteOne(createTarget.value.id);
  myCookbooks.value = myCookbooks.value.filter(c => c.id !== createTarget.value?.id);
  dialogStates.create = false;
  createTarget.value = null;
}
function handleUnmount() {
  if (!createTarget.value?.id || createTarget.value.queryFilterString) {
    return;
  }
  deleteCreateTarget();
}
let pageMounted = false;
onMounted(() => {
  pageMounted = true;
  window.addEventListener("beforeunload", handleUnmount);
  window.addEventListener("focus", loadUploadedBookReadingStates);
  void loadUploadedBooks();
});
onBeforeUnmount(() => {
  pageMounted = false;
  if (classificationRefreshTimer !== null) {
    window.clearTimeout(classificationRefreshTimer);
    classificationRefreshTimer = null;
  }
  handleUnmount();
  window.removeEventListener("beforeunload", handleUnmount);
  window.removeEventListener("focus", loadUploadedBookReadingStates);
});
</script>

<style scoped>
.cookbook-library {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.cookbook-library__filters {
  display: grid;
  grid-template-columns: minmax(240px, 1.4fr) minmax(170px, 0.7fr) minmax(240px, 1fr) minmax(170px, 0.7fr);
  gap: 12px;
}

.cookbook-library__group-divider {
  align-items: center;
  color: rgb(var(--v-theme-primary));
  display: flex;
  font-size: 1rem;
  font-weight: 700;
  gap: 12px;
  grid-column: 1 / -1;
  margin-top: 8px;
}

.cookbook-library__group-divider::after {
  background: rgba(var(--v-theme-primary), 0.28);
  content: "";
  flex: 1;
  height: 1px;
}

.book-recipe-catalog__search {
  align-items: stretch;
  display: grid;
  gap: 10px;
  grid-template-columns: minmax(240px, 1fr) minmax(150px, 190px) auto;
}

.book-recipe-catalog__list {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  max-height: min(48vh, 520px);
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}

.book-recipe-catalog__row {
  align-items: center;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  cursor: pointer;
  display: flex;
  gap: 8px;
  min-height: 58px;
  padding: 7px 10px;
}

.book-recipe-catalog__row:last-child {
  border-bottom: 0;
}

.book-recipe-catalog__row:hover {
  background: rgba(var(--v-theme-primary), 0.06);
}

.book-recipe-catalog__details {
  display: grid;
  flex: 1;
  min-width: 0;
}

.book-recipe-catalog__details strong,
.book-recipe-catalog__details small {
  overflow-wrap: anywhere;
}

.book-recipe-catalog__details small {
  color: rgba(var(--v-theme-on-surface), 0.67);
}

.cookbook-library__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.cookbook-library__book {
  display: flex;
  flex-direction: column;
  min-height: 250px;
  border-radius: 8px;
  transition:
    border-color 0.16s ease,
    box-shadow 0.16s ease,
    transform 0.16s ease;
}

.cookbook-library__book:hover,
.cookbook-library__book:focus-within {
  border-color: rgba(var(--v-theme-primary), 0.65);
  box-shadow: 0 5px 16px rgba(var(--v-theme-on-surface), 0.14);
  transform: translateY(-2px);
}

.cookbook-library__book--complete {
  border-color: rgba(var(--v-theme-success), 0.72);
  box-shadow: 0 0 0 1px rgba(var(--v-theme-success), 0.2);
}

.cookbook-library__cover {
  aspect-ratio: 4 / 3;
  background: rgb(var(--v-theme-surface-variant));
  overflow: hidden;
  position: relative;
  width: 100%;
}

.cookbook-library__cover--interactive {
  cursor: pointer;
  outline: none;
}

.cookbook-library__cover--interactive:focus-visible {
  box-shadow: inset 0 0 0 3px rgb(var(--v-theme-primary));
}

.cookbook-library__cover-action {
  align-items: center;
  background: rgba(0, 0, 0, 0.48);
  color: white;
  display: flex;
  inset: 0;
  justify-content: center;
  opacity: 0;
  pointer-events: none;
  position: absolute;
  transition: opacity 0.16s ease;
}

.cookbook-library__complete-mark {
  align-items: center;
  background: rgb(var(--v-theme-success));
  border-radius: 50%;
  color: rgb(var(--v-theme-on-success));
  display: flex;
  height: 34px;
  inset-inline-end: 10px;
  justify-content: center;
  position: absolute;
  top: 54px;
  width: 34px;
  z-index: 2;
}

.cookbook-library__cover-edit {
  inset-inline-start: 10px;
  position: absolute;
  top: 10px;
  z-index: 3;
}

.cookbook-library__cover-delete {
  inset-inline-end: 10px;
  position: absolute;
  top: 10px;
  z-index: 3;
}

.cookbook-library__reading-row {
  align-items: center;
  display: flex;
  font-size: 0.78rem;
  justify-content: space-between;
  margin-bottom: 3px;
}

.cookbook-library__translation-footer {
  align-items: center;
  color: rgba(var(--v-theme-on-surface), 0.67);
  display: flex;
  gap: 4px;
  justify-content: space-between;
  min-height: 28px;
}

.cookbook-library__translation-footer small {
  line-height: 1.25;
}

.cookbook-library__book:hover .cookbook-library__cover-action,
.cookbook-library__cover--interactive:focus-visible .cookbook-library__cover-action {
  opacity: 1;
}

.cookbook-library__cover-fallback {
  align-items: center;
  color: rgba(var(--v-theme-on-surface), 0.54);
  display: flex;
  height: 260px;
  justify-content: center;
  width: 100%;
}

.cookbook-library__book .v-card-actions {
  margin-top: auto;
}

.book-summary {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

@media (max-width: 900px) {
  .book-recipe-catalog__search {
    grid-template-columns: 1fr;
  }

  .cookbook-library__filters {
    grid-template-columns: 1fr;
  }
}
</style>
