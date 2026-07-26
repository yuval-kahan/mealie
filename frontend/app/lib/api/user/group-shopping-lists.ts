import { BaseCRUDAPI } from "../base/base-clients";
import type { ApiRequestInstance } from "~/lib/api/types/non-generated";
import type {
  ShoppingListAddRecipeParamsBulk,
  ShoppingListCreate,
  ShoppingListItemCreate,
  ShoppingListItemsCollectionOut,
  ShoppingListItemOut,
  ShoppingListItemUpdateBulk,
  ShoppingListMultiPurposeLabelUpdate,
  ShoppingListOut,
  ShoppingListUpdate,
} from "~/lib/api/types/household";

export interface ShoppingListItemImagesEnsureResponse {
  existing: number;
  created: number;
  failed: number;
}

export interface ShoppingListMergeRequest {
  sourceListIds: string[];
  name?: string | null;
}

export interface ShoppingListDeletePreview {
  recipeIds: string[];
  recipeNames: string[];
  websiteIds: string[];
  websiteNames: string[];
}

const prefix = "/api";

const routes = {
  shoppingLists: `${prefix}/households/shopping/lists`,
  shoppingListsMerge: `${prefix}/households/shopping/lists/merge`,
  shoppingListsId: (id: string) => `${prefix}/households/shopping/lists/${id}`,
  shoppingListIdOrganizeAi: (id: string) => `${prefix}/households/shopping/lists/${id}/organize-ai`,
  shoppingListIdAdjustQuantitiesAi: (id: string) => `${prefix}/households/shopping/lists/${id}/adjust-quantities-ai`,
  shoppingListIdItemImagesEnsure: (id: string) => `${prefix}/households/shopping/lists/${id}/item-images/ensure`,
  shoppingListIdAddRecipe: (id: string) => `${prefix}/households/shopping/lists/${id}/recipe`,
  shoppingListIdRemoveRecipe: (id: string, recipeId: string) => `${prefix}/households/shopping/lists/${id}/recipe/${recipeId}/delete`,
  shoppingListIdUpdateLabelSettings: (id: string) => `${prefix}/households/shopping/lists/${id}/label-settings`,

  shoppingListItems: `${prefix}/households/shopping/items`,
  shoppingListItemsCreateBulk: `${prefix}/households/shopping/items/create-bulk`,
  shoppingListItemsId: (id: string) => `${prefix}/households/shopping/items/${id}`,
};

export class ShoppingListsApi extends BaseCRUDAPI<ShoppingListCreate, ShoppingListOut, ShoppingListUpdate> {
  baseRoute = routes.shoppingLists;
  itemRoute = routes.shoppingListsId;

  async addRecipes(itemId: string, data: ShoppingListAddRecipeParamsBulk[]) {
    return await this.requests.post(routes.shoppingListIdAddRecipe(itemId), data);
  }

  async removeRecipe(itemId: string, recipeId: string, recipeDecrementQuantity = 1) {
    return await this.requests.post(routes.shoppingListIdRemoveRecipe(itemId, recipeId), { recipeDecrementQuantity });
  }

  async updateLabelSettings(itemId: string, listSettings: ShoppingListMultiPurposeLabelUpdate[]) {
    return await this.requests.put(routes.shoppingListIdUpdateLabelSettings(itemId), listSettings);
  }

  async merge(data: ShoppingListMergeRequest) {
    return await this.requests.post<ShoppingListOut>(routes.shoppingListsMerge, data);
  }

  async deleteMany(ids: string[]) {
    const query = new URLSearchParams();
    ids.forEach(id => query.append("ids", id));
    return await this.requests.delete<ShoppingListOut[]>(`${routes.shoppingLists}?${query.toString()}`);
  }

  async getDeletePreview(itemId: string) {
    return await this.requests.get<ShoppingListDeletePreview>(`${routes.shoppingListsId(itemId)}/delete-preview`);
  }

  async deleteWithLinks(itemId: string, recipeIds: string[], websiteIds: string[]) {
    const query = new URLSearchParams();
    recipeIds.forEach(id => query.append("delete_recipe_ids", id));
    websiteIds.forEach(id => query.append("delete_website_ids", id));
    const suffix = query.size ? `?${query.toString()}` : "";
    return await this.requests.delete<ShoppingListOut>(`${routes.shoppingListsId(itemId)}${suffix}`);
  }

  async organizeWithAi(itemId: string, includeAiTips = false, targetLanguage: string | null = null) {
    return await this.requests.post<ShoppingListOut>(routes.shoppingListIdOrganizeAi(itemId), {
      includeAiTips,
      targetLanguage,
    });
  }

  async adjustQuantitiesWithAi(itemId: string, request: string) {
    return await this.requests.post<ShoppingListOut>(routes.shoppingListIdAdjustQuantitiesAi(itemId), {
      request,
    });
  }

  async ensureItemImages(itemId: string) {
    return await this.requests.post<ShoppingListItemImagesEnsureResponse>(
      routes.shoppingListIdItemImagesEnsure(itemId),
      {},
      { suppressAlert: true },
    );
  }
}

export class ShoppingListItemsApi extends BaseCRUDAPI<
  ShoppingListItemCreate,
  ShoppingListItemOut,
  ShoppingListItemUpdateBulk
> {
  baseRoute = routes.shoppingListItems;
  itemRoute = routes.shoppingListItemsId;

  async updateOne(itemId: string | number, payload: ShoppingListItemUpdateBulk) {
    const response = await this.requests.put<ShoppingListItemsCollectionOut, ShoppingListItemUpdateBulk>(
      this.itemRoute(itemId),
      payload,
    );
    return {
      ...response,
      data: response.data?.updatedItems?.[0] || response.data?.createdItems?.[0] || null,
    };
  }

  async createMany(items: ShoppingListItemCreate[]) {
    return await this.requests.post(routes.shoppingListItemsCreateBulk, items);
  }

  async updateMany(items: ShoppingListItemOut[]) {
    return await this.requests.put(routes.shoppingListItems, items);
  }

  async deleteMany(items: ShoppingListItemOut[]) {
    let query = "?";

    items.forEach((item) => {
      query += `ids=${item.id}&`;
    });

    return await this.requests.delete(routes.shoppingListItems + query);
  }
}

export class ShoppingApi {
  public lists: ShoppingListsApi;
  public items: ShoppingListItemsApi;

  constructor(requests: ApiRequestInstance) {
    this.lists = new ShoppingListsApi(requests);
    this.items = new ShoppingListItemsApi(requests);
  }
}
