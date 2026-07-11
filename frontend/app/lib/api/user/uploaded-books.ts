import { BaseAPI } from "../base/base-clients";
import type {
  AICookbookGenerateRequest,
  UploadedBook,
  UploadedBookExtractRequest,
  UploadedBookRecipeDeleteResponse,
  UploadedBookRecipeSummary,
  UploadedBookTranslateRequest,
} from "~/lib/api/types/uploaded-book";

const prefix = "/api";

const routes = {
  uploadedBooks: `${prefix}/households/uploaded-books`,
  uploadedBook: (id: string) => `${prefix}/households/uploaded-books/${id}`,
  extractRecipes: (id: string) => `${prefix}/households/uploaded-books/${id}/extract-recipes`,
  cancelExtraction: (id: string) => `${prefix}/households/uploaded-books/${id}/extract-recipes/cancel`,
  translate: (id: string) => `${prefix}/households/uploaded-books/${id}/translate`,
  cancelTranslation: (id: string) => `${prefix}/households/uploaded-books/${id}/translate/cancel`,
  classify: (id: string) => `${prefix}/households/uploaded-books/${id}/classify`,
  generate: `${prefix}/households/uploaded-books/generate`,
  refreshAi: (id: string) => `${prefix}/households/uploaded-books/${id}/refresh-ai`,
  uploadedBookFile: (id: string) => `${prefix}/households/uploaded-books/${id}/file`,
  uploadedBookCover: (id: string) => `${prefix}/households/uploaded-books/${id}/cover`,
  openUploadedBook: (id: string) => `${prefix}/households/uploaded-books/${id}/open`,
  openUploadedBookSource: `${prefix}/households/uploaded-books/source/open`,
  uploadedBookRecipes: (id: string) => `${prefix}/households/uploaded-books/${id}/recipes`,
  deleteUploadedBookRecipes: (id: string) => `${prefix}/households/uploaded-books/${id}/recipes/delete`,
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

  async cancelExtraction(id: string) {
    return await this.requests.post<UploadedBook>(routes.cancelExtraction(id));
  }

  async translate(id: string, payload: UploadedBookTranslateRequest) {
    return await this.requests.post<UploadedBook, UploadedBookTranslateRequest>(routes.translate(id), payload);
  }

  async cancelTranslation(id: string) {
    return await this.requests.post<UploadedBook>(routes.cancelTranslation(id));
  }

  async classify(id: string) {
    return await this.requests.post<UploadedBook>(routes.classify(id));
  }

  async generate(payload: AICookbookGenerateRequest) {
    return await this.requests.post<UploadedBook[], AICookbookGenerateRequest>(routes.generate, payload);
  }

  async refreshAi(id: string) {
    return await this.requests.post<UploadedBook[]>(routes.refreshAi(id));
  }

  async delete(id: string) {
    return await this.requests.delete<unknown>(routes.uploadedBook(id));
  }

  async getRecipes(id: string) {
    return await this.requests.get<UploadedBookRecipeSummary[]>(routes.uploadedBookRecipes(id));
  }

  async deleteRecipes(id: string, recipeIds: string[]) {
    return await this.requests.post<UploadedBookRecipeDeleteResponse, { recipeIds: string[] }>(
      routes.deleteUploadedBookRecipes(id),
      { recipeIds },
    );
  }

  fileUrl(id: string) {
    return routes.uploadedBookFile(id);
  }

  coverUrl(id: string) {
    return routes.uploadedBookCover(id);
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
