"""Turn /audio/speech responses into audio Home Assistant can play."""
from __future__ import annotations

import io
import wave

PCM_RATE = 24000
PCM_CHANNELS = 1
PCM_SAMPLE_WIDTH = 2  # 16-bit little-endian


def to_ha_audio(data: bytes, content_type: str) -> tuple[str, bytes]:
    """Return (extension, bytes), wrapping raw PCM in a WAV header."""
    mime, *raw_params = (part.strip() for part in content_type.split(";"))
    mime = mime.lower()
    if mime in ("audio/mpeg", "audio/mp3"):
        return "mp3", data
    if mime in ("audio/wav", "audio/x-wav", "audio/wave"):
        return "wav", data
    if mime in ("audio/pcm", "audio/l16"):
        params = dict(param.lower().split("=", 1) for param in raw_params if "=" in param)
        return "wav", pcm_to_wav(data, _int(params.get("rate"), PCM_RATE), _int(params.get("channels"), PCM_CHANNELS))
    raise ValueError(f"Unsupported audio type: {content_type or 'missing'}")


def pcm_to_wav(data: bytes, rate: int = PCM_RATE, channels: int = PCM_CHANNELS) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(PCM_SAMPLE_WIDTH)
        wav.setframerate(rate)
        wav.writeframes(data)
    return buffer.getvalue()


def _int(value: str | None, default: int) -> int:
    try:
        return int(value) if value else default
    except ValueError:
        return default
