export interface ShoppingWebsite {
  id: string;
  groupId: string;
  householdId: string;
  userId: string;
  name: string;
  url: string;
  pageFood?: string | null;
  offeredFoods: string[];
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface ShoppingWebsiteCreate {
  name: string;
  url: string;
  pageFood?: string | null;
  offeredFoods: string[];
}

export type ShoppingWebsiteUpdate = ShoppingWebsiteCreate;

export interface ShoppingWebsiteAIRequest {
  url: string;
}

export interface ShoppingWebsiteBrowserPageRequest extends ShoppingWebsiteAIRequest {
  pageTitle?: string | null;
  pageText: string;
}
