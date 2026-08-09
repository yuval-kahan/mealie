<template>
  <v-container fluid class="notebook-page pa-0">
    <div class="notebook-shell">
      <aside class="notebook-panel notebook-panel--books">
        <div class="panel-heading">
          <div class="d-flex align-center ga-2 min-w-0">
            <v-icon color="primary">
              {{ $globals.icons.notebook }}
            </v-icon>
            <h1 class="panel-title">
              {{ $t("notebook.notebooks") }}
            </h1>
          </div>
          <v-btn
            icon
            size="small"
            color="primary"
            variant="text"
            :title="$t('notebook.new-notebook')"
            @click="openNotebookDialog()"
          >
            <v-icon>{{ $globals.icons.notebookPlus }}</v-icon>
          </v-btn>
        </div>

        <v-text-field
          v-model="notebookFilter"
          :placeholder="$t('search.search')"
          :prepend-inner-icon="$globals.icons.search"
          variant="outlined"
          density="compact"
          hide-details
          clearable
          class="panel-search"
        />

        <div class="panel-scroll">
          <button
            v-for="notebook in filteredNotebooks"
            :key="notebook.id"
            type="button"
            class="notebook-row"
            :class="{ 'notebook-row--active': activeNotebook?.id === notebook.id }"
            @click="selectNotebook(notebook.id)"
          >
            <span class="notebook-color" :style="{ backgroundColor: notebook.color }" />
            <span class="notebook-row__content">
              <strong>{{ notebook.title }}</strong>
              <small>{{ notebook.pageCount }} {{ $t("notebook.page") }}</small>
            </span>
            <v-icon v-if="notebook.isPinned" size="18">
              {{ $globals.icons.pin }}
            </v-icon>
            <v-icon v-if="notebook.isFavorite" size="18" color="warning">
              {{ $globals.icons.star }}
            </v-icon>
          </button>

          <v-btn
            v-if="ready && !filteredNotebooks.length"
            block
            variant="tonal"
            color="primary"
            class="mt-3"
            :prepend-icon="$globals.icons.notebookPlus"
            @click="openNotebookDialog()"
          >
            {{ $t("notebook.no-notebooks") }}
          </v-btn>
        </div>

        <div v-if="activeNotebook" class="panel-footer">
          <v-btn
            icon
            size="small"
            variant="text"
            :title="$t('general.edit')"
            @click="openNotebookDialog(activeNotebook)"
          >
            <v-icon>{{ $globals.icons.edit }}</v-icon>
          </v-btn>
          <v-btn
            icon
            size="small"
            variant="text"
            color="error"
            :title="$t('general.delete')"
            @click="confirmDeleteNotebook = true"
          >
            <v-icon>{{ $globals.icons.delete }}</v-icon>
          </v-btn>
        </div>
      </aside>

      <aside class="notebook-panel notebook-panel--outline">
        <div class="panel-heading">
          <h2 class="panel-title">
            {{ $t("notebook.outline") }}
          </h2>
          <v-menu v-if="activeNotebook">
            <template #activator="{ props }">
              <v-btn v-bind="props" icon size="small" variant="text" :title="$t('notebook.new-item')">
                <v-icon>{{ $globals.icons.createAlt }}</v-icon>
              </v-btn>
            </template>
            <v-list density="compact">
              <v-list-item
                v-for="option in nodeTypeOptions"
                :key="option.value"
                :prepend-icon="nodeIcon(option.value)"
                :title="option.title"
                @click="openNodeDialog(option.value)"
              />
            </v-list>
          </v-menu>
        </div>

        <v-text-field
          v-model="noteSearch"
          :placeholder="$t('notebook.search-notes')"
          :prepend-inner-icon="$globals.icons.search"
          variant="outlined"
          density="compact"
          hide-details
          clearable
          class="panel-search"
          @keydown.enter="searchNotes"
        />

        <div class="panel-scroll outline-scroll" @dragover.prevent @drop="dropOnRoot">
          <template v-if="searchResults !== null">
            <div class="search-result-heading">
              <span>{{ $t("notebook.search-results") }}</span>
              <v-btn icon size="x-small" variant="text" @click="clearSearchResults">
                <v-icon>{{ $globals.icons.close }}</v-icon>
              </v-btn>
            </div>
            <button
              v-for="result in searchResults"
              :key="result.nodeId"
              type="button"
              class="search-result"
              @click="openSearchResult(result)"
            >
              <strong>{{ result.nodeTitle }}</strong>
              <small>{{ result.notebookTitle }}</small>
              <span>{{ result.excerpt }}</span>
            </button>
            <p v-if="!searchResults.length" class="empty-note">
              {{ $t("notebook.no-results") }}
            </p>
          </template>

          <template v-else>
            <div
              v-for="entry in visibleTree"
              :key="entry.node.id"
              class="outline-row"
              :class="{ 'outline-row--active': selectedNode?.id === entry.node.id }"
              :style="{ paddingInlineStart: `${8 + entry.depth * 18}px` }"
              draggable="true"
              @dragstart="startNodeDrag(entry.node.id)"
              @dragover.prevent
              @drop.stop="dropOnNode(entry.node)"
            >
              <v-btn
                v-if="hasChildren(entry.node.id)"
                icon
                size="x-small"
                variant="text"
                :title="entry.node.isCollapsed ? $t('notebook.expand') : $t('notebook.collapse')"
                @click.stop="toggleNode(entry.node)"
              >
                <v-icon size="18">
                  {{ entry.node.isCollapsed ? $globals.icons.chevronRight : $globals.icons.chevronDown }}
                </v-icon>
              </v-btn>
              <span v-else class="outline-spacer" />
              <button type="button" class="outline-select" @click="selectNode(entry.node)">
                <v-icon size="19" :color="entry.node.color || undefined">
                  {{ nodeIcon(entry.node.nodeType) }}
                </v-icon>
                <span>{{ entry.node.title }}</span>
              </button>
              <v-menu>
                <template #activator="{ props }">
                  <v-btn v-bind="props" icon size="x-small" variant="text" @click.stop>
                    <v-icon>{{ $globals.icons.dotsVertical }}</v-icon>
                  </v-btn>
                </template>
                <v-list density="compact">
                  <v-list-item
                    :prepend-icon="$globals.icons.edit"
                    :title="$t('general.edit')"
                    @click="openNodeDialog(entry.node.nodeType, entry.node)"
                  />
                  <v-list-item
                    v-if="entry.node.nodeType !== 'page'"
                    :prepend-icon="$globals.icons.createAlt"
                    :title="$t('notebook.new-item')"
                    @click="openChildDialog(entry.node)"
                  />
                  <v-list-item
                    :prepend-icon="$globals.icons.star"
                    :title="$t('notebook.favorites')"
                    @click="toggleFavorite(entry.node)"
                  />
                  <v-list-item
                    :prepend-icon="$globals.icons.delete"
                    :title="$t('general.delete')"
                    base-color="error"
                    @click="openDeleteNode(entry.node)"
                  />
                </v-list>
              </v-menu>
            </div>
          </template>
        </div>
      </aside>

      <main class="notebook-editor-area">
        <template v-if="selectedNode?.nodeType === 'page'">
          <div class="editor-topline">
            <v-text-field
              v-model="draftTitle"
              variant="plain"
              density="compact"
              hide-details
              class="page-title-input"
              @update:model-value="scheduleSave"
            />
            <span class="save-status" :class="{ 'save-status--error': saveState === 'error' }">
              {{ saveStateLabel }}
            </span>
            <v-btn
              icon
              size="small"
              variant="text"
              :title="$t('notebook.version-history')"
              @click="openRevisionHistory"
            >
              <v-icon>{{ $globals.icons.timelineText }}</v-icon>
            </v-btn>
            <v-btn
              icon
              size="small"
              variant="text"
              :color="selectedNode.isFavorite ? 'warning' : undefined"
              :title="$t('notebook.favorites')"
              @click="toggleFavorite(selectedNode)"
            >
              <v-icon>{{ $globals.icons.star }}</v-icon>
            </v-btn>
          </div>

          <div class="editor-toolbar" role="toolbar" :aria-label="$t('notebook.formatting')">
            <v-btn icon size="small" variant="text" title="Bold" @click="exec('bold')">
              <v-icon>{{ $globals.icons.formatBold }}</v-icon>
            </v-btn>
            <v-btn icon size="small" variant="text" title="Italic" @click="exec('italic')">
              <v-icon>{{ $globals.icons.formatItalic }}</v-icon>
            </v-btn>
            <v-btn icon size="small" variant="text" title="Underline" @click="exec('underline')">
              <v-icon>{{ $globals.icons.formatUnderline }}</v-icon>
            </v-btn>
            <v-btn icon size="small" variant="text" title="Strikethrough" @click="exec('strikeThrough')">
              <v-icon>{{ $globals.icons.formatStrikethrough }}</v-icon>
            </v-btn>
            <v-btn icon size="small" variant="text" :title="$t('notebook.subscript')" @click="exec('subscript')">
              <v-icon>{{ $globals.icons.formatSubscript }}</v-icon>
            </v-btn>
            <v-btn icon size="small" variant="text" :title="$t('notebook.superscript')" @click="exec('superscript')">
              <v-icon>{{ $globals.icons.formatSuperscript }}</v-icon>
            </v-btn>
            <v-divider vertical class="mx-1" />
            <v-select
              v-model="blockFormat"
              :items="blockOptions"
              density="compact"
              variant="outlined"
              hide-details
              class="toolbar-select"
              @update:model-value="applyBlock"
            />
            <v-btn icon size="small" variant="text" title="Bulleted list" @click="exec('insertUnorderedList')">
              <v-icon>{{ $globals.icons.formatListBulleted }}</v-icon>
            </v-btn>
            <v-btn icon size="small" variant="text" title="Numbered list" @click="exec('insertOrderedList')">
              <v-icon>{{ $globals.icons.formatListNumbered }}</v-icon>
            </v-btn>
            <v-btn icon size="small" variant="text" :title="$t('notebook.checklist')" @click="insertChecklist">
              <v-icon>{{ $globals.icons.formatListCheck }}</v-icon>
            </v-btn>
            <v-btn icon size="small" variant="text" :title="$t('notebook.decrease-indent')" @click="exec('outdent')">
              <v-icon>{{ $globals.icons.formatIndentDecrease }}</v-icon>
            </v-btn>
            <v-btn icon size="small" variant="text" :title="$t('notebook.increase-indent')" @click="exec('indent')">
              <v-icon>{{ $globals.icons.formatIndentIncrease }}</v-icon>
            </v-btn>
            <v-divider vertical class="mx-1" />
            <v-btn icon size="small" variant="text" title="Align left" @click="exec('justifyLeft')">
              <v-icon>{{ $globals.icons.formatAlignLeft }}</v-icon>
            </v-btn>
            <v-btn icon size="small" variant="text" title="Align center" @click="exec('justifyCenter')">
              <v-icon>{{ $globals.icons.formatAlignCenter }}</v-icon>
            </v-btn>
            <v-btn icon size="small" variant="text" title="Align right" @click="exec('justifyRight')">
              <v-icon>{{ $globals.icons.formatAlignRight }}</v-icon>
            </v-btn>
            <v-divider vertical class="mx-1" />
            <label class="color-control" :title="$t('notebook.text-color')">
              <v-icon>{{ $globals.icons.textBoxCheckOutline }}</v-icon>
              <input v-model="inlineTextColor" type="color" @input="exec('foreColor', inlineTextColor)">
            </label>
            <v-menu>
              <template #activator="{ props }">
                <v-btn v-bind="props" icon size="small" variant="text" :title="$t('notebook.highlight-categories')">
                  <v-icon>{{ $globals.icons.formatColorFill }}</v-icon>
                </v-btn>
              </template>
              <v-list density="compact">
                <v-list-item
                  v-for="category in draftHighlightCategories"
                  :key="category.id"
                  :title="category.name"
                  @click="applyHighlight(category.color)"
                >
                  <template #prepend>
                    <span class="highlight-swatch" :style="{ backgroundColor: category.color }" />
                  </template>
                </v-list-item>
                <v-list-item :title="$t('notebook.add-highlight')" :prepend-icon="$globals.icons.createAlt" @click="highlightDialog = true" />
              </v-list>
            </v-menu>
            <v-btn icon size="small" variant="text" :title="$t('notebook.insert-link')" @click="linkDialog = true">
              <v-icon>{{ $globals.icons.link }}</v-icon>
            </v-btn>
            <v-btn icon size="small" variant="text" :title="$t('notebook.insert-image')" @click="imageDialog = true">
              <v-icon>{{ $globals.icons.fileImage }}</v-icon>
            </v-btn>
            <v-btn icon size="small" variant="text" :title="$t('notebook.insert-table')" @click="insertTable">
              <v-icon>{{ $globals.icons.manageData }}</v-icon>
            </v-btn>
            <v-btn icon size="small" variant="text" :title="$t('notebook.horizontal-line')" @click="insertHorizontalRule">
              <v-icon>{{ $globals.icons.minus }}</v-icon>
            </v-btn>
            <v-btn icon size="small" variant="text" :title="$t('notebook.clear-formatting')" @click="exec('removeFormat')">
              <v-icon>{{ $globals.icons.formatClear }}</v-icon>
            </v-btn>
            <v-btn icon size="small" variant="text" :title="$t('notebook.undo')" @click="exec('undo')">
              <v-icon>{{ $globals.icons.undo }}</v-icon>
            </v-btn>
            <v-btn icon size="small" variant="text" :title="$t('notebook.redo')" @click="exec('redo')">
              <v-icon>{{ $globals.icons.redo }}</v-icon>
            </v-btn>
            <v-btn icon size="small" variant="text" :title="$t('notebook.print')" @click="printPage">
              <v-icon>{{ $globals.icons.printer }}</v-icon>
            </v-btn>
            <v-btn icon size="small" variant="text" :title="$t('notebook.export-html')" @click="exportPageHtml">
              <v-icon>{{ $globals.icons.download }}</v-icon>
            </v-btn>
            <v-spacer />
            <v-btn
              icon
              size="small"
              variant="text"
              :title="$t('notebook.page-settings')"
              @click="settingsOpen = !settingsOpen"
            >
              <v-icon>{{ $globals.icons.cog }}</v-icon>
            </v-btn>
          </div>

          <v-expand-transition>
            <section v-if="settingsOpen" class="editor-settings">
              <v-select
                v-model="pageSettings.fontFamily"
                :items="fontOptions"
                :label="$t('notebook.font')"
                density="compact"
                hide-details
                @update:model-value="settingsChanged"
              />
              <v-number-input
                v-model="pageSettings.fontSize"
                :label="$t('notebook.font-size')"
                :min="10"
                :max="72"
                density="compact"
                hide-details
                @update:model-value="settingsChanged"
              />
              <v-number-input
                v-model="pageSettings.lineHeight"
                :label="$t('notebook.line-spacing')"
                :min="1"
                :max="3"
                :step="0.1"
                density="compact"
                hide-details
                @update:model-value="settingsChanged"
              />
              <v-number-input
                v-model="pageSettings.wordSpacing"
                :label="$t('notebook.word-spacing')"
                :min="0"
                :max="20"
                density="compact"
                hide-details
                @update:model-value="settingsChanged"
              />
              <v-number-input
                v-model="pageSettings.letterSpacing"
                :label="$t('notebook.letter-spacing')"
                :min="-2"
                :max="12"
                :step="0.25"
                density="compact"
                hide-details
                @update:model-value="settingsChanged"
              />
              <v-number-input
                v-model="pageSettings.paragraphSpacing"
                :label="$t('notebook.paragraph-spacing')"
                :min="0"
                :max="80"
                density="compact"
                hide-details
                @update:model-value="settingsChanged"
              />
              <v-number-input
                v-model="pageSettings.pageWidth"
                :label="$t('notebook.page-width')"
                :min="480"
                :max="1600"
                :step="20"
                density="compact"
                hide-details
                @update:model-value="settingsChanged"
              />
              <v-number-input
                v-model="pageSettings.pagePadding"
                :label="$t('notebook.page-margins')"
                :min="12"
                :max="140"
                :step="4"
                density="compact"
                hide-details
                @update:model-value="settingsChanged"
              />
              <v-select
                v-model="pageSettings.paperStyle"
                :items="paperStyleOptions"
                :label="$t('notebook.paper-style')"
                density="compact"
                hide-details
                @update:model-value="settingsChanged"
              />
              <v-select
                v-model="pageSettings.columns"
                :items="columnOptions"
                :label="$t('notebook.columns')"
                density="compact"
                hide-details
                @update:model-value="settingsChanged"
              />
              <v-number-input
                v-model="pageSettings.zoom"
                :label="$t('notebook.zoom')"
                :min="60"
                :max="180"
                :step="5"
                density="compact"
                hide-details
                @update:model-value="settingsChanged"
              />
              <v-select
                v-model="pageSettings.textDirection"
                :items="directionOptions"
                :label="$t('notebook.direction')"
                density="compact"
                hide-details
                @update:model-value="settingsChanged"
              />
              <v-switch
                v-model="pageSettings.spellcheck"
                :label="$t('notebook.spellcheck')"
                density="compact"
                hide-details
                color="primary"
                @update:model-value="settingsChanged"
              />
              <label class="settings-color"><span>{{ $t("notebook.page-color") }}</span><input v-model="pageSettings.pageColor" type="color" @input="settingsChanged"></label>
              <label class="settings-color"><span>{{ $t("notebook.text-color") }}</span><input v-model="pageSettings.textColor" type="color" @input="settingsChanged"></label>
              <v-combobox
                v-model="draftCategories"
                :label="$t('notebook.categories')"
                multiple
                chips
                closable-chips
                density="compact"
                hide-details
                @update:model-value="scheduleSave"
              />
              <v-combobox
                v-model="draftTags"
                :label="$t('notebook.tags')"
                multiple
                chips
                closable-chips
                density="compact"
                hide-details
                @update:model-value="scheduleSave"
              />
            </section>
          </v-expand-transition>

          <div class="editor-canvas-wrap">
            <article
              ref="editor"
              class="rich-editor"
              :style="editorStyles"
              :dir="resolvedDirection"
              :spellcheck="pageSettings.spellcheck"
              contenteditable="true"
              role="textbox"
              aria-multiline="true"
              :data-placeholder="$t('notebook.page-placeholder')"
              @input="editorInput"
              @click="editorChange"
              @change="editorChange"
            />
          </div>
        </template>

        <div v-else class="editor-empty">
          <v-icon size="96" color="primary">
            {{ $globals.icons.notebook }}
          </v-icon>
          <h2>{{ activeNotebook?.title || $t("notebook.notebooks") }}</h2>
          <p>{{ activeNotebook?.description || $t("notebook.no-notebooks") }}</p>
          <v-btn
            v-if="activeNotebook"
            color="primary"
            :prepend-icon="$globals.icons.createAlt"
            @click="openNodeDialog('page')"
          >
            {{ $t("notebook.page") }}
          </v-btn>
        </div>
      </main>
    </div>

    <BaseDialog
      v-model="notebookDialog"
      :title="editingNotebook ? $t('general.edit') : $t('notebook.new-notebook')"
      :icon="$globals.icons.notebook"
      can-submit
      :submit-disabled="!notebookForm.title.trim()"
      :loading="dialogSaving"
      @submit="saveNotebook"
    >
      <v-card-text class="pt-4">
        <v-text-field v-model="notebookForm.title" :label="$t('notebook.notebook-title')" variant="outlined" autofocus />
        <v-textarea v-model="notebookForm.description" :label="$t('notebook.description')" variant="outlined" rows="3" />
        <div class="d-flex align-center ga-4 flex-wrap">
          <label class="settings-color"><span>{{ $t("notebook.page-color") }}</span><input v-model="notebookForm.color" type="color"></label>
          <v-checkbox v-model="notebookForm.isFavorite" :label="$t('notebook.favorites')" hide-details />
          <v-checkbox v-model="notebookForm.isPinned" :label="$t('notebook.pinned')" hide-details />
        </div>
      </v-card-text>
    </BaseDialog>

    <BaseDialog
      v-model="nodeDialog"
      :title="editingNode ? $t('general.edit') : $t('notebook.new-item')"
      :icon="nodeIcon(nodeForm.nodeType)"
      can-submit
      :submit-disabled="!nodeForm.title.trim()"
      :loading="dialogSaving"
      @submit="saveNode"
    >
      <v-card-text class="pt-4">
        <v-select v-model="nodeForm.nodeType" :items="nodeTypeOptions" :label="$t('notebook.new-item')" variant="outlined" :disabled="Boolean(editingNode)" />
        <v-text-field v-model="nodeForm.title" :label="$t('notebook.item-title')" variant="outlined" autofocus />
        <v-select v-model="nodeForm.parentId" :items="parentOptions" :label="$t('notebook.parent')" variant="outlined" clearable />
        <div class="d-flex align-center ga-4 flex-wrap">
          <label class="settings-color"><span>{{ $t("notebook.page-color") }}</span><input v-model="nodeForm.color" type="color"></label>
          <v-checkbox v-model="nodeForm.isFavorite" :label="$t('notebook.favorites')" hide-details />
          <v-checkbox v-model="nodeForm.isPinned" :label="$t('notebook.pinned')" hide-details />
        </div>
      </v-card-text>
    </BaseDialog>

    <BaseDialog v-model="linkDialog" :title="$t('notebook.insert-link')" :icon="$globals.icons.link" can-submit @submit="insertLink">
      <v-card-text class="pt-4">
        <v-text-field v-model="linkForm.text" :label="$t('notebook.link-text')" variant="outlined" />
        <v-text-field v-model="linkForm.url" :label="$t('notebook.link-url')" variant="outlined" type="url" />
      </v-card-text>
    </BaseDialog>

    <BaseDialog v-model="imageDialog" :title="$t('notebook.insert-image')" :icon="$globals.icons.fileImage" can-submit @submit="insertImage">
      <v-card-text class="pt-4">
        <v-text-field v-model="imageUrl" :label="$t('notebook.image-url')" variant="outlined" type="url" />
      </v-card-text>
    </BaseDialog>

    <BaseDialog v-model="highlightDialog" :title="$t('notebook.add-highlight')" :icon="$globals.icons.formatColorFill" can-submit @submit="addHighlightCategory">
      <v-card-text class="pt-4 d-flex align-center ga-4">
        <v-text-field v-model="highlightForm.name" :label="$t('notebook.highlight-name')" variant="outlined" hide-details />
        <input v-model="highlightForm.color" type="color" class="large-color-input">
      </v-card-text>
    </BaseDialog>

    <BaseDialog v-model="revisionDialog" :title="$t('notebook.version-history')" :icon="$globals.icons.timelineText" width="720">
      <v-card-text>
        <v-list lines="two">
          <v-list-item v-for="revision in revisions" :key="revision.id">
            <v-list-item-title>{{ revision.title }}</v-list-item-title>
            <v-list-item-subtitle>{{ formatDate(revision.createdAt) }} · v{{ revision.contentVersion }}</v-list-item-subtitle>
            <template #append>
              <v-btn variant="text" color="primary" :loading="restoringRevision === revision.id" @click="restoreRevision(revision.id)">
                {{ $t("notebook.restore-version") }}
              </v-btn>
            </template>
          </v-list-item>
        </v-list>
      </v-card-text>
    </BaseDialog>

    <BaseDialog
      v-model="confirmDeleteNotebook"
      :title="$t('general.confirm')"
      :icon="$globals.icons.delete"
      color="error"
      can-confirm
      @confirm="deleteNotebook"
    >
      <v-card-text>{{ $t("notebook.delete-notebook-confirm") }}</v-card-text>
    </BaseDialog>

    <BaseDialog
      v-model="confirmDeleteNode"
      :title="$t('general.confirm')"
      :icon="$globals.icons.delete"
      color="error"
      can-confirm
      @confirm="deleteNode"
    >
      <v-card-text>{{ $t("notebook.delete-item-confirm") }}</v-card-text>
    </BaseDialog>
  </v-container>
