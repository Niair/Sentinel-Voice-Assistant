import os
import json
import asyncio
import contextvars
from typing import TypedDict, Annotated, Optional, List, Dict
from langchain_groq import ChatGroq
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_postgres import PGVector
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.store.base import BaseStore
from langgraph.store.postgres import PostgresStore
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
POSTGRES_URL = os.getenv(
    "POSTGRES_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5442/postgres"
)

def _langgraph_dsn(url: str) -> str:
    return (
        url.replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg://", "postgresql://")
    )

def _pgvector_conn(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://")
    return url
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
_retrievers_by_thread: Dict[str, object] = {}
_doc_info_by_thread: Dict[str, Dict[str, object]] = {}
_current_thread_id = contextvars.ContextVar("current_thread_id", default="default_thread")

# --- MCP Client ---
_mcp_client = MultiServerMCPClient(SERVERS)

# --- State Definition ---
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# --- RAG Logic ---
def process_document(pdf_path: str, thread_id: str = "default_thread"):
    """
    Process a PDF document and create a retriever.
    Returns document info and the retriever.
    """
    global _retrievers_by_thread, _doc_info_by_thread
    
    try:
        print(f"📄 Processing document: {pdf_path}")
        
        # Load PDF
        loader = PyMuPDFLoader(pdf_path)
        docs = loader.load()
        print(f"✅ Loaded {len(docs)} pages")
        
        # Split into chunks
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = splitter.split_documents(docs)
        print(f"✅ Created {len(chunks)} chunks")
        
        # Create embeddings and vector store
        embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
        collection_name = f"sentinel_thread_{thread_id}"
        _vector_store = PGVector.from_documents(
            documents=chunks,
            embedding=embeddings,
            connection=_pgvector_conn(POSTGRES_URL),
            collection_name=collection_name
        )
        print("✅ Vector store created")
        
        # Create retriever
        _retriever = _vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 4}
        )
        
        # Store document info
        _current_doc_info = {
            "filename": os.path.basename(pdf_path),
            "pages": len(docs),
            "chunks": len(chunks),
            "path": pdf_path,
            "thread_id": thread_id,
            "collection": collection_name
        }

        _retrievers_by_thread[thread_id] = _retriever
        _doc_info_by_thread[thread_id] = _current_doc_info
        
        print("✅ RAG system ready!")
        return {
            'success': True,
            "filename": _current_doc_info["filename"],
            'info': _current_doc_info
        }
        
    except Exception as e:
        print(f"❌ Error processing document: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def remove_document(thread_id: str = "default_thread"):
    """Remove the current document and disable RAG."""
    global _retrievers_by_thread, _doc_info_by_thread

    _retrievers_by_thread.pop(thread_id, None)
    _doc_info_by_thread.pop(thread_id, None)
    
    print("📭 Document removed, RAG disabled")
    return {'success': True}

def get_rag_status(thread_id: str = "default_thread"):
    """Get current RAG system status."""
    doc_info = _doc_info_by_thread.get(thread_id)
    return {
        "has_document": doc_info is not None,
        "document_info": doc_info,
        "rag_active": thread_id in _retrievers_by_thread
    }

# --- Tools ---
search_tool = DuckDuckGoSearchRun(region="us-en")

@tool
def rag_tool(query: str) -> dict:
    """
    Retrieve relevant information from the uploaded PDF document. 
    Use this when the user asks questions about the content of their uploaded files.
    """
    thread_id = _current_thread_id.get()
    retriever = _retrievers_by_thread.get(thread_id)
    doc_info = _doc_info_by_thread.get(thread_id)
    if retriever is None or doc_info is None:
        return {
            "query": query,
            "context": [],
            "metadata": [],
            "message": "No document is currently loaded. Please upload a PDF first.",
            "has_document": False
        }
    
    try:
        docs = retriever.invoke(query)
        context = [doc.page_content for doc in docs]
        metadata = [doc.metadata for doc in docs]
        return {
            "query": query,
            "context": context,
            "metadata": metadata,
            "document": doc_info.get("filename"),
            "has_document": True
        }
    except Exception as e:
        return {
            "query": query,
            "context": [],
            "metadata": [],
            "error": f"Error retrieving from document: {str(e)}",
            "has_document": True
        }

# --- Long-term Memory Logic ---
SYSTEM_PROMPT_TEMPLATE = """
You are a helpful assistant with memory capabilities.
If user-specific memory is available, use it to personalize 
your responses based on what you know about the user.

The user’s memory (which may be empty) is provided as: {user_details_content}
"""

async def agent(state: ChatState, config: RunnableConfig, store: BaseStore):
    user_id = config["configurable"].get("user_id", "default_user")
    thread_id = config["configurable"].get("thread_id", "default_thread")
    _current_thread_id.set(thread_id)
    
    # Fetch long-term memories from the store
    namespace = ("user", user_id, "details")
    items = store.search(namespace)
    
    if items:
        user_details_content = "\n".join(f"- {it.value.get('data', '')}" for it in items)
    else:
        user_details_content = "No previous memories found."

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        user_details_content=user_details_content
    )
    
    # Build tools
    static_tools = [search_tool, rag_tool]
    try:
        mcp_tools = await _mcp_client.get_tools()
        all_tools = static_tools + list(mcp_tools)
    except Exception as e:
        print(f"Warning: Failed to load MCP tools in agent: {e}")
        all_tools = static_tools
    
    # Determine which model to use
    selected_model = config["configurable"].get("model", "llama-3.3-70b-versatile")
    
    # Map frontend model IDs to Groq model names if necessary
    model_mapping = {
        "google/gemini-2.5-flash-lite": "llama-3.3-70b-versatile",
        "google/gemini-3-pro-preview": "llama-3.3-70b-specdec",
        "openai/gpt-4.1-mini": "llama-3.1-70b-versatile",
        "openai/gpt-5.2": "llama-3.3-70b-versatile",
        "anthropic/claude-haiku-4.5": "llama-3.1-8b-instant",
        "anthropic/claude-sonnet-4.5": "llama-3.3-70b-versatile",
        "llama-3.3-70b-versatile": "llama-3.3-70b-versatile",
        "grok-4.1-fast": "llama-3.1-70b-versatile"
    }
    
    groq_model = model_mapping.get(selected_model, "llama-3.3-70b-versatile")
    
    # Initialize model and bind tools
    model = ChatGroq(model=groq_model, temperature=0.4)
    llm_with_tools = model.bind_tools(all_tools)
    
    # Filter and validate messages before sending to LLM
    validated_messages = []
    for msg in state['messages']:
        # Skip tool messages with empty or invalid content
        if hasattr(msg, 'type') and msg.type == 'tool':
            if not msg.content or (isinstance(msg.content, list) and len(msg.content) == 0):
                print(f"Skipping empty tool message: {msg}")
                continue
            # Ensure content is a string for stability
            if isinstance(msg.content, list):
                msg.content = str(msg.content)
        validated_messages.append(msg)

    messages = [SystemMessage(content=system_prompt)] + validated_messages
    
    try:
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}
    except Exception as e:
        print(f"❌ Error in LLM invocation: {e}")
        import traceback
        traceback.print_exc()
        # Return a helpful error message to the UI
        return {"messages": [AIMessage(content=f"⚠️ I encountered an error while processing your request: {str(e)}")]}

