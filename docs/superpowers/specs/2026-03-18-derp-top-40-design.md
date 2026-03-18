# Derp Top 40 — Design Spec
**Date:** 2026-03-18
**Status:** Approved
**Scope:** Voice Training MVP — post-session roast generator

---

## Overview

After a sales role-play session ends, the platform automatically analyzes the conversation transcript, assigns a genre and character archetype to the rep's performance, extracts the most cringe-worthy quote, and synthesizes a 7-second dramatic narrator audio ditty. A "Now Playing" card surfaces in the UI with auto-play audio and a one-click share button.

---

## Trigger

Session end — the frontend's WebSocket `onclose` handler fires `POST /sessions/{id}/roast` immediately after disconnect. No manual action required from the user.

---

## Architecture

Three new components. Nothing existing is modified except adding one endpoint to `main.py` and one `onclose` handler in the frontend.

### 1. `roast_service.py` (new backend service)

Responsible for the full analysis-to-audio pipeline:

1. Pull `messages[]` for the session from SQLite
2. Call Claude with the Derp Top 40 analysis prompt → structured JSON
3. Call ElevenLabs TTS with the `tts_script` field → audio bytes
4. Return result dict

No database persistence. The roast is ephemeral — generated once, shown once.

### 2. `POST /sessions/{id}/roast` (new endpoint in `main.py`)

Calls `RoastService.generate(session_id)`. Returns:

```json
{
  "genre": "Death Metal",
  "genre_emoji": "🤘",
  "character_type": "The Price Dropper",
  "judgment": "He came in with a price. Left with a lower one. Nobody asked.",
  "quote": "I mean, we could probably do something on the cost side.",
  "audio_base64": "<base64-encoded mp3>"
}
```

### 3. `RoastCard` (new React component)

Renders on session end. Three states: LOADING → PLAYING → SHARED.

---

## Claude Analysis Prompt

Single call via the existing `AIService` (OpenAI-first, Anthropic fallback). `max_tokens: 250`. On JSON parse failure, `roast_service.py` catches the exception and returns a hardcoded fallback roast so the frontend always gets a valid response — never a 500.

**Hardcoded fallback:**
```json
{
  "genre": "Elevator Bossa Nova",
  "genre_emoji": "🛗",
  "character_type": "The Mystery Rep",
  "judgment": "Something happened. We're not sure what.",
  "quote": "...",
  "audio_base64": null
}
```
When `audio_base64` is null, RoastCard renders the text card only (no audio bar, no share button).

System prompt:

```
You are the Derp-Top-40 DJ. A salesperson just finished a role-play session.
Analyze the transcript and return JSON with exactly these fields:

{
  "genre": <see genre logic below>,
  "genre_emoji": <matching emoji>,
  "character_type": <rep archetype, max 4 words, e.g. "The Assumption Artist">,
  "judgment": <one punchy sentence, max 12 words>,
  "quote": <single most cringe/ironic/awkward verbatim rep line>,
  "tts_script": <30-word dramatic narrator script layering genre tone + judgment + quote>
}
```

**Genre selection logic:**

| Situation | Genre |
|-----------|-------|
| Bad discovery / wrong assumptions | Country Lament 🤠 |
| Price objection fumbled / immediate discount | Death Metal 🤘 |
| Ghost prospect / non-responsive buyer | Smooth Jazz 🎷 |
| Feature dump monologue | 80s Power Ballad 🎸 |
| Talking over the buyer | Polka 🪗 |
| Nervous filler words (um, so, basically) | Elevator Bossa Nova 🛗 |
| Unprompted "we're the best" pitch | Sea Shanty ⚓ |
| Existential loss / total silence | Gregorian Chant 🕯️ |

**Example TTS script output (Death Metal):**
> "He came in with a price. He left with a lower one. Nobody asked. In his own words: 'I mean, we could probably do something on the cost side.' The Price Dropper. On Death Metal."

---

## ElevenLabs TTS Parameters

- **Voice ID:** `onwK4e9ZLuTAKqWW03F9` (Daniel — deep, dramatic; distinct from all existing persona voices)
- **Voice settings:** `stability: 0.75`, `similarity_boost: 0.85`, `style: 0.4`, `use_speaker_boost: true`
- **Pacing:** Controlled entirely via `tts_script` wording (ellipses, sentence breaks). No `speed` parameter — the v1 ElevenLabs endpoint does not support it.
- **Input:** `tts_script` field from Claude response
- **Output:** mp3 bytes → base64 encoded in API response

**Note on audio response key:** The roast endpoint returns `audio_base64` as a flat top-level field. This intentionally differs from the existing `audio.audio_data` convention used by the WebSocket voice chat path — the roast is a one-shot REST response, not a streaming audio event.

---

## Frontend: RoastCard Component

**File:** `frontend/src/components/RoastCard.js`

**Timeout:** The `/roast` endpoint has a 15-second hard timeout (Claude + ElevenLabs combined). On timeout, the backend returns `HTTP 408` with `{"error": "timeout"}`. RoastCard renders: "The roast machine timed out. Your performance was too much to process." No spinner indefinitely.

**States:**

| State | Display |
|-------|---------|
| LOADING | Spinning 🎙️ + "Generating your roast..." |
| PLAYING | Now Playing card with auto-play audio |
| SHARED | Share button flips to "Copied!" for 2s |
| ERROR | Static fallback message (timeout or parse failure) |

**Card layout (PLAYING state):**
```
┌─────────────────────────────────────────┐
│  🎙️ DERP TOP 40                         │
│  ─────────────────────────────────────  │
│  🤘 DEATH METAL                         │
│                                         │
│  "The Price Dropper"                    │
│  He came in with a price. Left with     │
│  a lower one. Nobody asked.             │
│                                         │
│  ❝ I mean, we could probably do        │
│    something on the cost side. ❞        │
│                                         │
│  ▶ [audio bar / auto-playing]           │
│                                         │
│  [ 📋 Share This Shame ]               │
└─────────────────────────────────────────┘
```

**Share clipboard text format:**
```
🎙️ DERP TOP 40 | 🤘 DEATH METAL
"The Price Dropper"
❝ I mean, we could probably do something on the cost side. ❞
— LiquidSMARTS™ Voice Training
```

**Audio playback:** base64 response decoded to `Blob` → `Audio` element `src` → `.play()` called automatically on card render.

---

## Data Flow

```
Session ends (WebSocket onclose)
  → Frontend: POST /sessions/{id}/roast
  → Backend: pull messages[] from SQLite
  → Claude: analyze transcript → JSON
  → ElevenLabs: tts_script → audio bytes
  → Response: JSON + audio_base64
  → Frontend: decode audio → auto-play + render RoastCard
```

---

## Out of Scope

- Storing roast history in the database
- Multiple roasts per session
- Real-time / mid-session detection
- Music backing track (pure TTS narrator only)
- Admin controls / opt-out per session

---

## Files Changed

| File | Change |
|------|--------|
| `backend/roast_service.py` | New |
| `backend/main.py` | Add `POST /sessions/{id}/roast` endpoint |
| `frontend/src/components/RoastCard.js` | New |
| `frontend/src/App.js` | Wire `onclose` → roast call → RoastCard render |