</template>

<script setup lang="ts">
import { useUserApi } from "~/composables/api/api-client";
import { alert } from "~/composables/use-toast";
import type {
  NotebookCreate,
  NotebookDetail,
  NotebookHighlightCategory,
  NotebookNode,
  NotebookNodeCreate,
  NotebookNodeType,
  NotebookRevision,
  NotebookSearchResult,
  NotebookSummary,
} from "~/lib/api/types/notebook";

const api = useUserApi();
const i18n = useI18n();
const { $globals } = useNuxtApp();

useSeoMeta({ title: () => i18n.t("notebook.notebooks") });

const ready = ref(false);
const notebooks = ref<NotebookSummary[]>([]);
const activeNotebook = ref<NotebookDetail | null>(null);
const selectedNode = ref<NotebookNode | null>(null);
const notebookFilter = ref("");
const noteSearch = ref("");
const searchResults = ref<NotebookSearchResult[] | null>(null);
const editor = ref<HTMLElement | null>(null);
const draggedNodeId = ref<string | null>(null);

const notebookDialog = ref(false);
const nodeDialog = ref(false);
const linkDialog = ref(false);
const imageDialog = ref(false);
const highlightDialog = ref(false);
const revisionDialog = ref(false);
const confirmDeleteNotebook = ref(false);
const confirmDeleteNode = ref(false);
const settingsOpen = ref(false);
const dialogSaving = ref(false);
const editingNotebook = ref<NotebookSummary | null>(null);
const editingNode = ref<NotebookNode | null>(null);
const deletingNode = ref<NotebookNode | null>(null);
const revisions = ref<NotebookRevision[]>([]);
const restoringRevision = ref<string | null>(null);

