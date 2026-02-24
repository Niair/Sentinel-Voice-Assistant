================================================================================
                    SENTINEL AI - MULTI-AGENT ARCHITECTURE
================================================================================

                              ┌─────────────────────┐
                              │   USER INTERFACE    │
                              │  (Next.js Frontend) │
                              │                     │
                              │ • Chat Window       │
                              │ • Alert Panel       │
                              │ • Camera View       │
                              └──────────┬──────────┘
                                         │
                                         │ WebSocket / REST
                                         ▼
                         ┌──────────────────────────────┐
                         │   APPLICATION BACKEND LAYER  │
                         │        (FastAPI)             │
                         │                              │
                         │ • REST API Endpoints         │
                         │ • WebSocket Manager          │
                         │ • Event Queue (asyncio)     │
                         └──────────┬───────────────────┘
                                    │
          ┌──────────────────────────┼──────────────────────────┐
          │                          │                          │
          ▼                          ▼                          ▼
┌─────────────────┐     ┌──────────────────────┐    ┌─────────────────┐
│   CONVERSATIONAL│     │    VISION SUB-AGENT │    │  ALERT PROCESSOR│
│   ORCHESTRATION │     │    (Background)      │    │  (Background)    │
│   (LangGraph)   │     │                      │    │                  │
│                 │     │ • Camera Capture     │    │ • Event Filter   │
│ • Chat Agent   │     │ • YOLOv8 Detection   │    │ • Deduplication  │
│ • Intent Check │     │ • Event Generation  │    │ • Severity Score │
│ • Tool Router  │     │ • Queue Publishing   │    │ • DB Storage     │
│ • RAG Search   │     │                      │    │ • WebSocket Push │
└────────┬────────┘     └──────────┬───────────┘    └─────────────────┘
         │                        │                         │
         │                        │  Event Queue           │
         │                        │  (asyncio.Queue)       │
         │                        └──────────┬───────────────┘
         │                                   │
         ▼                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       LANGGRAPH ORCHESTRATION                       │
│                                                                     │
│   ┌──────────┐    ┌─────────────┐    ┌────────────┐               │
│   │  START   │───▶│    AGENT    │───▶│  TOOLS ?   │               │
│   └──────────┘    │  (LLM with  │    │   (Yes)    │               │
│                   │   Tools)     │    └─────┬──────┘               │
│                   └──────┬────────┘          │                      │
│                          │                   │ No                   │
│                          │◀──────────────────┘                      │
│                          │                                           │
│                   ┌──────▼──────┐                                    │
│                   │    END      │                                    │
│                   └─────────────┘                                    │
└─────────────────────────────────────────────────────────────────────┘
         │
         │ Tools: RAG, Search, Camera Query, Notifications
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        TOOLS & SERVICES                             │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │   Qdrant     │  │  PostgreSQL  │  │   EXTERNAL APIs        │  │
│  │ (Vector DB)  │  │   (Memory)   │  │ • Web Search (DDG)    │  │
│  │              │  │              │  │ • Gemini Vision       │  │
│  │ • Document   │  │ • Chat Hist │  │ • MCP Finance Tools   │  │
│  │   Embeddings │  │ • Memory    │  │                        │  │
│  └──────────────┘  └──────────────┘  └────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘


================================================================================
                         DATA FLOW EXAMPLES
================================================================================

EXAMPLE 1: User asks "What's happening?"
─────────────────────────────────────────
User ──▶ Chat ──▶ LangGraph Agent ──▶ Tool: what_is_happening()
                                                    │
                                                    ▼
                                            Camera Tools
                                                    │
                                                    ▼
                                            Get Latest Frame
                                                    │
                                                    ▼
                                            Gemini Vision API
                                                    │
                                                    ▼
                                            "Person detected in 
                                             living room"
                                                    │
                                                    ◀─────────────
                                            Answer User


EXAMPLE 2: Monkey detected by camera
────────────────────────────────────
Camera ──▶ YOLOv8 ──▶ "Monkey detected" ──▶ Event Queue
                                                  │
                                                  ▼
                                          Alert Processor
                                          (deduplicate, score)
                                                  │
                                                  ▼
                                          WebSocket ──▶ User Alert
                                          │
                                          ▼
                                    PostgreSQL (log)


================================================================================
                         KEY COMPONENTS
================================================================================

1. USER INTERFACE (Next.js 14 + React)
   - Chat window for conversation
   - Alert panel for notifications
   - Camera preview

2. FASTAPI BACKEND
   - /api/chat - Conversational endpoint
   - /api/upload - Document upload for RAG
   - /ws/alerts - WebSocket for real-time alerts
   - /api/camera/* - Camera control

3. LANGGRAPH ORCHESTRATION
   - Stateful conversation graphs
   - Tool routing (RAG, search, camera)
   - Memory persistence via PostgresStore

4. VISION SUB-AGENT (Background)
   - Continuous camera monitoring
   - YOLOv8 object detection [17]
   - Event generation for detections

5. ALERT PROCESSOR (Background)
   - Event deduplication
   - Severity scoring
   - Real-time WebSocket push

6. DATA STORES
   - Qdrant: Vector embeddings for RAG [18]
   - PostgreSQL: Chat history, memory, alerts [16]

================================================================================
                         TECHNOLOGIES USED
================================================================================

Backend:
- FastAPI (Python web framework)
- LangGraph (AI orchestration)
- LangChain (LLM integration)
- YOLOv8 [17] (Object detection - Ultralytics)
- Qwen2-VL-7B (Vision language model - Alibaba)
- Gemini (Google DeepMind - vision analysis)
- Qdrant [18] (Vector database)
- PostgreSQL (Database)
- OpenCV (Camera capture)
- Groq [15] (Fast LLM inference)
- Jina AI [16] (Embeddings)

Frontend:
- Next.js 14 (React framework)
- TypeScript
- Tailwind CSS
- Drizzle ORM
- WebSocket client

================================================================================
