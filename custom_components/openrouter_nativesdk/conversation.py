"""Conversation platform for OpenRouter Enhanced."""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Literal

from voluptuous_openapi import convert

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import CONF_LLM_HASS_API, CONF_MODEL, CONF_PROMPT, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import OpenRouterAPIError
from .const import (
    CONF_ALLOWED_MODELS, CONF_COST_QUALITY, CONF_PRESET, CONF_ROUTER,
    CONF_TEMPERATURE, CONF_WEB_SEARCH, DOMAIN,
)

MAX_TOOL_ITERATIONS = 10
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    for subentry in entry.subentries.values():
        if subentry.subentry_type == "conversation":
            async_add_entities([OpenRouterConversationEntity(entry, subentry)], config_subentry_id=subentry.subentry_id)


class OpenRouterConversationEntity(conversation.ConversationEntity):
    """OpenRouter Assist conversation agent."""
    _attr_name = None

    def __init__(self, entry: ConfigEntry, subentry: ConfigSubentry) -> None:
        self.entry = entry
        self.subentry = subentry
        self.client = entry.runtime_data
        self._attr_unique_id = subentry.subentry_id
        if subentry.data.get(CONF_LLM_HASS_API):
            self._attr_supported_features = conversation.ConversationEntityFeature.CONTROL

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        return MATCH_ALL

    async def _async_handle_message(self, user_input: conversation.ConversationInput, chat_log: conversation.ChatLog) -> conversation.ConversationResult:
        try:
            await chat_log.async_provide_llm_data(user_input.as_llm_context(DOMAIN), self.subentry.data.get(CONF_LLM_HASS_API), self.subentry.data.get(CONF_PROMPT), user_input.extra_system_prompt)
            await self._async_handle_chat_log(chat_log)
        except conversation.ConverseError as err:
            return err.as_conversation_result()
        except (HomeAssistantError, OpenRouterAPIError) as err:
            raise conversation.ConverseError("OpenRouter request failed") from err
        return conversation.async_get_result_from_chat_log(user_input, chat_log)

    async def _async_handle_chat_log(self, chat_log: conversation.ChatLog) -> None:
        options = self.subentry.data
        model = options.get(CONF_ROUTER) or options[CONF_MODEL]
        args: dict[str, Any] = {
            "model": model,
            "messages": await _async_messages(self.hass, chat_log),
            "session_id": chat_log.conversation_id,
            "temperature": options.get(CONF_TEMPERATURE),
        }
        if options.get(CONF_PRESET):
            preset = await self.client.async_get_preset(options[CONF_PRESET])
            version = preset.get("designated_version") or {}
            preset_config = version.get("config") or {}
            args = {**preset_config, **args}
            if system_prompt := version.get("system_prompt"):
                args["messages"] = [{"role": "system", "content": system_prompt}, *args["messages"]]
        if options.get(CONF_WEB_SEARCH):
            args["plugins"] = [{"id": "web"}]
        if options.get(CONF_ALLOWED_MODELS):
            allowed = [item.strip() for item in options[CONF_ALLOWED_MODELS].split(",") if item.strip()]
            args.setdefault("plugins", []).append({"id": "auto-beta-router", "allowed_models": allowed, "cost_quality_tradeoff": options.get(CONF_COST_QUALITY, 7)})
        if chat_log.llm_api:
            args["tools"] = [_format_tool(tool, chat_log.llm_api.custom_serializer) for tool in chat_log.llm_api.tools]

        for _ in range(MAX_TOOL_ITERATIONS):
            response = await self.client.async_chat(**args)
            assistant = _assistant_content(response, self.entity_id)
            async for _ in chat_log.async_add_assistant_content(assistant):
                pass
            if not chat_log.unresponded_tool_results:
                return
            args["messages"] = await _async_messages(self.hass, chat_log)
        raise HomeAssistantError("OpenRouter did not finish tool execution")


def _format_tool(tool: llm.Tool, serializer) -> dict[str, Any]:
    function: dict[str, Any] = {"name": tool.name, "parameters": convert(tool.parameters, custom_serializer=serializer)}
    if tool.description:
        function["description"] = tool.description
    return {"type": "function", "function": function}


async def _async_messages(hass: HomeAssistant, chat_log: conversation.ChatLog) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for content in chat_log.content:
        if isinstance(content, conversation.ToolResultContent):
            messages.append({"role": "tool", "tool_call_id": content.tool_call_id, "content": json.dumps(content.tool_result)})
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


def _assistant_content(response: Any, agent_id: str) -> conversation.AssistantContent:
    choices = getattr(response, "choices", None) or []
    if not choices:
        raise HomeAssistantError("OpenRouter returned no choices")
    message = choices[0].message
    tool_calls = []
    for call in getattr(message, "tool_calls", None) or []:
        function = call.function
        try:
            args = json.loads(function.arguments)
        except (TypeError, json.JSONDecodeError) as err:
            raise HomeAssistantError("OpenRouter returned invalid tool arguments") from err
        tool_calls.append(llm.ToolInput(id=call.id, tool_name=function.name, tool_args=args))
    return conversation.AssistantContent(agent_id=agent_id, content=getattr(message, "content", None), tool_calls=tool_calls or None)
