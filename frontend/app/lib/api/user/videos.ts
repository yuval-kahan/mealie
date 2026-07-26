import { BaseAPI } from "../base/base-clients";
import { route } from "../base";
import type {
  VideoCreate,
  VideoDeletePreview,
  VideoDownloadSettings,
  VideoRecord,
  VideoUpdate,
} from "~/lib/api/types/video";

const prefix = "/api/households/videos";

export class VideosAPI extends BaseAPI {
  async getAll(search?: string) {
    const query = search?.trim();
    return await this.requests.get<VideoRecord[]>(query ? route(prefix, { search: query }) : prefix);
  }

  async getOne(id: string) {
    return await this.requests.get<VideoRecord>(`${prefix}/${id}`);
  }

  async createOne(payload: VideoCreate) {
    return await this.requests.post<VideoRecord, VideoCreate>(prefix, payload);
  }

  async updateOne(id: string, payload: VideoUpdate) {
    return await this.requests.put<VideoRecord, VideoUpdate>(`${prefix}/${id}`, payload);
  }

  async retry(id: string) {
    return await this.requests.post<VideoRecord, Record<string, never>>(`${prefix}/${id}/retry`, {});
  }

  async cancel(id: string) {
    return await this.requests.post<VideoRecord, Record<string, never>>(`${prefix}/${id}/cancel`, {});
  }

  async getSettings() {
    return await this.requests.get<VideoDownloadSettings>(`${prefix}/settings`);
  }

  async updateSettings(payload: VideoDownloadSettings) {
    return await this.requests.put<VideoDownloadSettings, VideoDownloadSettings>(`${prefix}/settings`, payload);
  }

  async deletePreview(id: string) {
    return await this.requests.get<VideoDeletePreview>(`${prefix}/${id}/delete-preview`);
  }

  async deleteOne(id: string, options?: { deleteRecipes?: boolean; deleteShoppingLists?: boolean }) {
    return await this.requests.delete<unknown>(route(`${prefix}/${id}`, {
      deleteRecipes: options?.deleteRecipes ?? false,
      deleteShoppingLists: options?.deleteShoppingLists ?? false,
    }));
  }

  mediaUrl(id: string) {
    return `${prefix}/${id}/media`;
  }

  thumbnailUrl(id: string) {
    return `${prefix}/${id}/thumbnail`;
  }
}
