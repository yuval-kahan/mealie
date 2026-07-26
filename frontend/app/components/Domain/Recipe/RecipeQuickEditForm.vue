<template>
  <div class="recipe-quick-edit-form">
    <section class="recipe-quick-edit-section">
      <div class="recipe-quick-edit-heading">
        <v-icon color="primary">
          {{ $globals.icons.formatListCheck }}
        </v-icon>
        <span>{{ $t("recipe.mise-en-place") }}</span>
      </div>
      <div class="recipe-quick-edit-columns">
        <v-textarea
          v-model="miseEnPlaceFood"
          :label="$t('recipe.mise-en-place-food')"
          :hint="$t('recipe.mise-en-place-food-description')"
          persistent-hint
          rows="3"
          auto-grow
        />
        <v-textarea
          v-model="miseEnPlaceTools"
          :label="$t('recipe.mise-en-place-tools')"
          :hint="$t('recipe.mise-en-place-tools-description')"
          persistent-hint
          rows="3"
          auto-grow
        />
      </div>
    </section>

    <section class="recipe-quick-edit-section">
      <div class="recipe-quick-edit-heading">
        <v-icon color="primary">
          {{ $globals.icons.edit }}
        </v-icon>
        <span>{{ $t("recipe.recipe-name") }}</span>
      </div>
      <v-text-field
        v-model="recipe.name"
        :label="$t('recipe.recipe-name')"
        :rules="[value => Boolean(String(value || '').trim()) || $t('recipe.recipe-name-required')]"
        autofocus
      />
    </section>

    <div class="recipe-quick-edit-columns">
      <section class="recipe-quick-edit-section">
        <div class="recipe-quick-edit-heading">
          <v-icon color="primary">
            {{ $globals.icons.foods }}
          </v-icon>
          <span>{{ $t("recipe.ingredients") }}</span>
          <v-spacer />
          <v-btn
            icon
            size="small"
            variant="text"
            color="success"
            :title="$t('general.add')"
            :aria-label="$t('general.add')"
            @click="addIngredient"
          >
            <v-icon>{{ $globals.icons.createAlt }}</v-icon>
          </v-btn>
        </div>
        <div class="recipe-quick-edit-list">
          <div
            v-for="(ingredient, index) in ingredients"
            :key="ingredient.referenceId || index"
            class="recipe-quick-edit-row"
          >
            <v-text-field
              :model-value="ingredientText(ingredient)"
              :label="$t('recipe.ingredient')"
              density="compact"
              hide-details
              @update:model-value="updateIngredient(index, String($event || ''))"
            />
            <v-btn
              icon
              size="x-small"
              variant="text"
              color="error"
              :title="$t('general.delete')"
              :aria-label="$t('general.delete')"
              @click="removeIngredient(index)"
            >
              <v-icon>{{ $globals.icons.delete }}</v-icon>
            </v-btn>
          </div>
          <v-alert v-if="!ingredients.length" type="info" variant="tonal" density="compact">
            {{ $t("recipe.no-ingredients") }}
          </v-alert>
        </div>
      </section>

      <section class="recipe-quick-edit-section">
        <div class="recipe-quick-edit-heading">
          <v-icon color="primary">
            {{ $globals.icons.formatListCheck }}
          </v-icon>
          <span>{{ $t("recipe.instructions") }}</span>
          <v-spacer />
          <v-btn
            icon
            size="small"
            variant="text"
            color="success"
            :title="$t('general.add')"
            :aria-label="$t('general.add')"
            @click="addInstruction"
          >
            <v-icon>{{ $globals.icons.createAlt }}</v-icon>
          </v-btn>
        </div>
        <div class="recipe-quick-edit-list">
          <div
            v-for="(instruction, index) in instructions"
            :key="instruction.id || index"
            class="recipe-quick-edit-instruction"
          >
            <div class="recipe-quick-edit-step-number">
              {{ index + 1 }}
            </div>
            <div class="min-width-0 flex-grow-1">
              <v-text-field
                v-model="instruction.title"
                :label="$t('recipe.section-title')"
                density="compact"
                hide-details
                class="mb-2"
              />
              <v-textarea
                v-model="instruction.text"
                :label="$t('recipe.instructions')"
                rows="2"
                auto-grow
                hide-details
              />
            </div>
            <v-btn
              icon
              size="x-small"
              variant="text"
              color="error"
              :title="$t('general.delete')"
              :aria-label="$t('general.delete')"
              @click="removeInstruction(index)"
            >
              <v-icon>{{ $globals.icons.delete }}</v-icon>
            </v-btn>
          </div>
          <v-alert v-if="!instructions.length" type="info" variant="tonal" density="compact">
            {{ $t("recipe.no-instructions") }}
          </v-alert>
        </div>
      </section>
    </div>

    <section class="recipe-quick-edit-section">
      <div class="recipe-quick-edit-heading">
        <v-icon color="primary">
          {{ $globals.icons.messageText }}
        </v-icon>
        <span>{{ $t("recipe.notes") }}</span>
        <v-spacer />
        <v-btn
          icon
          size="small"
          variant="text"
          color="success"
          :title="$t('general.add')"
          :aria-label="$t('general.add')"
          @click="addNote"
        >
          <v-icon>{{ $globals.icons.createAlt }}</v-icon>
        </v-btn>
      </div>
      <div class="recipe-quick-edit-notes">
        <div v-for="(note, index) in notes" :key="index" class="recipe-quick-edit-note">
          <div class="min-width-0 flex-grow-1">
            <v-text-field
              v-model="note.title"
              :label="$t('general.title')"
              density="compact"
              hide-details
              class="mb-2"
            />
            <v-textarea
              v-model="note.text"
              :label="$t('recipe.notes')"
              rows="2"
              auto-grow
              hide-details
            />
          </div>
          <v-btn
            icon
            size="x-small"
            variant="text"
            color="error"
            :title="$t('general.delete')"
            :aria-label="$t('general.delete')"
            @click="removeNote(index)"
          >
            <v-icon>{{ $globals.icons.delete }}</v-icon>
          </v-btn>
        </div>
        <v-alert v-if="!notes.length" type="info" variant="tonal" density="compact">
          {{ $t("recipe.no-notes") }}
        </v-alert>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { Recipe, RecipeIngredient } from "~/lib/api/types/recipe";
