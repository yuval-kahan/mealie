import sqlalchemy as sa
from fastapi import HTTPException, status
from pydantic import UUID4

from mealie.db.models.group.ai_providers import AIProvider, AIProviderSettings
from mealie.schema.group.ai_providers import AIProviderCreate, AIProviderOut

from .repository_generic import GroupRepositoryGeneric


class GroupRepositoryAIProvider(GroupRepositoryGeneric[AIProviderOut, AIProvider]):
    @staticmethod
    def _split_api_keys(api_key: str) -> list[str]:
        keys = [key.strip() for key in api_key.replace(",", "\n").splitlines() if key.strip()]
        return list(dict.fromkeys(keys))

    @staticmethod
    def _is_gemini_provider_data(data: dict) -> bool:
        base_url = (data.get("base_url") or "").lower()
        model = (data.get("model") or "").lower()
        return "generativelanguage.googleapis.com" in base_url or model.startswith("gemini-")

    @classmethod
    def _normalize_api_key(cls, data: dict) -> None:
        api_key = data.get("api_key")
        if not api_key:
            return

        if cls._is_gemini_provider_data(data):
            data["api_key"] = "\n".join(cls._split_api_keys(api_key))
        else:
            data["api_key"] = api_key.strip()

    def create(self, data: AIProviderCreate | dict):
        if isinstance(data, AIProviderCreate):
            api_key = data.api_key
            data = data.model_dump()
            data["api_key"] = api_key

        self._normalize_api_key(data)

        if not data.get("api_key"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="API key cannot be empty")

        if not data.get("settings_id"):
            data["settings_id"] = self.session.execute(
                sa.select(AIProviderSettings.id).where(AIProviderSettings.group_id == self.group_id)
            ).scalar_one()

        return super().create(data)

    def update(self, match_value: str | int | UUID4, new_data: AIProviderCreate | dict):
        if isinstance(new_data, AIProviderCreate):
            api_key = new_data.api_key
            new_data = new_data.model_dump()
            if api_key:
                new_data["api_key"] = api_key

        # Merge existing API key into new data
        if not new_data.get("api_key"):
            existing = self.get_one(match_value)
            if existing:
                new_data["api_key"] = existing.api_key

        self._normalize_api_key(new_data)

        return super().update(match_value, new_data)

    def delete(self, value, match_key: str | None = None) -> AIProviderOut:
        # Null out any settings references to this provider before deleting
        self.session.execute(
            sa.update(AIProviderSettings)
            .where(AIProviderSettings.default_provider_id == value)
            .values(default_provider_id=None)
        )
        self.session.execute(
            sa.update(AIProviderSettings)
            .where(AIProviderSettings.audio_provider_id == value)
            .values(audio_provider_id=None)
        )
        self.session.execute(
            sa.update(AIProviderSettings)
            .where(AIProviderSettings.image_provider_id == value)
            .values(image_provider_id=None)
        )

        # Delete
        return super().delete(value, match_key)

    def update_many(self, data):
        raise NotImplementedError
