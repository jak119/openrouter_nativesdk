"""Repair flows for OpenRouter Enhanced."""
from __future__ import annotations

from typing import Any

from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN


class KeyExpiringRepairFlow(RepairsFlow):
    """Send the user to reauth, since OpenRouter keys can't be extended."""

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            if entry := self.hass.config_entries.async_get_entry(self._entry_id):
                entry.async_start_reauth(self.hass)
            return self.async_create_entry(data={})
        issue = ir.async_get(self.hass).async_get_issue(DOMAIN, self.issue_id)
        return self.async_show_form(step_id="confirm", description_placeholders=issue.translation_placeholders if issue else None)


async def async_create_fix_flow(hass: HomeAssistant, issue_id: str, data: dict[str, Any] | None) -> RepairsFlow:
    return KeyExpiringRepairFlow((data or {})["entry_id"])
