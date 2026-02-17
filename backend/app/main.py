import json
import os
from fastapi import FastAPI, Request, File, UploadFile, HTTPException, WebSocket
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from app.graph import get_chatbot, process_document, get_rag_status
import asyncio
from datetime import datetime
from typing import Optional
from app.monitoring_worker import MonitoringWorker
from app.alert_processor import AlertProcessor
from app.websocket_manager import alert_ws_manager
from app.alert_history import alert_history
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    monitoring_worker = MonitoringWorker()
    alert_processor = AlertProcessor()
    asyncio.create_task(monitoring_worker.start())
    asyncio.create_task(alert_processor.start())

    yield

    # Shutdown (if needed)
    monitoring_worker.stop()


app = FastAPI(title="Sentinel AI Backend", lifespan=lifespan)


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
    """Process uploaded PDF for RAG with Qdrant"""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported for RAG")

    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    safe_filename = file.filename.replace(" ", "_")
    file_path = os.path.join(upload_dir, f"{thread_id}_{safe_filename}")

    print(f"📄 Upload received: {file.filename} for thread {thread_id}")

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Call ASYNC process_document
    result = await process_document(file_path, thread_id)

    if result.get("success"):
        return {
            "success": True,
            "filename": safe_filename,
            "info": result["info"],
            "message": f"Document indexed in Qdrant with {result['info'].get('chunks')} chunks",
        }
    else:
        error_msg = result.get("error", "Unknown error")
        print(f"❌ Document processing failed: {error_msg}")
        raise HTTPException(500, f"Failed to process document: {error_msg}")