const draftTitle = ref("");
const draftContent = ref("");
const draftCategories = ref<string[]>([]);
const draftTags = ref<string[]>([]);
const draftHighlightCategories = ref<NotebookHighlightCategory[]>([]);
const saveState = ref<"saved" | "saving" | "error">("saved");
const blockFormat = ref("p");
const inlineTextColor = ref("#222222");
let saveTimer: ReturnType<typeof setTimeout> | null = null;
let saveInFlight = false;
let savePending = false;
let loadingDraft = false;

interface PageSettings {
  fontFamily: string;
  fontSize: number;
  lineHeight: number;
  wordSpacing: number;
  letterSpacing: number;
  paragraphSpacing: number;
  pageWidth: number;
  pagePadding: number;
  paperStyle: "plain" | "ruled" | "grid" | "dots";
  columns: number;
  zoom: number;
  textDirection: "auto" | "ltr" | "rtl";
  spellcheck: boolean;
  pageColor: string;
  textColor: string;
}

const defaultPageSettings = (): PageSettings => ({
  fontFamily: "Arial",
  fontSize: 16,
  lineHeight: 1.6,
  wordSpacing: 0,
  letterSpacing: 0,
  paragraphSpacing: 12,
  pageWidth: 980,
  pagePadding: 48,
  paperStyle: "plain",
  columns: 1,
  zoom: 100,
  textDirection: "auto",
  spellcheck: true,
  pageColor: "#ffffff",
  textColor: "#222222",
});
const pageSettings = reactive<PageSettings>(defaultPageSettings());

