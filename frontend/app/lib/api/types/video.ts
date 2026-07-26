export type VideoQuality = "best" | "2160" | "1080" | "720" | "480";
export type VideoContainer = "mp4" | "mkv" | "webm";
export type VideoCodec = "auto" | "h264" | "h265" | "vp9" | "av1";
export type AudioQuality = "best" | "320" | "256" | "192" | "128" | "96";

export interface VideoDownloadSettings {
  id?: string | null;
  downloadByDefault: boolean;
  quality: VideoQuality;
  container: VideoContainer;
  codec: VideoCodec;
  audioOnly: boolean;
  audioQuality: AudioQuality;
  saveSubtitles: boolean;
  saveThumbnail: boolean;
  saveMetadata: boolean;
  fallbackToLowerQuality: boolean;
}

export interface VideoCreate {
  url: string;
  title?: string | null;
  description?: string | null;
  processWithAi: boolean;
  downloadVideo?: boolean | null;
  createRecipe: boolean;
  createShoppingList: boolean;
  organizeShoppingList: boolean;
  includeAiTips: boolean;
  includeMiseEnPlace: boolean;
  targetLanguage?: string | null;
}

export interface VideoBrowserPageRequest extends VideoCreate {
  pageTitle?: string | null;
}

export interface VideoUpdate {
  title: string;
  description?: string | null;
  creator?: string | null;
  categories: string[];
  tags: string[];
}

export interface VideoRecord {
  id: string;
  groupId: string;
  householdId: string;
  userId: string;
  title: string;
  url: string;
  description?: string | null;
  originalDescription?: string | null;
  platform?: string | null;
  creator?: string | null;
  durationSeconds?: number | null;
  publishedAt?: string | null;
  language?: string | null;
  thumbnailUrl?: string | null;
  thumbnailFileName?: string | null;
  categories: string[];
  tags: string[];
  processWithAi: boolean;
  downloadEnabled: boolean;
  createRecipe: boolean;
  createShoppingList: boolean;
  organizeShoppingList: boolean;
  includeAiTips: boolean;
  includeMiseEnPlace: boolean;
  targetLanguage?: string | null;
  processingStatus: string;
  processingProgress: number;
  processingError?: string | null;
  localFileName?: string | null;
  localFormat?: string | null;
  localResolution?: string | null;
  localFileSize?: number | null;
  recipeDetected: boolean;
  recipeIds: string[];
  recipeSlugs: string[];
  shoppingListIds: string[];
  createdAt?: string | null;
  updatedAt?: string | null;
  hasLocalMedia: boolean;
  hasLocalThumbnail: boolean;
}

export interface VideoDeletePreview {
  recipeIds: string[];
  recipeNames: string[];
  shoppingListIds: string[];
  shoppingListNames: string[];
}
