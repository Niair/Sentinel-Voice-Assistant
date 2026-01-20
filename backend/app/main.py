import json
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from app.graph import get_chatbot

app = FastAPI(title="Sentinel AI Backend")

class Message(BaseModel):
    role: str
    content: str
    id: str = None

class ChatRequest(BaseModel):
    messages: List[Message]
    id: str # Vercel Chat ID
    user_id: str = "default_user"

async def stream_to_vercel(messages: List[Message], thread_id: str, user_id: str):
    chatbot = await get_chatbot()
    
    # Convert Vercel messages to LangChain format
    lc_messages = []
    for m in messages:
        if m.role == "user":
            lc_messages.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            lc_messages.append(AIMessage(content=m.content))

    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id
        }
    }

    # Use astream_events to capture everything (text + tools)
    async for event in chatbot.astream_events(
        {"messages": lc_messages}, 
        config, 
        version="v2"
    ):
        kind = event["event"]
        
        # 1. Stream Text (Vercel Prefix '0:')
        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content:
                yield f"0:{json.dumps(content)}\n"
        
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

@app.post("/api/chat")
async def chat(request: ChatRequest):
    return StreamingResponse(
        stream_to_vercel(request.messages, request.id, request.user_id),
        media_type="text/plain"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
