"""Config flow for OpenRouter Enhanced."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar

import voluptuous as vol
from homeassistant.config_entries import (
    SOURCE_USER,
    ConfigEntry,
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryData,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_API_KEY, CONF_LLM_HASS_API, CONF_MODEL, CONF_PROMPT
from homeassistant.core import callback
from homeassistant.helpers import llm
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TemplateSelector,
    TextSelector,
    TextSelectorConfig,
)

from .api import OpenRouterAPI, OpenRouterAPIError, OpenRouterAuthError
from .const import (
    CONF_ALLOWED_MODELS,
    CONF_COST_TIER,
    CONF_EXCLUDED_MODELS,
    CONF_INSTRUCTIONS,
    CONF_RESPONSE_FORMAT,
    CONF_SPEED,
    CONF_VOICE,
    CONF_WEB_SEARCH,
    COST_TIERS,
    DEFAULT_MODEL,
    DEFAULT_TTS_MODEL,
    DOMAIN,
    RECOMMENDED_AI_TASK_OPTIONS,
    RECOMMENDED_CONVERSATION_OPTIONS,
    RECOMMENDED_TTS_OPTIONS,
    RESPONSE_FORMATS,
    ROUTER_OPTIONS,
)

API_KEY_SCHEMA = vol.Schema({vol.Required(CONF_API_KEY): str})
ROUTER_SLUGS = {option["value"] for option in ROUTER_OPTIONS}


async def _async_validate_key(flow: ConfigFlow, api_key: str) -> tuple[str | None, str]:
    """Return an error key (None when the key works) and the key's label."""
    client = OpenRouterAPI(flow.hass, api_key)
    try:
        key_info = await client.async_validate_key()
        models = await client.async_list_models()
    except OpenRouterAuthError:
        return "invalid_auth", ""
    except OpenRouterAPIError:
        return "cannot_connect", ""
    return None if models else "no_models", key_info.get("label") or "OpenRouter"


class OpenRouterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle OpenRouter configuration."""

    VERSION = 1

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {"conversation": ConversationFlow, "ai_task_data": AITaskFlow, "tts": TTSFlow}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._async_abort_entries_match(user_input)
            error, label = await _async_validate_key(self, user_input[CONF_API_KEY])
            if not error:
                return self.async_create_entry(
                    title=label,
                    data=user_input,
                    subentries=[
                        ConfigSubentryData(subentry_type="conversation", title=ConversationFlow.title_for(DEFAULT_MODEL), data=RECOMMENDED_CONVERSATION_OPTIONS, unique_id=None),
                        ConfigSubentryData(subentry_type="ai_task_data", title=AITaskFlow.title_for(DEFAULT_MODEL), data=RECOMMENDED_AI_TASK_OPTIONS, unique_id=None),
                        ConfigSubentryData(subentry_type="tts", title=TTSFlow.title_for(DEFAULT_TTS_MODEL), data=RECOMMENDED_TTS_OPTIONS, unique_id=None),
                    ],
                )
            errors["base"] = error
        return self.async_show_form(step_id="user", data_schema=API_KEY_SCHEMA, errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Start API-key reauthentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Confirm a replacement API key."""
        errors: dict[str, str] = {}
        if user_input is not None:
            error, _ = await _async_validate_key(self, user_input[CONF_API_KEY])
            if not error:
                return self.async_update_reload_and_abort(self._get_reauth_entry(), data=user_input)
            errors["base"] = error
        return self.async_show_form(step_id="reauth_confirm", data_schema=API_KEY_SCHEMA, errors=errors)