const notebookForm = reactive<NotebookCreate>({
  title: "",
  description: "",
  color: "#ef8a1f",
  icon: "notebook",
  isFavorite: false,
  isPinned: false,
  position: 0,
  settings: {},
  createStarterPage: true,
});
const nodeForm = reactive<NotebookNodeCreate>({
  parentId: null,
  nodeType: "page",
  title: "",
  contentHtml: "",
  position: 0,
  isCollapsed: false,
  isFavorite: false,
  isPinned: false,
  color: "#ef8a1f",
  tags: [],
  categories: [],
  highlightCategories: [],
  settings: {},
});
const linkForm = reactive({ text: "", url: "" });
const imageUrl = ref("");
const highlightForm = reactive({ name: "", color: "#fff59d" });

const fontOptions = ["Arial", "Calibri", "Georgia", "Tahoma", "Times New Roman", "Verdana", "David Libre", "Noto Sans Hebrew"];
const blockOptions = [
  { title: "Paragraph", value: "p" },
  { title: "Heading 1", value: "h1" },
  { title: "Heading 2", value: "h2" },
  { title: "Heading 3", value: "h3" },
  { title: "Quote", value: "blockquote" },
  { title: "Code", value: "pre" },
];
const directionOptions = computed(() => [
  { title: i18n.t("notebook.automatic"), value: "auto" },
  { title: i18n.t("notebook.right-to-left"), value: "rtl" },
  { title: i18n.t("notebook.left-to-right"), value: "ltr" },
]);
const paperStyleOptions = computed(() => [
  { title: i18n.t("notebook.paper-plain"), value: "plain" },
  { title: i18n.t("notebook.paper-ruled"), value: "ruled" },
  { title: i18n.t("notebook.paper-grid"), value: "grid" },
  { title: i18n.t("notebook.paper-dots"), value: "dots" },
]);
const columnOptions = computed(() => [
  { title: i18n.t("notebook.one-column"), value: 1 },
  { title: i18n.t("notebook.two-columns"), value: 2 },
  { title: i18n.t("notebook.three-columns"), value: 3 },
]);
const nodeTypeOptions = computed(() => [
  { title: i18n.t("notebook.section-group"), value: "section_group" as NotebookNodeType },
  { title: i18n.t("notebook.section"), value: "section" as NotebookNodeType },
  { title: i18n.t("notebook.page"), value: "page" as NotebookNodeType },
]);

