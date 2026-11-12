"""Constants for OpenRouter Enhanced."""
from homeassistant.const import CONF_LLM_HASS_API, CONF_MODEL, CONF_PROMPT
from homeassistant.helpers import llm

DOMAIN = "openrouter_nativesdk"
APP_URL = "https://github.com/jak119/openrouter-enhanced"
APP_TITLE = "OpenRouter Enhanced for Home Assistant"
APP_CATEGORIES = "personal-agent,general-chat"
KEYS_URL = "https://openrouter.ai/settings/keys"
CONF_COST_TIER = "cost_tier"
CONF_ALLOWED_MODELS = "allowed_models"
CONF_EXCLUDED_MODELS = "excluded_models"
CONF_WEB_SEARCH = "web_search"
CONF_VOICE = "voice"
CONF_INSTRUCTIONS = "instructions"
CONF_RESPONSE_FORMAT = "response_format"
CONF_SPEED = "speed"

COST_TIERS = ["low", "medium", "high"]
ROUTER_OPTIONS = [
    {"value": "openrouter/auto", "label": "Auto Router"},
    {"value": "openrouter/auto-beta", "label": "Auto Router (beta channel)"},
    {"value": "typesafe/jev-router", "label": "Jev Router"},
]
DEFAULT_MODEL = "openrouter/auto"
DEFAULT_TTS_MODEL = "mistralai/voxtral-mini-tts-2603"
DEFAULT_TTS_VOICE = "en_paul_neutral"
RESPONSE_FORMATS = ["mp3", "pcm"]

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
RECOMMENDED_TTS_OPTIONS = {
    CONF_MODEL: DEFAULT_TTS_MODEL,
    CONF_VOICE: DEFAULT_TTS_VOICE,
    # mp3 carries its own sample rate; pcm relies on the Content-Type or a 24 kHz guess.
    CONF_RESPONSE_FORMAT: "mp3",
}
