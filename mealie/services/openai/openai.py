import base64
import binascii
import inspect
import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from textwrap import dedent
from typing import Any, TypeVar
from urllib.parse import urlsplit, urlunsplit

import httpx
import openai
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from pydantic import BaseModel, field_validator

from mealie.core import exceptions, root_logger
from mealie.core.config import get_app_settings
from mealie.pkgs import img, safehttp
from mealie.repos.repository_factory import AllRepositories
from mealie.schema.group.ai_providers import AIProviderCreate, AIProviderOut
from mealie.schema.openai._base import OpenAIBase
from mealie.schema.openai.general import OpenAIText

from .._base_service import BaseService

T = TypeVar("T", bound=OpenAIBase)
logger = root_logger.get_logger(__name__)
GENERATED_IMAGE_MAX_BYTES = 12 * 1024 * 1024


class OpenAINotEnabledException(Exception):
    def __init__(self, message: str = "OpenAI not enabled"):
        self.message = message
        super().__init__(self.message)


class AIProviderValidationError(Exception):
    def __init__(self, message: str = "AI provider validation failed"):
        self.message = message
        super().__init__(self.message)


class OpenAIDataInjection(BaseModel):
    description: str
    value: str

    @field_validator("value", mode="before")
    def parse_value(cls, value):
        if not value:
            raise ValueError("Value cannot be empty")
        if isinstance(value, str):
            return value

        # convert Pydantic models to JSON
        if isinstance(value, BaseModel):
            return value.model_dump_json()

        # convert Pydantic types to their JSON schema definition
        if inspect.isclass(value) and issubclass(value, BaseModel):
            value = value.model_json_schema()

        # attempt to convert object to JSON
        try:
            return json.dumps(value, separators=(",", ":"))
        except TypeError:
            return value


class OpenAIAttachment(BaseModel, ABC):
    @abstractmethod
    def build_message(self) -> dict: ...


class OpenAIImageBase(OpenAIAttachment):
    @abstractmethod
    def get_image_url(self) -> str: ...

    def build_message(self) -> dict:
        return {
            "type": "image_url",
            "image_url": {"url": self.get_image_url()},
        }


class OpenAIImageExternal(OpenAIImageBase):
    url: str

    def get_image_url(self) -> str:
        return self.url


class OpenAILocalImage(OpenAIImageBase):
    filename: str
    path: Path

    def get_image_url(self) -> str:
        image = img.PillowMinifier.to_jpg(
            self.path, dest=self.path.parent.joinpath(f"{self.filename}-min-original.jpg")
        )
        with open(image, "rb") as f:
            b64content = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/jpeg;base64,{b64content}"


class OpenAILocalAudio(OpenAIAttachment):
    data: str
    format: str

    def build_message(self) -> dict:
        return {
            "type": "input_audio",
            "input_audio": {"data": self.data, "format": self.format},
        }


