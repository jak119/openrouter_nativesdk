# Repository guide

## Build, test, and lint

The project targets Python 3.13. Install the test extra and Ruff with:

```sh
pip install ".[test]" ruff
```

Run the same checks as CI:

```sh
ruff check custom_components/
pytest tests/
```

Run a single test file or test case with pytest, for example:

```sh
pytest tests/test_routing.py
pytest tests/test_routing.py::test_plugin_id
```

## Architecture

- This is a Home Assistant custom integration. Its domain is `openrouter_nativesdk` (distinct from Home Assistant's built-in OpenRouter integration).
- A config entry owns the API key and one shared `OpenRouterAPI` client in `entry.runtime_data`. Conversation, AI-task, and TTS configurations are separate config subentries, each creating its corresponding platform entity.
- `config_flow.py` handles account setup/reauthentication and subentry model/options selection. `__init__.py` validates the key, initializes the shared client, manages Repairs issues, and forwards setup/unload to all three platforms.
- Conversation and AI-task entities share `OpenRouterLLMEntity` in `entity.py`, which builds chat payloads, serializes Home Assistant conversation content and tool schemas, and handles attachments. `conversation.py` processes tool-call rounds; `ai_task.py` adds structured JSON-schema output.
- TTS uses the same client and entity base, with speech response conversion isolated in `audio.py`; raw PCM is wrapped as WAV for Home Assistant playback.
- `api.py` is the HTTP boundary to OpenRouter and uses Home Assistant's shared aiohttp session. It translates transport, HTTP, and authentication failures into `OpenRouterAPIError` / `OpenRouterAuthError`.

## Repository-specific conventions

- Keep router selection behavior in the Home-Assistant-independent helpers in `routing.py`: fixed models do not get router plugins; router-specific options belong on the matching plugin. Keep `audio.py` similarly independent for audio-format conversion.
- Platform setup iterates `entry.subentries` and filters by `subentry_type`; associate each created entity with its `config_subentry_id`. Shared model behavior belongs in `OpenRouterLLMEntity`, while platform-specific behavior belongs in its platform module.
- Tests intentionally load pure helper modules directly and stub Home Assistant for platform tests, so these tests can run without installing Home Assistant. Preserve that boundary when adding focused tests.
- Keep user-facing config-flow strings and issue text in `strings.json` and `translations/en.json`; config and selector keys should use the existing constants in `const.py`.
- The release workflow keeps the integration version in `custom_components/openrouter_nativesdk/manifest.json` and `pyproject.toml` aligned; update both when changing the version.
