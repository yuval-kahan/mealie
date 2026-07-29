<template>
  <BaseDialog
    v-model="dialogOpen"
    :title="restaurant ? $t('restaurant.edit-restaurant') : $t('restaurant.quick-add')"
    :icon="$globals.icons.chefHat"
    width="760"
    max-width="96vw"
    can-submit
    keep-open
    disable-submit-on-enter
    :loading="saving"
    :submit-disabled="!canSubmit"
    :submit-text="$t('general.save')"
    @submit="submit"
    @close="resetForm"
  >
    <v-card-text class="pt-4">
      <v-btn-toggle
        v-if="!restaurant"
        v-model="mode"
        mandatory
        divided
        density="comfortable"
        class="mb-4"
      >
        <v-btn value="manual" :prepend-icon="$globals.icons.edit">
          {{ $t("restaurant.manual") }}
        </v-btn>
        <v-btn value="ai" :prepend-icon="$globals.icons.robot">
          {{ $t("restaurant.add-with-ai") }}
        </v-btn>
      </v-btn-toggle>

      <template v-if="mode === 'ai' && !restaurant">
        <v-textarea
          v-model="aiPrompt"
          :label="$t('restaurant.ai-research-request')"
          :hint="$t('restaurant.ai-research-hint')"
          persistent-hint
          autofocus
          rows="5"
          auto-grow
          variant="outlined"
        />
        <v-text-field
          v-model="aiName"
          :label="$t('restaurant.restaurant-name')"
          :hint="$t('restaurant.ai-name-hint')"
          persistent-hint
          variant="outlined"
          density="comfortable"
        />
        <v-text-field
          v-model="aiUrl"
          :label="$t('restaurant.website-url')"
          :prepend-inner-icon="$globals.icons.link"
          type="url"
          variant="outlined"
          density="comfortable"
        />
        <v-alert type="info" variant="tonal" density="compact">
          {{ $t("restaurant.ai-help") }}
        </v-alert>
      </template>

      <template v-else>
        <v-text-field
          v-model="form.name"
          :label="$t('restaurant.restaurant-name')"
          autofocus
          variant="outlined"
          density="comfortable"
        />
        <v-text-field
          v-model="form.websiteUrl"
          :label="$t('restaurant.website-url')"
          :prepend-inner-icon="$globals.icons.link"
          type="url"
          variant="outlined"
          density="comfortable"
        />
        <v-combobox
          v-model="form.cuisineTypes"
          :label="$t('restaurant.cuisine-types')"
          multiple
          chips
          closable-chips
          clearable
          variant="outlined"
          density="comfortable"
        />
        <v-combobox
          v-model="form.addresses"
          :label="$t('restaurant.addresses')"
          :hint="$t('restaurant.addresses-hint')"
          persistent-hint
          multiple
          chips
          closable-chips
          clearable
          variant="outlined"
          density="comfortable"
        />
        <v-row dense>
          <v-col cols="12" sm="6">
            <v-text-field
              v-model="form.phone"
              :label="$t('restaurant.phone')"
              variant="outlined"
              density="comfortable"
            />
          </v-col>
          <v-col cols="12" sm="6">
            <v-text-field
              v-model="form.priceRange"
              :label="$t('restaurant.price-range')"
              variant="outlined"
              density="comfortable"
            />
          </v-col>
        </v-row>
        <v-textarea
          v-model="form.description"
          :label="$t('restaurant.description')"
          rows="3"
          auto-grow
          variant="outlined"
        />
        <v-text-field
          v-model="form.michelinInfo"
          :label="$t('restaurant.michelin-info')"
          :hint="$t('restaurant.michelin-hint')"
          persistent-hint
          variant="outlined"
          density="comfortable"
        />
        <v-row dense>
          <v-col cols="12" sm="6">
            <v-text-field
              v-model.number="form.michelinStarCount"
              :label="$t('restaurant.michelin-star-count')"
              type="number"
              min="0"
              max="3"
              variant="outlined"
              density="comfortable"
            />
          </v-col>
          <v-col cols="12" sm="6">
            <v-switch
              v-model="form.isMichelinListed"
              color="primary"
              hide-details
              :label="$t('restaurant.is-michelin-listed')"
            />
          </v-col>
        </v-row>
        <v-row dense>
          <v-col cols="12" md="6">
            <v-select
              v-model="form.chefIds"
              :items="chefOptions"
              item-title="name"
              item-value="id"
              :label="$t('restaurant.linked-chefs')"
              multiple
              chips
              closable-chips
              clearable
              variant="outlined"
              density="comfortable"
            />
          </v-col>
          <v-col cols="12" md="6">
            <v-select
              v-model="form.uploadedBookIds"
              :items="bookOptions"
              item-title="name"
              item-value="id"
              :label="$t('restaurant.linked-books')"
              multiple
              chips
              closable-chips
              clearable
              variant="outlined"
              density="comfortable"
            />
          </v-col>
        </v-row>
        <v-combobox
          v-model="form.chefNames"
          :label="$t('restaurant.other-chefs')"
          multiple
          chips
          closable-chips
          clearable
          variant="outlined"
          density="comfortable"
        />
        <v-combobox
          v-model="form.bookTitles"
          :label="$t('restaurant.other-books')"
          multiple
          chips
          closable-chips
          clearable
          variant="outlined"
          density="comfortable"
        />
        <v-row dense>
          <v-col cols="12" sm="6">
            <v-text-field
              v-model.number="form.googleRating"
              :label="$t('restaurant.google-rating')"
              type="number"
              min="0"
              max="5"
              step="0.1"
              variant="outlined"
              density="comfortable"
            />
          </v-col>
          <v-col cols="12" sm="6">
            <v-text-field
              v-model.number="form.googleReviewCount"
              :label="$t('restaurant.google-review-count')"
              type="number"
              min="0"
              step="1"
              variant="outlined"
              density="comfortable"
            />
          </v-col>
        </v-row>
        <v-text-field
          v-model="form.googleMapsUrl"
          :label="$t('restaurant.google-maps-url')"
          :prepend-inner-icon="$globals.icons.link"
          type="url"
          variant="outlined"
          density="comfortable"
        />
        <div class="mb-4">
          <div class="text-body-2 mb-1">
            {{ $t("restaurant.our-rating") }}
          </div>
          <v-rating
            v-model="form.ourRating"
            color="warning"
            active-color="warning"
            half-increments
            clearable
            hover
            density="compact"
          />
        </div>
        <v-textarea
          v-model="form.notes"
          :label="$t('restaurant.notes')"
          rows="2"
          auto-grow
          variant="outlined"
        />
        <v-row dense>
          <v-col cols="12" sm="6">
            <v-select
              v-model="form.recommendationStatus"
              :items="recommendationOptions"
              item-title="text"
              item-value="value"
              :label="$t('restaurant.recommendation')"
              variant="outlined"
              density="comfortable"
            />
          </v-col>
          <v-col cols="12" sm="6">
            <v-select
              v-model="form.visitStatus"
              :items="visitOptions"
              item-title="text"
              item-value="value"
              :label="$t('restaurant.visit-status')"
              variant="outlined"
              density="comfortable"
            />
          </v-col>
        </v-row>
      </template>
    </v-card-text>
  </BaseDialog>
