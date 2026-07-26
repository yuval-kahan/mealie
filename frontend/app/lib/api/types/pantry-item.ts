import type { RecipeSummary } from "~/lib/api/types/recipe";

export interface PantryItem {
  id: string;
  groupId: string;
  householdId: string;
  userId: string;
  name: string;
  quantity?: number | null;
  unit?: string | null;
  category?: string | null;
  note?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface PantryItemCreate {
  name: string;
  quantity?: number | null;
  unit?: string | null;
  category?: string | null;
  note?: string | null;
}

export type PantryItemUpdate = PantryItemCreate;

export interface PantryRecipeSuggestionRequest {
  useAi: boolean;
  availableText?: string | null;
  limit?: number;
}

export interface PantryRecipeSuggestion {
  recipe: RecipeSummary;
  matchedItems: string[];
  missingIngredients: string[];
  reason: string;
  score: number;
}

export interface PantryRecipeSuggestionResponse {
  items: PantryRecipeSuggestion[];
  availableItems: string[];
  recipeCount: number;
}
