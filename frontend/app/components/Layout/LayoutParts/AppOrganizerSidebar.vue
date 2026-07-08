<template>
  <v-navigation-drawer
    v-if="showOrganizerDrawer"
    v-model="modelValue"
    class="app-organizer-sidebar d-flex flex-column d-print-none position-fixed"
    :class="{ 'app-organizer-sidebar--collapsed': collapsed }"
    :location="drawerLocation"
    :order="-1"
    :width="drawerWidth"
    touchless
  >
    <div class="app-organizer-sidebar__header">
      <div class="d-flex align-center min-w-0">
        <v-btn
          icon
          variant="text"
          size="small"
          :aria-label="toggleCollapsedLabel"
          :title="toggleCollapsedLabel"
          @click="toggleCollapsed"
        >
          <v-icon size="small">
            {{ $globals.icons.organizers }}
          </v-icon>
        </v-btn>
        <span
          v-if="!collapsed"
          class="text-subtitle-2 font-weight-bold text-truncate ms-1"
        >
          {{ $t("sidebar.organizer-navigation") }}
        </span>
      </div>

      <v-menu
        v-if="!collapsed"
        location="bottom"
        :close-on-content-click="false"
      >
        <template #activator="{ props: menuProps }">
          <v-btn
            v-bind="menuProps"
            icon
            variant="text"
            size="small"
            :aria-label="$t('sidebar.organizer-navigation-settings')"
          >
            <v-icon size="small">
              {{ $globals.icons.cog }}
            </v-icon>
          </v-btn>
        </template>

        <v-list
          density="compact"
          min-width="240"
        >
          <v-list-subheader>
            {{ $t("sidebar.show-in-organizer-navigation") }}
          </v-list-subheader>
          <VueDraggable
            v-model="orderedPreferenceOptions"
            handle=".organizer-sidebar-sort-handle"
            :delay="150"
            :delay-on-touch-only="true"
            v-bind="{
              animation: 180,
              ghostClass: 'organizer-sidebar-sort-ghost',
            }"
          >
            <v-list-item
              v-for="option in orderedPreferenceOptions"
              :key="option.key"
              :title="option.title"
              @click="togglePreference(option.preferenceKey)"
            >
              <template #prepend>
                <div class="d-flex align-center me-3">
                  <v-icon
                    class="organizer-sidebar-sort-handle me-2"
                    size="small"
                    :title="$t('sidebar.reorder-organizer-navigation')"
                    @click.stop
                  >
                    {{ $globals.icons.arrowUpDown }}
                  </v-icon>
                  <v-icon size="small">
                    {{ option.icon }}
                  </v-icon>
                </div>
              </template>
              <template #append>
                <v-checkbox-btn
                  v-model="preferences[option.preferenceKey]"
                  color="primary"
                  @click.stop
                />
              </template>
            </v-list-item>
          </VueDraggable>
        </v-list>
      </v-menu>
    </div>

    <v-divider />

    <v-list
      v-if="!collapsed && visibleSections.length"
      nav
      density="compact"
      class="app-organizer-sidebar__list"
    >
      <template
        v-for="section in visibleSections"
        :key="section.key"
      >
        <v-list-subheader class="app-organizer-sidebar__section-title">
          <v-icon
            class="me-2"
            size="small"
          >
            {{ section.icon }}
          </v-icon>
          <span class="text-truncate">{{ section.title }}</span>
          <v-spacer />
          <v-chip
            size="x-small"
            variant="tonal"
          >
            {{ section.links.length }}
          </v-chip>
        </v-list-subheader>

        <template
          v-for="nav in section.links"
          :key="section.key + '-' + (nav.key || nav.title)"
        >
          <v-list-group
            v-if="nav.children?.length"
            :key="section.key + '-' + (nav.key || nav.title) + '-group'"
            v-model="state.dropDowns[section.key + '-' + nav.title]"
            :prepend-icon="nav.icon"
            color="primary"
            fluid
          >
            <template #activator="{ props: hoverProps }">
              <v-list-item
                v-bind="hoverProps"
                :prepend-icon="nav.icon"
                :title="nav.title"
              />
            </template>

            <v-list-item
              v-for="child in nav.children"
              :key="section.key + '-' + (child.key || child.title)"
              exact
              :href="child.href"
              :rel="child.href ? 'noopener' : undefined"
              :target="child.href ? '_blank' : undefined"
              :to="child.href ? undefined : child.to"
              class="ms-2"
              :prepend-icon="child.icon"
              :title="child.title"
              @click="handleNavClick(child)"
            />
          </v-list-group>

          <v-list-item
            v-else
            :key="section.key + '-' + (nav.key || nav.title) + '-item'"
            exact
            link
            :href="nav.href"
            :rel="nav.href ? 'noopener' : undefined"
            :target="nav.href ? '_blank' : undefined"
            :to="nav.href ? undefined : nav.to"
            :prepend-icon="nav.icon"
            :title="nav.title"
            @click="handleNavClick(nav)"
          />
        </template>
      </template>
    </v-list>

    <div
      v-else-if="!collapsed"
      class="app-organizer-sidebar__empty"
    >
      <v-icon
        size="36"
        class="mb-2"
      >
        {{ $globals.icons.filter }}
      </v-icon>
      <div class="text-body-2 text-medium-emphasis">
        {{ $t("sidebar.no-organizer-navigation-items") }}
      </div>
    </div>
  </v-navigation-drawer>
