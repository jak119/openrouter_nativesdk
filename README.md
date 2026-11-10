# OpenRouter Enhanced for Home Assistant

An experimental HACS custom component that exposes OpenRouter's model routers to Home Assistant. It provides:

- **Conversation agent** for Assist, with Home Assistant tool calling and image attachments.
- **AI Task** entity for `ai_task.generate_data`, including structured output.

Both are configured the same way, so routing behaves identically for chat and tasks.

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

## Coexistence with Home Assistant Core

This custom component uses the distinct `openrouter_nativesdk` domain, so it can run alongside Home Assistant's built-in OpenRouter integration.

## Installation

Install through HACS as a custom repository with category **Integration**, or copy `custom_components/openrouter_nativesdk` into the Home Assistant configuration directory. Restart Home Assistant, then add **OpenRouter Enhanced** under Settings → Devices & services and enter an OpenRouter API key.

## Privacy

Conversation text, selected Home Assistant tool schemas and image attachments are sent to OpenRouter and the provider it selects. Conversation IDs are sent as OpenRouter session IDs so routers keep a conversation on the same model. Image attachments are limited to 10 MB and must have an image MIME type.

## Development

```sh
pip install ".[test]" ruff
ruff check custom_components/
pytest tests/
```
