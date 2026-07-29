<template>
  <BaseDialog
    v-model="dialogOpen"
    :title="chef ? $t('chef.edit-chef') : $t('chef.quick-add')"
    :icon="$globals.icons.chefHat"
    width="900"
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
        v-if="!chef"
        v-model="mode"
        mandatory
        divided
        density="comfortable"
        class="mb-4"
      >
        <v-btn value="manual" :prepend-icon="$globals.icons.edit">
          {{ $t("chef.manual") }}
        </v-btn>
        <v-btn value="ai" :prepend-icon="$globals.icons.robot">
          {{ $t("chef.add-with-ai") }}
        </v-btn>
      </v-btn-toggle>

      <template v-if="mode === 'ai' && !chef">
        <v-textarea
          v-model="aiPrompt"
          :label="$t('chef.ai-research-request')"
          :hint="$t('chef.ai-research-hint')"
          persistent-hint
          autofocus
          rows="6"
          auto-grow
          variant="outlined"
        />
        <v-row dense class="mt-1">
          <v-col cols="12" md="6">
            <v-text-field
              v-model="aiName"
              :label="$t('chef.chef-name')"
              variant="outlined"
              density="comfortable"
            />
          </v-col>
          <v-col cols="12" md="6">
            <v-text-field
              v-model="aiUrl"
              :label="$t('chef.reference-url')"
              :prepend-inner-icon="$globals.icons.link"
              type="url"
              variant="outlined"
              density="comfortable"
            />
          </v-col>
        </v-row>
        <v-alert type="info" variant="tonal" density="compact">
          {{ $t("chef.ai-help") }}
        </v-alert>
      </template>

      <template v-else>
        <v-row dense>
          <v-col cols="12" md="8">
            <v-text-field
              v-model="form.name"
              :label="$t('chef.chef-name')"
              autofocus
              variant="outlined"
              density="comfortable"
            />
          </v-col>
          <v-col cols="12" md="4">
            <v-select
              v-model="form.rank"
              :items="rankOptions"
              item-title="text"
              item-value="value"
              :label="$t('chef.rank')"
              variant="outlined"
              density="comfortable"
            />
          </v-col>
        </v-row>
        <v-combobox
          v-model="form.aliases"
          :label="$t('chef.aliases')"
          multiple
          chips
          closable-chips
          clearable
          variant="outlined"
          density="comfortable"
        />
        <v-row dense>
          <v-col cols="12" md="4">
            <v-text-field
              v-model="form.country"
              :label="$t('chef.country')"
              variant="outlined"
              density="comfortable"
            />
          </v-col>
          <v-col cols="12" md="4">
            <v-combobox
              v-model="form.cuisines"
              :label="$t('chef.cuisines')"
              multiple
              chips
              closable-chips
              clearable
              variant="outlined"
              density="comfortable"
            />
          </v-col>
          <v-col cols="12" md="4">
            <v-combobox
              v-model="form.specialties"
              :label="$t('chef.specialties')"
              multiple
              chips
              closable-chips
              clearable
              variant="outlined"
              density="comfortable"
            />
          </v-col>
        </v-row>
        <v-textarea
          v-model="form.biography"
          :label="$t('chef.biography')"
          rows="5"
          auto-grow
          variant="outlined"
        />
        <v-textarea
          v-model="form.careerSummary"
          :label="$t('chef.career-summary')"
          rows="4"
          auto-grow
          variant="outlined"
        />
        <v-combobox
          v-model="form.awards"
          :label="$t('chef.awards')"
          multiple
          chips
          closable-chips
          clearable
          variant="outlined"
          density="comfortable"
        />
        <v-row dense>
          <v-col cols="12" md="6">
            <v-select
              v-model="form.restaurantIds"
              :items="restaurantOptions"
              item-title="name"
              item-value="id"
              :label="$t('chef.linked-restaurants')"
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
              :label="$t('chef.linked-books')"
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
          v-model="form.notableRestaurants"
          :label="$t('chef.other-restaurants')"
          multiple
          chips
          closable-chips
          clearable
          variant="outlined"
          density="comfortable"
        />
        <v-combobox
          v-model="form.bookTitles"
          :label="$t('chef.other-books')"
          multiple
          chips
          closable-chips
          clearable
          variant="outlined"
          density="comfortable"
        />
        <v-row dense>
          <v-col cols="12" md="6">
            <v-text-field
              v-model="form.websiteUrl"
              :label="$t('chef.website-url')"
              :prepend-inner-icon="$globals.icons.link"
              type="url"
              variant="outlined"
              density="comfortable"
            />
          </v-col>
          <v-col cols="12" md="6">
            <v-text-field
              v-model="form.wikipediaUrl"
              :label="$t('chef.wikipedia-url')"
              :prepend-inner-icon="$globals.icons.link"
              type="url"
              variant="outlined"
              density="comfortable"
            />
          </v-col>
          <v-col cols="12" md="6">
            <v-text-field
              v-model="form.instagramUrl"
              :label="$t('chef.instagram-url')"
              :prepend-inner-icon="$globals.icons.link"
              type="url"
              variant="outlined"
              density="comfortable"
            />
          </v-col>
        </v-row>
        <v-row dense>
          <v-col cols="12" md="4">
            <v-switch
              v-model="form.hasMichelinRestaurant"
              color="primary"
              hide-details
              :label="$t('chef.has-michelin-restaurant')"
            />
          </v-col>
          <v-col cols="12" md="3">
            <v-text-field
              v-model.number="form.michelinStarCount"
              :label="$t('chef.michelin-star-count')"
              type="number"
              min="0"
              max="99"
              variant="outlined"
              density="comfortable"
            />
          </v-col>
          <v-col cols="12" md="5">
            <v-text-field
              v-model="form.michelinSummary"
              :label="$t('chef.michelin-summary')"
              variant="outlined"
              density="comfortable"
            />
          </v-col>
        </v-row>
        <v-textarea
          v-model="form.notes"
          :label="$t('chef.notes')"
          rows="3"
          auto-grow
          variant="outlined"
        />
      </template>

      <v-divider class="my-4" />
      <div class="text-subtitle-1 mb-2">
        {{ $t("chef.portrait") }}
      </div>
      <v-file-input
        v-model="imageFile"
        accept="image/*"
        :label="$t('chef.upload-portrait')"
        :prepend-inner-icon="$globals.icons.fileImage"
        prepend-icon=""
        clearable
        variant="outlined"
        density="comfortable"
      />
      <v-text-field
        v-model="imageUrl"
        :label="$t('chef.portrait-url')"
        :prepend-inner-icon="$globals.icons.link"
        type="url"
        variant="outlined"
        density="comfortable"
      />
      <v-checkbox
        v-model="findImageAutomatically"
        color="primary"
        hide-details
        :label="$t('chef.find-portrait-automatically')"
      />
    </v-card-text>
  </BaseDialog>
