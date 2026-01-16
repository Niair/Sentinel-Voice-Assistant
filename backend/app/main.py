import os
import json
from typing import List, Dict, Any
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Import your existing LangGraph logic
# Assuming you move your langgraph_rag_backend.py logic into graph.py
from app.graph import get_chatbot

app = FastAPI(title="Sentinel AI Backend")

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    thread_id: str = "default-thread"

async def stream_langgraph_to_vercel(messages: List[Dict], thread_id: str):
    """
    Bridge LangGraph's stream to Vercel AI SDK's expected format.
    Vercel AI SDK expects specific prefixes for different types of data.
    """
    chatbot = get_chatbot()
    config = {"configurable": {"thread_id": thread_id}}
    
    # Convert Vercel messages to LangChain format
    from langchain_core.messages import HumanMessage, AIMessage
    lc_messages = []
    for m in messages:
        if m["role"] == "user":
            lc_messages.append(HumanMessage(content=m["content"]))
        else:
            lc_messages.append(AIMessage(content=m["content"]))

    async for event in chatbot.astream_events(
        {"messages": lc_messages}, 
        config, 
        version="v2"
    ):
        kind = event["event"]
        
        # Handle text streaming
        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content:
                # Vercel AI SDK 'text' prefix is '0:'
                yield f"0:{json.dumps(content)}\n"
        
        # Handle tool calls (for UI animations)
        elif kind == "on_tool_start":
            tool_name = event["name"]
            # Vercel AI SDK 'tool_call' prefix is '9:'
            yield f'9:{{"toolCallId":"{event["run_id"]}","toolName":"{tool_name}","args":{json.dumps(event["data"].get("input", {}))}}}\n'
            
        elif kind == "on_tool_end":
            # Vercel AI SDK 'tool_result' prefix is 'a:'
            yield f'a:{{"toolCallId":"{event["run_id"]}","result":{json.dumps(event["data"].get("output", "Success"))}}}\n'

@app.post("/api/chat")
async def chat(request: ChatRequest):
    return StreamingResponse(
        stream_langgraph_to_vercel(
            [m.dict() for m in request.messages], 
            request.thread_id
        ),
        media_type="text/plain"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
