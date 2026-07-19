"""Speech-to-text platform."""
from __future__ import annotations

from collections.abc import AsyncIterable

from homeassistant.components import stt
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import OpenRouterAPIError
from .const import CONF_STT_MODEL


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    for subentry in entry.subentries.values():
        if subentry.subentry_type == "stt":
            async_add_entities([OpenRouterSTTEntity(entry, subentry)], config_subentry_id=subentry.subentry_id)


class OpenRouterSTTEntity(stt.SpeechToTextEntity):
    """OpenRouter transcription entity."""
    _attr_name = None
    _attr_supported_languages = ["*"]

    def __init__(self, entry: ConfigEntry, subentry: ConfigSubentry) -> None:
        self.client = entry.runtime_data
        self.subentry = subentry
        self._attr_unique_id = subentry.subentry_id

    @property
    def supported_languages(self) -> list[str]:
        return self._attr_supported_languages

    @property
    def supported_formats(self) -> list[stt.AudioFormats]:
        return [stt.AudioFormats.WAV, stt.AudioFormats.OGG]

    @property
    def supported_codecs(self) -> list[stt.AudioCodecs]:
        return [stt.AudioCodecs.PCM, stt.AudioCodecs.OPUS]

    @property
    def supported_bit_rates(self) -> list[stt.AudioBitRates]:
        return [stt.AudioBitRates.BITRATE_16]

    @property
    def supported_sample_rates(self) -> list[stt.AudioSampleRates]:
        return [stt.AudioSampleRates.SAMPLERATE_16000]

    @property
    def supported_channels(self) -> list[stt.AudioChannels]:
        return [stt.AudioChannels.CHANNEL_MONO]

    async def async_process_audio_stream(self, metadata: stt.SpeechMetadata, stream: AsyncIterable[bytes]) -> stt.SpeechResult:
        audio = b"".join([chunk async for chunk in stream])
        try:
            response = await self.client.async_transcribe(audio, metadata.format.value, model=self.subentry.data[CONF_STT_MODEL], language=metadata.language.split("-", 1)[0] if metadata.language else None)
        except OpenRouterAPIError:
            return stt.SpeechResult("", stt.SpeechResultState.ERROR)
        text = getattr(response, "text", None) or (response.get("text") if isinstance(response, dict) else "")
        return stt.SpeechResult(text, stt.SpeechResultState.SUCCESS)
