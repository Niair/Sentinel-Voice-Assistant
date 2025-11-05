# Sentinel
Build a modular personal AI voice assistant for daily automation and MCP server tasks.
Keep it simple, iterative, and test-first so the AI IDE can scaffold code from this doc. 

## Project Description
This AI Assistant should be able to:
- Understand **voice commands** in Hindi + English (Hinglish) and text input
- Respond with **text and voice**
- Automate daily tasks like:
  - Sending or replying to emails
  - Writing emails on command
  - Searching for product prices across multiple websites
  - Providing weather updates for any location
  - Booking flights or checking flight prices
  - Integrating with MCP servers for multi-server tasks
- Be **modular** so features can easily be added or updated (like AIOps systems)
- Maintain **conversation context and memory**
- Run on both **local system** and optionally on a web interface

## Requirements
- Python 3.11 backend (venv included or auto-created).
- Flask for now (code modularized so swapping to FastAPI is trivial).
- React (Vite) frontend with a minimal chat UI.
- Gemini = primary LLM (via LangChain); Groq = fallback.
- 11Labs for TTS; Whisper or Gemini STT for transcription.
- LangChain + LangGraph for planning & orchestration; optional LangSmith for observability.
- Vector memory: Qdrant / FAISS / Chroma (pluggable).
- Docker + docker-compose for local dev & prod readiness.
- GitHub Actions CI to run tests and run ci/plan_builder.py (creates ci/todo_list.json).
- Tests: unit + integration tests for Gemini/Groq/11Labs connectivity.
- Hinglish support (no separate translation service required initially; rely on multilingual LLMs + small preprocessing).

## Recommended Architecture & Technologies
Even if I am not familiar with all of these, use the most appropriate for a professional AI assistant:

### 1. Frontend / Interface
- **Primary options:** 
  - React + Tailwind CSS (for advanced UI)
  - HTML/CSS/JS (if web-based interface is required)
- **Optional for later:** Streamlit (for Python-friendly GUI), Flask
- Voice: Web Speech API + MediaRecorder
- Features:
  - Voice input capture
  - Chat interface with AI responses
  - Settings panel for API keys, server configs, and user preferences
  - Optional dashboard for tasks and logs

### Backend / AI Engine
- **Python** (primary language)
- **AI Models & Tools:**
  - Transformers (HuggingFace) for LLM responses
  - LangChain / LangGraph for orchestration, reasoning, and memory
- LLM:
  - Primary: Google Gemini (gemini-api)
  - Fallback: Groq (llama-3.1-70b, mixtral-8x7b)
- Orchestration: LangChain + LangGraph
- Voice:
  - STT: OpenAI Whisper (local) or Google Speech-to-Text
  - TTS: ElevenLabs API or Google Text-to-Speech
- Vector DB: Qdrant or ChromaDB (for memory)
- Database: SQLite (simple, file-based)
- MCP: MCP Python SDK

### 4. Utilities & Security
- Load all credentials from `.env` using `python-dotenv`
- Logging of errors and conversation history
- Exception handling code for API calls and integrations
- Input validation and sanitization

## .env.example
FLASK_ENV=development
SECRET_KEY=changeme
PORT=5000

GEMINI_API_KEY=
GROQ_API_KEY=
ELEVENLABS_API_KEY=
WHISPER_API_KEY=
LANGSMITH_API_KEY=

VECTORDB_PROVIDER=qdrant   # or faiss/chroma
VECTORDB_URL=
S3_BUCKET=                  # optional for audio storage

### 5. Optional Tools & Enhancements
- **Web scraping / API clients** for product search, flight booking, and weather
- **Scheduler / Automation module** for recurring tasks
- **Translation module** for Hinglish support
- **Notification system** (desktop, email, or mobile)

## Folder Structure Suggestion
Sentinel/
├── .github/workflows/ci.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── routes/
│       │   ├── ai_routes.py
│       │   └── system_routes.py
│       ├── services/
│       │   ├── task_manager.py
│       │   └── audio_manager.py
│       ├── integrations/
│       │   ├── gemini_client.py
│       │   ├── groq_client.py
│       │   ├── tts_client.py
│       │   └── stt_client.py
│       ├── agents/
│       │   └── plan_executor.py
│       ├── memory/
│       └── utils/
│   └── tests/
│       ├── test_ai_integrations.py
│       ├── test_tts_service.py
│       └── test_stt_service.py
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── index.jsx
│       ├── App.jsx
│       ├── components/
│       └── services/
├── ci/
│   ├── plan_builder.py
│   ├── integration_checker.py
│   └── todo_list.json     # generated
├── docker-compose.yml
├── .env.example
└── README.md              # (this file)

## Testing rules for the IDE

- Integration tests that call real APIs must be gated by CI secrets; if secrets missing, tests must pytest.skip.
- Unit tests should use mocked LangChain models or LangChain’s GenericFakeChatModel pattern.
- Health endpoint /system/integrations is used by ci/integration_checker.py before generation or code scaffolding.

## Features to Include
1. **Voice + Text input and output**
2. **Email automation**
3. **Web search and scraping for prices**
4. **Flight booking & price comparison**
5. **Weather updates**
6. **MCP server integration**
7. **Memory & context storage**
8. **Hinglish language understanding**
9. **Modular design for adding new tools**
10. **Secure API key management**

## Agent instructions for the AI IDE (explicit tasks to run)

- Read this README.md.
- Generate ci/todo_list.json prioritizing integration & test tasks first.
- Scaffold backend skeleton files (placeholders OK) and tests.
- Scaffold frontend chat UI and an example flow calling POST /api/v1/chat.
- Create ci/integration_checker.py that calls /api/v1/system/integrations and marks failing keys in todo_list.json.
- Add GH Actions ci.yml with steps: setup Python 3.11, run integration_checker.py, run tests, run plan_builder.py, build Docker images.
- Run tests locally (skip gated tests if keys missing) and report status.