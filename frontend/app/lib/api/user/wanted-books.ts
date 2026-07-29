import { BaseAPI } from "../base/base-clients";
import { route } from "../base";
import type {
  WantedBook,
  WantedBookAIRequest,
  WantedBookBrowserPageRequest,
  WantedBookCreate,
  WantedBookUpdate,
} from "~/lib/api/types/wanted-book";

const prefix = "/api/households/wanted-books";

export class WantedBooksAPI extends BaseAPI {
  async getAll(search?: string) {
    const query = search?.trim();
    return await this.requests.get<WantedBook[]>(query ? route(prefix, { search: query }) : prefix);
  }

  async createOne(payload: WantedBookCreate) {
    return await this.requests.post<WantedBook, WantedBookCreate>(prefix, payload);
  }

  async createWithAI(payload: WantedBookAIRequest) {
    return await this.requests.post<WantedBook, WantedBookAIRequest>(`${prefix}/ai-create`, payload);
  }

  async createFromBrowserPage(payload: WantedBookBrowserPageRequest) {
    return await this.requests.post<WantedBook, WantedBookBrowserPageRequest>(`${prefix}/browser-page`, payload);
  }

  async updateOne(id: string, payload: WantedBookUpdate) {
    return await this.requests.put<WantedBook, WantedBookUpdate>(`${prefix}/${id}`, payload);
  }

  async deleteOne(id: string) {
    return await this.requests.delete<unknown>(`${prefix}/${id}`);
  }

  async uploadImage(id: string, image: File) {
    const formData = new FormData();
    formData.append("image", image);
    return await this.requests.post<WantedBook>(`${prefix}/${id}/image`, formData);
  }

  async saveImageUrl(id: string, url: string) {
    return await this.requests.post<WantedBook, { url: string }>(`${prefix}/${id}/image-url`, { url });
  }

  async findImage(id: string) {
    return await this.requests.post<WantedBook>(`${prefix}/${id}/image-auto`);
  }

  imageUrl(book: WantedBook) {
    const version = book.imageVersion ? `?v=${encodeURIComponent(book.imageVersion)}` : "";
    return `${prefix}/${book.id}/image${version}`;
  }
}