class OpenAIService(BaseService):
    PROMPTS_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "prompts"

    def __init__(self, repos: AllRepositories) -> None:
        self.repos = repos
        self.provider_settings = repos.group_ai_provider_settings.get_one(repos.group_id)

        # Load providers
        self.default_provider = (
            self.repos.group_ai_providers.get_one(self.provider_settings.default_provider_id)
            if self.provider_settings and self.provider_settings.default_provider_id
            else None
        )
        self.audio_provider = (
            self.repos.group_ai_providers.get_one(self.provider_settings.audio_provider_id)
            if self.provider_settings and self.provider_settings.audio_provider_id
            else None
        )
        self.image_provider = (
            self.repos.group_ai_providers.get_one(self.provider_settings.image_provider_id)
            if self.provider_settings and self.provider_settings.image_provider_id
            else None
        )

        # Build client
        settings = get_app_settings()
        self.custom_prompt_dir = settings.OPENAI_CUSTOM_PROMPT_DIR

        super().__init__()

    def get_client(self, provider: AIProviderOut) -> AsyncOpenAI:
        api_key = self._first_api_key(provider.api_key) if self._is_gemini_provider_data(provider) else provider.api_key
        return AsyncOpenAI(
            base_url=provider.base_url or None,
            api_key=api_key,
            timeout=provider.timeout,
            default_headers=provider.request_headers or None,
            default_query=provider.request_params or None,
        )

    @staticmethod
    async def _close_client(client: AsyncOpenAI) -> None:
        close_result = client.close()
        if inspect.isawaitable(close_result):
            await close_result

    @staticmethod
    def _is_anthropic_provider_data(provider: AIProviderCreate | AIProviderOut) -> bool:
        base_url = (provider.base_url or "").lower()
        return "anthropic.com" in base_url or provider.model.startswith("claude-")

    @staticmethod
    def _is_gemini_provider_data(provider: AIProviderCreate | AIProviderOut) -> bool:
        base_url = (provider.base_url or "").lower()
        return "generativelanguage.googleapis.com" in base_url or provider.model.startswith("gemini-")

    @staticmethod
    def _split_api_keys(api_key: str) -> list[str]:
        keys = [key.strip() for key in api_key.replace(",", "\n").splitlines() if key.strip()]
        return list(dict.fromkeys(keys))

    @classmethod
    def _first_api_key(cls, api_key: str) -> str:
        return cls._split_api_keys(api_key)[0] if api_key else ""

    @staticmethod
    def _append_api_path(base_url: str, path: str) -> str:
        base_url = base_url.rstrip("/")
        if base_url.endswith(f"/{path}"):
            return base_url
        if base_url.endswith("/v1") or base_url.endswith("/v1beta"):
            return f"{base_url}/{path}"
        return f"{base_url}/v1/{path}"

    @staticmethod
    def _gemini_models_url(provider: AIProviderCreate | AIProviderOut) -> str:
        base_url = (provider.base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        if "generativelanguage.googleapis.com" not in base_url:
            base_url = "https://generativelanguage.googleapis.com/v1beta"

        # The app uses Google's OpenAI-compatible URL for generation, while the no-cost key check uses
        # Gemini's native models.list endpoint.
        split = urlsplit(base_url)
        path = split.path.rstrip("/")
        if path.endswith("/openai"):
            path = path[: -len("/openai")]
        if not path.endswith("/v1") and not path.endswith("/v1beta"):
            path = "/v1beta"
        return urlunsplit((split.scheme, split.netloc, f"{path}/models", "", ""))

    @staticmethod
    def _provider_error_message(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict):
            error = payload.get("error") or payload.get("detail")
            if isinstance(error, dict):
                return str(error.get("message") or error.get("detail") or error)
            if isinstance(error, str):
                return error
            message = payload.get("message")
            if isinstance(message, str):
                return message

        return response.text[:500] if response.text else response.reason_phrase

    @staticmethod
    def _redact_secret(message: str, secret: str) -> str:
        if not secret:
            return message
        return message.replace(secret, "[redacted]")

    @classmethod
    async def validate_provider_access(cls, provider: AIProviderCreate | AIProviderOut) -> None:
        """Validate provider credentials without creating a model completion."""

        if not provider.api_key:
            raise AIProviderValidationError("API key cannot be empty")

        timeout = min(provider.timeout or 30, 30)
        request_headers = provider.request_headers or {}
        request_params = provider.request_params or {}
        api_keys = cls._split_api_keys(provider.api_key)

        if cls._is_anthropic_provider_data(provider):
            base_url = provider.base_url or "https://api.anthropic.com/v1"
            url = cls._append_api_path(base_url, "models")
            headers = {
                "x-api-key": provider.api_key,
                "anthropic-version": "2023-06-01",
                **request_headers,
            }
            params = request_params or None
        elif cls._is_gemini_provider_data(provider):
            url = cls._gemini_models_url(provider)
            headers = request_headers
            params = {**request_params, "pageSize": "1"}
        else:
            base_url = provider.base_url or "https://api.openai.com/v1"
            url = cls._append_api_path(base_url, "models")
            headers = {"Authorization": f"Bearer {provider.api_key}", **request_headers}
            params = request_params or None

        if not api_keys:
            raise AIProviderValidationError("API key cannot be empty")

        if not cls._is_gemini_provider_data(provider) and len(api_keys) > 1:
            raise AIProviderValidationError("Only Google Gemini supports multiple API keys")

        async with httpx.AsyncClient(timeout=timeout) as client:
            for index, api_key in enumerate(api_keys, start=1):
                validation_headers = dict(headers)
                if cls._is_anthropic_provider_data(provider):
                    validation_headers["x-api-key"] = api_key
                elif cls._is_gemini_provider_data(provider):
                    validation_headers["x-goog-api-key"] = api_key
                else:
                    validation_headers["Authorization"] = f"Bearer {api_key}"

                try:
                    response = await client.get(url, headers=validation_headers, params=params)
                except httpx.TimeoutException as e:
                    raise AIProviderValidationError("Timed out while validating the AI provider API key") from e
                except httpx.RequestError as e:
                    raise AIProviderValidationError(f"Could not reach AI provider: {e}") from e

                key_label = f"API key #{index}" if len(api_keys) > 1 else "API key"

                if response.status_code in {401, 403}:
                    provider_message = cls._provider_error_message(response)
                    provider_message = cls._redact_secret(provider_message, api_key)
                    raise AIProviderValidationError(
                        f"Invalid {key_label} or missing access: {provider_message}",
                    )

                if response.status_code >= 400:
                    provider_message = cls._provider_error_message(response)
                    provider_message = cls._redact_secret(provider_message, api_key)
                    raise AIProviderValidationError(f"{key_label} validation failed: {provider_message}")

    def _get_provider(self, attachments: list[OpenAIAttachment] | None = None) -> AIProviderOut:
        """Select the appropriate provider based on attachment types, falling back to the default."""
        has_image = any(isinstance(a, OpenAIImageBase) for a in (attachments or []))
        has_audio = any(isinstance(a, OpenAILocalAudio) for a in (attachments or []))

        if has_image and has_audio:
            raise ValueError("Cannot process both images and audio in one request")

        if has_image:
            provider = self.image_provider or self.default_provider
            if not provider:
                raise OpenAINotEnabledException("No image provider set")
            return provider

        if has_audio:
            if not self.audio_provider:
                raise OpenAINotEnabledException("No audio provider set")
            return self.audio_provider

        else:
            if not self.default_provider:
                raise OpenAINotEnabledException("No default provider set")
            return self.default_provider

    def _get_prompt_file_candidates(self, name: str) -> list[Path]:
        """
        Returns a list of prompt file path candidates.
        First optional entry is the users custom prompt file, if configured and existing,
        second one (or only one) is the systems default prompt file
        """
        tree = name.split(".")
        relative_path = Path(*tree[:-1], tree[-1] + ".txt")

        default_prompt_file = (self.PROMPTS_DIR / relative_path).resolve()
        if not default_prompt_file.is_relative_to(self.PROMPTS_DIR.resolve()):
            raise ValueError(f"Invalid prompt name '{name}': resolves outside prompts directory")

        try:
            # Only include custom files if the custom_dir is configured, is a directory, and the prompt file exists
            custom_dir = Path(self.custom_prompt_dir).resolve() if self.custom_prompt_dir else None
            if custom_dir and not custom_dir.is_dir():
                custom_dir = None
        except Exception:
            custom_dir = None

        if custom_dir:
            custom_prompt_file = (custom_dir / relative_path).resolve()
            if not custom_prompt_file.is_relative_to(custom_dir):
                logger.warning(f"Custom prompt file resolves outside custom dir, skipping: {custom_prompt_file}")
            elif custom_prompt_file.exists():
                logger.debug(f"Found valid custom prompt file: {custom_prompt_file}")
                return [custom_prompt_file, default_prompt_file]
            else:
                logger.debug(f"Custom prompt file doesn't exist: {custom_prompt_file}")
        else:
            logger.debug(f"Custom prompt dir doesn't exist: {custom_dir}")

        # Otherwise, only return the default internal prompt file
        return [default_prompt_file]

    def _load_prompt_from_file(self, name: str) -> str:
        """Attempts to load custom prompt, otherwise falling back to the default"""
        prompt_file_candidates = self._get_prompt_file_candidates(name)
        content = None
        last_error = None
        for prompt_file in prompt_file_candidates:
            try:
                logger.debug(f"Trying to load prompt file: {prompt_file}")
                with open(prompt_file) as f:
                    content = f.read()
                    if content:
                        logger.debug(f"Successfully read prompt from {prompt_file}")
                        break
            except OSError as e:
                last_error = e

        if not content:
            if last_error:
                raise OSError(f"Unable to load prompt {name}") from last_error
            else:
                # This handles the case where the list was empty (no existing candidates found)
                attempted_paths = ", ".join(map(str, prompt_file_candidates))
                raise OSError(f"Unable to load prompt '{name}'. No valid content found in files: {attempted_paths}")

        return content

    def get_prompt(self, name: str, data_injections: list[OpenAIDataInjection] | None = None) -> str:
        """
        Load stored prompt and inject data into it.

        Access prompts with dot notation.
        For example, to access `prompts/recipes/parse-recipe-ingredients.txt`, use
        `recipes.parse-recipe-ingredients`
        """

        if not name:
            raise ValueError("Prompt name cannot be empty")

        content = self._load_prompt_from_file(name)

        if not data_injections:
            return content

        content_parts = [content]
        for data_injection in data_injections:
            content_parts.append(
                dedent(
                    f"""
                    ###
                    {data_injection.description}
                    ---

                    {data_injection.value}
                    """
                )
            )
        return "\n".join(content_parts)

    async def _get_raw_response(
        self, prompt: str, content: list[dict], response_schema: type[T], provider: AIProviderOut
    ) -> ChatCompletion:
        client = self.get_client(provider)
        try:
            return await client.chat.completions.parse(
                messages=[
                    {
                        "role": "system",
                        "content": prompt,
                    },
                    {
                        "role": "user",
                        "content": content,
                    },
                ],
                model=provider.model,
                response_format=response_schema,
            )
        finally:
            await self._close_client(client)

    def _is_anthropic_provider(self, provider: AIProviderOut) -> bool:
        return self._is_anthropic_provider_data(provider)

    def _get_anthropic_messages_url(self, provider: AIProviderOut) -> str:
        base_url = (provider.base_url or "https://api.anthropic.com/v1").rstrip("/")
        if base_url.endswith("/v1"):
            return f"{base_url}/messages"
        return f"{base_url}/v1/messages"

    async def _get_anthropic_response(
        self, prompt: str, content: list[dict], response_schema: type[T], provider: AIProviderOut
    ) -> T | None:
        text_parts: list[str] = []
        for item in content:
            if item.get("type") != "text":
                raise ValueError("Direct Anthropic providers currently support text-only AI requests")
            text_parts.append(item.get("text", ""))

        tool_name = "return_structured_data"
        payload = {
            "model": provider.model,
            "max_tokens": 8192,
            "system": prompt,
            "messages": [{"role": "user", "content": "\n\n".join(text_parts)}],
            "tools": [
                {
                    "name": tool_name,
                    "description": "Return the structured data requested by the schema.",
                    "input_schema": response_schema.model_json_schema(),
                }
            ],
            "tool_choice": {"type": "tool", "name": tool_name},
        }

        headers = {
            "x-api-key": provider.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            **(provider.request_headers or {}),
        }

        async with httpx.AsyncClient(timeout=provider.timeout) as client:
            response = await client.post(
                self._get_anthropic_messages_url(provider),
                headers=headers,
                params=provider.request_params or None,
                json=payload,
            )

        if response.status_code == 429:
            raise exceptions.RateLimitError(response.text)
        response.raise_for_status()

        response_data = response.json()
        for item in response_data.get("content", []):
            if item.get("type") == "tool_use" and item.get("name") == tool_name:
                tool_input: Any = item.get("input")
                if tool_input:
                    return response_schema.model_validate(tool_input)

        text_response = "\n".join(
            item.get("text", "") for item in response_data.get("content", []) if item.get("type") == "text"
        )
        if not text_response:
            return None

        return response_schema.parse_openai_response(text_response)

    async def get_response(
        self,
        prompt: str,
        message: str,
        *,
        response_schema: type[T],
        attachments: list[OpenAIAttachment] | None = None,
        provider: AIProviderOut | None = None,
    ) -> T | None:
        """Send data to OpenAI and return the response message content"""

        try:
            provider = provider or self._get_provider(attachments)
            user_messages: list[dict] = [{"type": "text", "text": message}]
            for attachment in attachments or []:
                user_messages.append(attachment.build_message())

            if self._is_anthropic_provider(provider):
                return await self._get_anthropic_response(prompt, user_messages, response_schema, provider)

            response = await self._get_raw_response(prompt, user_messages, response_schema, provider)
            if not response.choices:
                return None

            response_text = response.choices[0].message.content
            return response_schema.parse_openai_response(response_text)
        except openai.RateLimitError as e:
            raise exceptions.RateLimitError(str(e)) from e
        except Exception as e:
            raise Exception(f"OpenAI Request Failed. {e.__class__.__name__}: {e}") from e

    async def generate_image(self, prompt: str) -> bytes:
        """Generate one bounded image using the explicitly configured image provider."""

        if not self.image_provider:
            raise OpenAINotEnabledException("No image provider set")

        normalized_prompt = " ".join(prompt.split()).strip()
        if not normalized_prompt:
            raise ValueError("Image prompt cannot be empty")

        client = self.get_client(self.image_provider)
        try:
            response = await client.images.generate(
                model=self.image_provider.model,
                prompt=normalized_prompt[:8000],
                n=1,
                response_format="b64_json",
            )
        except openai.RateLimitError as e:
            raise exceptions.RateLimitError(str(e)) from e
        except Exception as e:
            raise Exception(f"Image generation failed. {e.__class__.__name__}: {e}") from e
        finally:
            await self._close_client(client)

        if not response.data:
            raise ValueError("The image provider returned no image")

        generated = response.data[0]
        encoded = generated.b64_json
        if encoded:
            max_encoded_length = ((GENERATED_IMAGE_MAX_BYTES + 2) // 3) * 4
            if len(encoded) > max_encoded_length:
                raise ValueError("Generated image exceeds the size limit")
            try:
                content = base64.b64decode(encoded, validate=True)
            except (binascii.Error, ValueError) as e:
                raise ValueError("The image provider returned invalid image data") from e
        elif generated.url:
            limits = httpx.Limits(max_connections=2, max_keepalive_connections=1)
            async with httpx.AsyncClient(
                transport=safehttp.AsyncSafeTransport(impersonate="chrome"),
                timeout=30.0,
                follow_redirects=True,
                limits=limits,
            ) as download_client:
                async with download_client.stream("GET", generated.url) as download_response:
                    download_response.raise_for_status()
                    chunks: list[bytes] = []
                    total = 0
                    async for chunk in download_response.aiter_bytes():
                        total += len(chunk)
                        if total > GENERATED_IMAGE_MAX_BYTES:
                            raise ValueError("Generated image exceeds the size limit")
                        chunks.append(chunk)
                    content = b"".join(chunks)
        else:
            raise ValueError("The image provider returned no usable image data")

        if not content or len(content) > GENERATED_IMAGE_MAX_BYTES:
            raise ValueError("Generated image is empty or exceeds the size limit")
        return content

    async def transcribe_audio(self, audio_file_path: Path) -> str | None:
        if not self.audio_provider:
            raise OpenAINotEnabledException("No audio provider set")

        client = self.get_client(self.audio_provider)

        # Create a transcription from the audio
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcript = await client.audio.transcriptions.create(
                    model=self.audio_provider.model,
                    file=audio_file,
                )
            return transcript.text
        except openai.RateLimitError as e:
            raise exceptions.RateLimitError(str(e)) from e
        except Exception as e:
            self.logger.warning(
                f"Failed to create audio transcription, falling back to chat completion ({e.__class__.__name__}: {e})"
            )
        finally:
            await self._close_client(client)

        # Fallback to chat completion
        path_obj = Path(audio_file_path)
        with open(path_obj, "rb") as audio_file:
            audio_data = base64.b64encode(audio_file.read()).decode("utf-8")

        file_ext = path_obj.suffix.lstrip(".").lower()
        audio_attachment = OpenAILocalAudio(data=audio_data, format=file_ext)
        response = await self.get_response(
            self.get_prompt("general.transcribe-audio"),
            "Attached is the audio data.",
            response_schema=OpenAIText,
            attachments=[audio_attachment],
        )

        return response.text if response else None
