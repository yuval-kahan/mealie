import { BaseAPI } from "../base/base-clients";
import type { AICookbookGenerateRequest, UploadedBook, UploadedBookExtractRequest, UploadedBookTranslateRequest } from "~/lib/api/types/uploaded-book";

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

  fileUrl(id: string) {
    return routes.uploadedBookFile(id);
  }
}
