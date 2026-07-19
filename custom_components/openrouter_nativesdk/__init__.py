"""OpenRouter Enhanced Home Assistant integration."""
from __future__ import annotations
from typing import TypeAlias
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from .api import OpenRouterAPI, OpenRouterAPIError

PLATFORMS = [Platform.CONVERSATION, Platform.AI_TASK, Platform.STT, Platform.TTS]
OpenRouterConfigEntry: TypeAlias = ConfigEntry[OpenRouterAPI]

async def async_setup_entry(hass: HomeAssistant, entry: OpenRouterConfigEntry) -> bool:
    """Set up OpenRouter."""
    client = OpenRouterAPI(hass, entry.data[CONF_API_KEY])
    try:
        await client.async_list_models()
    except OpenRouterAPIError as err:
        raise ConfigEntryNotReady(str(err)) from err
    entry.runtime_data = client
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True

async def async_unload_entry(hass: HomeAssistant, entry: OpenRouterConfigEntry) -> bool:
    """Unload OpenRouter."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

async def _async_update_listener(hass: HomeAssistant, entry: OpenRouterConfigEntry) -> None:
    """Reload when entry data changes."""
    await hass.config_entries.async_reload(entry.entry_id)
