"""Config flow for OpenRouter Enhanced."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_USER,
    ConfigEntry,
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
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
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TemplateSelector,
    TextSelector,
)

from .api import OpenRouterAPI, OpenRouterAPIError
from .const import (
    CONF_ALLOWED_MODELS,
    CONF_COST_QUALITY,
    CONF_IMAGE_MODEL,
    CONF_PRESET,
    CONF_ROUTER,
    CONF_STT_MODEL,
    CONF_TEMPERATURE,
    CONF_TTS_MODEL,
    CONF_VOICE,
    CONF_WEB_SEARCH,
    DOMAIN,
    RECOMMENDED_AI_TASK_OPTIONS,
    RECOMMENDED_CONVERSATION_OPTIONS,
    RECOMMENDED_STT_OPTIONS,
    RECOMMENDED_TTS_OPTIONS,
    ROUTER_OPTIONS,
)


class OpenRouterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle OpenRouter configuration."""

    VERSION = 1

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {
            "conversation": ConversationFlow,
            "ai_task_data": AITaskFlow,
            "stt": STTFlow,
            "tts": TTSFlow,
        }

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._async_abort_entries_match(user_input)
            try:
                models = await OpenRouterAPI(
                    self.hass, user_input[CONF_API_KEY]
                ).async_list_models()
            except OpenRouterAPIError:
                errors["base"] = "cannot_connect"
            else:
                if not models:
                    errors["base"] = "no_models"
                else:
                    return self.async_create_entry(
                        title="OpenRouter",
                        data=user_input,
                        subentries=[
                            {"subentry_type": "conversation", "title": "OpenRouter", "data": RECOMMENDED_CONVERSATION_OPTIONS, "unique_id": None},
                            {"subentry_type": "ai_task_data", "title": "OpenRouter AI Tasks", "data": RECOMMENDED_AI_TASK_OPTIONS, "unique_id": None},
                            {"subentry_type": "stt", "title": "OpenRouter Speech-to-Text", "data": RECOMMENDED_STT_OPTIONS, "unique_id": None},
                            {"subentry_type": "tts", "title": "OpenRouter Text-to-Speech", "data": RECOMMENDED_TTS_OPTIONS, "unique_id": None},
                        ],
                    )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Start API-key reauthentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Confirm a replacement API key."""
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm", data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}))
        try:
            await OpenRouterAPI(self.hass, user_input[CONF_API_KEY]).async_list_models()
        except OpenRouterAPIError:
            return self.async_show_form(step_id="reauth_confirm", data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}), errors={"base": "cannot_connect"})
        return self.async_update_reload_and_abort(self._get_reauth_entry(), data=user_input)


class OpenRouterSubentryFlow(ConfigSubentryFlow):
    """Shared model discovery and save behavior."""

    defaults: dict[str, Any] = {}

    @property
    def _is_new(self) -> bool:
        return self.source == SOURCE_USER

    async def _async_choices(self) -> tuple[list[SelectOptionDict], list[SelectOptionDict]]:
        client = self._get_entry().runtime_data
        models, presets = await client.async_list_models(), await client.async_list_presets()
        model_options = [
            SelectOptionDict(value=item["id"], label=item.get("name", item["id"]))
            for item in models
            if item.get("id")
        ]
        preset_options = [
            SelectOptionDict(value=item["id"], label=item.get("name", item["id"]))
            for item in presets
            if item.get("id")
        ]
        return model_options, preset_options

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        self.options = self.defaults.copy()
        return await self.async_step_init(user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        self.options = self._get_reconfigure_subentry().data.copy()
        return await self.async_step_init(user_input)

    async def _save(self, user_input: dict[str, Any], title: str) -> SubentryFlowResult:
        if self._is_new:
            return self.async_create_entry(title=title, data=user_input)
        return self.async_update_and_abort(self._get_entry(), self._get_reconfigure_subentry(), data=user_input)


class ConversationFlow(OpenRouterSubentryFlow):
    defaults = RECOMMENDED_CONVERSATION_OPTIONS

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        if self._get_entry().state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="entry_not_loaded")
        if user_input is not None:
            if not user_input.get(CONF_LLM_HASS_API):
                user_input.pop(CONF_LLM_HASS_API, None)
            return await self._save(user_input, "OpenRouter")
        try:
            models, presets = await self._async_choices()
        except OpenRouterAPIError:
            return self.async_abort(reason="cannot_connect")
        hass_apis = [SelectOptionDict(value=api.id, label=api.name) for api in llm.async_get_apis(self.hass)]
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_MODEL, default=self.options.get(CONF_MODEL)): SelectSelector(SelectSelectorConfig(options=models, mode=SelectSelectorMode.DROPDOWN, sort=True)),
                vol.Optional(CONF_PRESET, default=self.options.get(CONF_PRESET)): SelectSelector(SelectSelectorConfig(options=presets, mode=SelectSelectorMode.DROPDOWN, custom_value=True)),
                vol.Optional(CONF_ROUTER, default=self.options.get(CONF_ROUTER, "openrouter/auto-beta")): SelectSelector(SelectSelectorConfig(options=ROUTER_OPTIONS, mode=SelectSelectorMode.DROPDOWN)),
                vol.Optional(CONF_COST_QUALITY, default=self.options.get(CONF_COST_QUALITY, 7)): NumberSelector(NumberSelectorConfig(min=0, max=10, step=1)),
                vol.Optional(CONF_ALLOWED_MODELS, default=self.options.get(CONF_ALLOWED_MODELS, "")): TextSelector(),
                vol.Optional(CONF_TEMPERATURE, default=self.options.get(CONF_TEMPERATURE, 0.2)): NumberSelector(NumberSelectorConfig(min=0, max=2, step=0.1)),
                vol.Optional(CONF_PROMPT, description={"suggested_value": self.options.get(CONF_PROMPT)}): TemplateSelector(),
                vol.Optional(CONF_LLM_HASS_API, default=self.options.get(CONF_LLM_HASS_API, [])): SelectSelector(SelectSelectorConfig(options=hass_apis, multiple=True)),
                vol.Optional(CONF_WEB_SEARCH, default=self.options.get(CONF_WEB_SEARCH, False)): BooleanSelector(),
            }),
        )


class AITaskFlow(OpenRouterSubentryFlow):
    defaults = RECOMMENDED_AI_TASK_OPTIONS
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        if self._get_entry().state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="entry_not_loaded")
        if user_input is not None:
            return await self._save(user_input, "OpenRouter AI Tasks")
        try:
            models, _ = await self._async_choices()
        except OpenRouterAPIError:
            return self.async_abort(reason="cannot_connect")
        return self.async_show_form(step_id="init", data_schema=vol.Schema({
            vol.Required(CONF_MODEL, default=self.options.get(CONF_MODEL)): SelectSelector(SelectSelectorConfig(options=models, mode=SelectSelectorMode.DROPDOWN, sort=True)),
            vol.Optional(CONF_IMAGE_MODEL, default=self.options.get(CONF_IMAGE_MODEL)): SelectSelector(SelectSelectorConfig(options=models, mode=SelectSelectorMode.DROPDOWN, custom_value=True)),
        }))


class STTFlow(OpenRouterSubentryFlow):
    defaults = RECOMMENDED_STT_OPTIONS
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        if self._get_entry().state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="entry_not_loaded")
        if user_input is not None:
            return await self._save(user_input, "OpenRouter Speech-to-Text")
        models, _ = await self._async_choices()
        return self.async_show_form(step_id="init", data_schema=vol.Schema({vol.Required(CONF_STT_MODEL, default=self.options.get(CONF_STT_MODEL)): SelectSelector(SelectSelectorConfig(options=models, mode=SelectSelectorMode.DROPDOWN, custom_value=True))}))


class TTSFlow(OpenRouterSubentryFlow):
    defaults = RECOMMENDED_TTS_OPTIONS
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        if self._get_entry().state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="entry_not_loaded")
        if user_input is not None:
            return await self._save(user_input, "OpenRouter Text-to-Speech")
        models, _ = await self._async_choices()
        return self.async_show_form(step_id="init", data_schema=vol.Schema({
            vol.Required(CONF_TTS_MODEL, default=self.options.get(CONF_TTS_MODEL)): SelectSelector(SelectSelectorConfig(options=models, mode=SelectSelectorMode.DROPDOWN, custom_value=True)),
            vol.Required(CONF_VOICE, default=self.options.get(CONF_VOICE, "alloy")): str,
        }))