const filteredNotebooks = computed(() => {
  const query = notebookFilter.value.trim().toLocaleLowerCase();
  if (!query) return notebooks.value;
  return notebooks.value.filter(item => `${item.title} ${item.description || ""}`.toLocaleLowerCase().includes(query));
});

const nodeChildren = computed(() => {
  const result = new Map<string, NotebookNode[]>();
  for (const node of activeNotebook.value?.nodes || []) {
    const key = node.parentId || "root";
    const list = result.get(key) || [];
    list.push(node);
    result.set(key, list);
  }
  for (const list of result.values()) {
    list.sort((a, b) => Number(b.isPinned) - Number(a.isPinned) || a.position - b.position || a.title.localeCompare(b.title));
  }
  return result;
});

const visibleTree = computed(() => {
  const output: { node: NotebookNode; depth: number }[] = [];
  const visited = new Set<string>();
  const visit = (parentId: string | null, depth: number) => {
    if (depth > 20) return;
    for (const node of nodeChildren.value.get(parentId || "root") || []) {
      if (visited.has(node.id)) continue;
      visited.add(node.id);
      output.push({ node, depth });
      if (!node.isCollapsed) visit(node.id, depth + 1);
    }
  };
  visit(null, 0);
  return output;
});

const parentOptions = computed(() => {
  const type = nodeForm.nodeType;
  const allowed = type === "section_group" ? ["section_group"] : type === "section" ? ["section_group"] : ["section", "page"];
  const entries = (activeNotebook.value?.nodes || [])
    .filter(node => allowed.includes(node.nodeType) && node.id !== editingNode.value?.id)
    .map(node => ({ title: node.title, value: node.id }));
  return [{ title: i18n.t("notebook.no-parent"), value: null }, ...entries];
});

const saveStateLabel = computed(() => ({
  saved: i18n.t("notebook.saved"),
  saving: i18n.t("notebook.saving"),
  error: i18n.t("notebook.save-failed"),
})[saveState.value]);
const resolvedDirection = computed(() => pageSettings.textDirection === "auto" ? (String(i18n.locale.value).startsWith("he") ? "rtl" : "ltr") : pageSettings.textDirection);
const paperBackground = computed(() => {
  const line = "rgba(90, 110, 135, 0.16)";
  if (pageSettings.paperStyle === "ruled") {
    return `repeating-linear-gradient(to bottom, transparent 0, transparent 31px, ${line} 32px)`;
  }
  if (pageSettings.paperStyle === "grid") {
    return `linear-gradient(${line} 1px, transparent 1px), linear-gradient(90deg, ${line} 1px, transparent 1px)`;
  }
  if (pageSettings.paperStyle === "dots") {
    return "radial-gradient(circle, rgba(90, 110, 135, 0.28) 1px, transparent 1.4px)";
  }
  return "none";
});
const editorStyles = computed(() => ({
  "fontFamily": pageSettings.fontFamily,
  "fontSize": `${pageSettings.fontSize}px`,
  "lineHeight": String(pageSettings.lineHeight),
  "wordSpacing": `${pageSettings.wordSpacing}px`,
  "letterSpacing": `${pageSettings.letterSpacing}px`,
  "maxWidth": `${pageSettings.pageWidth}px`,
  "padding": `${pageSettings.pagePadding}px`,
  "zoom": `${pageSettings.zoom}%`,
  "backgroundColor": pageSettings.pageColor,
  "backgroundImage": paperBackground.value,
  "backgroundSize": pageSettings.paperStyle === "grid" || pageSettings.paperStyle === "dots" ? "32px 32px" : "auto",
  "color": pageSettings.textColor,
  "columnCount": pageSettings.columns,
  "columnGap": "42px",
  "columnRule": pageSettings.columns > 1 ? "1px solid rgba(90, 110, 135, 0.18)" : "none",
  "--paragraph-spacing": `${pageSettings.paragraphSpacing}px`,
}));

onMounted(loadNotebooks);
onBeforeUnmount(() => {
  if (saveTimer) clearTimeout(saveTimer);
  if (selectedNode.value?.nodeType === "page" && saveState.value !== "saved") void persistDraft();
});

watch(() => activeNotebook.value?.id, () => {
  searchResults.value = null;
  noteSearch.value = "";
});

async function loadNotebooks(selectId?: string) {
  const { data, error } = await api.notebooks.getAll();
  ready.value = true;
  if (error || !data) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }
  notebooks.value = data;
  const target = selectId || activeNotebook.value?.id || data[0]?.id;
  if (target) await selectNotebook(target);
}

async function selectNotebook(id: string) {
  await flushSave();
  const { data, error } = await api.notebooks.getOne(id);
  if (error || !data) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }
  activeNotebook.value = data;
  const preferred = data.nodes.find(node => node.id === selectedNode.value?.id && node.nodeType === "page")
    || data.nodes.find(node => node.nodeType === "page" && node.isPinned)
    || data.nodes.find(node => node.nodeType === "page");
  if (preferred) selectNode(preferred);
  else selectedNode.value = null;
}

function selectNode(node: NotebookNode) {
  if (node.nodeType !== "page") {
    void toggleNode(node);
    return;
  }
  void (async () => {
    await flushSave();
    selectedNode.value = node;
    loadDraft(node);
  })();
}