</template>

<script setup lang="ts">
import type {
  Restaurant,
  RestaurantCreate,
  RestaurantRecommendationStatus,
  RestaurantVisitStatus,
} from "~/lib/api/types/restaurant";
import type { Chef } from "~/lib/api/types/chef";
import type { UploadedBook } from "~/lib/api/types/uploaded-book";
import { useUserApi } from "~/composables/api/api-client";
import { alert } from "~/composables/use-toast";

const props = defineProps<{
  restaurant?: Restaurant | null;
}>();
const emit = defineEmits<{
  saved: [restaurant: Restaurant];
}>();
const dialogOpen = defineModel<boolean>({ default: false });
const i18n = useI18n();
const api = useUserApi();
const saving = ref(false);
const mode = ref<"manual" | "ai">("manual");
const aiPrompt = ref("");
const aiName = ref("");
const aiUrl = ref("");
const chefOptions = ref<Chef[]>([]);
const bookOptions = ref<UploadedBook[]>([]);

const emptyForm = (): RestaurantCreate => ({
  name: "",
  websiteUrl: "",
  cuisineTypes: [],
  addresses: [],
  phone: "",
  priceRange: "",
  description: "",
  notes: "",
  michelinInfo: "",
  michelinStarCount: 0,
  isMichelinListed: false,
  chefNames: [],
  bookTitles: [],
  chefIds: [],
  uploadedBookIds: [],
  googleRating: null,
  googleReviewCount: null,
  googleMapsUrl: "",
  ourRating: null,
  recommendationStatus: "recommended",
  visitStatus: "not_tried",
});