</template>

<script setup lang="ts">
import { useLocalStorage } from "@vueuse/core";
import { VueDraggable } from "vue-draggable-plus";
import type { OrganizerSidebarSection, OrganizerSidebarSectionKey, SideBarLink } from "~/types/application-types";
import type { UserOrganizerSidebarPreferences } from "~/composables/use-users/preferences";

type OrganizerVisibilityPreferenceKey = "showCookbooks" | "showTranslatedBooks" | "showCategories" | "showTags";

interface OrganizerPreferenceOption {
  key: OrganizerSidebarSectionKey;
  icon: string;
  title: string;
  preferenceKey: OrganizerVisibilityPreferenceKey;
}

const DEFAULT_SECTION_ORDER: OrganizerSidebarSectionKey[] = ["cookbooks", "translatedBooks", "categories", "tags"];

const props = defineProps<{
  sections: OrganizerSidebarSection[];
}>();

const modelValue = defineModel<boolean>({ default: false });
const preferences = defineModel<UserOrganizerSidebarPreferences>("preferences", {
  default: () => ({
    showCookbooks: true,
    showTranslatedBooks: false,
    showCategories: true,
    showTags: true,
    sectionOrder: ["cookbooks", "translatedBooks", "categories", "tags"],
  }),
});

const { $globals } = useNuxtApp();
const i18n = useI18n();
const display = useDisplay();
const { isRtl } = useRtl();

const drawerLocation = computed(() => isRtl.value ? "right" : "left");
const showOrganizerDrawer = computed(() => display.mdAndUp.value && props.sections.length > 0);
const collapsed = useLocalStorage("organizer-sidebar-collapsed", false);
const drawerWidth = computed(() => collapsed.value ? 56 : 280);
const toggleCollapsedLabel = computed(() => {
  return collapsed.value
    ? i18n.t("sidebar.expand-organizer-navigation")
    : i18n.t("sidebar.collapse-organizer-navigation");
});

const state = reactive({
  dropDowns: {} as Record<string, boolean>,
});

const preferenceKeyBySection: Record<OrganizerSidebarSectionKey, OrganizerVisibilityPreferenceKey> = {
  cookbooks: "showCookbooks",
  translatedBooks: "showTranslatedBooks",
  categories: "showCategories",
  tags: "showTags",
};

