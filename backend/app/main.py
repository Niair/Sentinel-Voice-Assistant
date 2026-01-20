import json
import os
import shutil
import tempfile
import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from app.graph import get_chatbot, process_document, remove_document, get_rag_status, init_persistence, close_persistence

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_persistence()
    yield
    await close_persistence()

app = FastAPI(title="Sentinel AI Backend", lifespan=lifespan)

class Message(BaseModel):
    role: str
    content: str
    id: str = None

class ChatRequest(BaseModel):
    messages: List[Message]
    id: str # Vercel Chat ID
    user_id: str = "default_user"
    model: str = "llama-3.3-70b-versatile"

async def stream_to_vercel(messages: List[Message], thread_id: str, user_id: str, model: str):
    chatbot = await get_chatbot()
    
    # Convert Vercel messages to LangChain format
    lc_messages = []
    for m in messages:
        if m.role == "user":
            lc_messages.append(HumanMessage(content=m.content, id=m.id))
        elif m.role == "assistant":
            lc_messages.append(AIMessage(content=m.content, id=m.id))
        elif m.role == "tool":
            # For ToolMessage, we need a tool_call_id.
            # In Vercel's protocol, this might be stored in the content or as a property.
            # Here we try to get it if available, or use the message ID.
            tool_call_id = getattr(m, 'tool_call_id', m.id)
            lc_messages.append(ToolMessage(content=m.content, tool_call_id=tool_call_id, id=m.id))

    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id,
            "model": model
        }
    }

    full_text = ""
    saw_stream = False
    # Use astream_events to capture everything (text + tools)
    async for event in chatbot.astream_events(
        {"messages": lc_messages}, 
        config, 
        version="v2"
    ):
        kind = event["event"]
        
        # 1. Stream Text (Vercel Prefix '0:')
        if kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            text = ""

            # Extract text from chunk (handling complex shapes)
            if isinstance(chunk.content, list):
                for part in chunk.content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text += part.get("text", "")
                    elif hasattr(part, "type") and part.type == "text":
                        text += getattr(part, "text", "") or ""
            elif isinstance(chunk.content, str):
                text = chunk.content
            
            if text:
                saw_stream = True
                full_text += text
                yield f"0:{json.dumps(text)}\n"
        
        # 2. Stream Tool Calls (Vercel Prefix '9:')
        elif kind == "on_tool_start":
            payload = {
                "toolCallId": event["run_id"],
                "toolName": event["name"],
                "args": event["data"].get("input", {})
            }
            yield f"9:{json.dumps(payload)}\n"
            
        # 3. Stream Tool Results (Vercel Prefix 'a:')
        elif kind == "on_tool_end":
            payload = {
                "toolCallId": event["run_id"],
                "result": event["data"].get("output", "Success")
            }
            yield f"a:{json.dumps(payload)}\n"

        # 4. Fallback for non-streaming models (emit full content)
        elif kind == "on_chat_model_end" and not saw_stream:
            message = event["data"].get("output")
            text = ""
            if hasattr(message, "content"):
                content = message.content
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            text += part.get("text", "")
                        elif hasattr(part, "type") and part.type == "text":
                            text += getattr(part, "text", "") or ""
                        elif isinstance(part, str):
                            text += part
                elif isinstance(content, str):
                    text = content
            elif isinstance(message, dict) and "content" in message:
                text = str(message.get("content", ""))

            if text:
                full_text += text
                yield f"0:{json.dumps(text)}\n"

    # 5. Generate and emit a title (Vercel Prefix 'c:')
    if full_text:
        # Simple heuristic: first 40 chars
        title = full_text[:40].replace("\n", " ")
        if len(full_text) > 40:
            title += "..."
        yield f"c:{json.dumps(title)}\n"

@app.post("/api/chat")
async def chat(request: ChatRequest):
    return StreamingResponse(
        stream_to_vercel(request.messages, request.id, request.user_id, request.model),
        media_type="text/plain"
    )

@app.post("/api/process-document")
async def process_doc(file: UploadFile = File(...), thread_id: str = "default_thread"):
    try:
        # Create a temporary file to store the upload
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        
        # Process the document
        result = process_document(tmp_path, thread_id=thread_id)
        
        # We can clean up the temp file after processing 
        # (FAISS will have the embeddings in memory, or we can keep it if needed)
        # For now, let's keep it until it's explicit removal
        
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/remove-document")
async def remove_doc(thread_id: str = "default_thread"):
    return remove_document(thread_id=thread_id)

@app.get("/api/rag-status")
async def rag_status(thread_id: str = "default_thread"):
    return get_rag_status(thread_id=thread_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
