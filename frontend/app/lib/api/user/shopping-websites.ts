import { BaseAPI } from "../base/base-clients";
import { route } from "../base";
import type {
  ShoppingWebsite,
  ShoppingWebsiteAIRequest,
  ShoppingWebsiteBrowserPageRequest,
  ShoppingWebsiteCreate,
  ShoppingWebsiteDeletePreview,
  ShoppingWebsiteDiscoveryRequest,
  ShoppingWebsiteEntityLinksUpdate,
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

  async discoverWithAI(payload: ShoppingWebsiteDiscoveryRequest) {
    return await this.requests.post<ShoppingWebsiteCreate[], ShoppingWebsiteDiscoveryRequest>(
      `${prefix}/ai-discover`,
      payload,
    );
  }

  async createFromBrowserPage(payload: ShoppingWebsiteBrowserPageRequest) {
    return await this.requests.post<ShoppingWebsite, ShoppingWebsiteBrowserPageRequest>(`${prefix}/browser-page`, payload);
  }

  async updateOne(id: string, payload: ShoppingWebsiteUpdate) {
    return await this.requests.put<ShoppingWebsite, ShoppingWebsiteUpdate>(`${prefix}/${id}`, payload);
  }

  async uploadImage(id: string, image: File) {
    const formData = new FormData();
    formData.append("image", image);
    return await this.requests.post<ShoppingWebsite>(`${prefix}/${id}/image`, formData);
  }

  async saveImageUrl(id: string, url: string) {
    return await this.requests.post<ShoppingWebsite, { url: string }>(`${prefix}/${id}/image-url`, { url });
  }

  async findImage(id: string) {
    return await this.requests.post<ShoppingWebsite>(`${prefix}/${id}/image-auto`);
  }

  imageUrl(id: string, version?: string | null) {
    const query = version ? `?v=${encodeURIComponent(version)}` : "";
    return `${prefix}/${id}/image${query}`;
  }

  async updateRecipeLinks(recipeId: string, websiteIds: string[]) {
    return await this.requests.put<ShoppingWebsite[], ShoppingWebsiteEntityLinksUpdate>(
      `${prefix}/links/recipe/${recipeId}`,
      { websiteIds },
    );
  }

  async updateShoppingListLinks(shoppingListId: string, websiteIds: string[]) {
    return await this.requests.put<ShoppingWebsite[], ShoppingWebsiteEntityLinksUpdate>(
      `${prefix}/links/shopping-list/${shoppingListId}`,
      { websiteIds },
    );
  }

  async deletePreview(id: string) {
    return await this.requests.get<ShoppingWebsiteDeletePreview>(`${prefix}/${id}/delete-preview`);
  }

  async deleteOne(id: string, options?: { deleteRecipes?: boolean; deleteShoppingLists?: boolean }) {
    return await this.requests.delete<unknown>(route(`${prefix}/${id}`, {
      deleteRecipes: options?.deleteRecipes ?? false,
      deleteShoppingLists: options?.deleteShoppingLists ?? false,
    }));
  }
}
