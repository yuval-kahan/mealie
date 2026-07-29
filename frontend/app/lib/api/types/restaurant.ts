export type RestaurantRecommendationStatus
  = | "strongly_recommended"
    | "recommended"
    | "neutral"
    | "not_recommended"
    | "strongly_not_recommended";

export type RestaurantVisitStatus = "not_tried" | "tried";

export interface Restaurant {
  id: string;
  groupId: string;
  householdId: string;
  userId: string;
  name: string;
  websiteUrl?: string | null;
  cuisineTypes: string[];
  addresses: string[];
  phone?: string | null;
  priceRange?: string | null;
  description?: string | null;
  notes?: string | null;
  michelinInfo?: string | null;
  michelinStarCount: number;
  isMichelinListed: boolean;
  chefNames: string[];
  bookTitles: string[];
  chefIds: string[];
  uploadedBookIds: string[];
  googleRating?: number | null;
  googleReviewCount?: number | null;
  googleMapsUrl?: string | null;
  ourRating?: number | null;
  recommendationStatus: RestaurantRecommendationStatus;
  visitStatus: RestaurantVisitStatus;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface RestaurantCreate {
  name: string;
  websiteUrl?: string | null;
  cuisineTypes: string[];
  addresses: string[];
  phone?: string | null;
  priceRange?: string | null;
  description?: string | null;
  notes?: string | null;
  michelinInfo?: string | null;
  michelinStarCount: number;
  isMichelinListed: boolean;
  chefNames: string[];
  bookTitles: string[];
  chefIds: string[];
  uploadedBookIds: string[];
  googleRating?: number | null;
  googleReviewCount?: number | null;
  googleMapsUrl?: string | null;
  ourRating?: number | null;
  recommendationStatus: RestaurantRecommendationStatus;
  visitStatus: RestaurantVisitStatus;
}

export type RestaurantUpdate = RestaurantCreate;

export interface RestaurantAIRequest {
  prompt?: string | null;
  name?: string | null;
  url?: string | null;
}

export interface RestaurantDiscoveryRequest {
  prompt: string;
  limit: number;
}

export interface RestaurantBrowserPageRequest {
  url: string;
  pageTitle?: string | null;
  pageText: string;
}
