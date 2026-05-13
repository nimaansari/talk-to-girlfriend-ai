"""TTS provider abstraction and Telegram voice delivery helpers.

The first production provider is ElevenLabs. OpenAI and other providers can be
added without changing Telegram or agent flow code.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger("girlfriend_ai.tts")


class TTSSettings(BaseModel):
    provider: str = Field(default_factory=lambda: os.getenv("TTS_PROVIDER", "elevenlabs").lower())
    api_key: str = Field(default_factory=lambda: os.getenv("TTS_API_KEY", ""))
    voice_id: str = Field(default_factory=lambda: os.getenv("TTS_VOICE_ID", ""))
    model: str = Field(default_factory=lambda: os.getenv("TTS_MODEL", "eleven_multilingual_v2"))
    output_format: str = Field(default_factory=lambda: os.getenv("TTS_OUTPUT_FORMAT", "ogg_opus"))
    temp_dir: Path = Field(default_factory=lambda: Path(os.getenv("TTS_TEMP_DIR", tempfile.gettempdir())))
    timeout_seconds: float = Field(default_factory=lambda: float(os.getenv("TTS_TIMEOUT_SECONDS", "45")))
    retries: int = Field(default_factory=lambda: int(os.getenv("TTS_RETRIES", "2")))


class TTSResult(BaseModel):
    path: Path
    mime_type: str
    provider: str


class TTSProvider(ABC):
    def __init__(self, settings: TTSSettings):
        self.settings = settings

    @abstractmethod
    async def synthesize_to_file(self, text: str, *, voice_id: Optional[str] = None) -> TTSResult:
        """Convert text to speech and return a temporary audio file."""


class ElevenLabsTTSProvider(TTSProvider):
    API_BASE = "https://api.elevenlabs.io/v1"

    async def synthesize_to_file(self, text: str, *, voice_id: Optional[str] = None) -> TTSResult:
        if not self.settings.api_key:
            raise RuntimeError("TTS_API_KEY is required for ElevenLabs TTS")
        selected_voice = voice_id or self.settings.voice_id
        if not selected_voice:
            raise RuntimeError("TTS_VOICE_ID is required for ElevenLabs TTS")

        output_format = self.settings.output_format or "ogg_opus"
        url = f"{self.API_BASE}/text-to-speech/{selected_voice}"
        params = {"output_format": output_format}
        payload = {
            "text": text,
            "model_id": self.settings.model or "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.45,
                "similarity_boost": 0.8,
                "style": 0.35,
                "use_speaker_boost": True,
            },
        }
        headers = {
            "xi-api-key": self.settings.api_key,
            "Accept": "audio/mpeg" if output_format.startswith("mp3") else "audio/ogg",
            "Content-Type": "application/json",
        }

        audio = await _request_bytes_with_retries(
            "POST",
            url,
            headers=headers,
            params=params,
            json=payload,
            timeout=self.settings.timeout_seconds,
            retries=self.settings.retries,
        )
        return _write_temp_audio(audio, provider="elevenlabs", output_format=output_format, temp_dir=self.settings.temp_dir)


class OpenAITTSProvider(TTSProvider):
    """Minimal OpenAI-compatible provider scaffold.

    Kept modular so switching providers later is a config change plus optional
    tuning, not an agent rewrite.
    """

    API_BASE = "https://api.openai.com/v1/audio/speech"

    async def synthesize_to_file(self, text: str, *, voice_id: Optional[str] = None) -> TTSResult:
        if not self.settings.api_key:
            raise RuntimeError("TTS_API_KEY is required for OpenAI TTS")
        output_format = self.settings.output_format or "mp3"
        payload = {
            "model": self.settings.model or "gpt-4o-mini-tts",
            "voice": voice_id or self.settings.voice_id or "alloy",
            "input": text,
            "format": "mp3" if output_format in {"mp3", "mpeg"} else output_format,
        }
        audio = await _request_bytes_with_retries(
            "POST",
            self.API_BASE,
            headers={"Authorization": f"Bearer {self.settings.api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=self.settings.timeout_seconds,
            retries=self.settings.retries,
        )
        return _write_temp_audio(audio, provider="openai", output_format=output_format, temp_dir=self.settings.temp_dir)


def get_tts_provider(settings: Optional[TTSSettings] = None) -> TTSProvider:
    settings = settings or TTSSettings()
    provider = settings.provider.lower()
    if provider in {"elevenlabs", "eleven_labs", "11labs"}:
        return ElevenLabsTTSProvider(settings)
    if provider in {"openai", "openai_tts"}:
        return OpenAITTSProvider(settings)
    raise RuntimeError(f"Unsupported TTS_PROVIDER: {settings.provider}")


async def text_to_speech_file(text: str, *, voice_id: Optional[str] = None, settings: Optional[TTSSettings] = None) -> TTSResult:
    if not text or not text.strip():
        raise ValueError("Cannot synthesize empty text")
    provider = get_tts_provider(settings)
    return await provider.synthesize_to_file(text.strip(), voice_id=voice_id)


def cleanup_temp_file(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except Exception as exc:
        logger.warning("Failed to remove temp audio file %s: %s", path, exc)


def _extension_for_format(output_format: str) -> tuple[str, str]:
    fmt = output_format.lower()
    if "ogg" in fmt or "opus" in fmt:
        return ".ogg", "audio/ogg"
    if "wav" in fmt:
        return ".wav", "audio/wav"
    return ".mp3", "audio/mpeg"


def _write_temp_audio(audio: bytes, *, provider: str, output_format: str, temp_dir: Path) -> TTSResult:
    if not audio:
        raise RuntimeError("TTS provider returned empty audio")
    suffix, mime_type = _extension_for_format(output_format)
    temp_dir.mkdir(parents=True, exist_ok=True)
    path = temp_dir / f"girlfriend-ai-{provider}-{uuid.uuid4().hex}{suffix}"
    path.write_bytes(audio)
    return TTSResult(path=path, mime_type=mime_type, provider=provider)


async def _request_bytes_with_retries(method: str, url: str, *, retries: int, timeout: float, **kwargs) -> bytes:
    last_error: Optional[Exception] = None
    attempts = max(1, retries + 1)
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(attempts):
            try:
                response = await client.request(method, url, **kwargs)
                if response.status_code == 429 or 500 <= response.status_code < 600:
                    response.raise_for_status()
                if response.status_code >= 400:
                    raise RuntimeError(f"TTS provider error {response.status_code}: {response.text[:500]}")
                return response.content
            except Exception as exc:
                last_error = exc
                if attempt >= attempts - 1:
                    break
                delay = min(2 ** attempt, 8)
                logger.warning("TTS request failed, retrying in %ss: %s", delay, exc)
                await asyncio.sleep(delay)
    raise RuntimeError(f"TTS request failed after {attempts} attempt(s): {last_error}")
