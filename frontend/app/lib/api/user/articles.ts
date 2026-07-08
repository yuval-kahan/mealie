import { BaseAPI } from "../base/base-clients";
import { route } from "../base";
import type {
  Article,
  ArticleAIRequest,
  ArticleAISearchRequest,
  ArticleAISearchResponse,
  ArticleCreate,
  ArticleUpdate,
} from "~/lib/api/types/article";

const prefix = "/api/households/articles";

export interface ArticleSearchParams {
  search?: string | null;
  categories?: string[];
  tags?: string[];
}

const routes = {
  articles: prefix,
  article: (id: string) => `${prefix}/${id}`,
  aiCreate: `${prefix}/ai-create`,
  aiSearch: `${prefix}/ai-search`,
};

export class ArticlesAPI extends BaseAPI {
  async getAll(params: ArticleSearchParams = {}) {
    return await this.requests.get<Article[]>(route(routes.articles, params));
  }

  async getOne(id: string) {
    return await this.requests.get<Article>(routes.article(id));
  }

  async createOne(payload: ArticleCreate) {
    return await this.requests.post<Article, ArticleCreate>(routes.articles, payload);
  }

  async createWithAI(payload: ArticleAIRequest) {
    return await this.requests.post<Article, ArticleAIRequest>(routes.aiCreate, payload);
  }

  async updateOne(id: string, payload: ArticleUpdate) {
    return await this.requests.put<Article, ArticleUpdate>(routes.article(id), payload);
  }

  async deleteOne(id: string) {
    return await this.requests.delete<unknown>(routes.article(id));
  }

  async searchWithAI(payload: ArticleAISearchRequest) {
    return await this.requests.post<ArticleAISearchResponse, ArticleAISearchRequest>(routes.aiSearch, payload);
  }
}
