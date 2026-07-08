<template>
  <div
    class="recipe-rating"
    @click.prevent
  >
    <div
      v-if="editButton"
      class="recipe-rating__editable"
    >
      <v-rating
        :model-value="editableRatingValue"
        :half-increments="!ratingEditEnabled"
        active-color="secondary"
        color="secondary-lighten-3"
        length="5"
        :density="small ? 'compact' : 'default'"
        :size="small ? 'x-small' : undefined"
        :readonly="!ratingEditEnabled || !isOwnGroup"
        :hover="ratingEditEnabled"
        :clearable="ratingEditEnabled"
        @update:model-value="updateEditableRating"
      />
      <v-tooltip
        v-if="isOwnGroup"
        location="bottom"
      >
        <template #activator="{ props: tooltipProps }">
          <v-btn
            v-bind="tooltipProps"
            icon
            size="x-small"
            variant="text"
            color="primary"
            @click.stop="toggleRatingEdit"
          >
            <v-icon>
              {{ ratingEditEnabled ? $globals.icons.check : $globals.icons.edit }}
            </v-icon>
          </v-btn>
        </template>
        <span>{{ ratingEditEnabled ? $t("general.close") : $t("general.edit") }}</span>
      </v-tooltip>
    </div>
    <!-- User Rating -->
    <v-hover
      v-else
      v-slot="{ isHovering, props: hoverProps }"
    >
      <v-rating
        v-if="isOwnGroup && (userRating || isHovering || !ratingsLoaded)"
        v-bind="hoverProps"
        :model-value="userRating"
        active-color="secondary"
        color="secondary-lighten-3"
        length="5"
        :density="small ? 'compact' : 'default'"
        :size="small ? 'x-small' : undefined"
        hover
        clearable
        @update:model-value="updateRating(+$event)"
      />
      <!-- Group Rating -->
      <v-rating
        v-else
        v-bind="hoverProps"
        :model-value="groupRating"
        :half-increments="true"
        active-color="grey-darken-1"
        color="secondary-lighten-3"
        length="5"
        :density="small ? 'compact' : 'default'"
        :size="small ? 'x-small' : undefined"
        hover
      />
    </v-hover>
  </div>
</template>

<script setup lang="ts">
import { useLoggedInState } from "~/composables/use-logged-in-state";
import { useUserSelfRatings } from "~/composables/use-users";

interface Props {
  emitOnly?: boolean;
  recipeId?: string;
  slug?: string;
  small?: boolean;
  editButton?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  emitOnly: false,
  recipeId: "",
  slug: "",
  small: false,
  editButton: false,
});

const modelValue = defineModel<number>({ default: 0 });

const { isOwnGroup } = useLoggedInState();
const { userRatings, setRating, ready: ratingsLoaded } = useUserSelfRatings();

const userRating = computed(() => {
  return userRatings.value.find(r => r.recipeId === props.recipeId)?.rating ?? undefined;
});

// if a user unsets their rating, we don't want to fall back to the group rating since it's out of sync
const hideGroupRating = ref(!!userRating.value);
watch(
  () => userRating.value,
  () => {
    if (userRating.value) {
      hideGroupRating.value = true;
    }
  },
);

const groupRating = computed(() => {
  return hideGroupRating.value ? 0 : modelValue.value;
});

const ratingEditEnabled = ref(false);

const editableRatingValue = computed(() => {
  return userRating.value ?? groupRating.value ?? 0;
});

function toggleRatingEdit() {
  ratingEditEnabled.value = !ratingEditEnabled.value;
}

function updateEditableRating(value?: number | string) {
  if (!ratingEditEnabled.value) {
    return;
  }

  const parsedValue = Number(value ?? 0);
  updateRating(Number.isFinite(parsedValue) ? parsedValue : 0);
  ratingEditEnabled.value = false;
}

function updateRating(val?: number) {
  if (!isOwnGroup.value) {
    return;
  }

  if (val === userRating.value) {
    val = 0;
  }

  if (!props.emitOnly) {
    setRating(props.slug, val || 0, null);
  }
  modelValue.value = val ?? 0;
}
</script>

<style lang="scss" scoped>
.recipe-rating__editable {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
</style>
