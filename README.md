# Telegram AI Dating Agent

# p.s: we broke up after this

A voice-first romantic Telegram agent for girlfriend-style chat: text replies, flirty message help, TTS voice notes, and a practical call-mode scaffold for realtime voice/video integrations.

This keeps the original theme and branding: it is still a girlfriend/dating-style agent, not a generic assistant.

## What Works Now

- Text chat and existing Telegram messaging tools still work
- Reads chats/messages and helps craft romantic, witty, or playful replies
- Searches pickup lines and dating advice through Nia
- Sends normal Telegram text messages
- Sends Telegram audio files and voice-note style replies
- Generates TTS from text through a provider abstraction
- ElevenLabs is implemented as the primary TTS provider
- OpenAI TTS provider scaffold is included for future swapping
- Voice mode toggles in the TypeScript CLI
- Call-mode session scaffold with honest Telegram limitations
- Optional avatar/video provider interfaces for future Tavus/HeyGen/LiveKit/Daily/WebRTC work

## What Is Scaffolded vs Fully Working

Fully working in this repo:

- Existing text chat workflow
- Telegram HTTP bridge endpoints for messages/files
- Telegram `/chats/{chat_id}/voice` endpoint for text-to-speech voice notes
- Telegram `/chats/{chat_id}/audio` endpoint for regular TTS audio files
- ElevenLabs TTS file generation
- Temporary audio file cleanup
- TypeScript tools: `sendVoiceReply`, `sendAudioReply`, `startCallMode`, `stopCallMode`
- CLI commands: `/voice on`, `/voice off`, `/voice status`, `/voice set <voice_id>`

Scaffolded honestly, not faked:

- Native Telegram live voice/video calls
- Realtime streaming audio transport
- Interruption/barge-in turn-taking
- Avatar/video calling frontend

Telegram-native live calls are fragile/not realistically supported through this stack. The practical architecture is: Telegram coordinates the relationship/chat flow, while realtime voice/video should run through a browser/WebRTC transport such as LiveKit, Daily, Tavus, or HeyGen.

## Powered by Nia

