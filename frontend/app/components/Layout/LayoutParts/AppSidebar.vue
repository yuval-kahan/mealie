<template>
  <AppOrganizerSidebar
    v-model="modelValue"
    v-model:preferences="organizerPreferences"
    :sections="organizerSections"
  />

  <v-navigation-drawer v-model="modelValue" class="d-flex flex-column d-print-none position-fixed" touchless>
    <AnnouncementDialog v-model="showAnnouncementsDialog" />
    <LanguageDialog v-model="state.languageDialog" />
    <BaseDialog
      v-model="state.apiDialog"
      title="API"
      :icon="$globals.icons.robot"
      width="720"
      can-submit
      :submit-text="$t('general.save')"
      @submit="handleQuickApiSettingsSubmit"
    >
      <v-card-text v-if="group?.aiProviderSettings">
        <GroupAIProviderSettingsEditor
          v-model="group.aiProviderSettings"
          hide-header
          @create="handleQuickApiCreate"
          @update="handleQuickApiUpdate"
          @delete="handleQuickApiDelete"
        />
      </v-card-text>
      <AppLoader v-else waiting-text="" />
    </BaseDialog>
    <!-- User Profile -->
    <template v-if="loggedIn && sessionUser">
      <v-list-item lines="two" :to="userProfileLink" exact>
        <div class="d-flex align-center ga-2">
          <UserAvatar list :user-id="sessionUser.id" :tooltip="false" />

          <div class="d-flex flex-column justify-start">
            <v-list-item-title class="pr-2 pl-1">
              {{ sessionUser.fullName }}
            </v-list-item-title>
            <v-list-item-subtitle class="opacity-100">
              <v-btn v-if="isOwnGroup" class="px-2 pa-0" variant="text" :to="userFavoritesLink" size="small">
                <v-icon start size="small">
                  {{ $globals.icons.heart }}
                </v-icon>
                {{ $t("user.favorite-recipes") }}
              </v-btn>
            </v-list-item-subtitle>
          </div>
        </div>
      </v-list-item>
      <v-divider />
    </template>

    <slot />

    <!-- Primary Links -->
    <template v-if="topLink">
      <v-list v-model:selected="state.secondarySelected" nav density="comfortable" color="primary">
        <template v-for="nav in topLink">
          <div v-if="!nav.restricted || isOwnGroup" :key="nav.key || nav.title">
            <!-- Multi Items -->
            <v-list-group
              v-if="nav.children"
              :key="(nav.key || nav.title) + 'multi-item'"
              v-model="state.dropDowns[nav.title]"
              color="primary"
              :prepend-icon="nav.icon"
              :fluid="true"
            >
              <template #activator="{ props: hoverProps }">
                <v-list-item v-bind="hoverProps" :prepend-icon="nav.icon" :title="nav.title" />
              </template>

              <v-list-item
                v-for="child in nav.children"
                :key="child.key || child.title"
                exact
                :to="child.to"
                :prepend-icon="child.icon"
                :title="child.title"
                class="ml-4"
              />
            </v-list-group>

            <!-- Single Item -->
            <template v-else>
              <v-list-item
                :key="(nav.key || nav.title) + 'single-item'"
                exact
                link
                :to="nav.to"
                :prepend-icon="nav.icon"
                :title="nav.title"
              />
            </template>
          </div>
        </template>
      </v-list>
    </template>

    <!-- Secondary Links -->
    <template v-if="secondaryLinks.length > 0">
      <v-divider class="mt-2" />
      <v-list v-model:selected="state.secondarySelected" nav density="compact" exact>
        <template v-for="nav in secondaryLinks">
          <div v-if="!nav.restricted || isOwnGroup" :key="nav.key || nav.title">
            <!-- Multi Items -->
            <v-list-group
              v-if="nav.children"
              :key="(nav.key || nav.title) + 'multi-item'"
              v-model="state.dropDowns[nav.title]"
              color="primary"
              :prepend-icon="nav.icon"
              fluid
            >
              <template #activator="{ props: hoverProps }">
                <v-list-item v-bind="hoverProps" :prepend-icon="nav.icon" :title="nav.title" />
              </template>

              <v-list-item
                v-for="child in nav.children"
                :key="child.key || child.title"
                exact
                :to="child.to"
                class="ml-2"
                :prepend-icon="child.icon"
                :title="child.title"
              />
            </v-list-group>

            <!-- Single Item -->
            <v-list-item v-else :key="(nav.key || nav.title) + 'single-item'" exact link :to="nav.to">
              <template #prepend>
                <v-icon>{{ nav.icon }}</v-icon>
              </template>
              <v-list-item-title>{{ nav.title }}</v-list-item-title>
            </v-list-item>
          </div>
        </template>
      </v-list>
    </template>

    <!-- Bottom Navigation Links -->
    <template #append>
      <v-list v-model:selected="state.bottomSelected" nav density="comfortable">
        <v-list-item
          v-if="loggedIn && announcementsEnabled"
          :title="$t('announcements.announcements')"
          @click="() => showAnnouncementsDialog = !showAnnouncementsDialog"
        >
          <template #prepend>
            <v-badge
              :model-value="!!newAnnouncements.length"
              color="accent"
              :content="newAnnouncements.length || undefined"
              offset-x="-2"
            >
              <v-icon>
                {{ $globals.icons.bullhornVariant }}
              </v-icon>
            </v-badge>
          </template>
        </v-list-item>
        <v-menu location="end bottom" :offset="15">
          <template #activator="{ props: hoverProps }">
            <v-list-item v-bind="hoverProps" :prepend-icon="$globals.icons.cog" :title="$t('general.settings')" />
          </template>
          <v-list density="comfortable" color="primary">
            <v-list-item :prepend-icon="$globals.icons.translate" :title="$t('sidebar.language')" @click="state.languageDialog=true" />
            <v-list-item :prepend-icon="$vuetify.theme.current.dark ? $globals.icons.weatherSunny : $globals.icons.weatherNight" :title="$vuetify.theme.current.dark ? $t('settings.theme.light-mode') : $t('settings.theme.dark-mode')" @click="toggleDark" />
            <v-divider v-if="loggedIn" class="my-2" />
            <v-list-item v-if="loggedIn" :prepend-icon="$globals.icons.cog" :title="$t('profile.user-settings')" to="/user/profile" />
            <v-list-item v-if="canManage" :prepend-icon="$globals.icons.manageData" :title="$t('data-pages.data-management')" to="/group/data" />
            <v-divider v-if="isAdmin" class="my-2" />
            <v-list-item v-if="isAdmin" :prepend-icon="$globals.icons.wrench" :title="$t('settings.admin-settings')" to="/admin/site-settings" />
          </v-list>
        </v-menu>
        <v-list-item
          v-if="canManage"
          :prepend-icon="$globals.icons.robot"
          title="API"
          @click="openQuickApiDialog"
        />
      </v-list>
    </template>
  </v-navigation-drawer>