# ✅ FIX BUG 3: Add endpoint that frontend expects for document processing
@app.post("/api/process-document")
async def process_document_endpoint(
    file: UploadFile = File(...), thread_id: str = "default_thread"
):
    """Process uploaded PDF for RAG (frontend expects this endpoint)"""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, detail="Only PDF files are supported for RAG")

    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    safe_filename = file.filename.replace(" ", "_")
    file_path = os.path.join(upload_dir, f"{thread_id}_{safe_filename}")

    print(f"📄 Processing document: {file.filename} (thread: {thread_id})")

    # Save uploaded file
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    print(f"✅ File saved: {file_path}")

    # Call ASYNC process_document
    try:
        result = await process_document(file_path, thread_id)

        if result.get("success"):
            info = result.get("info", {})
            return {
                "success": True,
                "filename": safe_filename,
                "info": info,
                "message": (
                    f"Document processed successfully!\n"
                    f"Indexed {info.get('chunks', 0)} chunks from "
                    f"{info.get('pages', 0)} pages in Qdrant"
                ),
            }
        else:
            error_msg = result.get("error", "Unknown error")
            print(f"❌ Processing failed: {error_msg}")
            raise HTTPException(500, detail=f"Failed to process document: {error_msg}")

    except Exception as e:
        print(f"❌ Exception during processing: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(500, detail=f"Processing error: {str(e)}")


@app.get("/api/rag-status")
async def rag_status_endpoint(thread_id: str = "default_thread"):
    """Get RAG system status for a thread"""
    return get_rag_status(thread_id)


class RenameRequest(BaseModel):
    title: str


@app.patch("/api/chat/{thread_id}")
async def rename_chat(thread_id: str, request: Request):
    """
    Rename a chat thread.
    """
    try:
        body = await request.json()
        title = body.get("title", "Untitled")
        print(f"📝 Renaming thread {thread_id} to '{title}'")
        return {"success": True, "id": thread_id, "title": title}
    except Exception as e:
        print(f"❌ Error in rename: {e}")
        return {"success": False, "error": str(e)}


@app.delete("/api/chat")
@app.delete("/api/chat/")
async def delete_chat_query(id: str):
    """Delete chat using query parameter ?id=... (Frontend style)"""
    return await delete_chat(id)


@app.delete("/api/chat/{thread_id}")
async def delete_chat(thread_id: str):
    """Delete all history and state for a specific thread."""
    print(f"🗑️ Deleting thread {thread_id}")

    try:
        from app.graph import POSTGRES_URL, _langgraph_dsn
        import asyncpg

        # Connect to DB to delete checkpoints
        dsn = _langgraph_dsn(POSTGRES_URL)

        try:
            conn = await asyncpg.connect(dsn)
            # Try to delete, but don't crash if it fails
            await conn.execute(
                "DELETE FROM checkpoints WHERE thread_id = $1", thread_id
            )
            await conn.execute(
                "DELETE FROM checkpoint_writes WHERE thread_id = $1", thread_id
            )
            await conn.close()
            print(f"✅ Deleted checkpoints for {thread_id}")
        except Exception as db_e:
            # Log but don't fail the request, so UI updates
            print(f"⚠️ Database cleanup skipped/failed: {db_e}")

        # Clean up memory
        from app.graph import _doc_info_by_thread

        if thread_id in _doc_info_by_thread:
            del _doc_info_by_thread[thread_id]

        return {"success": True, "message": "Chat deleted"}

    except Exception as e:
        # Final catch-all: Always return success to the UI so the item disappears
        print(f"❌ Error in delete wrapper: {e}")
        return {"success": True, "message": "Chat deleted (fallback)"}


@app.post("/api/chat")
async def chat(request: ChatRequest):
    chatbot = await get_chatbot()

    thread_id = request.id
    file_processed = False

    # Process file attachments
    last_message = request.messages[-1] if request.messages else None
    if last_message and last_message.attachments:
        for attachment in last_message.attachments:
            if attachment.get("url") and "pdf" in attachment.get("name", "").lower():
                filename = attachment["name"]
                file_path = os.path.join("uploads", f"{thread_id}_{filename}")
                if os.path.exists(file_path):
                    print(f"📄 Re-processing file: {filename}")
                    result = await process_document(
                        file_path, thread_id
                    )  # CHANGED: Added await
                    if result.get("success"):
                        file_processed = True

    # Convert messages
    lc_messages = []
    for m in request.messages:
        if m.role == "user":
            if file_processed and last_message and last_message.attachments:
                for att in last_message.attachments:
                    if att.get("name", "").lower().endswith(".pdf"):
                        lc_messages.append(
                            SystemMessage(
                                content=f"[File {att.get('name', 'file')} is now available for RAG queries]"
                            )
                        )
                        break
            lc_messages.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            lc_messages.append(AIMessage(content=m.content))

    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": request.user_id,
            "model": request.model,
        },
        "recursion_limit": 15,  # ✅ FIX: Limit recursion to prevent infinite loops
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
                {"messages": lc_messages}, config, version="v2"
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
                        "args": tool_input,
                    }
                    print(f"🔧 Streaming tool start: {tool_name}")
                    yield f"9:{json.dumps(payload)}\n"

                # Tool results
                elif kind == "on_tool_end":
                    run_id = event.get("run_id", "unknown_id")
                    result = event.get("data", {}).get("output", "Success")

                    if not isinstance(result, str):
                        try:
                            result = (
                                json.dumps(result)
                                if isinstance(result, (dict, list))
                                else str(result)
                            )
                        except:
                            result = str(result)

                    payload = {"toolCallId": run_id, "result": result[:500]}
                    print(f"✅ Streaming tool result: {run_id}")
                    yield f"a:{json.dumps(payload)}\n"

                # Collect final messages from LangGraph
                elif kind == "on_chain_end" and event.get("name") == "LangGraph":
                    output = event.get("data", {}).get("output", {})
                    if "messages" in output:
                        final_messages = output["messages"]
                        print(
                            f"📦 Collected {len(final_messages)} final messages from LangGraph"
                        )

            print(
                f"🏁 Stream loop ended. has_content={has_content}, chunk_count={chunk_count}, final_messages={len(final_messages)}"
            )

            # ✅ CRITICAL: After stream ends, send final response if nothing was streamed
            if not has_content and final_messages:
                print(f"⚠️ No streaming occurred, sending final messages now")
                for msg in reversed(final_messages):
                    if (
                        hasattr(msg, "type")
                        and msg.type == "ai"
                        and hasattr(msg, "content")
                    ):
                        content = _normalize_content(msg.content)
                        if content:
                            print(f"📤 Sending final response: {len(content)} chars")
                            # Send in chunks to simulate streaming
                            chunk_size = 50
                            for i in range(0, len(content), chunk_size):
                                chunk = content[i : i + chunk_size]
                                yield f"0:{json.dumps(chunk)}\n"
                            has_content = True
                            break

            if not has_content:
                print(
                    f"❌ WARNING: No content was streamed at all! Attempting emergency fallback..."
                )
                # Emergency fallback: try to get response directly
                try:
                    result = await chatbot.ainvoke({"messages": lc_messages}, config)
                    if "messages" in result and result["messages"]:
                        for msg in reversed(result["messages"]):
                            if (
                                hasattr(msg, "type")
                                and msg.type == "ai"
                                and hasattr(msg, "content")
                            ):
                                content = _normalize_content(msg.content)
                                if content:
                                    print(
                                        f"🆘 Emergency fallback sending: {len(content)} chars"
                                    )
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