This agent uses [Nia](https://trynia.ai) as its knowledge retrieval engine. Nia indexes and searches through:

- 500+ curated pickup lines
- flirting and dating guides
- conversation techniques
- romantic response ideas

You can index your own content by creating a source at [trynia.ai](https://trynia.ai).

## Architecture

```text
┌──────────────────────────┐
│ TypeScript Girlfriend AI │
│ agent / CLI              │
└────────────┬─────────────┘
             │ tools / HTTP
             ▼
┌──────────────────────────┐
│ Python Telegram Bridge   │
│ FastAPI + Telethon        │
└───────┬─────────┬────────┘
        │         │
        │         ▼
        │   ┌──────────────────────┐
        │   │ TTS Service          │
        │   │ ElevenLabs first     │
        │   │ OpenAI-ready adapter │
        │   └──────────┬───────────┘
        │              │ temp audio
        ▼              ▼
┌──────────────────────────────────┐
│ Telegram text / audio / voice    │
└──────────────────────────────────┘

Optional future realtime path:

┌──────────────────┐     ┌──────────────────────────┐
│ Browser/WebRTC   │────▶│ Call Service abstraction │
│ LiveKit/Daily/etc │     │ STT/TTS/turn-taking      │
└──────────────────┘     └──────────────────────────┘
          │
          ▼
┌──────────────────────────┐
│ Tavus / HeyGen / avatar  │
└──────────────────────────┘
```

## Quick Start

### 1. Get Telegram API Credentials

Get your API credentials at [my.telegram.org/apps](https://my.telegram.org/apps).

### 2. Install & Configure

```bash
git clone https://github.com/arlanrakh/talk-to-girlfriend-ai.git
cd talk-to-girlfriend-ai

# Install Python dependencies
uv sync
# or: pip install -r requirements.txt

# Generate Telegram session string
uv run session_string_generator.py

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### 3. Enable ElevenLabs Voice Replies

Create an ElevenLabs API key and choose/clone a voice in ElevenLabs. Then set:

```env
TTS_PROVIDER=elevenlabs
TTS_API_KEY=your_elevenlabs_api_key
TTS_VOICE_ID=your_elevenlabs_voice_id
TTS_MODEL=eleven_multilingual_v2
TTS_OUTPUT_FORMAT=ogg_opus
```

`ogg_opus` is recommended for Telegram voice notes. MP3 can work better for regular audio files.

### 4. Start the Telegram API Bridge

```bash
python telegram_api.py
```

This runs a FastAPI server on port `8765`.

### 5. Run the AI Agent

```bash
cd agent
bun install
bun run dev
```

## Voice Usage Examples

Natural language prompts:

```text
> reply to her last message with voice
> send this as audio to @her_username: i miss your laugh
> turn voice mode on
> send a sweet voice note saying good morning beautiful
```

CLI commands:

```text
/voice on
/voice off
/voice status
/voice set <elevenlabs_voice_id>
```

Direct bridge endpoints:

```bash
curl -X POST http://localhost:8765/chats/@her_username/voice \
  -H 'Content-Type: application/json' \
  -d '{"text":"hey, i was thinking about you", "voice_note": true}'
```

```bash
curl -X POST http://localhost:8765/chats/@her_username/audio \
  -H 'Content-Type: application/json' \
  -d '{"text":"this one is a regular audio file", "voice_note": false}'
```

## Text Usage Examples

```text
> Show me messages from @her_username
> Send "hey, i was just thinking about you" to @her_username
> Reply to her last message with something witty
> React to her last message with ❤️
> Search our chat for "dinner plans"
> Make this message more flirty: "want to hang out tomorrow?"
> Is she online right now?
```

## Environment Variables

Create a `.env` file in the project root:

```env
# Telegram API
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_SESSION_NAME=telegram_session
TELEGRAM_SESSION_STRING=your_session_string
TELEGRAM_API_URL=http://localhost:8765

# AI services
AI_GATEWAY_API_KEY=your_vercel_ai_gateway_key
NIA_API_KEY=your_nia_api_key
NIA_CODEBASE_SOURCE=your_pickup_lines_source_uuid

# TTS / voice replies
TTS_PROVIDER=elevenlabs
TTS_API_KEY=your_elevenlabs_api_key
TTS_VOICE_ID=your_elevenlabs_voice_id
TTS_MODEL=eleven_multilingual_v2
TTS_OUTPUT_FORMAT=ogg_opus
TTS_TIMEOUT_SECONDS=45
TTS_RETRIES=2
# TTS_TEMP_DIR=/tmp
```

## Custom / Cloned Voices

For ElevenLabs:

1. Create or clone a voice in ElevenLabs.
2. Copy the voice ID.
3. Set `TTS_VOICE_ID` in `.env`.
4. Restart `telegram_api.py`.

You can also override voice per message through the voice endpoint or the `sendVoiceReply` tool.

## Provider Swapping

TTS provider logic lives in `tts_service.py`:

- `TTSProvider` interface
- `ElevenLabsTTSProvider`
- `OpenAITTSProvider` scaffold
- `get_tts_provider()` factory

To add another provider, implement `TTSProvider.synthesize_to_file()` and register it in `get_tts_provider()`.

## Live Call Mode

The repo now includes `call_service.py` with interfaces for:

- session start
- session stop
- streaming input
- streaming output
- interruption / turn-taking

Current fallback transport:

- `TelegramCoordinationTransport`
- creates session metadata
- keeps Telegram as the coordination layer
- leaves realtime audio/video to a future browser/WebRTC transport

Endpoints:

```bash
POST /chats/{chat_id}/call/start
POST /call/stop
```

Recommended next step for full realtime calling:

1. Add a browser/WebRTC frontend.
2. Use LiveKit or Daily for realtime audio rooms.
3. Add STT for microphone input.
4. Feed transcripts into the existing girlfriend agent.
5. Stream TTS output back into the room.
6. Optionally connect Tavus or HeyGen for avatar/lip-sync video.

## Optional Avatar / Video Calling

`avatar_service.py` defines provider interfaces for:

- TTS audio output
- animated avatar / lip sync
- browser-based video sessions

Recommended integrations:

- LiveKit for realtime rooms
- Daily for quick hosted calls
- Tavus for conversational avatar video
- HeyGen for avatar/lip-sync video
- a custom WebRTC frontend for maximum control

This is intentionally separated from the Telegram bridge so the project does not pretend Telegram-native video calls are solved.

## Agent Commands

```text
/help          Show help
/clear         Clear conversation history
/status        Check Telegram + voice status
/voice on      Enable voice-mode guidance
/voice off     Disable voice-mode guidance
/voice status  Show voice settings
/voice set ID  Set preferred TTS voice
/quit          Exit
```

## Available Tools

Core messaging:

- `getChats`
- `getMessages`
- `sendMessage`
- `scheduleMessage`
- `getChat`
- `searchContacts`

Voice and calls:

- `sendVoiceReply`
- `sendAudioReply`
- `startCallMode`
- `stopCallMode`

Relationship intelligence:

- `searchPickupLines`
- `niaSearch`
- `webSearch`
- `aiifyMessage`

Telegram extras:

- `sendReaction`
- `replyToMessage`
- `editMessage`
- `deleteMessage`
- `forwardMessage`
- `pinMessage`
- `markAsRead`
- `getUserStatus`
- `getUserPhotos`
- `searchGifs`

## Deployment Topology

Recommended production-ish deployment:

```text
1 VPS / container host
├── Python FastAPI Telegram bridge
│   ├── Telethon session
│   ├── TTS service
│   └── call/avatar scaffolds
├── TypeScript agent process
├── .env secrets mounted securely
└── optional reverse proxy for HTTP bridge if needed
```

Keep the bridge private if possible. If exposing it, put authentication and TLS in front of it.

## Alternative: Use as MCP Server

You can still use this as a standalone MCP server with Claude Desktop or Cursor, without the TypeScript agent.

```json
{
  "mcpServers": {
    "telegram": {
      "command": "uv",
      "args": ["--directory", "/path/to/talk-to-girlfriend-ai", "run", "main.py"]
    }
  }
}
```

## Safety / Privacy Notes

- Keep `.env` out of git.
- Treat Telegram session strings like passwords.
- TTS sends generated text to the configured provider.
- The bridge can send Telegram messages as your account, so do not expose it publicly without auth.

## Development Checks

```bash
python -m py_compile telegram_api.py tts_service.py call_service.py avatar_service.py
python test_validation.py
cd agent && bun install && bun run tsc --noEmit
```

## License

Apache-2.0, inherited from the original project.
