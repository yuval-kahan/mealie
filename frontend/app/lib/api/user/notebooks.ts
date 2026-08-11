import { BaseAPI } from "../base/base-clients";
import { route } from "../base";
import type {
  NotebookCreate,
  NotebookDetail,
  NotebookNode,
  NotebookNodeCreate,
  NotebookRevision,
  NotebookSearchResult,
  NotebookSummary,
  NotebookTOCRequest,
  NotebookTOCResponse,
} from "~/lib/api/types/notebook";

const prefix = "/api/households/notebooks";

export class NotebooksAPI extends BaseAPI {
  async getAll(search?: string) {
    return await this.requests.get<NotebookSummary[]>(route(prefix, { search }));
  }

  async getOne(id: string) {
    return await this.requests.get<NotebookDetail>(`${prefix}/${id}`);
  }

  async createOne(payload: NotebookCreate) {
    return await this.requests.post<NotebookDetail, NotebookCreate>(prefix, payload);
  }

  async updateOne(id: string, payload: Omit<NotebookCreate, "createStarterPage">) {
    return await this.requests.put<NotebookSummary, Omit<NotebookCreate, "createStarterPage">>(`${prefix}/${id}`, payload);
  }

  async deleteOne(id: string) {
    return await this.requests.delete<unknown>(`${prefix}/${id}`);
  }

  async createNode(notebookId: string, payload: NotebookNodeCreate) {
    return await this.requests.post<NotebookNode, NotebookNodeCreate>(`${prefix}/${notebookId}/nodes`, payload);
  }

  async updateNode(notebookId: string, nodeId: string, payload: Partial<NotebookNodeCreate> & { expectedVersion?: number }) {
    return await this.requests.put<NotebookNode, Partial<NotebookNodeCreate> & { expectedVersion?: number }>(
      `${prefix}/${notebookId}/nodes/${nodeId}`,
      payload,
    );
  }

  async moveNode(notebookId: string, nodeId: string, parentId: string | null, position: number) {
    return await this.requests.post<NotebookNode>(`${prefix}/${notebookId}/nodes/${nodeId}/move`, { parentId, position });
  }

  async deleteNode(notebookId: string, nodeId: string) {
    return await this.requests.delete<unknown>(`${prefix}/${notebookId}/nodes/${nodeId}`);
  }

  async search(query: string, notebookId?: string) {
    return await this.requests.get<NotebookSearchResult[]>(route(`${prefix}/search`, { query, notebookId }));
  }

  async generateToc(notebookId: string, payload: NotebookTOCRequest) {
    return await this.requests.post<NotebookTOCResponse, NotebookTOCRequest>(
      `${prefix}/${notebookId}/generate-toc`,
      payload,
    );
  }

  async revisions(notebookId: string, nodeId: string) {
    return await this.requests.get<NotebookRevision[]>(`${prefix}/${notebookId}/nodes/${nodeId}/revisions`);
  }

  async restoreRevision(notebookId: string, nodeId: string, revisionId: string) {
    return await this.requests.post<NotebookNode>(`${prefix}/${notebookId}/nodes/${nodeId}/revisions/${revisionId}/restore`);
  }
}
