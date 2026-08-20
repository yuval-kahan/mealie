export interface UploadedBook {
  id: string;
  groupId: string;
  householdId: string;
  userId: string;
  categoryId?: string | null;
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
    recipe_catalog_candidates?: UploadedBookRecipeCandidate[];
    generation_config?: AICookbookGenerateRequest;
    classification?: UploadedBookClassification;
    translation_audit?: UploadedBookTranslationAudit;
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

export interface UploadedBookCategory {
  id: string;
  groupId: string;
  householdId: string;
  name: string;
  parentCategoryId?: string | null;
  position: number;
  isSystem: boolean;
  isProtected: boolean;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface UploadedBookTranslationAudit {
  version?: number;
  source_pages: number;
  translated_pages: number;
  verified_translated_pages?: number;
  missing_pages?: number[];
  unexpected_pages?: number[];
  suspicious_pages?: string[];
  suspicious_page_numbers?: number[];
  partial?: boolean;
  passed?: boolean;
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
  allowDuplicateRecipes?: boolean;
}

export interface UploadedBookRecipeCatalogRequest {
  query?: string;
  targetLanguage?: string;
  refresh?: boolean;
  internetOnly?: boolean;
}

export interface UploadedBookRecipeCandidate {
  id: string;
  title: string;
  sourceTitle: string;
  chapter?: string | null;
  source?: "book" | "internet";
  sourceUrl?: string | null;
  pageStart?: number | null;
  pageEnd?: number | null;
  reason?: string | null;
  importedRecipeSlug?: string | null;
}

export interface UploadedBookRecipeCatalog {
  bookId: string;
  query: string;
  source: "contents" | "headings" | "full_text" | "hybrid" | "internet";
  candidates: UploadedBookRecipeCandidate[];
  generatedAt?: string | null;
  usedAi: boolean;
  warning?: string | null;
}

export interface UploadedBookRecipeCatalogImportRequest {
  candidateIds: string[];
  targetLanguage?: string;
  autoRecipeImages?: boolean;
  includeItemImages?: boolean;
  includeAiTips?: boolean;
  createShoppingLists?: boolean;
  organizeShoppingListsWithAi?: boolean;
  allowDuplicateRecipes?: boolean;
}

export interface UploadedBookTranslateRequest {
  pagesPerChunk: number;
  targetLanguage: string;
  pageStart?: number | null;
  pageEnd?: number | null;
  includeLinkedRecipes?: boolean;
  extractRecipes?: boolean;
  autoRecipeImages?: boolean;
  includeItemImages?: boolean;
  includeAiTips?: boolean;
  createShoppingLists?: boolean;
  organizeShoppingListsWithAi?: boolean;
}

export interface UploadedBookManualTranslationPageRequest {
  page: number;
  text: string;
}

export interface UploadedBookRecipeSummary {
  id: string;
  slug: string;
  name: string;
  source?: string | null;
}

export interface UploadedBookRecipeSource {
  id: string;
  name: string;
  updatedRecipes: number;
  bookExists: boolean;
}

export interface UploadedBookRecipeDeleteResponse {
  deletedCount: number;
  deletedShoppingListCount: number;
  remainingCount: number;
  skippedCount: number;
  deletedRecipeIds: string[];
  deletedShoppingListIds: string[];
}

export interface UploadedBookRecipeDeleteRequest {
  recipeIds: string[];
  sourceName?: string | null;
  deleteAll?: boolean;
  deleteRecipes: boolean;
  deleteShoppingLists: boolean;
}

export interface UploadedBookDeletePreview {
  recipeIds: string[];
  recipeNames: string[];
  shoppingListIds: string[];
  shoppingListNames: string[];
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

export interface UploadedBookReaderPreferences {
  fontSize: number;
  fontFamily: "serif" | "sans-serif" | "dyslexic";
  lineHeight: number;
  wordSpacing: number;
  pageWidth: number;
}

export interface UploadedBookReaderNote {
  id: string;
  title?: string;
  text: string;
  page: number;
  pageIndex: number;
  chapterId?: string | null;
  createdAt?: string | null;
}

export interface UploadedBookReaderHighlight {
  id: string;
  text: string;
  page: number;
  pageIndex: number;
  chapterId?: string | null;
  start: number;
  end: number;
  createdAt?: string | null;
}

export interface UploadedBookReadingStateUpdate {
  currentPage: number;
  currentPageIndex: number;
  currentChapterId?: string | null;
  scrollOffset: number;
  readingPercent: number;
  completedChapters: string[];
  totalChapters: number;
  notes: UploadedBookReaderNote[];
  highlights: UploadedBookReaderHighlight[];
  preferences: UploadedBookReaderPreferences;
}

export interface UploadedBookReadingState extends UploadedBookReadingStateUpdate {
  id: string;
  bookId: string;
  userId: string;
  updatedAt?: string | null;
}
