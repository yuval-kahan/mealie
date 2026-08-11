<template>
  <section v-if="instructionImages.length" class="recipe-instruction-images mt-8 d-print-none">
    <div class="d-flex align-center ga-2 mb-3">
      <v-icon color="primary">
        {{ $globals.icons.fileImage }}
      </v-icon>
      <h2 class="text-h5 font-weight-medium opacity-80">
        {{ $t("recipe.instruction-images") }}
      </h2>
    </div>

    <div class="instruction-image-list">
      <figure
        v-for="(item, index) in instructionImages"
        :key="item.asset.fileName"
        class="instruction-image-figure"
      >
        <v-img
          :src="item.url"
          :alt="item.label"
          aspect-ratio="4/3"
          cover
          class="instruction-image"
          @click="openGallery(index)"
        />
        <figcaption class="text-body-2 mt-2 opacity-80">
          {{ item.label }}
        </figcaption>
      </figure>
    </div>

    <v-dialog v-model="galleryOpen" width="min(1100px, 96vw)">
      <v-card v-if="selectedImage" class="gallery-dialog" color="black">
        <v-btn
          icon
          variant="flat"
          class="gallery-close"
          :aria-label="$t('general.close')"
          @click="galleryOpen = false"
        >
          <v-icon>{{ $globals.icons.close }}</v-icon>
        </v-btn>
        <v-btn
          v-if="instructionImages.length > 1"
          icon
          variant="flat"
          class="gallery-previous"
          :aria-label="$t('general.previous')"
          @click="showPrevious"
        >
          <v-icon>{{ $globals.icons.chevronLeft }}</v-icon>
        </v-btn>
        <v-img
          :src="selectedImage.url"
          :alt="selectedImage.label"
          contain
          max-height="82vh"
          class="gallery-image"
        />
        <v-btn
          v-if="instructionImages.length > 1"
          icon
          variant="flat"
          class="gallery-next"
          :aria-label="$t('general.next')"
          @click="showNext"
        >
          <v-icon>{{ $globals.icons.chevronRight }}</v-icon>
        </v-btn>
        <div class="gallery-caption text-white text-center pa-3">
          {{ selectedImage.label }}
        </div>
      </v-card>
    </v-dialog>
  </section>
</template>

<script setup lang="ts">
import type { Recipe, RecipeAsset, RecipeStep } from "~/lib/api/types/recipe";
import type { NoUndefinedField } from "~/lib/api/types/non-generated";
import { useStaticRoutes } from "~/composables/api";

const INSTRUCTION_IMAGE_PREFIX = "instruction-ai::";

const props = defineProps({
  recipe: {
    type: Object as () => NoUndefinedField<Recipe>,
    required: true,
  },
});

interface InstructionImage {
  asset: RecipeAsset;
  step: RecipeStep;
  stepIndex: number;
  label: string;
  url: string;
}

const { recipeAssetPath } = useStaticRoutes();
const i18n = useI18n();
const galleryOpen = ref(false);
const selectedIndex = ref(0);

const instructionImages = computed<InstructionImage[]>(() => {
  const stepsById = new Map(
    props.recipe.recipeInstructions
      .map((step, stepIndex) => [step.id, { step, stepIndex }] as const)
      .filter(([id]) => Boolean(id)),
  );

  return props.recipe.assets
    .filter(asset => asset.name.startsWith(INSTRUCTION_IMAGE_PREFIX) && Boolean(asset.fileName))
    .map((asset) => {
      const stepId = asset.name.slice(INSTRUCTION_IMAGE_PREFIX.length);
      const stepData = stepsById.get(stepId);
      if (!stepData || !asset.fileName) {
        return null;
      }
      const summary = stepData.step.summary || stepData.step.title || "";
      const stepLabel = i18n.t("recipe.step-index", { step: stepData.stepIndex + 1 });
      return {
        asset,
        step: stepData.step,
        stepIndex: stepData.stepIndex,
        label: summary ? `${stepLabel}: ${summary}` : stepLabel,
        url: recipeAssetPath(props.recipe.id, asset.fileName),
      };
    })
    .filter((item): item is InstructionImage => item !== null)
    .sort((left, right) => left.stepIndex - right.stepIndex);
});

const selectedImage = computed(() => instructionImages.value[selectedIndex.value]);

function openGallery(index: number) {
  selectedIndex.value = index;
  galleryOpen.value = true;
}

function showPrevious() {
  selectedIndex.value = (selectedIndex.value - 1 + instructionImages.value.length) % instructionImages.value.length;
}

function showNext() {
  selectedIndex.value = (selectedIndex.value + 1) % instructionImages.value.length;
}
</script>

<style scoped>
.instruction-image-list {
  display: grid;
  gap: 24px;
  grid-template-columns: minmax(0, 1fr);
}

.instruction-image-figure {
  margin: 0;
  width: min(100%, 860px);
}

.instruction-image {
  border-radius: 4px;
  cursor: zoom-in;
  width: 100%;
}

.gallery-dialog {
  position: relative;
  overflow: hidden;
}

.gallery-image {
  min-height: min(68vh, 720px);
}

.gallery-close,
.gallery-previous,
.gallery-next {
  position: absolute;
  z-index: 2;
}

.gallery-close {
  inset-block-start: 12px;
  inset-inline-end: 12px;
}

.gallery-previous,
.gallery-next {
  inset-block-start: 50%;
  transform: translateY(-50%);
}

.gallery-previous {
  inset-inline-start: 12px;
}

.gallery-next {
  inset-inline-end: 12px;
}
</style>
