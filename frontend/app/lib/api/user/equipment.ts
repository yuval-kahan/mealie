import { BaseAPI } from "../base/base-clients";
import { route } from "../base";
import type {
  Equipment,
  EquipmentAICreateRequest,
  EquipmentCreate,
  EquipmentUpdate,
} from "~/lib/api/types/equipment";

const prefix = "/api/households/equipment";

export class EquipmentAPI extends BaseAPI {
  async getAll(filters?: { search?: string; category?: string }) {
    const query = Object.fromEntries(
      Object.entries(filters || {}).filter(([, value]) => value !== undefined && value !== ""),
    );
    return await this.requests.get<Equipment[]>(Object.keys(query).length ? route(prefix, query) : prefix);
  }

  async updateOne(id: string, payload: EquipmentUpdate) {
    return await this.requests.put<Equipment, EquipmentUpdate>(`${prefix}/${id}`, payload);
  }

  async createOne(payload: EquipmentCreate) {
    return await this.requests.post<Equipment, EquipmentCreate>(prefix, payload);
  }

  async createWithAI(payload: EquipmentAICreateRequest) {
    return await this.requests.post<Equipment, EquipmentAICreateRequest>(`${prefix}/ai-create`, payload);
  }

  async enrichWithAI(id: string) {
    return await this.requests.post<Equipment>(`${prefix}/${id}/enrich-ai`);
  }

  async enrichMissing(limit = 20) {
    return await this.requests.post<Equipment[]>(route(`${prefix}/enrich-missing`, { limit }));
  }

  async uploadImage(id: string, image: File) {
    const formData = new FormData();
    formData.append("image", image);
    return await this.requests.post<Equipment>(`${prefix}/${id}/image`, formData);
  }

  async saveImageUrl(id: string, url: string) {
    return await this.requests.post<Equipment, { url: string }>(`${prefix}/${id}/image-url`, { url });
  }

  async findImage(id: string) {
    return await this.requests.post<Equipment>(`${prefix}/${id}/image-auto`);
  }

  async deleteImage(id: string) {
    return await this.requests.delete<unknown>(`${prefix}/${id}/image`);
  }

  imageUrl(equipment: Equipment) {
    const imageName = equipment.imageName || equipment.name;
    const version = equipment.imageVersion ? `&v=${encodeURIComponent(equipment.imageVersion)}` : "";
    return `/api/media/item-images/${equipment.groupId}/tool/tiny-original.webp?name=${encodeURIComponent(imageName)}${version}`;
  }
}
