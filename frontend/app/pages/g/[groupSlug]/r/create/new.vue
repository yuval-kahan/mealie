<template>
  <div>
    <v-card-title class="headline">
      {{ $t('recipe.create-recipe') }}
    </v-card-title>
    <v-card-text>
      {{ $t('recipe.create-a-recipe-by-providing-the-name-all-recipes-must-have-unique-names') }}
      <v-form
        ref="domCreateByName"
        @submit.prevent
      >
        <v-text-field
          v-model="newRecipeName"
          :label="$t('recipe.recipe-name')"
          :prepend-inner-icon="$globals.icons.primary"
          validate-on="blur"
          autofocus
          variant="solo-filled"
          clearable
          class="rounded-lg mt-2"
          color="primary"
          rounded
          :rules="[validators.required]"
          :hint="$t('recipe.new-recipe-names-must-be-unique')"
          persistent-hint
          @keyup.enter="createByName(newRecipeName)"
        />
      </v-form>
      <v-divider class="my-4" />
      <RecipeVideoAssetUpload
        v-model="videoFile"
        :disabled="state.loading"
      />
    </v-card-text>
    <v-card-actions class="justify-center">
      <div style="width: 250px">
        <BaseButton
          :disabled="newRecipeName.trim() === ''"
          rounded
          block
          :loading="state.loading"
          @click="createByName(newRecipeName)"
        />
      </div>
    </v-card-actions>
  </div>
</template>

<script setup lang="ts">
import { useUserApi } from "~/composables/api";
import { validators } from "~/composables/use-validators";
import type { VForm } from "~/types/auto-forms";

const state = reactive({
  error: false,
  loading: false,
});
const auth = useMealieAuth();
const route = useRoute();
const groupSlug = computed(() => route.params.groupSlug as string || auth.user.value?.groupSlug || "");

const api = useUserApi();
const router = useRouter();
const { attachVideoToRecipe } = useRecipeVideoAsset();

const newRecipeName = ref("");
const videoFile = ref<File | null>(null);
const domCreateByName = ref<VForm | null>(null);

async function createByName(name: string) {
  const validation = await domCreateByName.value?.validate();
  if (!validation?.valid || name === "") {
    return;
  }

  state.loading = true;
  const { response } = await api.recipes.createOne({ name });
  if (response?.status !== 201 || !response.data) {
    state.error = true;
    state.loading = false;
    return;
  }

  if (videoFile.value) {
    await attachVideoToRecipe(response.data, videoFile.value);
  }

  router.push(`/g/${groupSlug.value}/r/${response.data}?edit=true`);
}
</script>
