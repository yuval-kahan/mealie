import { BaseAPI } from "../base/base-clients";
import type {
  AICookbookGenerateRequest,
  UploadedBook,
  UploadedBookExtractRequest,
  UploadedBookDeletePreview,
  UploadedBookRecipeDeleteResponse,
  UploadedBookRecipeDeleteRequest,
  UploadedBookRecipeCatalog,
  UploadedBookRecipeCatalogImportRequest,
  UploadedBookRecipeCatalogRequest,
  UploadedBookRecipeSummary,
  UploadedBookReadingState,
  UploadedBookReadingStateUpdate,
  UploadedBookManualTranslationPageRequest,
  UploadedBookTranslateRequest,
} from "~/lib/api/types/uploaded-book";

const prefix = "/api";

const routes = {
  uploadedBooks: `${prefix}/households/uploaded-books`,
  uploadedBook: (id: string) => `${prefix}/households/uploaded-books/${id}`,
  extractRecipes: (id: string) => `${prefix}/households/uploaded-books/${id}/extract-recipes`,
  recipeCatalog: (id: string) => `${prefix}/households/uploaded-books/${id}/recipe-catalog`,
  importRecipeCatalog: (id: string) => `${prefix}/households/uploaded-books/${id}/recipe-catalog/import`,
  cancelExtraction: (id: string) => `${prefix}/households/uploaded-books/${id}/extract-recipes/cancel`,
  translate: (id: string) => `${prefix}/households/uploaded-books/${id}/translate`,
  manualTranslationPage: (id: string) => `${prefix}/households/uploaded-books/${id}/translate/manual-page`,
  cancelTranslation: (id: string) => `${prefix}/households/uploaded-books/${id}/translate/cancel`,
  classify: (id: string) => `${prefix}/households/uploaded-books/${id}/classify`,
  generate: `${prefix}/households/uploaded-books/generate`,
  refreshAi: (id: string) => `${prefix}/households/uploaded-books/${id}/refresh-ai`,
  aiRecipeMembership: (id: string, slug: string) => `${prefix}/households/uploaded-books/${id}/ai-recipes/${encodeURIComponent(slug)}`,
  uploadedBookFile: (id: string) => `${prefix}/households/uploaded-books/${id}/file`,
  uploadedBookCover: (id: string) => `${prefix}/households/uploaded-books/${id}/cover`,
  uploadedBookCoverUrl: (id: string) => `${prefix}/households/uploaded-books/${id}/cover-url`,
  uploadedBookCoverAuto: (id: string) => `${prefix}/households/uploaded-books/${id}/cover-auto`,
  openUploadedBook: (id: string) => `${prefix}/households/uploaded-books/${id}/open`,
  openUploadedBookSource: `${prefix}/households/uploaded-books/source/open`,
  uploadedBookRecipes: (id: string) => `${prefix}/households/uploaded-books/${id}/recipes`,
  deleteUploadedBookRecipes: (id: string) => `${prefix}/households/uploaded-books/${id}/recipes/delete`,
  readingStates: `${prefix}/households/uploaded-books/reading-states`,
  readingState: (id: string) => `${prefix}/households/uploaded-books/${id}/reading-state`,
};

export class UploadedBooksAPI extends BaseAPI {
  async getAll() {
    return await this.requests.get<UploadedBook[]>(routes.uploadedBooks);
  }

  async upload(file: File, name: string | null = null, classifyWithAi = true) {
    const formData = new FormData();
    formData.append("file", file);

    if (name?.trim()) {
      formData.append("name", name.trim());
    }
    formData.append("classify_with_ai", String(classifyWithAi));

    return await this.requests.post<UploadedBook>(routes.uploadedBooks, formData);
  }

  async extractRecipes(id: string, payload: UploadedBookExtractRequest) {
    return await this.requests.post<UploadedBook, UploadedBookExtractRequest>(routes.extractRecipes(id), payload);
  }

  async discoverRecipeCatalog(id: string, payload: UploadedBookRecipeCatalogRequest) {
    return await this.requests.post<UploadedBookRecipeCatalog, UploadedBookRecipeCatalogRequest>(
      routes.recipeCatalog(id),
      payload,
    );
  }

