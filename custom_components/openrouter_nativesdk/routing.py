"""Request routing helpers. Kept free of Home Assistant imports so it can be unit tested."""
from __future__ import annotations

from typing import Any

ROUTERS = {
    "openrouter/auto": "auto-router",
    "openrouter/auto-beta": "auto-beta-router",
    "typesafe/jev-router": "jev-router",
}
WEB_SEARCH_TOOL = {"type": "openrouter:web_search"}


def plugin_id(model: str) -> str | None:
    """Return the router plugin id that reads settings for a model slug."""
    if model in ROUTERS:
        return ROUTERS[model]
    # Author routers such as anthropic/auto run Jev scoped to that author.
    if model.endswith("/auto") and model.count("/") == 1:
        return "jev-router"
    return None


def build_plugins(
    model: str,
    cost_tier: str | None = None,
    allowed_models: list[str] | None = None,
    excluded_models: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Build the router plugin, omitting unset fields (Jev rejects invalid values)."""
    if (pid := plugin_id(model)) is None:
        return []
    plugin: dict[str, Any] = {"id": pid}
    if cost_tier:
        plugin["cost_tier"] = cost_tier
    if allowed := [item.strip() for item in allowed_models or [] if item.strip()]:
        plugin["allowed_models"] = allowed
    if excluded := [item.strip() for item in excluded_models or [] if item.strip()]:
        plugin["excluded_models"] = excluded
    return [plugin]


def build_tools(web_search: bool) -> list[dict[str, Any]]:
    """Return OpenRouter server tools to include ahead of Assist function tools."""
    return [dict(WEB_SEARCH_TOOL)] if web_search else []
