from langchain_groq import ChatGroq
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.tools import tool

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from typing import TypedDict, Annotated

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_mcp_adapters.client import MultiServerMCPClient

from langchain_core.messages import BaseMessage, HumanMessage

import os
import asyncio
import aiosqlite
import threading

from dotenv import load_dotenv
load_dotenv()


# ============================================================
# BACKGROUND EVENT LOOP
# ============================================================

# Create a dedicated event loop in a background thread
_ASYNC_LOOP = asyncio.new_event_loop()
_ASYNC_THREAD = threading.Thread(target=_ASYNC_LOOP.run_forever, daemon=True)
_ASYNC_THREAD.start()


def _submit_async(coro):
    """Submit a coroutine to the background event loop."""
    return asyncio.run_coroutine_threadsafe(coro, _ASYNC_LOOP)


def run_async(coro):
    """Run a coroutine on the background loop and wait for result."""
    return _submit_async(coro).result()


def submit_async_task(coro):
    """Schedule a coroutine on the backend event loop without waiting."""
    return _submit_async(coro)


# ============================================================
# CONFIGURATION
# ============================================================

DB_PATH = "chatbot.db"

SERVERS = {
    "math": {
        "transport": "stdio",
        "command": "E:\\VS_Code\\Scripts\\uv.exe",
        "args": [
            "run",
            "fastmcp",
            "run",
            "E:\\_Projects\\GAIP\\MCP\\chat_bot_with_mcp\\local_mcp.py"
        ],
        "env": {},
        "cwd": "E:\\_Projects\\GAIP\\MCP\\chat_bot_with_mcp"
    },
    "expense": {
        "transport": "streamable_http",
        "url": "https://nihal-finance-server.fastmcp.app/mcp"
    }
}


# ============================================================
# GLOBAL STATE
# ============================================================

checkpointer = None
chatbot = None
model = None
mcp_client = None
_initialized = False
retriever = None
vector_store = None
current_document_info = None


# ============================================================
# TOOLS
# ============================================================

search_tool = DuckDuckGoSearchRun(region="us-en")

# Smart RAG tool that checks document availability
@tool
def rag_tool(query: str) -> dict:
    """
    Retrieve relevant information from the uploaded PDF document. 
    Use this tool when the user asks factual or conceptual questions 
    that might be answered from documents.
    
    This tool will inform if no document is currently loaded.
    """
    global retriever, current_document_info
    
    # Check if document is loaded
    if retriever is None or current_document_info is None:
        return {
            'query': query,
            'context': [],
            'metadata': [],
            'message': 'No document is currently loaded. Please upload a PDF document first to answer questions about document content.',
            'has_document': False
        }
    
    try:
        # Document exists - retrieve information
        result = retriever.invoke(query)
        
        context = [doc.page_content for doc in result]
        metadata = [doc.metadata for doc in result]
        
        return {
            'query': query,
            'context': context,
            'metadata': metadata,
            'document': current_document_info['filename'],
            'has_document': True
        }
    
    except Exception as e:
        return {
            'query': query,
            'context': [],
            'metadata': [],
            'error': f"Error retrieving documents: {str(e)}",
            'has_document': True
        }


