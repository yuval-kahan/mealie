import { BaseAPI } from "../base/base-clients";
import { route } from "../base";
import type {
  ProductKnowledge,
  ProductKnowledgeAIRequest,
  ProductKnowledgeCreate,
  ProductKnowledgeUpdate,
} from "~/lib/api/types/product-knowledge";

const prefix = "/api/households/product-knowledge";

export interface ProductKnowledgeSearchParams {
  search?: string | null;
  categories?: string[];
  tags?: string[];
}

export class ProductKnowledgeAPI extends BaseAPI {
  async getAll(params: ProductKnowledgeSearchParams = {}) {
    return await this.requests.get<ProductKnowledge[]>(route(prefix, params));
  }

  async getOne(id: string) {
    return await this.requests.get<ProductKnowledge>(`${prefix}/${id}`);
  }

  async createOne(payload: ProductKnowledgeCreate) {
    return await this.requests.post<ProductKnowledge, ProductKnowledgeCreate>(prefix, payload);
  }

  async createWithAI(payload: ProductKnowledgeAIRequest) {
    return await this.requests.post<ProductKnowledge, ProductKnowledgeAIRequest>(`${prefix}/ai-create`, payload);
  }

  async updateOne(id: string, payload: ProductKnowledgeUpdate) {
    return await this.requests.put<ProductKnowledge, ProductKnowledgeUpdate>(`${prefix}/${id}`, payload);
  }

  async deleteOne(id: string) {
    return await this.requests.delete<unknown>(`${prefix}/${id}`);
  }
}
