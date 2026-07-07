import { BaseAPI } from "../base/base-clients";
import type { UploadedBook, UploadedBookExtractRequest, UploadedBookTranslateRequest } from "~/lib/api/types/uploaded-book";

const prefix = "/api";

const routes = {
  uploadedBooks: `${prefix}/households/uploaded-books`,
  uploadedBook: (id: string) => `${prefix}/households/uploaded-books/${id}`,
  extractRecipes: (id: string) => `${prefix}/households/uploaded-books/${id}/extract-recipes`,
  translate: (id: string) => `${prefix}/households/uploaded-books/${id}/translate`,
  uploadedBookFile: (id: string) => `${prefix}/households/uploaded-books/${id}/file`,
};

export class UploadedBooksAPI extends BaseAPI {
  async getAll() {
    return await this.requests.get<UploadedBook[]>(routes.uploadedBooks);
  }

  async upload(file: File, name: string | null = null) {
    const formData = new FormData();
    formData.append("file", file);

    if (name?.trim()) {
      formData.append("name", name.trim());
    }

    return await this.requests.post<UploadedBook>(routes.uploadedBooks, formData);
  }

  async extractRecipes(id: string, payload: UploadedBookExtractRequest) {
    return await this.requests.post<UploadedBook, UploadedBookExtractRequest>(routes.extractRecipes(id), payload);
  }

  async translate(id: string, payload: UploadedBookTranslateRequest) {
    return await this.requests.post<UploadedBook, UploadedBookTranslateRequest>(routes.translate(id), payload);
  }

  async delete(id: string) {
    return await this.requests.delete<unknown>(routes.uploadedBook(id));
  }

  fileUrl(id: string) {
    return routes.uploadedBookFile(id);
  }
}
