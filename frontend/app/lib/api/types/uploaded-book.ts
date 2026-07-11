export interface UploadedBook {
  id: string;
  groupId: string;
  householdId: string;
  userId: string;
  name: string;
  fileName: string;
  originalFileName: string;
  extension: string;
  contentType?: string | null;
  size: number;
  bookMetadata?: {
    generated_by_ai?: boolean;
    series_id?: string;
    volume_number?: number;
    volume_count?: number;
    included_recipe_slugs?: string[];
    generation_config?: AICookbookGenerateRequest;
    classification?: UploadedBookClassification;
    [key: string]: unknown;
  };
  classificationStatus?: "not_started" | "processing" | "completed" | "failed" | string;
  classificationError?: string | null;
  classificationUpdatedAt?: string | null;
  isTranslatedBook: boolean;
  translatedFromBookId?: string | null;
  translatedBookId?: string | null;
  translationLanguage?: string | null;
  translationStatus: "not_started" | "processing" | "retrying" | "completed" | "partial_failed" | "failed" | "cancelled" | string;
  translationPagesPerChunk: number;
  translationPageStart?: number | null;
  translationPageEnd?: number | null;
  translationTotalChunks: number;
  translationCompletedChunks: number;
  translationFailedChunks: number;
  translationRetryCount: number;
  translationError?: string | null;
  translationChunkStatus?: string | null;
  translationStartedAt?: string | null;
  translationCompletedAt?: string | null;
  extractionStatus: "not_started" | "processing" | "retrying" | "completed" | "partial_failed" | "failed" | "cancelled" | string;
  extractionPagesPerChunk: number;
  extractionTranslateLanguage?: string | null;
  extractionPageStart?: number | null;
  extractionPageEnd?: number | null;
  extractionTotalChunks: number;
  extractionCompletedChunks: number;
  extractionFailedChunks: number;
  extractionRetryCount: number;
  extractionRecipesFound: number;
  extractionRecipesCreated: number;
  extractionError?: string | null;
  extractionChunkStatus?: string | null;
  extractionStartedAt?: string | null;
  extractionCompletedAt?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface UploadedBookExtractRequest {
  pagesPerChunk: number;
  translateLanguage?: string;
  pageStart?: number | null;
  pageEnd?: number | null;
  autoRecipeImages?: boolean;
  includeItemImages?: boolean;
  includeAiTips?: boolean;
  createShoppingLists?: boolean;
  organizeShoppingListsWithAi?: boolean;
}

export interface UploadedBookTranslateRequest {
  pagesPerChunk: number;
  targetLanguage: string;
  pageStart?: number | null;
  pageEnd?: number | null;
}

export interface UploadedBookRecipeSummary {
  id: string;
  slug: string;
  name: string;
  source?: string | null;
}

export interface UploadedBookRecipeDeleteResponse {
  deletedCount: number;
  remainingCount: number;
  skippedCount: number;
  deletedRecipeIds: string[];
}

export interface UploadedBookClassification {
  summary?: string;
  cuisines?: string[];
  difficulty?: string;
  book_type?: string;
  teaching_level?: string;
  author_or_chef?: string;
  restaurant?: string;
  michelin_related?: boolean;
  techniques?: string[];
  categories?: string[];
  tags?: string[];
  language?: string;
}

export interface AICookbookGenerateRequest {
  mode: "preset" | "prompt";
  preset?: string | null;
  prompt?: string | null;
  title?: string | null;
  maxRecipesPerVolume?: number;
  maxEstimatedPagesPerVolume?: number;
}
