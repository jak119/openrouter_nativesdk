"""Tests for router plugin and server tool construction."""
import importlib.util
from pathlib import Path

import pytest

# Load routing.py directly so the Home Assistant-dependent package __init__ is not imported.
_PATH = Path(__file__).parent.parent / "custom_components" / "openrouter_nativesdk" / "routing.py"
_spec = importlib.util.spec_from_file_location("routing", _PATH)
routing = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(routing)


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("openrouter/auto", "auto-router"),
        ("openrouter/auto-beta", "auto-beta-router"),
        ("typesafe/jev-router", "jev-router"),
        ("anthropic/auto", "jev-router"),
        ("openai/gpt-5.1", None),
        ("openrouter/auto-code", None),
    ],
)
def test_plugin_id(model, expected):
    assert routing.plugin_id(model) == expected


def test_fixed_model_sends_no_plugin():
    assert routing.build_plugins("openai/gpt-5.1", "low", ["anthropic/*"], ["x"]) == []


def test_router_without_settings_sends_bare_plugin():
    assert routing.build_plugins("typesafe/jev-router") == [{"id": "jev-router"}]


def test_empty_values_are_omitted():
    assert routing.build_plugins("openrouter/auto", "", [], [" ", ""]) == [{"id": "auto-router"}]


def test_full_plugin_shape():
    assert routing.build_plugins(
        "openrouter/auto-beta", "high", ["anthropic/*", " google/* "], ["anthropic/claude-opus*"]
    ) == [
        {
            "id": "auto-beta-router",
            "cost_tier": "high",
            "allowed_models": ["anthropic/*", "google/*"],
            "excluded_models": ["anthropic/claude-opus*"],
        }
    ]


def test_build_tools():
    assert routing.build_tools(True) == [{"type": "openrouter:web_search"}]
    assert routing.build_tools(False) == []
    # Callers extend the returned list, so it must not alias the module constant.
    routing.build_tools(True).append({"type": "function"})
    assert routing.build_tools(True) == [{"type": "openrouter:web_search"}]