</template>

<script setup lang="ts">
import { useLoggedInState } from "~/composables/use-logged-in-state";
import type { OrganizerSidebarSection, SidebarLinks } from "~/types/application-types";
import AnnouncementDialog from "~/components/Domain/Announcement/AnnouncementDialog.vue";
import UserAvatar from "~/components/Domain/User/UserAvatar.vue";
import GroupAIProviderSettingsEditor from "~/components/Domain/Group/GroupAIProviderSettingsEditor.vue";
import AppOrganizerSidebar from "~/components/Layout/LayoutParts/AppOrganizerSidebar.vue";
import { useToggleDarkMode } from "~/composables/use-utils";
import { useAnnouncements } from "~/composables/use-announcements";
import { useGroupSelf } from "~/composables/use-groups";
import { useAIProviders } from "~/composables/use-ai-providers";
import { alert } from "~/composables/use-toast";
import type { AIProviderCreate, AIProviderUpdate } from "~/lib/api/types/group";
import type { UserOrganizerSidebarPreferences } from "~/composables/use-users/preferences";

const props = defineProps({
  user: {
    type: Object,
    default: null,
  },
  topLink: {
    type: Array as () => SidebarLinks,
    required: true,
  },
  secondaryLinks: {
    type: Array as () => SidebarLinks,
    required: false,
    default: null,
  },
  organizerSections: {
    type: Array as () => OrganizerSidebarSection[],
    required: false,
    default: () => [],
  },
});

