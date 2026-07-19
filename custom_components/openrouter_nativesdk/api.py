"""Async boundary around the official OpenRouter Python SDK."""
from __future__ import annotations
import base64
from typing import Any
from homeassistant.core import HomeAssistant

class OpenRouterAPIError(Exception):
    """OpenRouter request failed."""

class OpenRouterAPI:
    """Run the synchronous generated SDK without blocking Home Assistant."""
    def __init__(self, hass: HomeAssistant, api_key: str) -> None:
        self.hass = hass
        self.api_key = api_key

    def _client(self):
        from openrouter import OpenRouter
        return OpenRouter(api_key=self.api_key)

    async def _run(self, operation, *args, **kwargs):
        def call():
            try:
                with self._client() as client:
                    return operation(client, *args, **kwargs)
            except Exception as err:
                raise OpenRouterAPIError(str(err)) from err
        return await self.hass.async_add_executor_job(call)

    async def async_list_models(self) -> list[dict[str, Any]]:
        response = await self._run(lambda c: c.models.list())
        return _items(response)

    async def async_list_presets(self) -> list[dict[str, Any]]:
        response = await self._run(lambda c: c.presets.list())
        return _items(response)

    async def async_get_preset(self, slug: str) -> dict[str, Any]:
        response = await self._run(lambda c: c.presets.get(slug=slug))
        data = getattr(response, "data", response)
        return data.model_dump() if hasattr(data, "model_dump") else data

    async def async_chat(self, **kwargs):
        return await self._run(lambda c: c.chat.send(**kwargs))

    async def async_transcribe(self, audio: bytes, audio_format: str, **kwargs):
        payload = {"data": base64.b64encode(audio).decode(), "format": audio_format}
        return await self._run(lambda c: c.stt.create_transcription(input_audio=payload, **kwargs))

    async def async_speech(self, **kwargs) -> tuple[bytes, str]:
        """Generate speech and read the response before closing the SDK client."""
        def read_response(response):
            return response.content, response.headers.get("content-type", "audio/mpeg")
        return await self._run(lambda c: read_response(c.tts.create_speech(**kwargs)))

    async def async_generate_image(self, **kwargs):
        return await self._run(lambda c: c.images.generate(**kwargs))

def _items(response: Any) -> list[dict[str, Any]]:
    value = response.get("data", response) if isinstance(response, dict) else getattr(response, "data", response)
    return [item if isinstance(item, dict) else item.__dict__ for item in value or []]
