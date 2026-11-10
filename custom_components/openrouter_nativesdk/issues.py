"""Repair issues raised from the /key endpoint."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util

from .api import OpenRouterAPIError, OpenRouterAuthError
from .const import DOMAIN, KEYS_URL

KEY_EXPIRY_WARNING = timedelta(days=7)


def expiry_issue_id(entry: ConfigEntry) -> str:
    return f"key_expiring_{entry.entry_id}"


def budget_issue_id(entry: ConfigEntry) -> str:
    return f"budget_exhausted_{entry.entry_id}"


@callback
def async_delete_issues(hass: HomeAssistant, entry: ConfigEntry) -> None:
    ir.async_delete_issue(hass, DOMAIN, expiry_issue_id(entry))
    ir.async_delete_issue(hass, DOMAIN, budget_issue_id(entry))


async def async_check_key(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Re-read /key to refresh the issues, or start reauth if the key is rejected."""
    try:
        key_info = await entry.runtime_data.async_validate_key()
    except OpenRouterAuthError:
        async_delete_issues(hass, entry)
        entry.async_start_reauth(hass)
        return
    except OpenRouterAPIError:
        return
    async_update_issues(hass, entry, key_info)


@callback
def async_update_issues(hass: HomeAssistant, entry: ConfigEntry, key_info: dict[str, Any]) -> None:
    label = key_info.get("label") or entry.title
    _async_update_expiry_issue(hass, entry, key_info, label)
    _async_update_budget_issue(hass, entry, key_info, label)


@callback
def _async_update_expiry_issue(hass: HomeAssistant, entry: ConfigEntry, key_info: dict[str, Any], label: str) -> None:
    """Warn in Repairs when the key expires within a week; reauth once it has."""
    issue_id = expiry_issue_id(entry)
    raw = key_info.get("expires_at")
    expires_at = dt_util.parse_datetime(raw) if isinstance(raw, str) else None
    remaining = expires_at - dt_util.utcnow() if expires_at else None
    if remaining is None or remaining > KEY_EXPIRY_WARNING:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    if remaining <= timedelta(0):
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        entry.async_start_reauth(hass)
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key="key_expiring",
        translation_placeholders={
            "label": label,
            "expires_at": dt_util.as_local(expires_at).strftime("%Y-%m-%d %H:%M"),
            "keys_url": KEYS_URL,
        },
        data={"entry_id": entry.entry_id},
    )


@callback
def _async_update_budget_issue(hass: HomeAssistant, entry: ConfigEntry, key_info: dict[str, Any], label: str) -> None:
    """Raise an error in Repairs while the key's own limit or a guardrail budget is spent."""
    issue_id = budget_issue_id(entry)
    remaining = [key_info.get("limit_remaining")]
    if isinstance(effective := key_info.get("effective_budget"), dict):
        remaining.append(effective.get("remaining_usd"))
    if not any(isinstance(value, (int, float)) and value <= 0 for value in remaining):
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        learn_more_url=KEYS_URL,
        translation_key="budget_exhausted",
        translation_placeholders={"label": label},
    )
