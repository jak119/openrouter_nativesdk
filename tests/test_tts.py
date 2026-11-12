"""Tests for the TTS entity without requiring a Home Assistant installation."""
import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


def load_tts_entity():
    """Load the platform with minimal Home Assistant and integration stubs."""
    def module(name, **attributes):
        stub = ModuleType(name)
        stub.__dict__.update(attributes)
        sys.modules[name] = stub
        return stub

    class Entity:
        _attr_has_entity_name = True
        _attr_name = None

        def __init__(self, entry, subentry):
            self.entry = entry
            self.subentry = subentry
            self.client = entry.runtime_data
            self._attr_unique_id = subentry.subentry_id

        @property
        def name(self):
            return self._attr_name

    class TTSEntity:
        pass

    module("homeassistant")
    module("homeassistant.components")
    module("homeassistant.components.tts", ATTR_VOICE="voice", TextToSpeechEntity=TTSEntity, TtsAudioType=tuple)
    module("homeassistant.config_entries", ConfigEntry=object, ConfigSubentry=object)
    module("homeassistant.const", CONF_MODEL="model")
    module("homeassistant.core", HomeAssistant=object)
    module("homeassistant.exceptions", HomeAssistantError=Exception)
    module("homeassistant.helpers")
    module("homeassistant.helpers.entity_platform", AddConfigEntryEntitiesCallback=object)
    module("_test_openrouter")
    module("_test_openrouter.api", OpenRouterAPIError=Exception)
    module("_test_openrouter.audio", to_ha_audio=lambda data, content_type: (content_type, data))
    module(
        "_test_openrouter.const",
        CONF_INSTRUCTIONS="instructions",
        CONF_RESPONSE_FORMAT="response_format",
        CONF_SPEED="speed",
        CONF_VOICE="voice",
    )
    module("_test_openrouter.entity", OpenRouterLLMEntity=Entity)

    path = Path(__file__).parent.parent / "custom_components" / "openrouter_nativesdk" / "tts.py"
    spec = importlib.util.spec_from_file_location("_test_openrouter.tts", path)
    platform = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(platform)
    return platform.OpenRouterTTSEntity


class TestTTSEntity(unittest.TestCase):
    def test_tts_engine_has_subentry_name(self):
        with patch.dict(sys.modules):
            entity_class = load_tts_entity()
            for title in ("Voxtral TTS", "Custom voice"):
                with self.subTest(title=title):
                    entry = SimpleNamespace(runtime_data=object())
                    subentry = SimpleNamespace(title=title, subentry_id="test-id", data={"model": "test/model"})
                    entity = entity_class(entry, subentry)

                    self.assertEqual(entity.name, title)
                    self.assertFalse(entity._attr_has_entity_name)
                    self.assertEqual(entity._attr_unique_id, "test-id")


if __name__ == "__main__":
    unittest.main()
