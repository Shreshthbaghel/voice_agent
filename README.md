# Voice Medicine Assistant

A full-stack, web-based voice agent for interactive medicine information, built with LiveKit, FastAPI, and React (Vite). 

> **Disclaimer**: This is a demonstration and learning project only. It is **not** a substitute for professional medical advice.

## Tech Stack

- **Frontend**: React, Vite, LiveKit Components
- **Backend API**: FastAPI, SQLAlchemy, SQLite (Local) / PostgreSQL (Production)
- **Voice Agent**: LiveKit Agents framework, OpenAI (LLM)
- **Speech Providers**: Deepgram (English STT/TTS), Sarvam (Hindi STT/TTS), ElevenLabs (TTS)
- **Authentication**: JWT Bearer Tokens

## Project Structure

```text
voice-medicine-assistant/
├── README.md
├── backend/
│   ├── main.py              # FastAPI entrypoint
│   ├── database.py          # SQLAlchemy engine
│   ├── orm_models.py        # SQLAlchemy models (User, Medicine, Conversation, Message)
│   ├── schemas.py           # Pydantic schemas
│   ├── requirements.txt
│   ├── routers/             # API routes (voice, query, history, auth, dashboard)
│   ├── services/            # Business logic & Proxy settings
│   └── agents/              # LiveKit voice agent & tool logic
└── frontend/
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx
        ├── api/client.js
        ├── pages/
        └── components/
```

## Quick Start (Local Development)

### 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
cp .env.example .env           # Add your API keys!
uvicorn main:app --reload
```
API runs on `http://localhost:8000` — docs at `/docs`

### 2. LiveKit Voice Agent

The LiveKit agent runs as a separate background worker process.

```bash
cd backend
python -m agents.agent dev
```

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```
UI runs on `http://localhost:5173`

## Configuration & Environment Variables

Key variables for `backend/.env`:
- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`: Required for voice sessions.
- `OPENAI_API_KEY`: For the conversational LLM.
- `DEEPGRAM_API_KEY`, `SARVAM_API_KEY`: For Speech-To-Text / Text-To-Speech.
- `DATABASE_URL`: Defaults to `sqlite:///./voicemed.db` locally.

*Note on Proxies*: The project supports routing OpenAI and Voice requests through a MetricAI proxy for telemetry. You can disable this by commenting out `METRICAI_API_KEY` in your `.env`.

## Deployment

The stack is designed to be easily deployed to modern cloud providers:
- **Frontend**: Vercel (Auto-detects Vite)
- **Backend API**: Render (Web Service)
- **LiveKit Agent**: Render (Background Worker)
- **Database**: Supabase (PostgreSQL)

Set your `DATABASE_URL` to your Supabase Postgres connection string, deploy your web services, and ensure your `FRONTEND_URL` environment variable matches your Vercel domain for CORS.
