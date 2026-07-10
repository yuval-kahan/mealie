from fastapi import APIRouter, HTTPException, status
from pydantic import UUID4

from mealie.core.root_logger import get_logger
from mealie.routes._base import controller
from mealie.routes._base.base_controllers import BaseUserController
from mealie.routes._base.mixins import HttpRepo
from mealie.schema.group.ai_providers import (
    AIProviderCreate,
    AIProviderOut,
    AIProviderSettingsOut,
    AIProviderSettingsUpdate,
    AIProviderUpdate,
)
from mealie.schema.response import ErrorResponse
from mealie.schema.response.responses import SuccessResponse
from mealie.services.openai import AIProviderValidationError, OpenAIService

logger = get_logger()
settings_router = APIRouter(prefix="/groups/ai-providers/settings", tags=["Groups: AI Provider Settings"])
providers_router = APIRouter(prefix="/groups/ai-providers/providers", tags=["Groups: AI Providers"])


@controller(settings_router)
class GroupAIProviderSettingsController(BaseUserController):
    @settings_router.get("", response_model=AIProviderSettingsOut)
    def get_ai_provider_settings(self) -> AIProviderSettingsOut:
        self.checks.can_manage()

        self.repos.group_ai_providers.ensure_default_provider()
        return self.repos.group_ai_provider_settings.get_one(self.group_id)

    @settings_router.put("", response_model=AIProviderSettingsOut)
    def update_ai_provider_settings(self, settings: AIProviderSettingsUpdate) -> AIProviderSettingsOut:
        self.checks.can_manage()

        updated = self.repos.group_ai_provider_settings.update(self.group_id, settings)
        if not updated.default_provider_id:
            self.repos.group_ai_providers.ensure_default_provider()
            updated = self.repos.group_ai_provider_settings.get_one(self.group_id)
        return updated


@controller(providers_router)
class GroupAIProviderController(BaseUserController):
    @property
    def mixins(self):
        return HttpRepo[AIProviderCreate, AIProviderOut, AIProviderUpdate](self.repos.group_ai_providers, self.logger)

    async def _validate_provider_or_raise(self, data: AIProviderCreate | AIProviderUpdate) -> None:
        try:
            await OpenAIService.validate_provider_access(data)
        except AIProviderValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse.respond("AI provider API key validation failed", e.message),
            ) from e

    @providers_router.post("/validate")
    async def validate_ai_provider(self, data: AIProviderCreate):
        self.checks.can_manage()

        await self._validate_provider_or_raise(data)
        return SuccessResponse.respond("AI provider API key is valid")

    @providers_router.post("", response_model=AIProviderOut)
    async def create_ai_provider(self, data: AIProviderCreate) -> AIProviderOut:
        self.checks.can_manage()

        await self._validate_provider_or_raise(data)

        return self.mixins.create_one(data)

    @providers_router.get("/{provider_id}", response_model=AIProviderOut)
    def get_ai_provider(self, provider_id: UUID4) -> AIProviderOut:
        self.checks.can_manage()

        return self.mixins.get_one(provider_id)

    @providers_router.put("/{provider_id}", response_model=AIProviderOut)
    async def update_ai_provider(self, provider_id: UUID4, data: AIProviderUpdate) -> AIProviderOut:
        self.checks.can_manage()

        existing = self.repos.group_ai_providers.get_one(provider_id)
        validation_data = data.model_copy(update={"api_key": data.api_key or existing.api_key})
        await self._validate_provider_or_raise(validation_data)

        return self.mixins.update_one(data, provider_id)

    @providers_router.delete("/{provider_id}", response_model=AIProviderOut)
    def delete_ai_provider(self, provider_id: UUID4) -> AIProviderOut:
        self.checks.can_manage()

        return self.mixins.delete_one(provider_id)
