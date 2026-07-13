import { BaseAPI } from "../base/base-clients";
import { route } from "../base";
import type {
  ShoppingWebsite,
  ShoppingWebsiteAIRequest,
  ShoppingWebsiteBrowserPageRequest,
  ShoppingWebsiteCreate,
  ShoppingWebsiteUpdate,
} from "~/lib/api/types/shopping-website";

const prefix = "/api/households/shopping-websites";

export class ShoppingWebsitesAPI extends BaseAPI {
  async getAll(search?: string) {
    const query = search?.trim();
    return await this.requests.get<ShoppingWebsite[]>(query ? route(prefix, { search: query }) : prefix);
  }

  async createOne(payload: ShoppingWebsiteCreate) {
    return await this.requests.post<ShoppingWebsite, ShoppingWebsiteCreate>(prefix, payload);
  }

  async createWithAI(payload: ShoppingWebsiteAIRequest) {
    return await this.requests.post<ShoppingWebsite, ShoppingWebsiteAIRequest>(`${prefix}/ai-create`, payload);
  }

  async createFromBrowserPage(payload: ShoppingWebsiteBrowserPageRequest) {
    return await this.requests.post<ShoppingWebsite, ShoppingWebsiteBrowserPageRequest>(`${prefix}/browser-page`, payload);
  }

  async updateOne(id: string, payload: ShoppingWebsiteUpdate) {
    return await this.requests.put<ShoppingWebsite, ShoppingWebsiteUpdate>(`${prefix}/${id}`, payload);
  }

  async deleteOne(id: string) {
    return await this.requests.delete<unknown>(`${prefix}/${id}`);
  }
}
