# OpenRouter Enhanced for Home Assistant

An experimental HACS custom component using OpenRouter's official Python SDK. It exposes OpenRouter models and routing to Home Assistant Assist, including Auto Router, presets, multimodal conversation, speech-to-text, text-to-speech, AI tasks, and image generation.

## Coexistence with Home Assistant Core

This custom component uses the distinct `openrouter_nativesdk` domain, so it can run alongside Home Assistant's built-in OpenRouter integration. Existing built-in OpenRouter entries are not changed or migrated.

## Installation

Install through HACS as a custom repository with category **Integration**, or copy `custom_components/openrouter_nativesdk` into the Home Assistant configuration directory. Restart Home Assistant, then add **OpenRouter Enhanced** under Settings → Devices & services.

An OpenRouter API key and account with available credits may be required. Models, voices, audio formats, and image options are provider-dependent.

## Image generation

Image generation is exposed through Home Assistant's built-in `ai_task.generate_image` action. Generated files are stored through Home Assistant's media source and returned as a media source ID and signed URL; raw provider payloads are not published to the event bus.

## Privacy

Conversation text, selected Home Assistant tool schemas, audio sent for transcription, and image attachments are sent to OpenRouter and the provider it selects. Conversation IDs are used as OpenRouter session IDs to keep Auto Router selections sticky within a conversation. Image attachments are limited to 10 MB and must have an image MIME type.

## Development

Use Home Assistant's supported Python version and `uv` to create a virtual environment. Run the integration tests and static checks before publishing. The official SDK documentation is at https://openrouter.ai/docs/client-sdks/overview.
