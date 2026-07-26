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
  recipeIds: string[];
  shoppingListIds: string[];
  hasImage: boolean;
  imageVersion?: string | null;
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

export interface ShoppingWebsiteEntityLinksUpdate {
  websiteIds: string[];
}

export interface ShoppingWebsiteDeletePreview {
  recipeIds: string[];
  recipeNames: string[];
  shoppingListIds: string[];
  shoppingListNames: string[];
}
