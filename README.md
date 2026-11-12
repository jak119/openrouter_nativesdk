# OpenRouter Enhanced for Home Assistant

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/jak119/openrouter-enhanced)

A HACS custom component that exposes OpenRouter's model routers and associated settings to Home Assistant. It provides:

- **Conversation agent** for Assist, with Home Assistant tool calling and image attachments.
- **AI Task** entity for `ai_task.generate_data`, including structured output.
- **Text-to-speech** entity backed by OpenRouter's `/audio/speech` endpoint, usable from Assist pipelines and `tts.speak`.

The conversation agent and AI task are configured the same way, so routing behaves identically for chat and tasks.

## Routing options

Each conversation agent or AI task subentry has these options:

| Option | What it does |
| - | - |
| Model or router | A router (`openrouter/auto`, `openrouter/auto-beta`, `typesafe/jev-router`, or any `<author>/auto` alias such as `anthropic/auto`) or a fixed model slug. |
| Cost tier | `low`, `medium` or `high` router policy. Leave empty for the router's default. |
| Allowed models | Slugs or wildcard patterns such as `anthropic/*`. The Auto Router treats this as a hard limit. Jev treats it as a preference and falls back to the full pool when nothing it matches can be routed. |
| Excluded models | Patterns the router never selects. Always enforced. |
| Web search | Adds OpenRouter's `openrouter:web_search` server tool so the model can search when it needs current information. On by default; searches are billed by OpenRouter. |

The integration sends the matching plugin id for the selected router (`auto-router`, `auto-beta-router` or `jev-router`). Cost tier and the model lists are ignored for fixed models. Jev requires a workspace with access to it; otherwise OpenRouter returns a 404, and the error message is shown in Home Assistant.

Your account defaults on OpenRouter's [Routing page](https://openrouter.ai/settings/routing) still apply, and request settings override them unless "prevent overrides" is on.

## Text-to-speech

New entries get a TTS subentry using `mistralai/voxtral-mini-tts-2603` with the `en_paul_neutral` voice and MP3 output. Entries created before TTS support, or entries that want more voices, can add one from the entry's menu with **Add text-to-speech**. It reuses the entry's API key.

| Option | What it does |
| - | - |
| Model | Any OpenRouter speech model, such as `openai/gpt-4o-mini-tts-2025-12-15` or `google/gemini-3.8-flash-tts`. |
| Voice | Provider-specific voice ID, such as `alloy` (OpenAI) or `Kore` (Gemini). The `voice` option of `tts.speak` overrides it per call. |
| Delivery instructions | Tone or pacing guidance for models that support it (OpenAI gpt-4o-mini-tts, Gemini, Fish Audio). Gemini requires it. The `instructions` option overrides it per call. |
| Audio format | `mp3` or `pcm`. Leave empty for the model's default; some models only return one. PCM is wrapped as WAV for playback. |
| Speed | Playback speed multiplier for models that support it. |

## Coexistence with Home Assistant Core

This custom component uses the distinct `openrouter_nativesdk` domain, so it can run alongside Home Assistant's built-in OpenRouter integration.

## Installation

Install through HACS by adding `https://github.com/jak119/openrouter-enhanced` as a custom repository with category **Integration**, or copy `custom_components/openrouter_nativesdk` into the Home Assistant configuration directory. Restart Home Assistant, then add **OpenRouter Enhanced** under Settings → Devices & services and enter an OpenRouter API key.

## Privacy

Conversation text, selected Home Assistant tool schemas and image attachments are sent to OpenRouter and the provider it selects. Conversation IDs are sent as OpenRouter session IDs so routers keep a conversation on the same model. Image attachments are limited to 10 MB and must have an image MIME type. Text sent to the TTS entity is sent to OpenRouter and the speech provider it selects.

## Development

```sh
pip install ".[test]" ruff
ruff check custom_components/
pytest tests/
```
