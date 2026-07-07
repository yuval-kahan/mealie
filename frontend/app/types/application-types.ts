export interface SideBarLink {
  key?: string;
  icon: string;
  to?: string;
  href?: string;
  title: string;
  children?: SideBarLink[];
  childrenStartExpanded?: boolean;
  onClick?: () => void;
  restricted: boolean;
}

export type SidebarLinks = Array<SideBarLink>;

export type OrganizerSidebarSectionKey = "cookbooks" | "translatedBooks" | "categories" | "tags";

export interface OrganizerSidebarSection {
  key: OrganizerSidebarSectionKey;
  icon: string;
  title: string;
  links: SidebarLinks;
}
