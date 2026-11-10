"""Tests for converting /audio/speech responses to playable audio."""
import importlib.util
import io
import wave
from pathlib import Path

import pytest

# Load audio.py directly so the Home Assistant-dependent package __init__ is not imported.
_PATH = Path(__file__).parent.parent / "custom_components" / "openrouter_nativesdk" / "audio.py"
_spec = importlib.util.spec_from_file_location("audio", _PATH)
audio = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audio)

PCM = b"\x00\x01" * 480


def _read_wav(data):
    with wave.open(io.BytesIO(data)) as wav:
        return wav.getframerate(), wav.getnchannels(), wav.getsampwidth(), wav.readframes(wav.getnframes())


@pytest.mark.parametrize("content_type", ["audio/mpeg", "audio/MPEG; charset=binary", "audio/mp3"])
def test_mp3_passthrough(content_type):
    assert audio.to_ha_audio(b"ID3data", content_type) == ("mp3", b"ID3data")


def test_wav_passthrough():
    assert audio.to_ha_audio(b"RIFF", "audio/wav") == ("wav", b"RIFF")


def test_pcm_with_params():
    extension, data = audio.to_ha_audio(PCM, "audio/pcm;rate=16000;channels=2")
    assert extension == "wav"
    assert _read_wav(data) == (16000, 2, 2, PCM)


def test_pcm_defaults():
    extension, data = audio.to_ha_audio(PCM, "audio/pcm")
    assert extension == "wav"
    assert _read_wav(data) == (24000, 1, 2, PCM)


def test_bad_rate_falls_back():
    _, data = audio.to_ha_audio(PCM, "audio/L16; rate=abc")
    assert _read_wav(data)[0] == 24000


@pytest.mark.parametrize("content_type", ["", "application/octet-stream", "audio/ogg"])
def test_unsupported_type(content_type):
    with pytest.raises(ValueError):
        audio.to_ha_audio(b"x", content_type)
