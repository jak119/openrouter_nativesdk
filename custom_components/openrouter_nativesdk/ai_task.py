"""AI task platform."""
from __future__ import annotations

import base64
import json

from homeassistant.components import ai_task, conversation
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.json import json_loads

from .api import OpenRouterAPIError
from .const import CONF_IMAGE_MODEL, CONF_MODEL
from .conversation import _async_image_part, _async_messages


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    for subentry in entry.subentries.values():
        if subentry.subentry_type == "ai_task_data":
            async_add_entities([OpenRouterAITaskEntity(entry, subentry)], config_subentry_id=subentry.subentry_id)


class OpenRouterAITaskEntity(ai_task.AITaskEntity):
    """OpenRouter structured-data and image-generation entity."""
    _attr_name = None
    _attr_supported_features = ai_task.AITaskEntityFeature.GENERATE_DATA | ai_task.AITaskEntityFeature.GENERATE_IMAGE | ai_task.AITaskEntityFeature.SUPPORT_ATTACHMENTS

    def __init__(self, entry: ConfigEntry, subentry: ConfigSubentry) -> None:
        self.client = entry.runtime_data
        self.subentry = subentry
        self._attr_unique_id = subentry.subentry_id

    async def _async_generate_data(self, task: ai_task.GenDataTask, chat_log: conversation.ChatLog) -> ai_task.GenDataTaskResult:
        try:
            response = await self.client.async_chat(
                model=self.subentry.data[CONF_MODEL],
                messages=await _async_messages(self.hass, chat_log),
                response_format={"type": "json_object"} if task.structure else None,
                session_id=chat_log.conversation_id,
            )
        except OpenRouterAPIError as err:
            raise HomeAssistantError("OpenRouter data-generation request failed") from err
        if not response.choices or not response.choices[0].message.content:
            raise HomeAssistantError("OpenRouter returned no data")
        text = response.choices[0].message.content
        if task.structure is None:
            data = text
        else:
            try:
                data = json_loads(text)
            except json.JSONDecodeError as err:
                raise HomeAssistantError("OpenRouter returned invalid structured data") from err
        return ai_task.GenDataTaskResult(conversation_id=chat_log.conversation_id, data=data)

    async def _async_generate_image(self, task: ai_task.GenImageTask, chat_log: conversation.ChatLog) -> ai_task.GenImageTaskResult:
        last_message = chat_log.content[-1]
        if not isinstance(last_message, conversation.UserContent):
            raise HomeAssistantError("Image task has no user prompt")
        references = []
        for attachment in last_message.attachments or []:
            references.append(await _async_image_part(self.hass, attachment.path, attachment.mime_type))
        try:
            response = await self.client.async_generate_image(
                model=self.subentry.data[CONF_IMAGE_MODEL],
                prompt=last_message.content,
                input_references=references or None,
                output_format="png",
            )
        except OpenRouterAPIError as err:
            raise HomeAssistantError("OpenRouter image-generation request failed") from err
        data = getattr(response, "data", None) or []
        if not data:
            raise HomeAssistantError("OpenRouter returned no image")
        image = data[0]
        encoded = getattr(image, "b64_json", None) or image.get("b64_json")
        mime_type = getattr(image, "media_type", None) or (image.get("media_type") if isinstance(image, dict) else None) or "image/png"
        return ai_task.GenImageTaskResult(image_data=base64.b64decode(encoded), conversation_id=chat_log.conversation_id, mime_type=mime_type, model=self.subentry.data[CONF_IMAGE_MODEL])