# --- Graph Builder ---
async def build_graph(checkpointer, store):
    # Base tools
    static_tools = [search_tool, rag_tool]
    
    # Try to get MCP tools safely
    try:
        mcp_tools = await _mcp_client.get_tools()
        all_tools = static_tools + list(mcp_tools)
    except Exception as e:
        print(f"Warning: Failed to load MCP tools in build_graph: {e}")
        all_tools = static_tools

    # 1. Base ToolNode
    base_tool_node = ToolNode(all_tools) 

    # 2. Safe ToolNode Wrapper (Ported from old code)
    async def safe_tool_node(state: ChatState) -> ChatState:
        """Wrapper around tool node to ensure all tool messages have content and handle errors"""
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
            # Identify the missing tool call id to return a proper ToolMessage
            tool_call_id = "error"
            if state['messages'] and hasattr(state['messages'][-1], 'tool_calls') and state['messages'][-1].tool_calls:
                tool_call_id = state['messages'][-1].tool_calls[0].get('id', 'error')
            
            return {"messages": [ToolMessage(
                content=f"Tool execution failed: {str(e)}",
                tool_call_id=tool_call_id
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

_store = None
_store_cm = None

_checkpointer = False

async def init_persistence():
    global _store, _store_cm
    if _store is not None:
        return

    dsn = _langgraph_dsn(POSTGRES_URL)

    _store_cm = PostgresStore.from_conn_string(dsn)
    _store = _store_cm.__enter__()
    _store.setup()

async def close_persistence():
    global _store, _store_cm

    if _store_cm is not None:
        _store_cm.__exit__(None, None, None)
        _store_cm = None
        _store = None

async def get_chatbot():
    global _chatbot
    await init_persistence()
    if _chatbot is None:
        _chatbot = await build_graph(_checkpointer, _store)
    return _chatbot
