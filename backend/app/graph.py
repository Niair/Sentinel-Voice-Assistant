import os
import asyncio
from typing import TypedDict, Annotated
from langchain_groq import ChatGroq
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
import aiosqlite
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
DB_PATH = "sentinel_chatbot.db"
SERVERS = {
    "math": {
        "transport": "stdio",
        "command": "uv",
        "args": ["run", "fastmcp", "run", "E:/_Projects/GAIP/MCP/chat_bot_with_mcp/local_mcp.py"], # Use absolute path
        "env": {
            "PYTHONPATH": "E:/_Projects/GAIP/MCP/chat_bot_with_mcp" # Ensure imports work
        }
    }
}

# --- State ---
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# --- Tools ---
search_tool = DuckDuckGoSearchRun(region="us-en")

@tool
def rag_tool(query: str) -> str:
    """Retrieve information from uploaded documents."""
    # This is a placeholder for the logic in your langgraph_rag_backend.py
    # In production, you'd access the global retriever here
    return "RAG search result for: " + query

# --- Graph Builder ---
async def build_graph(checkpointer):
    # Initialize MCP Client
    mcp_client = MultiServerMCPClient(SERVERS)
    mcp_tools = await mcp_client.get_tools()
    all_tools = [search_tool, rag_tool] + list(mcp_tools)

    model = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.4)
    llm_with_tools = model.bind_tools(all_tools)

    async def main_llm_function(state: ChatState):
        response = await llm_with_tools.ainvoke(state['messages'])
        return {"messages": [response]}

    tool_node = ToolNode(all_tools)

    graph = StateGraph(ChatState)
    graph.add_node("agent", main_llm_function)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")

    return graph.compile(checkpointer=checkpointer)

# --- Singleton Pattern for API ---
_chatbot = None

async def get_chatbot():
    global _chatbot
    if _chatbot is None:
        conn = await aiosqlite.connect(DB_PATH)
        checkpointer = AsyncSqliteSaver(conn)
        _chatbot = await build_graph(checkpointer)
    return _chatbot
