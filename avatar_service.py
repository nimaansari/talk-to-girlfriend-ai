"""Optional avatar/video provider interfaces.

This repo intentionally does not pretend Telegram-native video calls are solved.
Use these interfaces to plug in Tavus, HeyGen, LiveKit, Daily, or a custom
WebRTC/browser frontend later.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel


class AvatarSession(BaseModel):
    session_id: str
    provider: str
    join_url: Optional[str] = None
    status: str = "created"


class AvatarProvider(ABC):
    @abstractmethod
    async def create_session(self, *, audio_session_id: str, persona: str) -> AvatarSession:
        """Create an avatar/video session bound to a realtime voice session."""

    @abstractmethod
    async def stop_session(self, session_id: str) -> None:
        """Stop an avatar/video session."""


class BrowserAvatarProvider(AvatarProvider):
    """Placeholder for a browser/WebRTC avatar frontend."""

    async def create_session(self, *, audio_session_id: str, persona: str) -> AvatarSession:
        return AvatarSession(
            session_id=audio_session_id,
            provider="browser-webrtc-placeholder",
            join_url=None,
            status="scaffolded",
        )

    async def stop_session(self, session_id: str) -> None:
        return None