const modelValue = defineModel<boolean>({ default: false });
const organizerPreferences = defineModel<UserOrganizerSidebarPreferences>("organizerPreferences", {
  default: () => ({
    showCookbooks: true,
    showCategories: false,
    showTags: false,
    sectionOrder: ["cookbooks", "categories", "tags"],
  }),
});

const auth = useMealieAuth();
const sessionUser = computed(() => auth.user.value);
const { loggedIn, isOwnGroup } = useLoggedInState();
const isAdmin = computed(() => auth.user.value?.admin);
const canManage = computed(() => auth.user.value?.canManage);
const { group, actions: groupActions } = useGroupSelf();
const { createOne, updateOne, deleteOne } = useAIProviders();

const userFavoritesLink = computed(() => auth.user.value ? `/user/${auth.user.value.id}/favorites` : undefined);
const userProfileLink = computed(() => auth.user.value ? "/user/profile" : undefined);

const toggleDark = useToggleDarkMode();

const showAnnouncementsDialog = ref(false);
const { announcementsEnabled, newAnnouncements } = useAnnouncements();

const state = reactive({
  dropDowns: {} as Record<string, boolean>,
  secondarySelected: null as string[] | null,
  bottomSelected: null as string[] | null,
  languageDialog: false as boolean,
  apiDialog: false as boolean,
});

const allLinks = computed(() => [...props.topLink, ...(props.secondaryLinks || [])]);
function initDropdowns() {
  allLinks.value.forEach((link) => {
    state.dropDowns[link.title] = link.childrenStartExpanded || false;
  });
}

function openQuickApiDialog() {
  state.apiDialog = true;
}

function providerErrorMessage(error: unknown, fallback: string) {
  const responseData = (error as { response?: { data?: { detail?: unknown } } })?.response?.data;
  const detail = responseData?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (detail && typeof detail === "object") {
    const detailObject = detail as { message?: string; exception?: string };
    return detailObject.exception || detailObject.message || fallback;
  }

  return fallback;
}

async function handleQuickApiCreate(data: AIProviderCreate) {
  const result = await createOne(data);
  if (!result.data) {
    alert.error(providerErrorMessage(result.error, "שמירת ה-API נכשלה"));
    return;
  }

  await groupActions.refresh();

  if (group.value?.aiProviderSettings && !group.value.aiProviderSettings.defaultProviderId) {
    group.value.aiProviderSettings.defaultProviderId = result.data.id;
    await groupActions.updateAIProviderSettings();
  }

  await groupActions.refresh();
  alert.success("ה-API נשמר");
}

async function handleQuickApiUpdate(id: string, data: AIProviderUpdate) {
  const result = await updateOne(id, data);
  if (!result.data) {
    alert.error(providerErrorMessage(result.error, "עדכון ה-API נכשל"));
    return;
  }

  await groupActions.refresh();
  alert.success("ה-API עודכן");
}

async function handleQuickApiDelete(id: string) {
  const result = await deleteOne(id);
  if (!result.data) {
    alert.error(providerErrorMessage(result.error, "מחיקת ה-API נכשלה"));
    return;
  }

  await groupActions.refresh();
  alert.success("ה-API נמחק");
}

async function handleQuickApiSettingsSubmit() {
  const data = await groupActions.updateAIProviderSettings();
  if (data) {
    alert.success("הגדרות ה-API נשמרו");
  }
  else {
    alert.error("שמירת הגדרות ה-API נכשלה");
  }
}
watch(
  () => allLinks,
  () => {
    initDropdowns();
  },
  {
    deep: true,
  },
);
</script>

<style scoped>
@media print {
  .no-print {
    display: none;
  }
}

.favorites-link {
  text-decoration: none;
}

.favorites-link:hover {
  text-decoration: underline;
}
</style>