class OpenRouterSubentryFlow(ConfigSubentryFlow):
    """Shared model picker for conversation, AI task and TTS subentries."""

    defaults: ClassVar[dict[str, Any]] = {}
    title_suffix = ""
    _catalog: list[dict[str, Any]]

    @classmethod
    def title_for(cls, model: str, catalog: list[dict[str, Any]] | None = None) -> str:
        """Name a subentry after its router or model, e.g. "Jev Router"."""
        names = {option["value"]: option["label"] for option in ROUTER_OPTIONS}
        names.update({item["id"]: item.get("name") or item["id"] for item in catalog or [] if item.get("id")})
        return f"{names.get(model, model)}{cls.title_suffix}"

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        self.options = self.defaults.copy()
        return await self.async_step_init(user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        self.options = self._get_reconfigure_subentry().data.copy()
        return await self.async_step_init(user_input)

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        if self._get_entry().state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="entry_not_loaded")
        if user_input is not None:
            data = {key: value for key, value in user_input.items() if value not in (None, "", [])}
            title = self.title_for(data[CONF_MODEL], self._catalog)
            if self.source == SOURCE_USER:
                return self.async_create_entry(title=title, data=data)
            subentry = self._get_reconfigure_subentry()
            # Follow the model only while the title is still the generated one.
            previous = subentry.data[CONF_MODEL]
            if subentry.title not in (self.title_for(previous, self._catalog), self.title_for(previous), f"OpenRouter{self.title_suffix}"):
                title = subentry.title
            return self.async_update_and_abort(self._get_entry(), subentry, title=title, data=data)
        try:
            self._catalog = await self._async_load_catalog()
        except OpenRouterAPIError:
            return self.async_abort(reason="cannot_connect")
        return self.async_show_form(step_id="init", data_schema=vol.Schema(self._schema(self._catalog)))

    async def _async_load_catalog(self) -> list[dict[str, Any]]:
        return await self._get_entry().runtime_data.async_list_models()

    def _schema(self, catalog: list[dict[str, Any]]) -> dict[Any, Any]:
        models = [
            SelectOptionDict(value=item["id"], label=item.get("name") or item["id"])
            for item in sorted(catalog, key=lambda item: item.get("name") or item.get("id") or "")
            if item.get("id") and item["id"] not in ROUTER_SLUGS
        ]
        options = self.options
        return {
            vol.Required(CONF_MODEL, default=options.get(CONF_MODEL, DEFAULT_MODEL)): SelectSelector(
                SelectSelectorConfig(options=[*ROUTER_OPTIONS, *models], mode=SelectSelectorMode.DROPDOWN, custom_value=True)
            ),
            vol.Optional(CONF_COST_TIER, description={"suggested_value": options.get(CONF_COST_TIER)}): SelectSelector(
                SelectSelectorConfig(options=COST_TIERS, mode=SelectSelectorMode.DROPDOWN, translation_key=CONF_COST_TIER)
            ),
            vol.Optional(CONF_ALLOWED_MODELS, description={"suggested_value": options.get(CONF_ALLOWED_MODELS, [])}): SelectSelector(
                SelectSelectorConfig(options=models, multiple=True, custom_value=True, mode=SelectSelectorMode.DROPDOWN)
            ),
            vol.Optional(CONF_EXCLUDED_MODELS, description={"suggested_value": options.get(CONF_EXCLUDED_MODELS, [])}): SelectSelector(
                SelectSelectorConfig(options=models, multiple=True, custom_value=True, mode=SelectSelectorMode.DROPDOWN)
            ),
            vol.Optional(CONF_WEB_SEARCH, default=options.get(CONF_WEB_SEARCH, True)): BooleanSelector(),
        }


class ConversationFlow(OpenRouterSubentryFlow):
    defaults = RECOMMENDED_CONVERSATION_OPTIONS

    def _schema(self, catalog: list[dict[str, Any]]) -> dict[Any, Any]:
        hass_apis = [SelectOptionDict(value=api.id, label=api.name) for api in llm.async_get_apis(self.hass)]
        return {
            **super()._schema(catalog),
            vol.Optional(CONF_PROMPT, description={"suggested_value": self.options.get(CONF_PROMPT)}): TemplateSelector(),
            vol.Optional(CONF_LLM_HASS_API, description={"suggested_value": self.options.get(CONF_LLM_HASS_API, [])}): SelectSelector(
                SelectSelectorConfig(options=hass_apis, multiple=True)
            ),
        }


class AITaskFlow(OpenRouterSubentryFlow):
    defaults = RECOMMENDED_AI_TASK_OPTIONS
    title_suffix = " AI Task"


class TTSFlow(OpenRouterSubentryFlow):
    defaults = RECOMMENDED_TTS_OPTIONS
    title_suffix = " TTS"

    async def _async_load_catalog(self) -> list[dict[str, Any]]:
        return await self._get_entry().runtime_data.async_list_models("speech")

    def _schema(self, catalog: list[dict[str, Any]]) -> dict[Any, Any]:
        options = self.options
        model = options.get(CONF_MODEL, DEFAULT_TTS_MODEL)
        models = [
            SelectOptionDict(value=item["id"], label=item.get("name") or item["id"])
            for item in sorted(catalog, key=lambda item: item.get("name") or item.get("id") or "")
            if item.get("id")
        ]
        # Voices are listed for the saved model only; other models' voices can be typed in.
        voices = next((_voice_ids(item) for item in catalog if item.get("id") == model), [])
        return {
            vol.Required(CONF_MODEL, default=model): SelectSelector(
                SelectSelectorConfig(options=models, mode=SelectSelectorMode.DROPDOWN, custom_value=True)
            ),
            vol.Optional(CONF_VOICE, description={"suggested_value": options.get(CONF_VOICE)}): SelectSelector(
                SelectSelectorConfig(options=voices, mode=SelectSelectorMode.DROPDOWN, custom_value=True)
            ),
            vol.Optional(CONF_INSTRUCTIONS, description={"suggested_value": options.get(CONF_INSTRUCTIONS)}): TextSelector(
                TextSelectorConfig(multiline=True)
            ),
            vol.Optional(CONF_RESPONSE_FORMAT, description={"suggested_value": options.get(CONF_RESPONSE_FORMAT)}): SelectSelector(
                SelectSelectorConfig(options=RESPONSE_FORMATS, mode=SelectSelectorMode.DROPDOWN, translation_key=CONF_RESPONSE_FORMAT)
            ),
            vol.Optional(CONF_SPEED, description={"suggested_value": options.get(CONF_SPEED)}): NumberSelector(
                NumberSelectorConfig(min=0.25, max=4, step=0.05, mode=NumberSelectorMode.BOX)
            ),
        }


def _voice_ids(item: dict[str, Any]) -> list[str]:
    """Read a model's supported_voices, which may hold ids or {"id": ...} objects."""
    voices = item.get("supported_voices") or []
    ids = [voice.get("id") if isinstance(voice, dict) else voice for voice in voices]
    return sorted({voice for voice in ids if isinstance(voice, str) and voice})
