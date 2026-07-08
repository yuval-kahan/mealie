import { BaseCRUDAPI } from "../base/base-clients";
import { config } from "../config";
import type { CategoryBase, CategoryIn, RecipeCategoryResponse } from "~/lib/api/types/recipe";

const prefix = config.PREFIX + "/organizers";

const routes = {
  categories: `${prefix}/categories`,
  categoriesEmpty: `${prefix}/categories/empty`,
  categoriesId: (category: string) => `${prefix}/categories/${category}`,
  categoriesSlug: (category: string) => `${prefix}/categories/slug/${category}`,
};

export class CategoriesAPI extends BaseCRUDAPI<CategoryIn, RecipeCategoryResponse> {
  baseRoute: string = routes.categories;
  itemRoute = routes.categoriesId;

  async bySlug(slug: string) {
    return await this.requests.get<RecipeCategoryResponse>(routes.categoriesSlug(slug));
  }

  async getEmpty() {
    return await this.requests.get<CategoryBase[]>(routes.categoriesEmpty);
  }
}
