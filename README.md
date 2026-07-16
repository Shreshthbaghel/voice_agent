# Voice Medicine Assistant

Web-based voice agent for medicine information — built on the same architecture as `decision_os` and `roast_my_pitchdeck`.

> Learning project only. Not a medical product.

## Structure

```
voice-medicine-assistant/
├── README.md
├── backend/
│   ├── main.py              # FastAPI entrypoint
│   ├── config.py            # pydantic-settings
│   ├── database.py          # SQLAlchemy engine + get_db
│   ├── orm_models.py        # SQLAlchemy models
│   ├── schemas.py           # Pydantic request/response models
│   ├── seed_data.py         # Medicine reference data
│   ├── requirements.txt
│   ├── Procfile
│   ├── .env.example
│   ├── routers/             # voice, query, history, knowledge, dashboard
│   ├── services/            # Business logic
│   ├── agents/              # LiveKit voice agent
│   ├── retriever/           # ChromaDB vector search
│   ├── embeddings/
│   ├── crawler/
│   └── cache/
└── frontend/
    ├── index.html
    ├── vite.config.js
    ├── package.json
    ├── .env.example
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── api/client.js
        ├── pages/
        ├── components/
        └── hooks/
```

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env           # add API keys
uvicorn main:app --reload
```

API: `http://localhost:8000` — docs at `/docs`

### LiveKit Agent

```bash
cd backend
set VOICE_PROVIDER=deepgram
python -m agents.agent dev
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

UI: `http://localhost:5173`

## API Routes

| Method | Path | Description |
|--------|------|-------------|
| POST | `/voice/token` | LiveKit access token |
| POST | `/query` | Text medicine query |
| GET | `/history` | Past sessions |
| GET | `/history/{id}` | Session detail |
| POST | `/history/sessions/{id}/end` | End session |
| GET | `/knowledge` | Cached knowledge |
| GET | `/dashboard` | Stats |

## Voice Providers

| Provider | Language | Env var |
|----------|----------|---------|
| `deepgram` | English | `DEEPGRAM_API_KEY` |
| `sarvam` | Hindi | `SARVAM_API_KEY` |

Set `VOICE_PROVIDER=deepgram` or `sarvam` in `backend/.env`.
