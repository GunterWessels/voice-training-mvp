import base64
import json
import logging
import re
from typing import Dict, Any, List

from ai_service import AIService
from database import Database
from elevenlabs_service import ElevenLabsService

logger = logging.getLogger(__name__)

NARRATOR_VOICE_ID = "onwK4e9ZLuTAKqWW03F9"  # Daniel — deep, dramatic

NARRATOR_VOICE_SETTINGS = {
    "voice_id": NARRATOR_VOICE_ID,
    "stability": 0.75,
    "similarity_boost": 0.85,
    "style": 0.4,
    "use_speaker_boost": True,
}

FALLBACK_ROAST: Dict[str, Any] = {
    "genre": "Elevator Bossa Nova",
    "genre_emoji": "🛗",
    "character_type": "The Mystery Rep",
    "judgment": "Something happened. We're not sure what",
    "quote": "...",
    "audio_base64": None,
}

REQUIRED_FIELDS = {"genre", "genre_emoji", "character_type", "judgment", "quote", "tts_script"}

SYSTEM_PROMPT = """You are the Derp-Top-40 DJ. A salesperson just finished a role-play session.
Analyze the transcript and return ONLY a valid JSON object with exactly these fields — no markdown, no explanation:

{
  "genre": <one of: "Country Lament", "Death Metal", "Smooth Jazz", "80s Power Ballad", "Polka", "Elevator Bossa Nova", "Sea Shanty", "Gregorian Chant">,
  "genre_emoji": <matching emoji for the genre>,
  "character_type": <rep archetype, max 4 words, starting with "The", e.g. "The Assumption Artist">,
  "judgment": <one punchy sentence judging the rep, max 12 words, no period>,
  "quote": <single most cringe-worthy, ironic, or awkward verbatim rep line from the transcript>,
  "tts_script": <30-word dramatic narrator script. Weave in genre tone, judgment, and the quote as the hook. Use ellipses for pacing.>
}

Genre selection:
- Bad discovery or wrong assumptions → Country Lament 🤠
- Price objection fumbled or immediate self-discount → Death Metal 🤘
- Ghost prospect or non-responsive buyer → Smooth Jazz 🎷
- Feature dump monologue → 80s Power Ballad 🎸
- Talking over or interrupting the buyer → Polka 🪗
- Nervous filler words (um, so, basically, kind of) → Elevator Bossa Nova 🛗
- Unprompted "we're the best" pitch → Sea Shanty ⚓
- Existential loss, total silence, or complete confusion → Gregorian Chant 🕯️"""


class RoastService:
    def __init__(self):
        self.db = Database()
        self.ai_service = AIService()
        self.elevenlabs = ElevenLabsService()

    def _format_transcript(self, messages: list) -> str:
        lines = []
        for msg in messages:
            speaker = "Rep" if msg["speaker"] == "user" else "Buyer"
            lines.append(f"{speaker}: {msg['text']}")
        return "\n".join(lines)

    def _parse_claude_response(self, raw: str) -> Dict[str, Any]:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.DOTALL)
        try:
            data = json.loads(cleaned)
            if not REQUIRED_FIELDS.issubset(data.keys()):
                logger.warning("Claude response missing required fields — using fallback")
                return dict(FALLBACK_ROAST)
            return data
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Claude JSON parse failed: {e} — using fallback")
            return dict(FALLBACK_ROAST)

    async def _call_claude(self, transcript: str) -> str:
        # _call_provider signature: (messages, max_tokens, temperature)
        # System prompt is passed as the first message with role "system"
        user_message = f"Here is the sales role-play transcript:\n\n{transcript}"
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]
        return await self.ai_service._call_provider(
            messages=messages,
            max_tokens=250,
            temperature=0.4,
        )

    async def generate(self, session_id: str) -> Dict[str, Any]:
        messages = self.db.get_messages(session_id)

        if not messages:
            logger.warning(f"No messages found for session {session_id} — using fallback")
            return dict(FALLBACK_ROAST)

        transcript = self._format_transcript(messages)

        try:
            raw = await self._call_claude(transcript)
            roast = self._parse_claude_response(raw)
        except Exception as e:
            logger.error(f"Claude call failed: {e}")
            roast = dict(FALLBACK_ROAST)

        tts_script = roast.get("tts_script")
        audio_base64 = None

        if tts_script:
            try:
                audio_bytes = await self.elevenlabs.text_to_speech(
                    text=tts_script,
                    voice_settings=NARRATOR_VOICE_SETTINGS,
                )
                if audio_bytes:
                    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
            except Exception as e:
                logger.error(f"ElevenLabs TTS failed: {e}")

        return {
            "genre": roast.get("genre", FALLBACK_ROAST["genre"]),
            "genre_emoji": roast.get("genre_emoji", FALLBACK_ROAST["genre_emoji"]),
            "character_type": roast.get("character_type", FALLBACK_ROAST["character_type"]),
            "judgment": roast.get("judgment", FALLBACK_ROAST["judgment"]),
            "quote": roast.get("quote", FALLBACK_ROAST["quote"]),
            "audio_base64": audio_base64,
        }
