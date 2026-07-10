<template>
  <section class="recipe-manual-content my-4">
    <div v-if="edit && showModeSelector" class="recipe-manual-content__mode mb-4">
      <div class="text-subtitle-1 font-weight-medium mb-2">
        {{ $t("recipe.manual-content-mode") }}
      </div>
      <v-btn-toggle
        v-model="contentMode"
        mandatory
        divided
        color="primary"
        density="comfortable"
      >
        <v-btn value="structured" :prepend-icon="$globals.icons.formatListCheck">
          {{ $t("recipe.manual-content-structured") }}
        </v-btn>
        <v-btn value="plain" :prepend-icon="$globals.icons.textBoxCheckOutline">
          {{ $t("recipe.manual-content-plain") }}
        </v-btn>
        <v-btn value="rich" :prepend-icon="$globals.icons.messageText">
          {{ $t("recipe.manual-content-rich") }}
        </v-btn>
      </v-btn-toggle>
      <div class="text-caption text-medium-emphasis mt-2">
        {{ $t("recipe.manual-content-mode-description") }}
      </div>
    </div>

    <template v-if="contentMode !== 'structured'">
      <v-textarea
        v-if="edit"
        v-model="manualText"
        :label="$t('recipe.manual-content')"
        :hint="contentMode === 'rich' ? $t('recipe.manual-content-rich-description') : $t('recipe.manual-content-plain-description')"
        persistent-hint
        variant="outlined"
        rows="16"
        auto-grow
        clearable
        class="recipe-manual-content__editor"
      />
      <SafeMarkdown
        v-else-if="contentMode === 'rich'"
        :source="manualText"
        class="recipe-manual-content__rich"
      />
      <pre v-else class="recipe-manual-content__plain">{{ manualText }}</pre>
    </template>
  </section>
</template>

<script setup lang="ts">
import type { NoUndefinedField } from "~/lib/api/types/non-generated";
import type { Recipe } from "~/lib/api/types/recipe";

type ManualContentMode = "structured" | "plain" | "rich";

withDefaults(defineProps<{
  edit?: boolean;
  showModeSelector?: boolean;
}>(), {
  edit: false,
  showModeSelector: false,
});

const recipe = defineModel<NoUndefinedField<Recipe>>({ required: true });

const contentMode = computed<ManualContentMode>({
  get: () => {
    const value = recipe.value.extras?.manualContentMode;
    return value === "plain" || value === "rich" ? value : "structured";
  },
  set: (value) => {
    recipe.value.extras = {
      ...(recipe.value.extras || {}),
      manualCreation: true,
      manualContentMode: value,
    };
  },
});

const manualText = computed({
  get: () => String(recipe.value.extras?.manualContent || ""),
  set: (value: string) => {
    recipe.value.extras = {
      ...(recipe.value.extras || {}),
      manualCreation: true,
      manualContentMode: contentMode.value,
      manualContent: value,
    };
  },
});
</script>

<style scoped>
.recipe-manual-content__mode {
  border-block: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  padding-block: 16px;
}

.recipe-manual-content__plain {
  margin: 0;
  padding: 20px 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font: inherit;
  line-height: 1.75;
}

.recipe-manual-content__rich {
  line-height: 1.75;
}

@media (max-width: 600px) {
  .recipe-manual-content :deep(.v-btn-toggle) {
    width: 100%;
    flex-direction: column;
    height: auto;
  }

  .recipe-manual-content :deep(.v-btn-toggle .v-btn) {
    width: 100%;
  }
}
</style>
