import json
import os
import time
from fastapi import FastAPI, Request, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from app.graph import get_chatbot, process_document, get_rag_status

# #region agent log
_DEBUG_LOG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".cursor", "debug.log"))

def _debug_log(obj: dict) -> None:
    try:
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps({**obj, "timestamp": int(time.time() * 1000), "sessionId": "debug-session"}) + "\n")
    except Exception:
        pass
# #endregion

app = FastAPI(title="Sentinel AI Backend")

class Message(BaseModel):
    role: str
    content: str
    id: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None

class ChatRequest(BaseModel):
    messages: List[Message]
    id: str
    user_id: str
    model: Optional[str] = "llama-3.3-70b-versatile"

# Add CORS middleware
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), thread_id: str = "default_thread"):
    """Process uploaded PDF for RAG"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, "Only PDF files are supported for RAG")
    
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{thread_id}_{file.filename}")
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    result = process_document(file_path, thread_id)
    
    if result.get('success'):
        return {
            "success": True,
            "filename": result['filename'],
            "info": result['info'],
            "message": "Document processed successfully"
        }
    else:
        raise HTTPException(500, f"Failed to process document: {result.get('error')}")

@app.post("/api/chat")
async def chat(request: ChatRequest):
    chatbot = await get_chatbot()
    
    thread_id = request.id
    file_processed = False
    
    # Process file attachments
    last_message = request.messages[-1] if request.messages else None
    if last_message and last_message.attachments:
        for attachment in last_message.attachments:
            if attachment.get('url') and 'pdf' in attachment.get('name', '').lower():
                filename = attachment['name']
                file_path = os.path.join("uploads", f"{thread_id}_{filename}")
                if os.path.exists(file_path):
                    print(f"🔄 Re-processing file: {filename}")
                    result = process_document(file_path, thread_id)
                    if result.get('success'):
                        file_processed = True
    
    # Convert messages
    lc_messages = []
    for m in request.messages:
        if m.role == "user":
            if file_processed and last_message and last_message.attachments:
                for att in last_message.attachments:
                    if att.get("name", "").lower().endswith(".pdf"):
                        lc_messages.append(SystemMessage(content=f"[File {att.get('name', 'file')} is now available for RAG queries]"))
                        break
            lc_messages.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            lc_messages.append(AIMessage(content=m.content))
    
    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": request.user_id,
            "model": request.model
        }
    }

    def _normalize_content(raw) -> str:
        """Ensure content is a string. LangChain chunk.content can be str or list of blocks."""
        if raw is None:
            return ""
        if isinstance(raw, str):
            return raw
        if isinstance(raw, list):
            parts = []
            for b in raw:
                if isinstance(b, dict):
                    t = b.get("text") or b.get("content")
                    if t is not None:
                        parts.append(str(t))
            return "".join(parts)
        return str(raw)

    async def stream_generator(lc_messages):
        first_text = True
        try:
            async for event in chatbot.astream_events(
                {"messages": lc_messages}, config, version="v2"
            ):
                kind = event["event"]

                # Text streaming
                if kind == "on_chat_model_stream":
                    raw = event["data"]["chunk"].content
                    content = _normalize_content(raw)
                    if content:
                        # #region agent log
                        if first_text:
                            _debug_log({"location": "backend:stream", "message": "first 0: chunk", "data": {"contentLen": len(content)}, "hypothesisId": "H6"})
                            first_text = False
                        # #endregion
                        yield f"0:{json.dumps(content)}\n"
                
                # Tool calls
                elif kind == "on_tool_start":
                    payload = {
                        "toolCallId": event["run_id"],
                        "toolName": event["name"],
                        "args": event["data"].get("input", {})
                    }
                    yield f"9:{json.dumps(payload)}\n"
                    
                # Tool results
                elif kind == "on_tool_end":
                    result = event["data"].get("output", "Success")
                    # ✅ FIX: Ensure result is serializable
                    if isinstance(result, dict):
                        if "error" in result:
                            result = f"Tool error: {result['error']}"
                        else:
                            result = json.dumps(result)
                    payload = {
                        "toolCallId": event["run_id"],
                        "result": result
                    }
                    yield f"a:{json.dumps(payload)}\n"
                    
        except Exception as e:
            # #region agent log
            _debug_log({"location": "backend:stream", "message": "stream error", "data": {"error": str(e)}, "hypothesisId": "H6"})
            # #endregion
            print(f"Stream error: {e}")
            # ✅ FIX: Send error as complete assistant message
            error_msg = f"I encountered an error: {str(e)}. Please try rephrasing your question."
            yield f"0:{json.dumps(error_msg)}\n"
            yield f"c:{json.dumps([error_msg])}\n"

    return StreamingResponse(stream_generator(lc_messages), media_type="text/plain")

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "Sentinel AI Backend"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)