function loadDraft(node: NotebookNode) {
  loadingDraft = true;
  draftTitle.value = node.title;
  draftContent.value = node.contentHtml || "";
  draftCategories.value = [...(node.categories || [])];
  draftTags.value = [...(node.tags || [])];
  draftHighlightCategories.value = node.highlightCategories?.length
    ? node.highlightCategories.map(item => ({ ...item }))
    : [
        { id: "important", name: "Important", color: "#fff59d" },
        { id: "question", name: "Question", color: "#90caf9" },
        { id: "idea", name: "Idea", color: "#a5d6a7" },
      ];
  Object.assign(pageSettings, defaultPageSettings(), node.settings || {});
  saveState.value = "saved";
  nextTick(() => {
    if (editor.value) editor.value.innerHTML = draftContent.value;
    loadingDraft = false;
  });
}

function editorInput() {
  if (!editor.value) return;
  draftContent.value = editor.value.innerHTML;
  scheduleSave();
}

function editorChange(event: Event) {
  const target = event.target as HTMLInputElement;
  if (target?.type === "checkbox") {
    nextTick(() => {
      if (target.checked) target.setAttribute("checked", "checked");
      else target.removeAttribute("checked");
      editorInput();
    });
  }
}

function scheduleSave() {
  if (loadingDraft || !selectedNode.value || selectedNode.value.nodeType !== "page") return;
  saveState.value = "saving";
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => void persistDraft(), 850);
}

async function flushSave() {
  if (saveTimer) {
    clearTimeout(saveTimer);
    saveTimer = null;
  }
  if (selectedNode.value?.nodeType === "page" && saveState.value !== "saved") await persistDraft();
}

async function persistDraft() {
  const node = selectedNode.value;
  const notebook = activeNotebook.value;
  if (!node || !notebook || node.nodeType !== "page") return;
  if (saveInFlight) {
    savePending = true;
    return;
  }
  saveInFlight = true;
  savePending = false;
  saveState.value = "saving";
  const expectedVersion = node.contentVersion;
  const payload = {
    title: draftTitle.value.trim() || i18n.t("notebook.starter-page"),
    contentHtml: draftContent.value,
    tags: draftTags.value,
    categories: draftCategories.value,
    highlightCategories: draftHighlightCategories.value,
    settings: { ...pageSettings },
    expectedVersion,
  };
  const result = await api.notebooks.updateNode(notebook.id, node.id, payload);
  saveInFlight = false;
  if (result.error || !result.data) {
    const status = result.error?.response?.status;
    saveState.value = "error";
    if (status === 409) {
      alert.warning(i18n.t("notebook.conflict"));
      await selectNotebook(notebook.id);
    }
    else {
      alert.error(i18n.t("notebook.save-failed"));
    }
  }
  else {
    selectedNode.value = result.data;
    const index = notebook.nodes.findIndex(item => item.id === result.data?.id);
    if (index >= 0) notebook.nodes[index] = result.data;
    saveState.value = "saved";
  }
  if (savePending) {
    savePending = false;
    await persistDraft();
  }
}

function exec(command: string, value?: string) {
  editor.value?.focus();
  document.execCommand(command, false, value);
  editorInput();
}

function applyBlock(value: string) {
  exec("formatBlock", value);
}

function applyHighlight(color: string) {
  exec("hiliteColor", color);
}

function insertChecklist() {
  exec("insertHTML", "<ul class=\"notebook-checklist\"><li><label><input type=\"checkbox\"> <span>Task</span></label></li></ul><p><br></p>");
}

function insertTable() {
  exec("insertHTML", "<table><tbody><tr><th>Heading</th><th>Heading</th></tr><tr><td>Cell</td><td>Cell</td></tr></tbody></table><p><br></p>");
}

function insertHorizontalRule() {
  exec("insertHTML", "<hr><p><br></p>");
}

function printableDocument() {
  const title = escapeHtml(draftTitle.value.trim() || i18n.t("notebook.starter-page"));
  const direction = resolvedDirection.value;
  const content = editor.value?.innerHTML || draftContent.value;
  return `<!doctype html><html lang="${escapeAttribute(String(i18n.locale.value))}" dir="${direction}"><head><meta charset="utf-8"><title>${title}</title><style>body{max-width:${pageSettings.pageWidth}px;margin:0 auto;padding:${pageSettings.pagePadding}px;font-family:${JSON.stringify(pageSettings.fontFamily)};font-size:${pageSettings.fontSize}px;line-height:${pageSettings.lineHeight};word-spacing:${pageSettings.wordSpacing}px;letter-spacing:${pageSettings.letterSpacing}px;color:${pageSettings.textColor};background:${pageSettings.pageColor}}h1{margin-top:0}p{margin-bottom:${pageSettings.paragraphSpacing}px}img{max-width:100%;height:auto}table{width:100%;border-collapse:collapse}th,td{padding:7px;border:1px solid #aaa}@media print{body{max-width:none}}</style></head><body><h1>${title}</h1>${content}</body></html>`;
}

function printPage() {
  const printWindow = window.open("", "_blank");
  if (!printWindow) return;
  printWindow.opener = null;
  printWindow.document.open();
  printWindow.document.write(printableDocument());
  printWindow.document.close();
  printWindow.addEventListener("load", () => {
    printWindow.focus();
    printWindow.print();
  }, { once: true });
}

function exportPageHtml() {
  const blob = new Blob([printableDocument()], { type: "text/html;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${(draftTitle.value.trim() || "notebook-page").replace(/[\\/:*?"<>|]+/g, "-")}.html`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function insertLink() {
  const url = linkForm.url.trim();
  if (!/^https?:\/\//i.test(url)) return;
  const text = escapeHtml(linkForm.text.trim() || url);
  exec("insertHTML", `<a href="${escapeAttribute(url)}" target="_blank" rel="noopener noreferrer">${text}</a>`);
  linkDialog.value = false;
  linkForm.text = "";
  linkForm.url = "";
}

function insertImage() {
  const url = imageUrl.value.trim();
  if (!/^https?:\/\//i.test(url)) return;
  exec("insertHTML", `<img src="${escapeAttribute(url)}" alt="" loading="lazy"><p><br></p>`);
  imageDialog.value = false;
  imageUrl.value = "";
}

function escapeHtml(value: string) {
  const element = document.createElement("div");
  element.textContent = value;
  return element.innerHTML;
}

function escapeAttribute(value: string) {
  return escapeHtml(value).replaceAll("`", "&#96;");
}

function addHighlightCategory() {
  const name = highlightForm.name.trim();
  if (!name) return;
  draftHighlightCategories.value.push({
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    name,
    color: highlightForm.color,
  });
  highlightDialog.value = false;
  highlightForm.name = "";
  highlightForm.color = "#fff59d";
  scheduleSave();
}

function settingsChanged() {
  scheduleSave();
}

function resetNotebookForm() {
  Object.assign(notebookForm, {
    title: "",
    description: "",
    color: "#ef8a1f",
    icon: "notebook",
    isFavorite: false,
    isPinned: false,
    position: notebooks.value.length,
    settings: {},
    createStarterPage: true,
  });
}

