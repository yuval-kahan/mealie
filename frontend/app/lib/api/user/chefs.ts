import { BaseAPI } from "../base/base-clients";
import { route } from "../base";
import type {
  Chef,
  ChefAIRequest,
  ChefBrowserPageRequest,
  ChefCreate,
  ChefUpdate,
} from "~/lib/api/types/chef";

const prefix = "/api/households/chefs";

export class ChefsAPI extends BaseAPI {
  async getAll(filters?: {
    search?: string;
    rank?: string;
    cuisine?: string;
    michelinOnly?: boolean;
  }) {
    const query = {
      ...(filters?.search ? { search: filters.search } : {}),
      ...(filters?.rank ? { rank: filters.rank } : {}),
      ...(filters?.cuisine ? { cuisine: filters.cuisine } : {}),
      ...(filters?.michelinOnly ? { michelin_only: true } : {}),
    };
    return await this.requests.get<Chef[]>(Object.keys(query).length ? route(prefix, query) : prefix);
  }

  async createOne(payload: ChefCreate) {
    return await this.requests.post<Chef, ChefCreate>(prefix, payload);
  }

  async createWithAI(payload: ChefAIRequest) {
    return await this.requests.post<Chef, ChefAIRequest>(`${prefix}/ai-create`, payload);
  }

  async createFromBrowserPage(payload: ChefBrowserPageRequest) {
    return await this.requests.post<Chef, ChefBrowserPageRequest>(`${prefix}/browser-page`, payload);
  }

  async updateOne(id: string, payload: ChefUpdate) {
    return await this.requests.put<Chef, ChefUpdate>(`${prefix}/${id}`, payload);
  }

  async deleteOne(id: string) {
    return await this.requests.delete<unknown>(`${prefix}/${id}`);
  }

  async uploadImage(id: string, image: File) {
    const formData = new FormData();
    formData.append("image", image);
    return await this.requests.post<Chef>(`${prefix}/${id}/image`, formData);
  }

  async saveImageUrl(id: string, url: string) {
    return await this.requests.post<Chef, { url: string }>(`${prefix}/${id}/image-url`, { url });
  }

  async findImage(id: string) {
    return await this.requests.post<Chef>(`${prefix}/${id}/image-auto`);
  }

  imageUrl(chef: Chef) {
    const version = chef.imageVersion ? `?v=${encodeURIComponent(chef.imageVersion)}` : "";
    return `${prefix}/${chef.id}/image${version}`;
  }
}
