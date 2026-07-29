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

  async uploadImage(id: string, image: File) {
    const formData = new FormData();
    formData.append("image", image);
    return await this.requests.post<ProductKnowledge>(`${prefix}/${id}/image`, formData);
  }

  async saveImageUrl(id: string, url: string) {
    return await this.requests.post<ProductKnowledge, { url: string }>(`${prefix}/${id}/image-url`, { url });
  }

  async findImage(id: string) {
    return await this.requests.post<ProductKnowledge>(`${prefix}/${id}/image-auto`);
  }

  async deleteImage(id: string) {
    return await this.requests.delete<unknown>(`${prefix}/${id}/image`);
  }

  imageUrl(item: ProductKnowledge) {
    const version = item.imageVersion ? `?v=${encodeURIComponent(item.imageVersion)}` : "";
    return `${prefix}/${item.id}/image${version}`;
  }

  async deleteOne(id: string) {
    return await this.requests.delete<unknown>(`${prefix}/${id}`);
  }
}
