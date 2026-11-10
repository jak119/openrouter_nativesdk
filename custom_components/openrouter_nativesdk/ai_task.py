"""AI task platform."""
from __future__ import annotations

import json

import probatio
from homeassistant.components import ai_task, conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import slugify
from homeassistant.util.json import json_loads

from .api import OpenRouterAPIError
from .entity import OpenRouterLLMEntity, response_message


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    for subentry in entry.subentries.values():
        if subentry.subentry_type == "ai_task_data":
            async_add_entities([OpenRouterAITaskEntity(entry, subentry)], config_subentry_id=subentry.subentry_id)


class OpenRouterAITaskEntity(OpenRouterLLMEntity, ai_task.AITaskEntity):
    """OpenRouter structured-data entity."""

    _attr_supported_features = ai_task.AITaskEntityFeature.GENERATE_DATA | ai_task.AITaskEntityFeature.SUPPORT_ATTACHMENTS

    async def _async_generate_data(self, task: ai_task.GenDataTask, chat_log: conversation.ChatLog) -> ai_task.GenDataTaskResult:
        extra = {}
        if task.structure:
            serializer = chat_log.llm_api.custom_serializer if chat_log.llm_api else llm.selector_serializer
            schema = probatio.to_openapi(task.structure, custom_serializer=serializer, openapi_version="3.1.0")
            extra = {
                "response_format": {"type": "json_schema", "json_schema": {"name": slugify(task.name)[:64] or "response", "schema": schema}},
                # Only route to endpoints that honour response_format.
                "provider": {"require_parameters": True},
            }
        try:
            response = await self.client.async_chat(await self._async_build_payload(chat_log, **extra))
        except OpenRouterAPIError as err:
            raise HomeAssistantError(f"OpenRouter data-generation request failed: {err}") from err
        text = response_message(response).get("content")
        if not text:
            raise HomeAssistantError("OpenRouter returned no data")
        if task.structure is None:
            return ai_task.GenDataTaskResult(conversation_id=chat_log.conversation_id, data=text)
        try:
            data = json_loads(text)
        except json.JSONDecodeError as err:
            raise HomeAssistantError("OpenRouter returned invalid structured data") from err
        return ai_task.GenDataTaskResult(conversation_id=chat_log.conversation_id, data=data)