</template>

<script setup lang="ts">
import type { Chef, ChefCreate, ChefRank } from "~/lib/api/types/chef";
import type { Restaurant } from "~/lib/api/types/restaurant";
import type { UploadedBook } from "~/lib/api/types/uploaded-book";
import { useUserApi } from "~/composables/api/api-client";
import { alert } from "~/composables/use-toast";

const props = defineProps<{
  chef?: Chef | null;
}>();
const emit = defineEmits<{
  saved: [chef: Chef];
}>();
const dialogOpen = defineModel<boolean>({ default: false });
const i18n = useI18n();
const api = useUserApi();
const saving = ref(false);
const mode = ref<"manual" | "ai">("manual");
const aiPrompt = ref("");
const aiName = ref("");
const aiUrl = ref("");
const imageFile = ref<File | File[] | null>(null);
const imageUrl = ref("");
const findImageAutomatically = ref(true);
const restaurantOptions = ref<Restaurant[]>([]);
const bookOptions = ref<UploadedBook[]>([]);

const emptyForm = (): ChefCreate => ({
  name: "",
  aliases: [],
  rank: "good",
  country: "",
  cuisines: [],
  specialties: [],
  biography: "",
  careerSummary: "",
  awards: [],
  notableRestaurants: [],
  bookTitles: [],
  websiteUrl: "",
  wikipediaUrl: "",
  instagramUrl: "",
  hasMichelinRestaurant: false,
  michelinStarCount: 0,
  michelinSummary: "",
  notes: "",
  restaurantIds: [],
  uploadedBookIds: [],
});

