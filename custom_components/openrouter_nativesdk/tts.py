"""Text-to-speech platform."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.components.tts import ATTR_VOICE, TextToSpeechEntity, TtsAudioType
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import CONF_MODEL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import OpenRouterAPIError
from .audio import to_ha_audio
from .const import CONF_INSTRUCTIONS, CONF_RESPONSE_FORMAT, CONF_SPEED, CONF_VOICE
from .entity import OpenRouterLLMEntity

# Speech models detect the language from the text; this list only satisfies HA's language matching.
SUPPORTED_LANGUAGES = [
    "ar", "bg", "bn", "ca", "cs", "cy", "da", "de", "el", "en", "en-AU", "en-GB", "en-IN", "en-US",
    "es", "es-ES", "es-MX", "et", "fa", "fi", "fil", "fr", "fr-CA", "fr-FR", "gu", "he", "hi", "hr",
    "hu", "id", "is", "it", "ja", "kn", "ko", "lt", "lv", "ml", "mr", "ms", "nb", "nl", "pl", "pt",
    "pt-BR", "pt-PT", "ro", "ru", "sk", "sl", "sr", "sv", "sw", "ta", "te", "th", "tr", "uk", "ur",
    "vi", "zh", "zh-CN", "zh-HK", "zh-TW",
]
SUPPORTED_OPTIONS = [ATTR_VOICE, CONF_INSTRUCTIONS]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    for subentry in entry.subentries.values():
        if subentry.subentry_type == "tts":
            async_add_entities([OpenRouterTTSEntity(entry, subentry)], config_subentry_id=subentry.subentry_id)


class OpenRouterTTSEntity(OpenRouterLLMEntity, TextToSpeechEntity):
    """OpenRouter speech synthesis entity."""

    _attr_has_entity_name = False
    _attr_supported_languages = SUPPORTED_LANGUAGES
    _attr_default_language = "en-US"
    _attr_supported_options = SUPPORTED_OPTIONS

    def __init__(self, entry: ConfigEntry, subentry: ConfigSubentry) -> None:
        super().__init__(entry, subentry)
        self._attr_name = subentry.title

    @property
    def default_options(self) -> Mapping[str, Any]:
        options = self.subentry.data
        return {key: options[key] for key in (CONF_VOICE, CONF_INSTRUCTIONS) if options.get(key)}

    async def async_get_tts_audio(self, message: str, language: str, options: dict[str, Any]) -> TtsAudioType:
        settings = self.subentry.data
        payload: dict[str, Any] = {
            "model": settings[CONF_MODEL],
            "input": message,
            "voice": options.get(ATTR_VOICE),
            "instructions": options.get(CONF_INSTRUCTIONS),
            "response_format": settings.get(CONF_RESPONSE_FORMAT),
            "speed": settings.get(CONF_SPEED),
        }
        payload = {key: value for key, value in payload.items() if value not in (None, "")}
        try:
            data, content_type = await self._async_call(self.client.async_speech, payload)
        except OpenRouterAPIError as err:
            raise HomeAssistantError(f"OpenRouter speech request failed: {err}") from err
        try:
            return to_ha_audio(data, content_type)
        except ValueError as err:
            raise HomeAssistantError(f"OpenRouter returned unplayable audio: {err}") from err
