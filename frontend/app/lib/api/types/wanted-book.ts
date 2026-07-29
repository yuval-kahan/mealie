export interface WantedBook {
  id: string;
  groupId: string;
  householdId: string;
  userId: string;
  title: string;
  subtitle?: string | null;
  authors: string[];
  isbn10?: string | null;
  isbn13?: string | null;
  publisher?: string | null;
  publishedYear?: number | null;
  summary?: string | null;
  sourceUrl?: string | null;
  coverSourceUrl?: string | null;
  categories: string[];
  tags: string[];
  notes?: string | null;
  hasImage: boolean;
  imageVersion?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface WantedBookCreate {
  title: string;
  subtitle?: string | null;
  authors: string[];
  isbn10?: string | null;
  isbn13?: string | null;
  publisher?: string | null;
  publishedYear?: number | null;
  summary?: string | null;
  sourceUrl?: string | null;
  coverSourceUrl?: string | null;
  categories: string[];
  tags: string[];
  notes?: string | null;
}

export type WantedBookUpdate = WantedBookCreate;

export interface WantedBookAIRequest {
  prompt?: string | null;
  url?: string | null;
}

export interface WantedBookBrowserPageRequest extends WantedBookAIRequest {
  pageTitle?: string | null;
  pageText: string;
  pageImageUrl?: string | null;
}