const form = reactive<RestaurantCreate>(emptyForm());

const recommendationOptions = computed<{ text: string; value: RestaurantRecommendationStatus }[]>(() => [
  { text: i18n.t("restaurant.strongly-recommended"), value: "strongly_recommended" },
  { text: i18n.t("restaurant.recommended"), value: "recommended" },
  { text: i18n.t("restaurant.neutral"), value: "neutral" },
  { text: i18n.t("restaurant.not-recommended"), value: "not_recommended" },
  { text: i18n.t("restaurant.strongly-not-recommended"), value: "strongly_not_recommended" },
]);

const visitOptions = computed<{ text: string; value: RestaurantVisitStatus }[]>(() => [
  { text: i18n.t("restaurant.not-tried"), value: "not_tried" },
  { text: i18n.t("restaurant.tried"), value: "tried" },
]);

const canSubmit = computed(() => mode.value === "ai" && !props.restaurant
  ? Boolean(aiPrompt.value.trim() || aiName.value.trim() || aiUrl.value.trim())
  : Boolean(form.name.trim()));

watch(
  () => [dialogOpen.value, props.restaurant] as const,
  async ([open]) => {
    if (!open) return;
    loadForm();
    const [chefsResponse, booksResponse] = await Promise.all([
      api.chefs.getAll(),
      api.uploadedBooks.getAll(),
    ]);
    chefOptions.value = chefsResponse.data || [];
    bookOptions.value = booksResponse.data || [];
  },
);

function loadForm() {
  mode.value = "manual";
  aiPrompt.value = "";
  aiName.value = "";
  aiUrl.value = "";
  Object.assign(form, props.restaurant
    ? {
        name: props.restaurant.name,
        websiteUrl: props.restaurant.websiteUrl || "",
        cuisineTypes: [...props.restaurant.cuisineTypes],
        addresses: [...props.restaurant.addresses],
        phone: props.restaurant.phone || "",
        priceRange: props.restaurant.priceRange || "",
        description: props.restaurant.description || "",
        notes: props.restaurant.notes || "",
        michelinInfo: props.restaurant.michelinInfo || "",
        michelinStarCount: props.restaurant.michelinStarCount,
        isMichelinListed: props.restaurant.isMichelinListed,
        chefNames: [...props.restaurant.chefNames],
        bookTitles: [...props.restaurant.bookTitles],
        chefIds: [...props.restaurant.chefIds],
        uploadedBookIds: [...props.restaurant.uploadedBookIds],
        googleRating: props.restaurant.googleRating ?? null,
        googleReviewCount: props.restaurant.googleReviewCount ?? null,
        googleMapsUrl: props.restaurant.googleMapsUrl || "",
        ourRating: props.restaurant.ourRating ?? null,
        recommendationStatus: props.restaurant.recommendationStatus,
        visitStatus: props.restaurant.visitStatus,
      }
    : emptyForm());
}

function resetForm() {
  mode.value = "manual";
  aiPrompt.value = "";
  aiName.value = "";
  aiUrl.value = "";
  Object.assign(form, emptyForm());
}

async function submit() {
  saving.value = true;
  const response = props.restaurant
    ? await api.restaurants.updateOne(props.restaurant.id, form)
    : mode.value === "ai"
      ? await api.restaurants.createWithAI({
          prompt: aiPrompt.value || null,
          name: aiName.value || null,
          url: aiUrl.value || null,
        })
      : await api.restaurants.createOne(form);
  saving.value = false;

  if (!response.data || response.error) {
    const detail = response.error?.response?.data?.detail;
    const message = typeof detail?.message === "string"
      ? detail.message
      : typeof detail === "string"
        ? detail
        : i18n.t("events.something-went-wrong");
    alert.error(message);
    return;
  }
  emit("saved", response.data);
  dialogOpen.value = false;
  resetForm();
}
</script>
