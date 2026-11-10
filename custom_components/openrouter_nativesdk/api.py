"""Thin async client for the OpenRouter HTTP API."""
from __future__ import annotations

from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

BASE_URL = "https://openrouter.ai/api/v1"
TIMEOUT = aiohttp.ClientTimeout(total=120)


class OpenRouterAPIError(Exception):
    """OpenRouter request failed."""


class OpenRouterAuthError(OpenRouterAPIError):
    """OpenRouter rejected the API key."""


class OpenRouterAPI:
    """Call OpenRouter with Home Assistant's shared aiohttp session."""

    def __init__(self, hass: HomeAssistant, api_key: str) -> None:
        self._session = async_get_clientsession(hass)
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://www.home-assistant.io",
            "X-Title": "Home Assistant",
        }

    async def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            async with self._session.request(method, f"{BASE_URL}{path}", headers=self._headers, json=payload, timeout=TIMEOUT) as resp:
                try:
                    data = await resp.json(content_type=None)
                except ValueError:
                    data = {}
                if resp.status in (401, 403):
                    raise OpenRouterAuthError(_error_message(data, resp.status))
                if resp.status >= 400:
                    raise OpenRouterAPIError(_error_message(data, resp.status))
        except (aiohttp.ClientError, TimeoutError) as err:
            raise OpenRouterAPIError(f"Cannot reach OpenRouter: {err}") from err
        if isinstance(data, dict) and "error" in data:
            # Errors can arrive with a 200 status, for example mid-route failures.
            raise OpenRouterAPIError(_error_message(data, resp.status))
        return data if isinstance(data, dict) else {}

    async def async_validate_key(self) -> None:
        """Raise OpenRouterAuthError for a bad key; /models is public so it can't tell."""
        await self._request("GET", "/key")

    async def async_list_models(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/models")
        return [item for item in data.get("data") or [] if isinstance(item, dict)]

    async def async_chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/chat/completions", payload)


def _error_message(data: Any, status: int) -> str:
    error = data.get("error") if isinstance(data, dict) else None
    message = error.get("message") if isinstance(error, dict) else error
    return f"HTTP {status}: {message or 'request failed'}"