function openNotebookDialog(notebook?: NotebookSummary) {
  resetNotebookForm();
  editingNotebook.value = notebook || null;
  if (notebook) Object.assign(notebookForm, { ...notebook, createStarterPage: false });
  notebookDialog.value = true;
}

async function saveNotebook() {
  dialogSaving.value = true;
  const payload = { ...notebookForm };
  const result = editingNotebook.value
    ? await api.notebooks.updateOne(editingNotebook.value.id, payload)
    : await api.notebooks.createOne(payload);
  dialogSaving.value = false;
  if (result.error || !result.data) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }
  notebookDialog.value = false;
  await loadNotebooks(result.data.id);
}

function defaultNodeTitle(type: NotebookNodeType) {
  return type === "section_group" ? i18n.t("notebook.section-group") : type === "section" ? i18n.t("notebook.section") : i18n.t("notebook.starter-page");
}

function resetNodeForm(type: NotebookNodeType, parentId: string | null = null) {
  Object.assign(nodeForm, {
    parentId,
    nodeType: type,
    title: defaultNodeTitle(type),
    contentHtml: "",
    position: activeNotebook.value?.nodes.length || 0,
    isCollapsed: false,
    isFavorite: false,
    isPinned: false,
    color: activeNotebook.value?.color || "#ef8a1f",
    tags: [],
    categories: [],
    highlightCategories: [],
    settings: type === "page" ? defaultPageSettings() : {},
  });
}

function openNodeDialog(type: NotebookNodeType, node?: NotebookNode, parentId: string | null = null) {
  resetNodeForm(type, parentId);
  editingNode.value = node || null;
  if (node) {
    Object.assign(nodeForm, {
      parentId: node.parentId || null,
      nodeType: node.nodeType,
      title: node.title,
      contentHtml: node.contentHtml,
      position: node.position,
      isCollapsed: node.isCollapsed,
      isFavorite: node.isFavorite,
      isPinned: node.isPinned,
      color: node.color || "#ef8a1f",
      tags: [...node.tags],
      categories: [...node.categories],
      highlightCategories: node.highlightCategories.map(item => ({ ...item })),
      settings: { ...node.settings },
    });
  }
  nodeDialog.value = true;
}

function openChildDialog(parent: NotebookNode) {
  const type: NotebookNodeType = parent.nodeType === "section_group" ? "section" : "page";
  openNodeDialog(type, undefined, parent.id);
}

async function saveNode() {
  const notebook = activeNotebook.value;
  if (!notebook) return;
  dialogSaving.value = true;
  const result = editingNode.value
    ? await api.notebooks.updateNode(notebook.id, editingNode.value.id, nodeForm)
    : await api.notebooks.createNode(notebook.id, nodeForm);
  dialogSaving.value = false;
  if (result.error || !result.data) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }
  nodeDialog.value = false;
  await selectNotebook(notebook.id);
  if (result.data.nodeType === "page") selectNode(result.data);
}

async function toggleNode(node: NotebookNode) {
  const notebook = activeNotebook.value;
  if (!notebook) return;
  const result = await api.notebooks.updateNode(notebook.id, node.id, { isCollapsed: !node.isCollapsed });
  if (result.data) Object.assign(node, result.data);
}

async function toggleFavorite(node: NotebookNode) {
  const notebook = activeNotebook.value;
  if (!notebook) return;
  const result = await api.notebooks.updateNode(notebook.id, node.id, { isFavorite: !node.isFavorite });
  if (result.data) {
    Object.assign(node, result.data);
    if (selectedNode.value?.id === node.id) selectedNode.value = result.data;
  }
}

function hasChildren(id: string) {
  return Boolean(nodeChildren.value.get(id)?.length);
}

function nodeIcon(type: NotebookNodeType) {
  return type === "section_group" ? $globals.icons.folderOutline : type === "section" ? $globals.icons.pages : $globals.icons.file;
}

function startNodeDrag(id: string) {
  draggedNodeId.value = id;
}

async function dropOnRoot() {
  const id = draggedNodeId.value;
  const notebook = activeNotebook.value;
  draggedNodeId.value = null;
  if (!id || !notebook) return;
  const node = notebook.nodes.find(item => item.id === id);
  if (!node || (node.nodeType !== "section_group" && node.nodeType !== "section")) return;
  const result = await api.notebooks.moveNode(notebook.id, id, null, notebook.nodes.length);
  if (result.error) alert.error(i18n.t("events.something-went-wrong"));
  else await selectNotebook(notebook.id);
}

async function dropOnNode(target: NotebookNode) {
  const id = draggedNodeId.value;
  const notebook = activeNotebook.value;
  draggedNodeId.value = null;
  if (!id || id === target.id || !notebook) return;
  const result = await api.notebooks.moveNode(notebook.id, id, target.id, (nodeChildren.value.get(target.id)?.length || 0));
  if (result.error) alert.error(i18n.t("events.something-went-wrong"));
  else await selectNotebook(notebook.id);
}

function openDeleteNode(node: NotebookNode) {
  deletingNode.value = node;
  confirmDeleteNode.value = true;
}

async function deleteNode() {
  const notebook = activeNotebook.value;
  if (!notebook || !deletingNode.value) return;
  const result = await api.notebooks.deleteNode(notebook.id, deletingNode.value.id);
  confirmDeleteNode.value = false;
  if (result.error) alert.error(i18n.t("events.something-went-wrong"));
  else {
    if (selectedNode.value?.id === deletingNode.value.id) selectedNode.value = null;
    deletingNode.value = null;
    await selectNotebook(notebook.id);
  }
}

async function deleteNotebook() {
  if (!activeNotebook.value) return;
  const result = await api.notebooks.deleteOne(activeNotebook.value.id);
  confirmDeleteNotebook.value = false;
  if (result.error) alert.error(i18n.t("events.something-went-wrong"));
  else {
    activeNotebook.value = null;
    selectedNode.value = null;
    await loadNotebooks();
  }
}

async function searchNotes() {
  const query = noteSearch.value.trim();
  if (!query) {
    searchResults.value = null;
    return;
  }
  const { data, error } = await api.notebooks.search(query);
  if (error || !data) alert.error(i18n.t("events.something-went-wrong"));
  else searchResults.value = data;
}

function clearSearchResults() {
  searchResults.value = null;
  noteSearch.value = "";
}

async function openSearchResult(result: NotebookSearchResult) {
  if (activeNotebook.value?.id !== result.notebookId) await selectNotebook(result.notebookId);
  const node = activeNotebook.value?.nodes.find(item => item.id === result.nodeId);
  if (node) selectNode(node);
  clearSearchResults();
}

async function openRevisionHistory() {
  if (!activeNotebook.value || !selectedNode.value) return;
  const { data, error } = await api.notebooks.revisions(activeNotebook.value.id, selectedNode.value.id);
  if (error || !data) {
    alert.error(i18n.t("events.something-went-wrong"));
    return;
  }
  revisions.value = data;
  revisionDialog.value = true;
}

