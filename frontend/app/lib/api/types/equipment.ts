export interface EquipmentRecipeSummary {
  slug: string;
  name: string;
}

export interface Equipment {
  id: string;
  groupId: string;
  name: string;
  slug: string;
  category?: string | null;
  description?: string | null;
  imageSourceUrl?: string | null;
  aiEnriched: boolean;
  hasImage: boolean;
  imageVersion?: string | null;
  recipeCount: number;
  recipes: EquipmentRecipeSummary[];
}

export interface EquipmentUpdate {
  category?: string | null;
  description?: string | null;
}

export interface EquipmentCreate extends EquipmentUpdate {
  name: string;
}

export interface EquipmentAICreateRequest {
  prompt: string;
  name?: string | null;
}
