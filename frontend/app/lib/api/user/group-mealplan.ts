import { BaseCRUDAPI } from "../base/base-clients";
import type {
  AIMealSuggestRequest,
  AIMealSuggestResponse,
  CreatePlanEntry,
  CreateRandomEntry,
  ReadPlanEntry,
  UpdatePlanEntry,
} from "~/lib/api/types/meal-plan";

const prefix = "/api";

const routes = {
  mealplan: `${prefix}/households/mealplans`,
  random: `${prefix}/households/mealplans/random`,
  aiSuggest: `${prefix}/households/mealplans/ai-suggest`,
  mealplanId: (id: string | number) => `${prefix}/households/mealplans/${id}`,
};

export class MealPlanAPI extends BaseCRUDAPI<CreatePlanEntry, ReadPlanEntry, UpdatePlanEntry> {
  baseRoute = routes.mealplan;
  itemRoute = routes.mealplanId;

  async setRandom(payload: CreateRandomEntry) {
    return await this.requests.post<ReadPlanEntry>(routes.random, payload);
  }

  async suggestWithAI(payload: AIMealSuggestRequest) {
    return await this.requests.post<AIMealSuggestResponse>(routes.aiSuggest, payload);
  }
}
