import { BaseAPI } from "../base/base-clients";
import type { AIProviderCreate, AIProviderOut, AIProviderUpdate } from "~/lib/api/types/group";

const prefix = "/api/groups/ai-providers";

const routes = {
  providers: `${prefix}/providers`,
  validateProvider: `${prefix}/providers/validate`,
  providersId: (id: string) => `${prefix}/providers/${id}`,
};

export class AIProvidersAPI extends BaseAPI {
  async getOne(id: string) {
    return await this.requests.get<AIProviderOut>(routes.providersId(id));
  }

  async createOne(payload: AIProviderCreate) {
    return await this.requests.post<AIProviderOut>(routes.providers, payload);
  }

  async validateOne(payload: AIProviderCreate) {
    return await this.requests.post<{ message: string; error: boolean }>(routes.validateProvider, payload);
  }

  async updateOne(id: string, payload: AIProviderUpdate) {
    return await this.requests.put<AIProviderOut, AIProviderUpdate>(routes.providersId(id), payload);
  }

  async deleteOne(id: string) {
    return await this.requests.delete<AIProviderOut>(routes.providersId(id));
  }
}
