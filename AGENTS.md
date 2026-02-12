# Agent Guidelines for Sentinel AI Voice Assistant

## Project Overview
This is a full-stack AI voice assistant application with:
- **Backend**: Python FastAPI with LangChain/LangGraph for AI orchestration
- **Frontend**: Next.js 14 + TypeScript + Tailwind CSS + Drizzle ORM
- **Database**: PostgreSQL with pgvector for vector storage
- **Features**: Chat with RAG, monitoring, alerting, file uploads

## Build Commands

### Backend (Python)
```bash
cd backend

# Run development server
uv run python -m app.main

# Run single test file
set PYTHONPATH=. && python tests/test_event_bus.py
set PYTHONPATH=. && python tests/test_database_connection.py

# Install dependencies
uv pip install -r requirements.txt
```

### Frontend (Next.js)
```bash
cd frontend

# Development
pnpm dev

# Build
pnpm build

# Lint
pnpm lint

# Database migrations
pnpm db:push
npx drizzle-kit push --config=drizzle.config.ts
```

## Code Style Guidelines

### Python (Backend)

#### Imports
- Group imports: stdlib → third-party → local
- Use absolute imports with `from app.module import ...`
- Example:
```python
import json
import os
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from langchain_core.messages import HumanMessage, AIMessage

from app.graph import get_chatbot, process_document
```

#### Naming Conventions
- Functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_CASE`
- Private functions: `_private_function`
- Async functions preferred for I/O operations

#### Type Hints
- Use type hints for function parameters and return types
- Use `Optional[T]` for nullable values
- Use `Dict[str, Any]` for flexible dicts
- Example: `async def process_document(file_path: str, thread_id: str) -> Dict[str, Any]:`

#### Error Handling
- Use try/except with specific exceptions
- Log errors with descriptive messages using emoji prefixes:
  - `✅` Success
  - `❌` Error
  - `⚠️` Warning
  - `📄` File operation
  - `🔧` Tool call
- Always use `traceback.print_exc()` for debugging
- Return dicts with `{"success": bool, "error": str}` pattern

#### Pydantic Models
- Use for request/response validation
- Example:
```python
class ChatRequest(BaseModel):
    messages: List[Message]
    id: str
    user_id: str
    model: Optional[str] = "qwen/qwen3-32b"
```

### TypeScript (Frontend)

#### Imports
- Group: React/Next → third-party → local (@/lib, @/components)
- Use `@/` path alias for local imports
- Example:
```typescript
import { useState } from 'react';
import { Message } from 'ai';

import { getChatById } from '@/lib/db/queries';
import { generateUUID } from '@/lib/utils';
```

#### Naming Conventions
- Components: `PascalCase` (e.g., `ChatComponent`)
- Functions/variables: `camelCase` (e.g., `handleSubmit`)
- Types/Interfaces: `PascalCase` with descriptive names
- Constants: `UPPER_CASE` for true constants

#### Type Safety
- Use strict TypeScript (strict: false in tsconfig but prefer types)
- Define explicit return types for exported functions
- Use `unknown` over `any` when type is uncertain
- Cast with `as` sparingly, prefer type guards

#### React Patterns
- Use functional components with hooks
- Prefer `async/await` for data fetching
- Use `useCallback`/`useMemo` for optimization when needed
- Server Actions go in `actions.ts` files

#### Error Handling
- Use try/catch for async operations
- Log with descriptive messages
- Use error boundaries for React components
- Pattern: `console.error('Context:', error)`

## Database

### PostgreSQL with Drizzle ORM
- Schema definitions in `lib/db/schema.ts`
- Queries in `lib/db/queries.ts`
- Use transactions for related operations
- Vector operations via pgvector extension

## Docker Commands
```bash
# Start PostgreSQL
docker run -d --name sentinel-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_USER=postgres -e POSTGRES_DB=postgres -p 5442:5432 postgres:15-alpine

# Connect to DB
docker exec -it sentinel-postgres psql -U postgres -d postgres
```

## Key Patterns

### Backend
- LangGraph for AI workflow orchestration
- FastAPI for REST endpoints
- Async throughout for I/O
- Event-driven architecture with event bus
- Streaming responses for chat

### Frontend
- App Router pattern (Next.js 14)
- Server Components by default
- Client Components when interactivity needed
- Streaming with Vercel AI SDK
- Radix UI for accessible components
- Tailwind for styling

## Testing
- Backend: Simple Python scripts, run individually
- Frontend: Manual testing via UI
- Use debug logging liberally during development

## Environment Setup
- Backend: Python 3.11+, use `uv` for package management
- Frontend: Node.js 20+, use `pnpm` for package management
- Always activate `.venv` before running backend
