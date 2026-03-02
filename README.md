# Voice Training Platform MVP

A simplified, focused voice training platform for MedTech sales professionals.

## Core Philosophy

**Less is more.** Focus on the essential voice training experience without enterprise complexity.

## Architecture

```
Frontend (React) ←→ Backend (FastAPI) ←→ LLM (OpenAI/Anthropic)
                        ↓
                   SQLite Database
```

## Core Features (MVP)

1. **Voice Conversations**: Real-time voice chat with AI personas
2. **Simple Personas**: Pre-built buyer personas (CFO, Clinical Director, etc.)
3. **Basic Scoring**: Simple conversation evaluation
4. **Session History**: Track past conversations
5. **Local Storage**: No complex user management

## What's NOT in MVP

- Complex user management/organizations
- Email notifications
- File uploads
- Complex rubrics
- Bulk imports
- Multi-tenant architecture

## Tech Stack

- **Frontend**: React + Tailwind CSS
- **Backend**: FastAPI (Python)
- **Database**: SQLite (simple, no setup)
- **Voice**: Web Speech API (no external APIs needed)
- **LLM**: OpenAI or Anthropic (single API)

## Quick Start

1. `cd backend && python main.py`
2. `cd frontend && npm start`
3. Open browser and start training

## File Structure

```
voice-training-mvp/
├── backend/
│   ├── main.py          # FastAPI server
│   ├── models.py        # Simple data models
│   ├── ai_service.py    # LLM integration
│   └── database.py      # SQLite setup
├── frontend/
│   ├── src/
│   │   ├── App.js       # Main app
│   │   ├── VoiceChat.js # Voice interface
│   │   └── PersonaList.js # Persona selection
│   └── package.json
└── README.md
```