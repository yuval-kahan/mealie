import { BaseAPI } from "../base/base-clients";
import { route } from "../base";
import type {
  PantryItem,
  PantryItemCreate,
  PantryItemUpdate,
  PantryRecipeSuggestionRequest,
  PantryRecipeSuggestionResponse,
} from "~/lib/api/types/pantry-item";

const prefix = "/api/households/pantry-items";

export class PantryItemsAPI extends BaseAPI {
  async getAll(search?: string) {
    const query = search?.trim();
    return await this.requests.get<PantryItem[]>(query ? route(prefix, { search: query }) : prefix);
  }

  async createOne(payload: PantryItemCreate) {
    return await this.requests.post<PantryItem, PantryItemCreate>(prefix, payload);
  }

  async updateOne(id: string, payload: PantryItemUpdate) {
    return await this.requests.put<PantryItem, PantryItemUpdate>(`${prefix}/${id}`, payload);
  }

  async deleteOne(id: string) {
    return await this.requests.delete<unknown>(`${prefix}/${id}`);
  }

  async suggestRecipes(payload: PantryRecipeSuggestionRequest) {
    return await this.requests.post<PantryRecipeSuggestionResponse, PantryRecipeSuggestionRequest>(
      `${prefix}/suggest-recipes`,
      payload,
    );
  }
}