async function restoreRevision(revisionId: string) {
  if (!activeNotebook.value || !selectedNode.value) return;
  restoringRevision.value = revisionId;
  const { data, error } = await api.notebooks.restoreRevision(activeNotebook.value.id, selectedNode.value.id, revisionId);
  restoringRevision.value = null;
  if (error || !data) alert.error(i18n.t("events.something-went-wrong"));
  else {
    selectedNode.value = data;
    const index = activeNotebook.value.nodes.findIndex(item => item.id === data.id);
    if (index >= 0) activeNotebook.value.nodes[index] = data;
    loadDraft(data);
    revisionDialog.value = false;
  }
}

function formatDate(value?: string | null) {
  return value ? new Intl.DateTimeFormat(i18n.locale.value, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "";
}
</script>

<style scoped>
.notebook-page {
  height: calc(100vh - 64px);
  overflow: hidden;
}

.notebook-shell {
  display: grid;
  grid-template-columns: 230px 300px minmax(0, 1fr);
  height: 100%;
  background: rgb(var(--v-theme-background));
}

.notebook-panel {
  display: flex;
  min-width: 0;
  flex-direction: column;
  border-inline-end: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  background: rgb(var(--v-theme-surface));
}

.panel-heading {
  display: flex;
  min-height: 54px;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.panel-title {
  overflow: hidden;
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.panel-search {
  margin: 10px;
}
.panel-scroll {
  min-height: 0;
  flex: 1;
  overflow: auto;
  padding: 0 8px 8px;
}
.panel-footer {
  display: flex;
  justify-content: flex-end;
  padding: 6px;
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.notebook-row {
  display: flex;
  width: 100%;
  min-height: 54px;
  align-items: center;
  gap: 9px;
  padding: 7px 9px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: start;
}
.notebook-row:hover {
  background: rgba(var(--v-theme-primary), 0.08);
}
.notebook-row--active {
  background: rgba(var(--v-theme-primary), 0.13);
}
.notebook-color {
  width: 5px;
  height: 34px;
  flex: 0 0 5px;
  border-radius: 2px;
}
.notebook-row__content {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
}
.notebook-row__content strong,
.notebook-row__content small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.notebook-row__content small {
  opacity: 0.65;
}

.outline-scroll {
  padding-inline: 4px;
}
.outline-row {
  display: flex;
  min-height: 36px;
  align-items: center;
  border-radius: 3px;
}
.outline-row:hover {
  background: rgba(var(--v-theme-on-surface), 0.05);
}
.outline-row--active {
  background: rgba(var(--v-theme-primary), 0.12);
  color: rgb(var(--v-theme-primary));
}
.outline-select {
  display: flex;
  min-width: 0;
  flex: 1;
  align-items: center;
  gap: 7px;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: start;
}
.outline-select span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.outline-spacer {
  width: 28px;
  flex: 0 0 28px;
}
.search-result-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 8px 8px;
  font-weight: 700;
}
.search-result {
  display: flex;
  width: 100%;
  flex-direction: column;
  gap: 2px;
  padding: 9px;
  border: 0;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: start;
}
.search-result:hover {
  background: rgba(var(--v-theme-primary), 0.08);
}
.search-result small {
  color: rgb(var(--v-theme-primary));
}
.search-result span {
  overflow: hidden;
  opacity: 0.7;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.empty-note {
  padding: 18px;
  opacity: 0.65;
  text-align: center;
}

.notebook-editor-area {
  min-width: 0;
  overflow: auto;
  background: rgba(var(--v-theme-on-surface), 0.025);
}
.editor-topline {
  position: sticky;
  z-index: 4;
  top: 0;
  display: flex;
  min-height: 54px;
  align-items: center;
  gap: 8px;
  padding: 5px 14px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  background: rgb(var(--v-theme-surface));
}
.page-title-input {
  min-width: 120px;
  flex: 1;
  font-size: 1.15rem;
  font-weight: 700;
}
.save-status {
  flex: 0 0 auto;
  color: rgb(var(--v-theme-success));
  font-size: 0.75rem;
}
.save-status--error {
  color: rgb(var(--v-theme-error));
}
.editor-toolbar {
  position: sticky;
  z-index: 3;
  top: 54px;
  display: flex;
  min-height: 46px;
  align-items: center;
  gap: 1px;
  padding: 4px 10px;
  overflow-x: auto;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  background: rgb(var(--v-theme-surface));
}
.toolbar-select {
  width: 125px;
  flex: 0 0 125px;
}
.color-control {
  position: relative;
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  cursor: pointer;
}
.color-control input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
}
.highlight-swatch {
  width: 18px;
  height: 18px;
  border: 1px solid rgba(0, 0, 0, 0.2);
  border-radius: 2px;
}
.editor-settings {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 10px;
  padding: 12px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  background: rgb(var(--v-theme-surface));
}
.settings-color {
  display: flex;
  min-height: 40px;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 5px 9px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
}
.settings-color input,
.large-color-input {
  width: 42px;
  height: 30px;
  border: 0;
  background: transparent;
}
.large-color-input {
  width: 64px;
  height: 48px;
}
.editor-canvas-wrap {
  min-height: calc(100% - 100px);
  padding: 22px;
}
.rich-editor {
  min-height: calc(100vh - 190px);
  margin: 0 auto;
  padding: 42px 48px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
  box-shadow: 0 2px 9px rgba(0, 0, 0, 0.08);
  outline: none;
  transform-origin: top center;
}
.rich-editor:empty::before {
  color: rgba(var(--v-theme-on-surface), 0.42);
  content: attr(data-placeholder);
  pointer-events: none;
}
.rich-editor :deep(p) {
  margin-bottom: var(--paragraph-spacing);
}
.rich-editor :deep(img) {
  max-width: 100%;
  height: auto;
}
.rich-editor :deep(table) {
  width: 100%;
  border-collapse: collapse;
}
.rich-editor :deep(th),
.rich-editor :deep(td) {
  padding: 7px;
  border: 1px solid rgba(var(--v-border-color), 0.45);
}
.rich-editor :deep(.notebook-checklist) {
  padding-inline-start: 0;
  list-style: none;
}
.editor-empty {
  display: flex;
  height: 100%;
  min-height: 420px;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 10px;
  padding: 28px;
  text-align: center;
}
.editor-empty h2,
.editor-empty p {
  margin: 0;
}

@media (max-width: 1050px) {
  .notebook-shell {
    grid-template-columns: 190px 250px minmax(0, 1fr);
  }
  .rich-editor {
    padding: 30px 28px;
  }
}

@media (max-width: 760px) {
  .notebook-page {
    height: auto;
    min-height: calc(100vh - 56px);
    overflow: visible;
  }
  .notebook-shell {
    display: flex;
    min-height: calc(100vh - 56px);
    flex-direction: column;
  }
  .notebook-panel {
    max-height: 240px;
    border-inline-end: 0;
    border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  }
  .notebook-panel--books {
    max-height: 190px;
  }
  .notebook-editor-area {
    min-height: 560px;
    overflow: visible;
  }
  .editor-topline,
  .editor-toolbar {
    position: static;
  }
  .editor-canvas-wrap {
    padding: 8px;
  }
  .rich-editor {
    min-height: 520px;
    padding: 24px 18px;
  }
}
</style>