def process_document(pdf_path: str):
    """
    Process a PDF document and create a retriever.
    Returns document info and the retriever.
    """
    global retriever, vector_store, current_document_info
    
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
        vector_store = FAISS.from_documents(chunks, embeddings)
        print("✅ Vector store created")
        
        # Create retriever
        retriever = vector_store.as_retriever(
            search_type='similarity',
            search_kwargs={'k': 4}
        )
        
        # Store document info
        current_document_info = {
            'filename': os.path.basename(pdf_path),
            'pages': len(docs),
            'chunks': len(chunks),
            'path': pdf_path
        }
        
        print("✅ RAG system ready!")
        return {
            'success': True,
            'info': current_document_info
        }
        
    except Exception as e:
        print(f"❌ Error processing document: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def remove_document():
    """Remove the current document and disable RAG."""
    global retriever, vector_store, current_document_info
    
    retriever = None
    vector_store = None
    current_document_info = None
    
    print("📭 Document removed, RAG disabled")
    return {'success': True}


def get_rag_status():
    """Get current RAG system status."""
    return {
        'has_document': current_document_info is not None,
        'document_info': current_document_info,
        'rag_active': retriever is not None  # FIXED: was rag_tool_instance
    }


# ============================================================
# STATE DEFINITION
# ============================================================

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ============================================================
# GRAPH BUILDER
# ============================================================

async def build_graph(client, checkpointer_param):
    """Build the LangGraph chatbot with MCP tools"""
    global model
    
    mcp_tools = await client.get_tools()
    all_tools = [search_tool, rag_tool] + list(mcp_tools)

    print("Available tools:")
    for tool in all_tools:
        print(f"  - {tool.name}: {tool.description}")

    model = ChatGroq(model="openai/gpt-oss-20b", temperature=0.4) # openai/gpt-oss-120b
    llm_with_tools = model.bind_tools(all_tools)

    async def main_llm_function(state: ChatState) -> ChatState:
        messages = state['messages']
        
        # Filter and validate messages before sending to LLM
        validated_messages = []
        for msg in messages:
            # Skip tool messages with empty or invalid content
            if hasattr(msg, 'type') and msg.type == 'tool':
                if not msg.content or (isinstance(msg.content, list) and len(msg.content) == 0):
                    print(f"Skipping empty tool message: {msg}")
                    continue
                # Ensure content is a string
                if isinstance(msg.content, list):
                    msg.content = str(msg.content)
            validated_messages.append(msg)
        
        response = await llm_with_tools.ainvoke(validated_messages)
        return {"messages": [response]}

    # Create tool node with wrapper for error handling
    base_tool_node = ToolNode(all_tools)
    
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
            from langchain_core.messages import ToolMessage
            return {"messages": [ToolMessage(
                content=f"Tool execution failed: {str(e)}",
                tool_call_id=state['messages'][-1].tool_calls[0]['id'] if state['messages'][-1].tool_calls else "error"
            )]}

    graph = StateGraph(ChatState)
    graph.add_node("main_llm_function", main_llm_function)
    graph.add_node("tools", safe_tool_node)
    
    graph.add_edge(START, "main_llm_function")
    graph.add_conditional_edges("main_llm_function", tools_condition)
    graph.add_edge("tools", "main_llm_function")

    compiled_graph = graph.compile(checkpointer=checkpointer_param)
    return compiled_graph

# ============================================================
# INITIALIZATION
# ============================================================

async def _init_async():
    """Async initialization function"""
    global checkpointer, chatbot, mcp_client
    
    print("Initializing MCP client...")
    mcp_client = MultiServerMCPClient(SERVERS)
    print("✓ MCP client created")
    
    print("Initializing database...")
    conn = await aiosqlite.connect(DB_PATH)
    checkpointer = AsyncSqliteSaver(conn=conn)
    print("✓ Checkpointer initialized")
    
    print("Building chatbot graph...")
    chatbot_instance = await build_graph(mcp_client, checkpointer)
    print("✓ Chatbot graph built successfully")
    
    return chatbot_instance


def initialize_sync():
    """Synchronously initialize all async components using background thread"""
    global chatbot, _initialized
    
    if _initialized:
        return chatbot
    
    try:
        chatbot = run_async(_init_async())
        _initialized = True
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    return chatbot


def get_chatbot():
    """Get or initialize chatbot instance"""
    global chatbot
    if chatbot is None:
        initialize_sync()
    return chatbot


# ============================================================
# HELPER FUNCTIONS
# ============================================================

async def _alist_threads():
    """Async function to retrieve all thread IDs from checkpointer"""
    if checkpointer is None:
        return []
    
    all_threads = set()
    try:
        async for checkpoint in checkpointer.alist(None):
            thread_id = checkpoint.config.get("configurable", {}).get("thread_id")
            if thread_id:
                all_threads.add(thread_id)
    except Exception as e:
        print(f"Error retrieving threads: {e}")
    
    return list(all_threads)


def retrieve_all_threads():
    """Retrieve all thread IDs from checkpointer (sync wrapper)"""
    return run_async(_alist_threads())


# ============================================================
# MAIN EXECUTION (for testing)
# ============================================================

async def main():
    """Test function"""
    client = MultiServerMCPClient(SERVERS)
    
    async with aiosqlite.connect(DB_PATH) as conn:
        global checkpointer, chatbot, model
        checkpointer = AsyncSqliteSaver(conn=conn)
        chatbot = await build_graph(client, checkpointer)
        
        print("\n" + "="*50)
        print("Testing chatbot...")
        print("="*50 + "\n")
        
        async for message_chunk, metadata in chatbot.astream(
            {'messages': [HumanMessage(content="Hello! Can you help me calculate 15 + 27?")]},
            config={'configurable': {'thread_id': 'test-thread'}},
            stream_mode='messages'
        ):
            if hasattr(message_chunk, 'content') and message_chunk.content:
                print(message_chunk.content, end="", flush=True)
        
        print("\n" + "="*50)
        print("Test completed!")
        print("="*50)


if __name__ == "__main__":
    asyncio.run(main())