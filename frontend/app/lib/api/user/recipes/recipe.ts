import { SSE } from "sse.js";
import type { SSEvent } from "sse.js";
import { BaseCRUDAPI } from "../../base/base-clients";
import { route } from "../../base";
import { CommentsApi } from "./recipe-comments";
import { RecipeShareApi } from "./recipe-share";
import type {
  Recipe,
  CreateRecipe,
  RecipeAsset,
  CreateRecipeByUrlBulk,
  ParsedIngredient,
  UpdateImageResponse,
  RecipeLastMade,
  RecipeSuggestionQuery,
  RecipeSuggestionResponse,
  RecipeAISearchRequest,
  RecipeAISearchResponse,
  RecipeTimelineEventIn,
  RecipeTimelineEventOut,
  RecipeTimelineEventUpdate,
} from "~/lib/api/types/recipe";
import type { SSEDataEventDone, SSEDataEventMessage } from "~/lib/api/types/response";
import type { ApiRequestInstance, PaginationData, RequestResponse } from "~/lib/api/types/non-generated";
import { SSEDataEventStatus } from "~/lib/api/types/non-generated";

export type Parser = "nlp" | "brute" | "openai";

export interface CreateAsset {
  name: string;
  icon: string;
  extension: string;
  file: File;
}

export interface CreateRecipeFromText {
  text: string;
  translateLanguage?: string | null;
  includeAiTips?: boolean;
  autoImage?: boolean;
  includeItemImages?: boolean;
}

export interface RecipeAIShoppingListRequest {
  includeAiTips?: boolean;
  organizeShoppingListWithAi?: boolean;
  includeItemImages?: boolean;
}

export interface ItemImagesEnsureResponse {
  existing: number;
  created: number;
  failed: number;
}

export interface RecipeAIShoppingListResponse {
  recipeSlug?: string;
  recipe_slug?: string;
  groupSlug?: string | null;
  group_slug?: string | null;
  shoppingListId?: string | null;
  shopping_list_id?: string | null;
  shoppingListName?: string | null;
  shopping_list_name?: string | null;
  shoppingListCreated?: boolean;
  shopping_list_created?: boolean;
  shoppingListOrganized?: boolean;
  shopping_list_organized?: boolean;
  shoppingListError?: string | null;
  shopping_list_error?: string | null;
}

const prefix = "/api";

const routes = {
  recipesCreate: `${prefix}/recipes/create`,
  recipesBase: `${prefix}/recipes`,
  recipesSuggestions: `${prefix}/recipes/suggestions`,
  recipesAISearch: `${prefix}/recipes/ai-search`,
  recipesTestScrapeUrl: `${prefix}/recipes/test-scrape-url`,
  recipesCreateUrl: `${prefix}/recipes/create/url/stream`,
  recipesCreateUrlBulk: `${prefix}/recipes/create/url/bulk`,
  recipesCreateUrlBulkAssets: `${prefix}/recipes/create/url/bulk/assets`,
  recipesCreateFromZip: `${prefix}/recipes/create/zip`,
  recipesCreateFromImage: `${prefix}/recipes/create/image`,
  recipesCreateFromText: `${prefix}/recipes/create/text`,
  recipesCreateFromHtmlOrJson: `${prefix}/recipes/create/html-or-json/stream`,
  recipesCategory: `${prefix}/recipes/category`,
  recipesParseIngredient: `${prefix}/parser/ingredient`,
  recipesParseIngredients: `${prefix}/parser/ingredients`,
  recipesTimelineEvent: `${prefix}/recipes/timeline/events`,

  recipesRecipeSlug: (recipe_slug: string) => `${prefix}/recipes/${recipe_slug}`,
  recipesRecipeSlugShoppingListAi: (recipe_slug: string) => `${prefix}/recipes/${recipe_slug}/shopping-list-ai`,
  recipesRecipeSlugShoppingListOpenOrCreate: (recipe_slug: string) => `${prefix}/recipes/${recipe_slug}/shopping-list/open-or-create`,
  recipesRecipeSlugImage: (recipe_slug: string) => `${prefix}/recipes/${recipe_slug}/image`,
  recipesRecipeSlugImageAi: (recipe_slug: string) => `${prefix}/recipes/${recipe_slug}/image/ai`,
  recipesRecipeSlugItemImagesEnsure: (recipe_slug: string) => `${prefix}/recipes/${recipe_slug}/item-images/ensure`,
  recipesRecipeSlugAssets: (recipe_slug: string) => `${prefix}/recipes/${recipe_slug}/assets`,

  recipesSlugComments: (slug: string) => `${prefix}/recipes/${slug}/comments`,
  recipesSlugCommentsId: (slug: string, id: number) => `${prefix}/recipes/${slug}/comments/${id}`,

  recipesSlugLastMade: (slug: string) => `${prefix}/recipes/${slug}/last-made`,
  recipesTimelineEventId: (id: string) => `${prefix}/recipes/timeline/events/${id}`,
  recipesTimelineEventIdImage: (id: string) => `${prefix}/recipes/timeline/events/${id}/image`,
};

