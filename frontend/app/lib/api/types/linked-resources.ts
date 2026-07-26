export type LinkedResourceEntityType = "recipe" | "shopping-list" | "video" | "website";

export interface LinkedResourceItem {
  id: string;
  name: string;
  slug?: string | null;
  url?: string | null;
}

export interface LinkedResources {
  recipes: LinkedResourceItem[];
  shoppingLists: LinkedResourceItem[];
  videos: LinkedResourceItem[];
  websites: LinkedResourceItem[];
}