import { useIngredientTextParser } from "~/composables/recipes/use-recipe-ingredients";
import { uuid4 } from "~/composables/use-utils";

const recipe = defineModel<Recipe>({ required: true });
const { ingredientToParserString } = useIngredientTextParser();

const ingredients = computed(() => recipe.value.recipeIngredient || []);
const instructions = computed(() => recipe.value.recipeInstructions || []);
const notes = computed(() => recipe.value.notes || []);
const miseEnPlaceFood = computed({
  get: () => String(recipe.value.extras?.miseEnPlaceFood || recipe.value.extras?.miseEnPlace || ""),
  set: (value: string) => {
    recipe.value.extras = {
      ...(recipe.value.extras || {}),
      miseEnPlaceFood: value,
      miseEnPlace: "",
    };
  },
});
const miseEnPlaceTools = computed({
  get: () => String(recipe.value.extras?.miseEnPlaceTools || ""),
  set: (value: string) => {
    recipe.value.extras = {
      ...(recipe.value.extras || {}),
      miseEnPlaceTools: value,
    };
  },
});

function ingredientText(ingredient: RecipeIngredient) {
  return ingredientToParserString(ingredient);
}

function updateIngredient(index: number, text: string) {
  const existing = ingredients.value[index];
  if (!existing) return;
  const nextIngredients = [...ingredients.value];
  nextIngredients[index] = {
    ...existing,
    quantity: null,
    unit: null,
    food: null,
    referencedRecipe: null,
    note: text,
    display: text,
    originalText: text,
    referenceId: existing.referenceId || uuid4(),
  };
  recipe.value.recipeIngredient = nextIngredients;
}

function addIngredient() {
  recipe.value.recipeIngredient = [
    ...ingredients.value,
    {
      quantity: null,
      unit: null,
      food: null,
      referencedRecipe: null,
      note: "",
      display: "",
      originalText: "",
      referenceId: uuid4(),
    },
  ];
}

function removeIngredient(index: number) {
  recipe.value.recipeIngredient = ingredients.value.filter((_, itemIndex) => itemIndex !== index);
}

function addInstruction() {
  recipe.value.recipeInstructions = [
    ...instructions.value,
    { id: uuid4(), title: "", summary: "", text: "", ingredientReferences: [] },
  ];
}

function removeInstruction(index: number) {
  recipe.value.recipeInstructions = instructions.value.filter((_, itemIndex) => itemIndex !== index);
}

function addNote() {
  recipe.value.notes = [...notes.value, { title: "", text: "" }];
}

function removeNote(index: number) {
  recipe.value.notes = notes.value.filter((_, itemIndex) => itemIndex !== index);
}
</script>

<style scoped>
.recipe-quick-edit-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.recipe-quick-edit-columns {
  display: grid;
  gap: 20px;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
}

.recipe-quick-edit-section {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  padding-top: 12px;
}

.recipe-quick-edit-heading {
  align-items: center;
  display: flex;
  font-size: 1.05rem;
  font-weight: 700;
  gap: 8px;
  margin-bottom: 12px;
  min-height: 40px;
}

.recipe-quick-edit-list,
.recipe-quick-edit-notes {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.recipe-quick-edit-row,
.recipe-quick-edit-instruction,
.recipe-quick-edit-note {
  align-items: flex-start;
  display: flex;
  gap: 8px;
  min-width: 0;
}

.recipe-quick-edit-step-number {
  align-items: center;
  background: rgba(var(--v-theme-primary), 0.1);
  border-radius: 4px;
  color: rgb(var(--v-theme-primary));
  display: flex;
  flex: 0 0 32px;
  font-weight: 700;
  height: 32px;
  justify-content: center;
}

@media (max-width: 959px) {
  .recipe-quick-edit-columns {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
