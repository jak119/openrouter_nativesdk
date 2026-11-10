"""Shared entity base for OpenRouter LLM platforms."""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import probatio
from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import CONF_MODEL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import llm
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.json import json_dumps

from .api import OpenRouterAPI
from .const import (
    CONF_ALLOWED_MODELS,
    CONF_COST_TIER,
    CONF_EXCLUDED_MODELS,
    CONF_WEB_SEARCH,
    DOMAIN,
)
from .routing import build_plugins, build_tools

MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024


class OpenRouterLLMEntity(Entity):
    """Common request building for conversation and AI task entities."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, entry: ConfigEntry, subentry: ConfigSubentry) -> None:
        self.entry = entry
        self.subentry = subentry
        self.client: OpenRouterAPI = entry.runtime_data
        self._attr_unique_id = subentry.subentry_id
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, subentry.subentry_id)},
            name=subentry.title,
            manufacturer="OpenRouter",
            model=subentry.data[CONF_MODEL],
            entry_type=dr.DeviceEntryType.SERVICE,
        )

    async def _async_build_payload(self, chat_log: conversation.ChatLog, **extra: Any) -> dict[str, Any]:
        options = self.subentry.data
        model = options[CONF_MODEL]
        payload: dict[str, Any] = {
            "model": model,
            "messages": await async_messages(self.hass, chat_log),
            "session_id": chat_log.conversation_id,
            **extra,
        }
        if plugins := build_plugins(model, options.get(CONF_COST_TIER), options.get(CONF_ALLOWED_MODELS), options.get(CONF_EXCLUDED_MODELS)):
            payload["plugins"] = plugins
        tools = build_tools(options.get(CONF_WEB_SEARCH, False))
        if chat_log.llm_api:
            tools.extend(_format_tool(tool, chat_log.llm_api.custom_serializer) for tool in chat_log.llm_api.tools)
        if tools:
            payload["tools"] = tools
        return payload


def _format_tool(tool: llm.Tool, serializer) -> dict[str, Any]:
    schema = probatio.to_openapi(tool.parameters, custom_serializer=serializer, openapi_version="3.1.0")
    # Providers reject top-level combinators in function parameters.
    schema = {key: value for key, value in schema.items() if key not in {"oneOf", "anyOf", "allOf"}}
    function: dict[str, Any] = {"name": tool.name, "parameters": schema}
    if tool.description:
        function["description"] = tool.description
    return {"type": "function", "function": function}


async def async_messages(hass: HomeAssistant, chat_log: conversation.ChatLog) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for content in chat_log.content:
        if isinstance(content, conversation.ToolResultContent):
            messages.append({"role": "tool", "tool_call_id": content.tool_call_id, "content": json_dumps({"data": content.result.data, "error": content.result.error})})
        elif isinstance(content, conversation.AssistantContent):
            message: dict[str, Any] = {"role": "assistant", "content": content.content}
            if content.tool_calls:
                message["tool_calls"] = [{"id": call.id, "type": "function", "function": {"name": call.tool_name, "arguments": json.dumps(call.tool_args)}} for call in content.tool_calls]
            messages.append(message)
        elif content.role == "system":
            messages.append({"role": "system", "content": content.content})
        else:
            message = {"role": "user", "content": content.content}
            if isinstance(content, conversation.UserContent) and content.attachments:
                parts: list[dict[str, Any]] = [{"type": "text", "text": content.content}]
                for attachment in content.attachments:
                    parts.append(await _async_image_part(hass, attachment.path, attachment.mime_type))
                message["content"] = parts
            messages.append(message)
    return messages


async def _async_image_part(hass: HomeAssistant, path: Path, mime_type: str) -> dict[str, Any]:
    def encode() -> str:
        if not mime_type.startswith("image/"):
            raise HomeAssistantError("Only image attachments are supported")
        if not path.is_file() or path.stat().st_size > MAX_ATTACHMENT_BYTES:
            raise HomeAssistantError("Image attachment is missing or exceeds 10 MB")
        return base64.b64encode(path.read_bytes()).decode()
    encoded = await hass.async_add_executor_job(encode)
    return {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}}


def response_message(response: dict[str, Any]) -> dict[str, Any]:
    """Return the first choice's message from a chat completion."""
    choices = response.get("choices") or []
    if not choices or not isinstance(choices[0].get("message"), dict):
        raise HomeAssistantError("OpenRouter returned no choices")
    return choices[0]["message"]
