"""Text-to-speech platform."""
from __future__ import annotations

from typing import Any

from homeassistant.components import tts
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_TTS_MODEL, CONF_VOICE


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    for subentry in entry.subentries.values():
        if subentry.subentry_type == "tts":
            async_add_entities([OpenRouterTTSEntity(entry, subentry)], config_subentry_id=subentry.subentry_id)


class OpenRouterTTSEntity(tts.TextToSpeechEntity):
    """OpenRouter speech entity."""
    _attr_name = None
    _attr_default_language = "en-US"
    _attr_supported_languages = ["en-US"]
    _attr_supported_options = [tts.ATTR_VOICE]

    def __init__(self, entry: ConfigEntry, subentry: ConfigSubentry) -> None:
        self.client = entry.runtime_data
        self.subentry = subentry
        self._attr_unique_id = subentry.subentry_id

    async def async_get_tts_audio(self, message: str, language: str, options: dict[str, Any]) -> tts.TtsAudioType:
        voice = options.get(tts.ATTR_VOICE, self.subentry.data[CONF_VOICE])
        data, content_type = await self.client.async_speech(model=self.subentry.data[CONF_TTS_MODEL], input=message, voice=voice, response_format="mp3")
        return ("mp3" if "mpeg" in content_type else "wav"), data
