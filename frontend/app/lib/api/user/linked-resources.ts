import { BaseAPI } from "../base/base-clients";
import type { LinkedResourceEntityType, LinkedResources } from "~/lib/api/types/linked-resources";

const prefix = "/api/households/linked-resources";

export class LinkedResourcesAPI extends BaseAPI {
  async getOne(entityType: LinkedResourceEntityType, entityId: string) {
    return await this.requests.get<LinkedResources>(`${prefix}/${entityType}/${entityId}`);
  }
}
