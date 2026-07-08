export interface SideBarLinkAction {
  key?: string;
  icon: string;
  title: string;
  loading?: boolean;
  disabled?: boolean;
  onClick?: () => void | Promise<void>;
}

export interface SideBarLink {
  key?: string;
  icon: string;
  to?: string;
  href?: string;
  title: string;
  children?: SideBarLink[];
  childrenStartExpanded?: boolean;
  actions?: SideBarLinkAction[];
  onClick?: () => void;
  restricted: boolean;
}

export type SidebarLinks = Array<SideBarLink>;

export type OrganizerSidebarSectionKey = "shoppingLists" | "cookbooks" | "translatedBooks" | "categories" | "tags";

export interface OrganizerSidebarSection {
  key: OrganizerSidebarSectionKey;
  icon: string;
  title: string;
  links: SidebarLinks;
}