export type RecipeSearchQuery = {
  search?: string;
  orderDirection?: "asc" | "desc";
  groupId?: string;

  queryFilter?: string;

  cookbook?: string;
  households?: string[];

  categories?: string[];
  requireAllCategories?: boolean;

  tags?: string[];
  requireAllTags?: boolean;

  tools?: string[];
  requireAllTools?: boolean;

  foods?: string[];
  requireAllFoods?: boolean;

  page?: number;
  perPage?: number;
  orderBy?: string;
  orderByNullPosition?: "first" | "last";

  _searchSeed?: string;
};

export class RecipeAPI extends BaseCRUDAPI<CreateRecipe, Recipe, Recipe> {
  baseRoute: string = routes.recipesBase;
  itemRoute = routes.recipesRecipeSlug;

  comments: CommentsApi;
  share: RecipeShareApi;

  constructor(requests: ApiRequestInstance) {
    super(requests);

    this.comments = new CommentsApi(requests);
    this.share = new RecipeShareApi(requests);
  }

  async search(rsq: RecipeSearchQuery) {
    return await this.requests.get<PaginationData<Recipe>>(route(routes.recipesBase, rsq));
  }

  async getAllByCategory(categories: string[]) {
    return await this.requests.get<Recipe[]>(routes.recipesCategory, {
      categories,
    });
  }

  async getSuggestions(q: RecipeSuggestionQuery, foods: string[] | null = null, tools: string[] | null = null) {
    return await this.requests.get<RecipeSuggestionResponse>(
      route(routes.recipesSuggestions, { ...q, foods, tools }),
    );
  }

  async aiSearch(payload: RecipeAISearchRequest) {
    return await this.requests.post<RecipeAISearchResponse>(routes.recipesAISearch, payload);
  }

  async createAsset(recipeSlug: string, payload: CreateAsset) {
    const formData = new FormData();
    formData.append("file", payload.file);
    formData.append("name", payload.name);
    formData.append("extension", payload.extension);
    formData.append("icon", payload.icon);

    return await this.requests.post<RecipeAsset>(routes.recipesRecipeSlugAssets(recipeSlug), formData);
  }

  updateImage(slug: string, fileObject: File) {
    const formData = new FormData();
    formData.append("image", fileObject);
    formData.append("extension", fileObject.name.split(".").pop() ?? "");

    return this.requests.put<UpdateImageResponse, FormData>(routes.recipesRecipeSlugImage(slug), formData);
  }

  updateImagebyURL(slug: string, url: string) {
    return this.requests.post<UpdateImageResponse>(routes.recipesRecipeSlugImage(slug), { url });
  }

  createAIImage(slug: string) {
    return this.requests.post<UpdateImageResponse>(routes.recipesRecipeSlugImageAi(slug), {});
  }

  deleteImage(slug: string) {
    return this.requests.delete<string>(routes.recipesRecipeSlugImage(slug));
  }

  async testCreateOneUrl(url: string, useOpenAI = false) {
    return await this.requests.post<Recipe | null>(routes.recipesTestScrapeUrl, { url, useOpenAI });
  }

  private streamRecipeCreate(streamRoute: string, payload: object, onProgress?: (message: string) => void): Promise<RequestResponse<string>> {
    return new Promise((resolve) => {
      const { token } = useMealieAuth();

      const sse = new SSE(streamRoute, {
        headers: {
          "Content-Type": "application/json",
          ...(token.value ? { Authorization: `Bearer ${token.value}` } : {}),
        },
        payload: JSON.stringify(payload),
        withCredentials: true,
        autoReconnect: false,
      });

      if (onProgress) {
        sse.addEventListener(SSEDataEventStatus.Progress, (e: SSEvent) => {
          const { message } = JSON.parse(e.data) as SSEDataEventMessage;
          onProgress(message);
        });
      }

      sse.addEventListener(SSEDataEventStatus.Done, (e: SSEvent) => {
        const { slug } = JSON.parse(e.data) as SSEDataEventDone;
        sse.close();
        resolve({ response: { status: 201, data: slug } as any, data: slug, error: null });
      });

      sse.addEventListener(SSEDataEventStatus.Error, (e: SSEvent) => {
        try {
          const { message } = JSON.parse(e.data) as SSEDataEventMessage;
          sse.close();
          resolve({ response: null, data: null, error: new Error(message) });
        }
        catch {
          // Not a backend error payload (e.g. XHR connection-close event); ignore
        }
      });

      sse.stream();
    });
  }

  async createOneByHtmlOrJson(
    data: string,
    includeTags: boolean,
    includeCategories: boolean,
    url: string | null = null,
    onProgress?: (message: string) => void,
  ): Promise<RequestResponse<string>> {
    return this.streamRecipeCreate(routes.recipesCreateFromHtmlOrJson, { data, includeTags, includeCategories, url }, onProgress);
  }

