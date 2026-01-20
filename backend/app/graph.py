import os
import json
import asyncio
from typing import TypedDict, Annotated, Optional, List, Dict
from langchain_groq import ChatGroq
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore
import aiosqlite
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
DB_PATH = "sentinel_chatbot.db"
# UPDATE THESE PATHS TO YOUR ACTUAL LOCAL PATHS
MCP_PATH = "E:/_Projects/GAIP/MCP/chat_bot_with_mcp/local_mcp.py"

SERVERS = {
    "math": {
        "transport": "stdio",
        "command": "uv",
        "args": ["run", "fastmcp", "run", MCP_PATH],
        "env": {"PYTHONPATH": os.path.dirname(MCP_PATH)}
    }
}

# --- Global RAG State ---
_retriever = None
_current_doc = None

# --- State Definition ---
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# --- RAG Logic ---
def process_document(pdf_path: str):
    global _retriever, _current_doc
    try:
        loader = PyMuPDFLoader(pdf_path)
        docs = loader.load()
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_documents(docs)
        embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
        vector_store = FAISS.from_documents(chunks, embeddings)
        _retriever = vector_store.as_retriever(search_type='similarity', search_kwargs={'k': 4})
        _current_doc = os.path.basename(pdf_path)
        return {"success": True, "filename": _current_doc}
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- Tools ---
search_tool = DuckDuckGoSearchRun(region="us-en")

@tool
def rag_tool(query: str) -> str:
    """
    Retrieve relevant information from the uploaded PDF document. 
    Use this when the user asks questions about the content of their uploaded files.
    """
    global _retriever
    if _retriever is None:
        return "No document is currently loaded. Please upload a PDF first."
    
    try:
        docs = _retriever.invoke(query)
        context = "\n\n".join([doc.page_content for doc in docs])
        return f"Context from document ({_current_doc}):\n\n{context}"
    except Exception as e:
        return f"Error retrieving from document: {str(e)}"

# --- Long-term Memory Logic ---
SYSTEM_PROMPT_TEMPLATE = """
You are a helpful assistant with memory capabilities.
If user-specific memory is available, use it to personalize 
your responses based on what you know about the user.

The user's memory (which may be empty) is provided as: {user_details_content}
"""

async def agent(state: ChatState, config: RunnableConfig, store: BaseStore):
    user_id = config["configurable"].get("user_id", "default_user")
    
    # Fetch long-term memories from the store
    namespace = ("user", user_id, "details")
    items = await store.asearch(namespace)
    
    if items:
        user_details_content = "\n".join(f"- {it.value.get('data', '')}" for it in items)
    else:
        user_details_content = "No previous memories found."

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        user_details_content=user_details_content
    )
    
    # Build tools
    mcp_client = MultiServerMCPClient(SERVERS)
    try:
        mcp_tools = await mcp_client.get_tools()
    except Exception:
        mcp_tools = []
    
    all_tools = [search_tool, rag_tool] + list(mcp_tools)
    model = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.4)
    llm_with_tools = model.bind_tools(all_tools)

    # Filter and validate messages
    validated_messages = []
    for msg in state['messages']:
        # Skip tool messages with empty or invalid content
        if hasattr(msg, 'type') and msg.type == 'tool':
            if not msg.content or (isinstance(msg.content, list) and len(msg.content) == 0):
                continue
            # Ensure content is a string
            if isinstance(msg.content, list):
                msg.content = str(msg.content)
        validated_messages.append(msg)

    messages = [SystemMessage(content=system_prompt)] + validated_messages
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}

# --- Graph Builder ---
async def build_graph(checkpointer, store):
    # ToolNode needs all tools that might be called
    # For MCP tools, we'd ideally know them beforehand or add them dynamically
    # For now, we include the static ones.
    
    # Create safe tool node wrapper
    base_tool_node = ToolNode([search_tool, rag_tool])
    
    async def safe_tool_node(state: ChatState) -> ChatState:
        """Wrapper around tool node to ensure all tool messages have content"""
        try:
            result = await base_tool_node.ainvoke(state)
            
            # Validate and fix tool message content
            if 'messages' in result:
                fixed_messages = []
                for msg in result['messages']:
                    if hasattr(msg, 'type') and msg.type == 'tool':
                        # Ensure tool message has content
                        if not msg.content or (isinstance(msg.content, list) and len(msg.content) == 0):
                            msg.content = "Tool executed successfully with no output"
                        # Ensure content is a string
                        elif isinstance(msg.content, list):
                            msg.content = str(msg.content)
                    fixed_messages.append(msg)
                result['messages'] = fixed_messages
            
            return result
        except Exception as e:
            print(f"Error in tool execution: {e}")
            # Return error message as tool result
            return {"messages": [ToolMessage(
                content=f"Tool execution failed: {str(e)}",
                tool_call_id=state['messages'][-1].tool_calls[0]['id'] if state['messages'][-1].tool_calls else "error"
            )]}

    graph = StateGraph(ChatState)
    graph.add_node("agent", agent)
    graph.add_node("tools", safe_tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")

    return graph.compile(checkpointer=checkpointer, store=store)

# --- Singleton ---
_chatbot = None
_store = InMemoryStore() # In production, use a persistent store like PostgresStore
model = None  # Export model for title generation

async def get_chatbot():
    global _chatbot, model
    if _chatbot is None:
        conn = await aiosqlite.connect(DB_PATH)
        checkpointer = AsyncSqliteSaver(conn)
        _chatbot = await build_graph(checkpointer, _store)
        # Initialize model for title generation
        model = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.4)
    return _chatbot