import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from call_service import CallMode, CallService
from tts_service import TTSSettings, _extension_for_format, cleanup_temp_file, text_to_speech_file


class TTSServiceTests(unittest.TestCase):
    def test_extension_mapping(self):
        self.assertEqual(_extension_for_format("ogg_opus"), (".ogg", "audio/ogg"))
        self.assertEqual(_extension_for_format("mp3_44100_128"), (".mp3", "audio/mpeg"))
        self.assertEqual(_extension_for_format("wav"), (".wav", "audio/wav"))

    def test_elevenlabs_provider_writes_temp_audio(self):
        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                settings = TTSSettings(
                    provider="elevenlabs",
                    api_key="test-key",
                    voice_id="test-voice",
                    output_format="ogg_opus",
                    temp_dir=Path(tmp),
                    retries=0,
                )
                with patch("tts_service._request_bytes_with_retries", new=AsyncMock(return_value=b"audio-bytes")):
                    result = await text_to_speech_file("hey love", settings=settings)
                self.assertTrue(result.path.exists())
                self.assertEqual(result.mime_type, "audio/ogg")
                self.assertEqual(result.path.read_bytes(), b"audio-bytes")
                cleanup_temp_file(result.path)
                self.assertFalse(result.path.exists())

        asyncio.run(run())


class CallServiceTests(unittest.TestCase):
    def test_start_and_stop_call_session(self):
        async def run():
            service = CallService()
            session = await service.start_session("@her", CallMode.VOICE)
            self.assertEqual(session.status, "active")
            stopped = await service.stop_session(session.session_id)
            self.assertEqual(stopped.status, "stopped")
            self.assertIsNotNone(stopped.stopped_at)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