  async importRecipeCatalog(id: string, payload: UploadedBookRecipeCatalogImportRequest) {
    return await this.requests.post<UploadedBook, UploadedBookRecipeCatalogImportRequest>(
      routes.importRecipeCatalog(id),
      payload,
    );
  }

  async cancelExtraction(id: string) {
    return await this.requests.post<UploadedBook>(routes.cancelExtraction(id));
  }

  async translate(id: string, payload: UploadedBookTranslateRequest) {
    return await this.requests.post<UploadedBook, UploadedBookTranslateRequest>(routes.translate(id), payload);
  }

  async cancelTranslation(id: string) {
    return await this.requests.post<UploadedBook>(routes.cancelTranslation(id));
  }

  async saveManualTranslationPage(id: string, payload: UploadedBookManualTranslationPageRequest) {
    return await this.requests.post<UploadedBook, UploadedBookManualTranslationPageRequest>(
      routes.manualTranslationPage(id),
      payload,
    );
  }

  async classify(id: string) {
    return await this.requests.post<UploadedBook>(routes.classify(id));
  }

  async uploadCover(id: string, image: File) {
    const formData = new FormData();
    formData.append("image", image);
    return await this.requests.post<UploadedBook>(routes.uploadedBookCover(id), formData);
  }

  async saveCoverUrl(id: string, url: string) {
    return await this.requests.post<UploadedBook, { url: string }>(routes.uploadedBookCoverUrl(id), { url });
  }

  async findCover(id: string) {
    return await this.requests.post<UploadedBook>(routes.uploadedBookCoverAuto(id));
  }

  async generate(payload: AICookbookGenerateRequest) {
    return await this.requests.post<UploadedBook[], AICookbookGenerateRequest>(routes.generate, payload);
  }

  async refreshAi(id: string) {
    return await this.requests.post<UploadedBook[]>(routes.refreshAi(id));
  }

  async addRecipeToAiBook(id: string, slug: string) {
    return await this.requests.put<UploadedBook>(routes.aiRecipeMembership(id, slug), {});
  }

  async removeRecipeFromAiBook(id: string, slug: string) {
    return await this.requests.delete<UploadedBook>(routes.aiRecipeMembership(id, slug));
  }

  async deletePreview(id: string) {
    return await this.requests.get<UploadedBookDeletePreview>(`${routes.uploadedBook(id)}/delete-preview`);
  }

  async delete(id: string, options?: { deleteRecipes?: boolean; deleteShoppingLists?: boolean }) {
    const query = new URLSearchParams({
      delete_recipes: String(options?.deleteRecipes ?? false),
      delete_shopping_lists: String(options?.deleteShoppingLists ?? false),
    });
    return await this.requests.delete<unknown>(`${routes.uploadedBook(id)}?${query.toString()}`);
  }

  async getRecipes(id: string) {
    return await this.requests.get<UploadedBookRecipeSummary[]>(routes.uploadedBookRecipes(id));
  }

  async getReadingStates() {
    return await this.requests.get<UploadedBookReadingState[]>(routes.readingStates);
  }

  async getReadingState(id: string) {
    return await this.requests.get<UploadedBookReadingState>(routes.readingState(id));
  }

  async updateReadingState(id: string, payload: UploadedBookReadingStateUpdate) {
    return await this.requests.put<UploadedBookReadingState, UploadedBookReadingStateUpdate>(
      routes.readingState(id),
      payload,
    );
  }

  async deleteRecipes(id: string, payload: UploadedBookRecipeDeleteRequest) {
    return await this.requests.post<UploadedBookRecipeDeleteResponse, UploadedBookRecipeDeleteRequest>(
      routes.deleteUploadedBookRecipes(id),
      payload,
    );
  }

  fileUrl(id: string) {
    return routes.uploadedBookFile(id);
  }

  coverUrl(id: string, version?: string | null) {
    const query = version ? `?v=${encodeURIComponent(version)}` : "";
    return `${routes.uploadedBookCover(id)}${query}`;
  }

  openUrl(id: string, page?: number | null) {
    const params = page && page > 0 ? `?page=${page}` : "";
    return `${routes.openUploadedBook(id)}${params}`;
  }

  openSourceUrl(source: string, page?: number | null) {
    const params = new URLSearchParams({ source });
    if (page && page > 0) {
      params.set("page", String(page));
    }
    return `${routes.openUploadedBookSource}?${params.toString()}`;
  }
}
