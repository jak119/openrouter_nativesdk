"""OpenRouter Enhanced Home Assistant integration."""
from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.event import async_track_time_interval

from .api import OpenRouterAPI, OpenRouterAPIError, OpenRouterAuthError
from .issues import async_check_key, async_delete_issues, async_update_issues

PLATFORMS = [Platform.AI_TASK, Platform.CONVERSATION]
KEY_CHECK_INTERVAL = timedelta(days=1)
type OpenRouterConfigEntry = ConfigEntry[OpenRouterAPI]

async def async_setup_entry(hass: HomeAssistant, entry: OpenRouterConfigEntry) -> bool:
    """Set up OpenRouter."""
    client = OpenRouterAPI(hass, entry.data[CONF_API_KEY])
    try:
        key_info = await client.async_validate_key()
    except OpenRouterAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except OpenRouterAPIError as err:
        raise ConfigEntryNotReady(str(err)) from err
    entry.runtime_data = client
    async_update_issues(hass, entry, key_info)

    async def _async_check_key(now: datetime) -> None:
        """Re-read the key daily; HA can run for weeks without a reload."""
        await async_check_key(hass, entry)

    entry.async_on_unload(async_track_time_interval(hass, _async_check_key, KEY_CHECK_INTERVAL))
    entry.async_on_unload(lambda: async_delete_issues(hass, entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True

async def async_unload_entry(hass: HomeAssistant, entry: OpenRouterConfigEntry) -> bool:
    """Unload OpenRouter."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

async def _async_update_listener(hass: HomeAssistant, entry: OpenRouterConfigEntry) -> None:
    """Reload when entry data changes."""
    await hass.config_entries.async_reload(entry.entry_id)