const form = reactive<ChefCreate>(emptyForm());

const rankOptions = computed<{ text: string; value: ChefRank }[]>(() => [
  { text: i18n.t("chef.rank-world-class"), value: "world_class" },
  { text: i18n.t("chef.rank-excellent"), value: "excellent" },
  { text: i18n.t("chef.rank-good"), value: "good" },
  { text: i18n.t("chef.rank-medium"), value: "medium" },
  { text: i18n.t("chef.rank-emerging"), value: "emerging" },
]);

const canSubmit = computed(() => mode.value === "ai" && !props.chef
  ? Boolean(aiPrompt.value.trim() || aiName.value.trim() || aiUrl.value.trim())
  : Boolean(form.name.trim()));

watch(
  () => [dialogOpen.value, props.chef] as const,
  async ([open]) => {
    if (!open) return;
    loadForm();
    const [restaurantsResponse, booksResponse] = await Promise.all([
      api.restaurants.getAll(),
      api.uploadedBooks.getAll(),
    ]);
    restaurantOptions.value = restaurantsResponse.data || [];
    bookOptions.value = booksResponse.data || [];
  },
);

function loadForm() {
  mode.value = "manual";
  aiPrompt.value = "";
  aiName.value = "";
  aiUrl.value = "";
  imageFile.value = null;
  imageUrl.value = "";
  findImageAutomatically.value = !props.chef?.hasImage;
  Object.assign(form, props.chef
    ? {
        name: props.chef.name,
        aliases: [...props.chef.aliases],
        rank: props.chef.rank,
        country: props.chef.country || "",
        cuisines: [...props.chef.cuisines],
        specialties: [...props.chef.specialties],
        biography: props.chef.biography || "",
        careerSummary: props.chef.careerSummary || "",
        awards: [...props.chef.awards],
        notableRestaurants: [...props.chef.notableRestaurants],
        bookTitles: [...props.chef.bookTitles],
        websiteUrl: props.chef.websiteUrl || "",
        wikipediaUrl: props.chef.wikipediaUrl || "",
        instagramUrl: props.chef.instagramUrl || "",
        hasMichelinRestaurant: props.chef.hasMichelinRestaurant,
        michelinStarCount: props.chef.michelinStarCount,
        michelinSummary: props.chef.michelinSummary || "",
        notes: props.chef.notes || "",
        restaurantIds: [...props.chef.restaurantIds],
        uploadedBookIds: [...props.chef.uploadedBookIds],
      }
    : emptyForm());
}

function resetForm() {
  loadForm();
  Object.assign(form, emptyForm());
}

function selectedImage(): File | null {
  if (imageFile.value instanceof File) return imageFile.value;
  return Array.isArray(imageFile.value) ? imageFile.value[0] || null : null;
}

async function saveImage(chef: Chef): Promise<Chef> {
  const file = selectedImage();
  const response = file
    ? await api.chefs.uploadImage(chef.id, file)
    : imageUrl.value.trim()
      ? await api.chefs.saveImageUrl(chef.id, imageUrl.value.trim())
      : findImageAutomatically.value && !chef.hasImage
        ? await api.chefs.findImage(chef.id)
        : { data: chef, error: null };
  if (response.data && !response.error) return response.data;
  alert.warning(i18n.t("chef.portrait-save-failed"));
  return chef;
}

async function submit() {
  saving.value = true;
  const response = props.chef
    ? await api.chefs.updateOne(props.chef.id, form)
    : mode.value === "ai"
      ? await api.chefs.createWithAI({
          prompt: aiPrompt.value || null,
          name: aiName.value || null,
          url: aiUrl.value || null,
        })
      : await api.chefs.createOne(form);

  if (!response.data || response.error) {
    saving.value = false;
    const detail = response.error?.response?.data?.detail;
    const message = typeof detail?.message === "string"
      ? detail.message
      : typeof detail === "string"
        ? detail
        : i18n.t("events.something-went-wrong");
    alert.error(message);
    return;
  }

  const savedChef = await saveImage(response.data);
  saving.value = false;
  emit("saved", savedChef);
  dialogOpen.value = false;
  resetForm();
}
</script>
