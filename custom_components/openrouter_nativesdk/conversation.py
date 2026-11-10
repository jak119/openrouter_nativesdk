"""Conversation platform for OpenRouter Enhanced."""
from __future__ import annotations

import json
import logging
from typing import Any, Literal

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import CONF_LLM_HASS_API, CONF_PROMPT, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import OpenRouterAPIError
from .const import DOMAIN
from .entity import OpenRouterLLMEntity, async_messages, response_message

_LOGGER = logging.getLogger(__name__)
MAX_TOOL_ITERATIONS = 10


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    for subentry in entry.subentries.values():
        if subentry.subentry_type == "conversation":
            async_add_entities([OpenRouterConversationEntity(entry, subentry)], config_subentry_id=subentry.subentry_id)


class OpenRouterConversationEntity(OpenRouterLLMEntity, conversation.ConversationEntity):
    """OpenRouter Assist conversation agent."""

    def __init__(self, entry: ConfigEntry, subentry: ConfigSubentry) -> None:
        super().__init__(entry, subentry)
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
            raise HomeAssistantError(f"OpenRouter request failed: {err}") from err
        return conversation.async_get_result_from_chat_log(user_input, chat_log)

    async def _async_handle_chat_log(self, chat_log: conversation.ChatLog) -> None:
        payload = await self._async_build_payload(chat_log)
        for _ in range(MAX_TOOL_ITERATIONS):
            response = await self.client.async_chat(payload)
            _LOGGER.debug("OpenRouter answered with %s", response.get("model"))
            assistant = _assistant_content(response_message(response), self.entity_id)
            async for _ in chat_log.async_add_assistant_content(assistant):
                pass
            if not chat_log.unresponded_tool_results:
                return
            payload["messages"] = await async_messages(self.hass, chat_log)
        raise HomeAssistantError("OpenRouter did not finish tool execution")


def _assistant_content(message: dict[str, Any], agent_id: str) -> conversation.AssistantContent:
    tool_calls = []
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        try:
            args = json.loads(function.get("arguments") or "{}")
        except (TypeError, json.JSONDecodeError) as err:
            raise HomeAssistantError("OpenRouter returned invalid tool arguments") from err
        tool_calls.append(llm.ToolInput(id=call["id"], tool_name=function["name"], tool_args=args))
    return conversation.AssistantContent(agent_id=agent_id, content=message.get("content"), tool_calls=tool_calls or None)
