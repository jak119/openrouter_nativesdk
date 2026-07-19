"""Constants for OpenRouter Enhanced."""
from homeassistant.const import CONF_LLM_HASS_API, CONF_MODEL, CONF_PROMPT
from homeassistant.helpers import llm

DOMAIN = "openrouter_nativesdk"
CONF_PRESET = "preset"
CONF_ROUTER = "router"
CONF_COST_QUALITY = "cost_quality_tradeoff"
CONF_ALLOWED_MODELS = "allowed_models"
CONF_TEMPERATURE = "temperature"
CONF_MAX_TOKENS = "max_tokens"
CONF_WEB_SEARCH = "web_search"
CONF_VOICE = "voice"
CONF_LANGUAGE = "language"
CONF_STT_MODEL = "stt_model"
CONF_TTS_MODEL = "tts_model"
CONF_IMAGE_MODEL = "image_model"

ROUTER_OPTIONS = [
    {"value": "", "label": "Fixed model"},
    {"value": "openrouter/auto-beta", "label": "Auto Router Beta"},
    {"value": "openrouter/auto", "label": "Auto Router (legacy)"},
]
RECOMMENDED_CONVERSATION_OPTIONS = {
    CONF_MODEL: "openrouter/auto-beta",
    CONF_ROUTER: "openrouter/auto-beta",
    CONF_LLM_HASS_API: [llm.LLM_API_ASSIST],
    CONF_PROMPT: llm.DEFAULT_INSTRUCTIONS_PROMPT,
    CONF_COST_QUALITY: 7,
    CONF_WEB_SEARCH: False,
}
RECOMMENDED_STT_OPTIONS = {CONF_STT_MODEL: "openai/whisper-large-v3"}
RECOMMENDED_TTS_OPTIONS = {CONF_TTS_MODEL: "openai/gpt-4o-mini-tts", CONF_VOICE: "alloy"}
RECOMMENDED_AI_TASK_OPTIONS = {CONF_MODEL: "openrouter/auto-beta", CONF_IMAGE_MODEL: "bytedance-seed/seedream-4.5"}
