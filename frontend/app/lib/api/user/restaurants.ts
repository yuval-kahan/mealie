import { BaseAPI } from "../base/base-clients";
import { route } from "../base";
import type {
  Restaurant,
  RestaurantAIRequest,
  RestaurantBrowserPageRequest,
  RestaurantCreate,
  RestaurantDiscoveryRequest,
  RestaurantUpdate,
} from "~/lib/api/types/restaurant";

const prefix = "/api/households/restaurants";

export class RestaurantsAPI extends BaseAPI {
  async getAll(search?: string) {
    const query = search?.trim();
    return await this.requests.get<Restaurant[]>(query ? route(prefix, { search: query }) : prefix);
  }

  async createOne(payload: RestaurantCreate) {
    return await this.requests.post<Restaurant, RestaurantCreate>(prefix, payload);
  }

  async createWithAI(payload: RestaurantAIRequest) {
    return await this.requests.post<Restaurant, RestaurantAIRequest>(`${prefix}/ai-create`, payload);
  }

  async discoverWithAI(payload: RestaurantDiscoveryRequest) {
    return await this.requests.post<RestaurantCreate[], RestaurantDiscoveryRequest>(
      `${prefix}/ai-discover`,
      payload,
    );
  }

  async createFromBrowserPage(payload: RestaurantBrowserPageRequest) {
    return await this.requests.post<Restaurant, RestaurantBrowserPageRequest>(`${prefix}/browser-page`, payload);
  }

  async updateOne(id: string, payload: RestaurantUpdate) {
    return await this.requests.put<Restaurant, RestaurantUpdate>(`${prefix}/${id}`, payload);
  }

  async deleteOne(id: string) {
    return await this.requests.delete<unknown>(`${prefix}/${id}`);
  }
}
