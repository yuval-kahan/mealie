export interface Article {
  id: string;
  groupId: string;
  householdId: string;
  userId: string;
  title: string;
  slug: string;
  summary?: string | null;
  content: string;
  source?: string | null;
  author?: string | null;
  categories: string[];
  tags: string[];
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface ArticleCreate {
  title: string;
  summary?: string | null;
  content: string;
  source?: string | null;
  author?: string | null;
  categories: string[];
  tags: string[];
}

export type ArticleUpdate = ArticleCreate;

export interface ArticleAIRequest {
  text?: string | null;
  url?: string | null;
  translateLanguage?: string | null;
}

export interface ArticleAISearchRequest {
  query: string;
  limit?: number;
}

export interface ArticleAISearchItem {
  id: string;
  score: number;
  reason: string;
}

export interface ArticleAISearchResponse {
  items: ArticleAISearchItem[];
}
