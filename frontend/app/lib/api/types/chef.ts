export type ChefRank = "world_class" | "excellent" | "good" | "medium" | "emerging";

export interface ChefRelatedRestaurant {
  id: string;
  name: string;
  michelinStarCount: number;
}

export interface ChefRelatedBook {
  id: string;
  name: string;
  isTranslatedBook: boolean;
}

export interface ChefCreate {
  name: string;
  aliases: string[];
  rank: ChefRank;
  country?: string | null;
  cuisines: string[];
  specialties: string[];
  biography?: string | null;
  careerSummary?: string | null;
  awards: string[];
  notableRestaurants: string[];
  bookTitles: string[];
  websiteUrl?: string | null;
  wikipediaUrl?: string | null;
  instagramUrl?: string | null;
  hasMichelinRestaurant: boolean;
  michelinStarCount: number;
  michelinSummary?: string | null;
  notes?: string | null;
  restaurantIds: string[];
  uploadedBookIds: string[];
}

export interface Chef extends ChefCreate {
  id: string;
  groupId: string;
  householdId: string;
  userId: string;
  restaurants: ChefRelatedRestaurant[];
  uploadedBooks: ChefRelatedBook[];
  hasImage: boolean;
  imageVersion?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export type ChefUpdate = ChefCreate;

export interface ChefAIRequest {
  prompt?: string | null;
  name?: string | null;
  url?: string | null;
}

export interface ChefBrowserPageRequest extends ChefAIRequest {
  pageTitle?: string | null;
  pageText: string;
  pageImageUrl?: string | null;
}
