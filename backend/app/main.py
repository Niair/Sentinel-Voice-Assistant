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
    model: Optional[str] = "qwen/qwen3-32b"

# Add CORS middleware
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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


# ✅ FIX BUG 3: Add endpoint that frontend expects for document processing
@app.post("/api/process-document")
async def process_document_endpoint(file: UploadFile = File(...), thread_id: str = "default_thread"):
    """Process uploaded PDF for RAG (frontend expects this endpoint)"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, detail="Only PDF files are supported for RAG")
    
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    # Use just the filename without thread prefix for consistent lookups
    safe_filename = file.filename.replace(' ', '_')
    file_path = os.path.join(upload_dir, f"{thread_id}_{safe_filename}")
    
    print(f"📄 Processing document upload: {file.filename} for thread {thread_id}")
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    result = process_document(file_path, thread_id)
    
    if result.get('success'):
        return {
            "success": True,
            "filename": safe_filename,
            "info": result.get('info'),
            "message": "Document processed successfully"
        }
    else:
        raise HTTPException(500, detail=f"Failed to process document: {result.get('error')}")


@app.get("/api/rag-status")
async def rag_status_endpoint(thread_id: str = "default_thread"):
    """Get RAG system status for a thread"""
    return get_rag_status(thread_id)

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
        },
        "recursion_limit": 15  # ✅ FIX: Limit recursion to prevent infinite loops
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
        has_content = False
        final_messages = []
        chunk_count = 0
        
        try:
            print(f"🚀 Starting stream generator for thread {thread_id}")
            async for event in chatbot.astream_events(
                {"messages": lc_messages}, 
                config, 
                version="v2"
            ):
                kind = event["event"]
                
                # Text streaming from chat model
                if kind == "on_chat_model_stream":
                    raw = event["data"]["chunk"].content
                    content = _normalize_content(raw)
                    if content:
                        has_content = True
                        chunk_count += 1
                        if first_text:
                            _debug_log({"location": "backend:stream", "message": "first 0: chunk", "data": {"contentLen": len(content)}, "hypothesisId": "H6"})
                            first_text = False
                            print(f"📤 First chunk streaming: {len(content)} chars")
                        yield f"0:{json.dumps(content)}\n"
                
                # Tool calls
                elif kind == "on_tool_start":
                    tool_name = event.get("name", "unknown_tool")
                    run_id = event.get("run_id", "unknown_id")
                    tool_input = event.get("data", {}).get("input", {})
                    
                    try:
                        json.dumps(tool_input)
                    except:
                        tool_input = str(tool_input)
                    
                    payload = {
                        "toolCallId": run_id,
                        "toolName": tool_name,
                        "args": tool_input
                    }
                    print(f"🔧 Streaming tool start: {tool_name}")
                    yield f"9:{json.dumps(payload)}\n"
                    
                # Tool results
                elif kind == "on_tool_end":
                    run_id = event.get("run_id", "unknown_id")
                    result = event.get("data", {}).get("output", "Success")
                    
                    if not isinstance(result, str):
                        try:
                            result = json.dumps(result) if isinstance(result, (dict, list)) else str(result)
                        except:
                            result = str(result)
                    
                    payload = {
                        "toolCallId": run_id,
                        "result": result[:500]
                    }
                    print(f"✅ Streaming tool result: {run_id}")
                    yield f"a:{json.dumps(payload)}\n"
                
                # Collect final messages from LangGraph
                elif kind == "on_chain_end" and event.get("name") == "LangGraph":
                    output = event.get("data", {}).get("output", {})
                    if "messages" in output:
                        final_messages = output["messages"]
                        print(f"📦 Collected {len(final_messages)} final messages from LangGraph")
            
            print(f"🏁 Stream loop ended. has_content={has_content}, chunk_count={chunk_count}, final_messages={len(final_messages)}")
            
            # ✅ CRITICAL: After stream ends, send final response if nothing was streamed
            if not has_content and final_messages:
                print(f"⚠️ No streaming occurred, sending final messages now")
                for msg in reversed(final_messages):
                    if hasattr(msg, 'type') and msg.type == 'ai' and hasattr(msg, 'content'):
                        content = _normalize_content(msg.content)
                        if content:
                            print(f"📤 Sending final response: {len(content)} chars")
                            # Send in chunks to simulate streaming
                            chunk_size = 50
                            for i in range(0, len(content), chunk_size):
                                chunk = content[i:i+chunk_size]
                                yield f"0:{json.dumps(chunk)}\n"
                            has_content = True
                            break
            
            if not has_content:
                print(f"❌ WARNING: No content was streamed at all! Attempting emergency fallback...")
                # Emergency fallback: try to get response directly
                try:
                    result = await chatbot.ainvoke({"messages": lc_messages}, config)
                    if "messages" in result and result["messages"]:
                        for msg in reversed(result["messages"]):
                            if hasattr(msg, 'type') and msg.type == 'ai' and hasattr(msg, 'content'):
                                content = _normalize_content(msg.content)
                                if content:
                                    print(f"🆘 Emergency fallback sending: {len(content)} chars")
                                    yield f"0:{json.dumps(content)}\n"
                                    has_content = True
                                    break
                except Exception as fallback_error:
                    print(f"❌ Emergency fallback failed: {fallback_error}")
            
            if has_content:
                print(f"✅ Stream completed successfully")
            else:
                print(f"❌ CRITICAL: No content sent to client!")
                    
        except Exception as e:
            _debug_log({"location": "backend:stream", "message": "stream error", "data": {"error": str(e)}, "hypothesisId": "H6"})
            print(f"❌ Stream error: {e}")
            import traceback
            traceback.print_exc()
            error_msg = f"I encountered an error: {str(e)}. Please try again."
            yield f"0:{json.dumps(error_msg)}\n"

    return StreamingResponse(stream_generator(lc_messages), media_type="text/plain")

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "Sentinel AI Backend"}

@app.get("/api/test-stream")
async def test_stream():
    """Test endpoint to verify streaming works"""
    async def test_gen():
        yield f"0:{json.dumps('Hello ')}\n"
        yield f"0:{json.dumps('World!')}\n"
    return StreamingResponse(test_gen(), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)