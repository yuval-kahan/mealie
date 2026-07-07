from fastapi import APIRouter, HTTPException, status
from pydantic import UUID4

from mealie.repos.repository_factory import AllRepositories
from mealie.routes._base import BaseAdminController, controller
from mealie.routes._base.mixins import HttpRepo
from mealie.schema.group.ai_providers import (
    AIProviderCreate,
    AIProviderOut,
    AIProviderUpdate,
)
from mealie.schema.response import ErrorResponse
from mealie.services.openai import AIProviderValidationError, OpenAIService

router = APIRouter(prefix="/groups/{group_id}/ai-providers")


@controller(router)
class AdminGroupAIProviderController(BaseAdminController):
    def _group_repos(self, group_id: UUID4) -> AllRepositories:
        """Return repos scoped to the target group."""
        return AllRepositories(self.session, group_id=group_id, household_id=None)

    def _mixins(self, group_id: UUID4) -> HttpRepo:
        return HttpRepo[AIProviderCreate, AIProviderOut, AIProviderUpdate](
            self._group_repos(group_id).group_ai_providers, self.logger
        )

    async def _validate_provider_or_raise(self, data: AIProviderCreate | AIProviderUpdate) -> None:
        try:
            await OpenAIService.validate_provider_access(data)
        except AIProviderValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("AI provider API key validation failed", e.message),
            ) from e

    # =======================================================================
    # Provider CRUD

    @router.post("/providers", response_model=AIProviderOut, tags=["Admin: AI Providers"])
    async def create_ai_provider(self, group_id: UUID4, data: AIProviderCreate):
        await self._validate_provider_or_raise(data)

        return self._mixins(group_id).create_one(data)

    @router.get("/providers/{provider_id}", response_model=AIProviderOut, tags=["Admin: AI Providers"])
    def get_ai_provider(self, group_id: UUID4, provider_id: UUID4):
        return self._mixins(group_id).get_one(provider_id)

    @router.put("/providers/{provider_id}", response_model=AIProviderOut, tags=["Admin: AI Providers"])
    async def update_ai_provider(self, group_id: UUID4, provider_id: UUID4, data: AIProviderUpdate):
        existing = self._group_repos(group_id).group_ai_providers.get_one(provider_id)
        validation_data = data.model_copy(update={"api_key": data.api_key or existing.api_key})
        await self._validate_provider_or_raise(validation_data)

        return self._mixins(group_id).update_one(data, provider_id)

    @router.delete("/providers/{provider_id}", response_model=AIProviderOut, tags=["Admin: AI Providers"])
    def delete_ai_provider(self, group_id: UUID4, provider_id: UUID4):
        return self._mixins(group_id).delete_one(provider_id)