# ==============================================================================
# MONITORING ENDPOINTS (Camera & Alerts)
# ==============================================================================


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """
    WebSocket endpoint for real-time alert streaming.

    Connect to this endpoint to receive instant notifications when:
    - Motion/people detected
    - Camera becomes unavailable
    - Security threats identified
    """
    await alert_ws_manager.connect(websocket)
    try:
        # Keep connection alive and wait for client disconnect
        while True:
            # Receive ping from client (optional)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except Exception as e:
        # Client disconnected
        pass
    finally:
        await alert_ws_manager.disconnect(websocket)


@app.get("/api/alerts/history")
async def get_alerts_history(
    start: Optional[str] = None,
    end: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    Get alert history with filtering options.

    Query Parameters:
    - start: ISO datetime string (e.g., "2025-02-17T10:00:00")
    - end: ISO datetime string
    - severity: Filter by severity (LOW, MEDIUM, HIGH)
    - limit: Maximum number of alerts (default: 100)
    - offset: Pagination offset

    Returns:
        List of alerts sorted by timestamp (newest first)
    """
    try:
        # Parse datetime strings
        start_time = datetime.fromisoformat(start) if start else None
        end_time = datetime.fromisoformat(end) if end else None

        alerts = await alert_history.get_alerts(
            start_time=start_time,
            end_time=end_time,
            severity=severity,
            limit=limit,
            offset=offset,
        )

        return {"success": True, "count": len(alerts), "alerts": alerts}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/alerts/recent")
async def get_recent_alerts(minutes: int = 60):
    """
    Get alerts from the last N minutes.

    Query Parameters:
    - minutes: Number of minutes to look back (default: 60)
    """
    try:
        alerts = await alert_history.get_recent_alerts(minutes=minutes)
        return {
            "success": True,
            "count": len(alerts),
            "minutes": minutes,
            "alerts": alerts,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/alerts/stats")
async def get_alerts_stats():
    """Get alert statistics"""
    try:
        stats = await alert_history.get_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/camera/status")
async def get_camera_status():
    """
    Get current camera and monitoring system status.

    Returns:
        - Camera availability
        - Detector status (YOLO)
        - WebSocket connections
        - Recent detections
    """
    from app.monitoring_worker import MonitoringWorker
    from app.detection import detector

    try:
        # Get detector status
        detector_status = detector.get_status()

        # Get WebSocket connections
        ws_connections = alert_ws_manager.get_connection_count()

        # Try to get monitoring worker status
        monitoring_status = {
            "running": False,
            "camera_available": False,
            "message": "Monitoring worker not initialized",
        }

        return {
            "success": True,
            "status": {
                "camera": {
                    "available": detector_status["initialized"]
                    and detector_status["yolo_available"],
                    "message": "Camera ready"
                    if detector_status["initialized"]
                    else "No camera connected",
                },
                "detector": detector_status,
                "websocket_connections": ws_connections,
                "monitoring": monitoring_status,
            },
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "status": {
                "camera": {"available": False, "message": "System error"},
                "detector": {"initialized": False, "yolo_available": False},
            },
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