const preferenceOptions = computed<OrganizerPreferenceOption[]>(() => [
  {
    key: "cookbooks",
    icon: $globals.icons.book,
    title: i18n.t("cookbook.cookbooks"),
    preferenceKey: "showCookbooks" as const,
  },
  {
    key: "translatedBooks",
    icon: $globals.icons.translate,
    title: i18n.t("cookbook.translated-books"),
    preferenceKey: "showTranslatedBooks" as const,
  },
  {
    key: "categories",
    icon: $globals.icons.categories,
    title: i18n.t("category.categories"),
    preferenceKey: "showCategories" as const,
  },
  {
    key: "tags",
    icon: $globals.icons.tags,
    title: i18n.t("tag.tags"),
    preferenceKey: "showTags" as const,
  },
]);

function normalizeSectionOrder(order?: OrganizerSidebarSectionKey[]) {
  const existingOrder = Array.isArray(order) ? order : [];
  const validKeys = new Set(DEFAULT_SECTION_ORDER);
  const normalized = existingOrder.filter((key): key is OrganizerSidebarSectionKey => validKeys.has(key));

  DEFAULT_SECTION_ORDER.forEach((key) => {
    if (!normalized.includes(key)) {
      normalized.push(key);
    }
  });

  return normalized;
}

function getOptionOrderIndex(key: OrganizerSidebarSectionKey) {
  const order = normalizeSectionOrder(preferences.value.sectionOrder);
  return order.indexOf(key);
}

const orderedPreferenceOptions = computed<OrganizerPreferenceOption[]>({
  get() {
    return [...preferenceOptions.value].sort((a, b) => getOptionOrderIndex(a.key) - getOptionOrderIndex(b.key));
  },
  set(options) {
    preferences.value.sectionOrder = options.map(option => option.key);
  },
});

const orderedSections = computed(() => {
  const order = normalizeSectionOrder(preferences.value.sectionOrder);
  return [...props.sections].sort((a, b) => order.indexOf(a.key) - order.indexOf(b.key));
});

const enabledSections = computed(() => {
  return orderedSections.value.filter(section => preferences.value[preferenceKeyBySection[section.key]]);
});

const visibleSections = computed(() => {
  return enabledSections.value.filter(section => section.links.length > 0);
});

function togglePreference(key: keyof UserOrganizerSidebarPreferences) {
  preferences.value[key] = !preferences.value[key];
}

function toggleCollapsed() {
  collapsed.value = !collapsed.value;
}

function handleNavClick(nav: SideBarLink) {
  nav.onClick?.();
}

watchEffect(() => {
  const normalizedOrder = normalizeSectionOrder(preferences.value.sectionOrder);
  if (JSON.stringify(preferences.value.sectionOrder) !== JSON.stringify(normalizedOrder)) {
    preferences.value.sectionOrder = normalizedOrder;
  }
});

watch(
  () => props.sections,
  (sections) => {
    const nextDropDowns: Record<string, boolean> = {};

    sections.forEach((section) => {
      section.links.forEach((link) => {
        if (link.children?.length) {
          const key = section.key + "-" + link.title;
          nextDropDowns[key] = state.dropDowns[key] ?? link.childrenStartExpanded ?? false;
        }
      });
    });

    state.dropDowns = nextDropDowns;
  },
  {
    deep: true,
    immediate: true,
  },
);
</script>

<style scoped>
.app-organizer-sidebar__header {
  align-items: center;
  display: flex;
  gap: 8px;
  justify-content: space-between;
  min-height: 56px;
  padding: 8px 12px;
}

.app-organizer-sidebar__list {
  max-height: calc(100vh - 112px);
  overflow-y: auto;
  padding-bottom: 12px;
}

.app-organizer-sidebar__section-title {
  align-items: center;
  display: flex;
  gap: 4px;
}

.organizer-sidebar-sort-handle {
  cursor: grab;
}

.organizer-sidebar-sort-handle:active {
  cursor: grabbing;
}

.organizer-sidebar-sort-ghost {
  opacity: 0.55;
}

.app-organizer-sidebar__empty {
  align-items: center;
  display: flex;
  flex: 1;
  flex-direction: column;
  justify-content: center;
  padding: 24px;
  text-align: center;
}
</style>
