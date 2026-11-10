"""Constants for OpenRouter Enhanced."""
from homeassistant.const import CONF_LLM_HASS_API, CONF_MODEL, CONF_PROMPT
from homeassistant.helpers import llm

DOMAIN = "openrouter_nativesdk"
CONF_COST_TIER = "cost_tier"
CONF_ALLOWED_MODELS = "allowed_models"
CONF_EXCLUDED_MODELS = "excluded_models"
CONF_WEB_SEARCH = "web_search"

COST_TIERS = ["low", "medium", "high"]
ROUTER_OPTIONS = [
    {"value": "openrouter/auto", "label": "Auto Router"},
    {"value": "openrouter/auto-beta", "label": "Auto Router (beta channel)"},
    {"value": "typesafe/jev-router", "label": "Jev Router"},
]
DEFAULT_MODEL = "openrouter/auto"

RECOMMENDED_CONVERSATION_OPTIONS = {
    CONF_MODEL: DEFAULT_MODEL,
    CONF_LLM_HASS_API: [llm.LLM_API_ASSIST],
    CONF_PROMPT: llm.DEFAULT_INSTRUCTIONS_PROMPT,
    CONF_WEB_SEARCH: True,
}
RECOMMENDED_AI_TASK_OPTIONS = {
    CONF_MODEL: DEFAULT_MODEL,
    CONF_WEB_SEARCH: True,
}
