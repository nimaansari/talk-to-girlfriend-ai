"""Call mode abstraction for voice-first girlfriend AI.

Telegram's public/Telethon userbot APIs are not a reliable foundation for
native Telegram voice/video calls. This module keeps call orchestration separate
from the conversation engine so a real transport (LiveKit, Daily, WebRTC app,
Tavus, HeyGen, etc.) can be plugged in later without rewriting the agent.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, Field


class CallMode(str, Enum):
    VOICE = "voice"
    VIDEO = "video"
    AVATAR = "avatar"


class CallStatus(str, Enum):
    STARTING = "starting"
    ACTIVE = "active"
    STOPPED = "stopped"
    ERROR = "error"


class CallSession(BaseModel):
    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    chat_id: str
    mode: CallMode = CallMode.VOICE
    status: CallStatus = CallStatus.STARTING
    transport: str = "telegram-coordination"
    join_url: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    stopped_at: Optional[datetime] = None
    note: str = "Telegram native live calls are scaffolded via an external realtime transport."


class CallTransport(ABC):
    @abstractmethod
    async def start(self, chat_id: str, mode: CallMode) -> CallSession:
        """Start a realtime session and return join/session metadata."""

    @abstractmethod
    async def stop(self, session_id: str) -> CallSession:
        """Stop a realtime session."""

    @abstractmethod
    async def stream_input(self, session_id: str, audio_chunk: bytes) -> None:
        """Accept microphone/audio chunks from the transport."""

    @abstractmethod
    async def stream_output(self, session_id: str, audio_chunk: bytes) -> None:
        """Send synthesized audio chunks back through the transport."""

    @abstractmethod
    async def interrupt(self, session_id: str) -> None:
        """Handle barge-in / turn-taking interruption."""


class TelegramCoordinationTransport(CallTransport):
    """Working fallback transport scaffold.

    It creates a session record and lets Telegram coordinate text/voice-note
    messages while a future browser/WebRTC transport handles realtime audio.
    """

    def __init__(self):
        self.sessions: Dict[str, CallSession] = {}

    async def start(self, chat_id: str, mode: CallMode) -> CallSession:
        session = CallSession(chat_id=str(chat_id), mode=mode, status=CallStatus.ACTIVE)
        self.sessions[session.session_id] = session
        return session

    async def stop(self, session_id: str) -> CallSession:
        session = self.sessions.get(session_id)
        if not session:
            raise KeyError(f"Unknown call session: {session_id}")
        session.status = CallStatus.STOPPED
        session.stopped_at = datetime.now(timezone.utc)
        return session

    async def stream_input(self, session_id: str, audio_chunk: bytes) -> None:
        if session_id not in self.sessions:
            raise KeyError(f"Unknown call session: {session_id}")
        # TODO: route audio chunks into STT/conversation engine.

    async def stream_output(self, session_id: str, audio_chunk: bytes) -> None:
        if session_id not in self.sessions:
            raise KeyError(f"Unknown call session: {session_id}")
        # TODO: route TTS chunks into WebRTC/LiveKit/Daily transport.

    async def interrupt(self, session_id: str) -> None:
        if session_id not in self.sessions:
            raise KeyError(f"Unknown call session: {session_id}")
        # TODO: cancel current TTS playback / model generation for barge-in.


class CallService:
    def __init__(self, transport: Optional[CallTransport] = None):
        self.transport = transport or TelegramCoordinationTransport()

    async def start_session(self, chat_id: str, mode: CallMode = CallMode.VOICE) -> CallSession:
        return await self.transport.start(chat_id, mode)

    async def stop_session(self, session_id: str) -> CallSession:
        return await self.transport.stop(session_id)

    async def interrupt(self, session_id: str) -> None:
        await self.transport.interrupt(session_id)


call_service = CallService()