  async createOneByUrl(
    url: string,
    includeTags: boolean,
    includeCategories: boolean,
    onProgress?: (message: string) => void,
    useOpenAI = false,
  ): Promise<RequestResponse<string>> {
    return this.streamRecipeCreate(routes.recipesCreateUrl, { url, includeTags, includeCategories, useOpenAI }, onProgress);
  }

  async createManyByUrl(payload: CreateRecipeByUrlBulk, videos: (File | null)[] = []) {
    if (videos.some(Boolean)) {
      const formData = new FormData();
      formData.append("bulk", JSON.stringify(payload));
      videos.forEach((video, index) => {
        if (!video) {
          return;
        }
        formData.append("video_indexes", index.toString());
        formData.append("videos", video);
      });

      return await this.requests.post<string>(routes.recipesCreateUrlBulkAssets, formData);
    }

    return await this.requests.post<string>(routes.recipesCreateUrlBulk, payload);
  }

  async createOneFromImages(
    fileObjects: (Blob | File)[],
    translateLanguage: string | null = null,
    includeAiTips = true,
    includeItemImages = true,
    notes: string | null = null,
  ) {
    const formData = new FormData();

    fileObjects.forEach((file) => {
      formData.append("images", file);
    });
    if (notes?.trim()) {
      formData.append("notes", notes.trim());
    }

    let apiRoute = routes.recipesCreateFromImage;
    const query = new URLSearchParams();
    if (translateLanguage) {
      query.set("translateLanguage", translateLanguage);
    }
    query.set("includeAiTips", String(includeAiTips));
    query.set("includeItemImages", String(includeItemImages));
    const queryString = query.toString();
    if (queryString) {
      apiRoute = `${apiRoute}?${queryString}`;
    }

    return await this.requests.post<string>(apiRoute, formData);
  }

  async createOneFromText(payload: CreateRecipeFromText) {
    return await this.requests.post<string>(routes.recipesCreateFromText, payload, { suppressAlert: true });
  }

  async ensureItemImages(recipeSlug: string) {
    return await this.requests.post<ItemImagesEnsureResponse>(
      routes.recipesRecipeSlugItemImagesEnsure(recipeSlug),
      {},
      { suppressAlert: true },
    );
  }

  async createAIShoppingList(recipeSlug: string, payload: RecipeAIShoppingListRequest = {}) {
    return await this.requests.post<RecipeAIShoppingListResponse>(
      routes.recipesRecipeSlugShoppingListAi(recipeSlug),
      {
        includeAiTips: payload.includeAiTips !== false,
        organizeShoppingListWithAi: payload.organizeShoppingListWithAi !== false,
        includeItemImages: payload.includeItemImages !== false,
      },
      { suppressAlert: true },
    );
  }

  async openOrCreateShoppingList(recipeSlug: string) {
    return await this.requests.post<RecipeAIShoppingListResponse>(
      routes.recipesRecipeSlugShoppingListOpenOrCreate(recipeSlug),
      {},
      { suppressAlert: true },
    );
  }

  async parseIngredients(parser: Parser, ingredients: Array<string>) {
    parser = parser || "nlp";
    return await this.requests.post<ParsedIngredient[]>(routes.recipesParseIngredients, { parser, ingredients });
  }

  async parseIngredient(parser: Parser, ingredient: string) {
    parser = parser || "nlp";
    return await this.requests.post<ParsedIngredient>(routes.recipesParseIngredient, { parser, ingredient });
  }

  async updateMany(payload: Recipe[]) {
    return await this.requests.put<Recipe[]>(routes.recipesBase, payload);
  }

  async patchMany(payload: Recipe[]) {
    return await this.requests.patch<Recipe[]>(routes.recipesBase, payload);
  }

  async updateLastMade(recipeSlug: string, timestamp: string) {
    return await this.requests.patch<Recipe, RecipeLastMade>(routes.recipesSlugLastMade(recipeSlug), { timestamp });
  }

  async createTimelineEvent(payload: RecipeTimelineEventIn) {
    return await this.requests.post<RecipeTimelineEventOut>(routes.recipesTimelineEvent, payload);
  }

  async updateTimelineEvent(eventId: string, payload: RecipeTimelineEventUpdate) {
    return await this.requests.put<RecipeTimelineEventOut, RecipeTimelineEventUpdate>(
      routes.recipesTimelineEventId(eventId),
      payload,
    );
  }

  async deleteTimelineEvent(eventId: string) {
    return await this.requests.delete<RecipeTimelineEventOut>(routes.recipesTimelineEventId(eventId));
  }

  async getAllTimelineEvents(page = 1, perPage = -1, params = {} as any) {
    return await this.requests.get<PaginationData<RecipeTimelineEventOut>>(
      routes.recipesTimelineEvent, { page, perPage, ...params },
    );
  }

  async updateTimelineEventImage(eventId: string, fileObject: Blob | File, fileName: string) {
    const formData = new FormData();
    formData.append("image", fileObject);
    formData.append("extension", fileName.split(".").pop() ?? "");

    return await this.requests.put<UpdateImageResponse, FormData>(routes.recipesTimelineEventIdImage(eventId), formData);
  }
}
