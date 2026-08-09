export interface ProductKnowledge {
  id: string;
  groupId: string;
  householdId: string;
  userId: string;
  title: string;
  summary?: string | null;
  content: string;
  source?: string | null;
  imageSourceUrl?: string | null;
  hasImage: boolean;
  imageVersion?: string | null;
  categories: string[];
  tags: string[];
  qualityRating?: number | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface ProductKnowledgeCreate {
  title: string;
  summary?: string | null;
  content: string;
  source?: string | null;
  categories: string[];
  tags: string[];
  qualityRating?: number | null;
}

export type ProductKnowledgeUpdate = ProductKnowledgeCreate;

export interface ProductKnowledgeAIRequest {
  topic: string;
  targetLanguage?: string | null;
}
