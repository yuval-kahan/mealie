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
}

export interface UploadedBookTranslateRequest {
  pagesPerChunk: number;
  targetLanguage: string;
  pageStart?: number | null;
  pageEnd?: number | null;
}
