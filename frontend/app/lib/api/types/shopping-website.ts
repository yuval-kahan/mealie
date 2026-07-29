export interface ShoppingWebsite {
  id: string;
  groupId: string;
  householdId: string;
  userId: string;
  name: string;
  url: string;
  pageFood?: string | null;
  offeredFoods: string[];
  isRecipeSite: boolean;
  isShoppingSite: boolean;
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
  isRecipeSite: boolean;
  isShoppingSite: boolean;
}

export type ShoppingWebsiteUpdate = ShoppingWebsiteCreate;

export interface ShoppingWebsiteAIRequest {
  url: string;
  isRecipeSite?: boolean | null;
  isShoppingSite?: boolean | null;
}

export interface ShoppingWebsiteDiscoveryRequest {
  prompt: string;
  limit: number;
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
