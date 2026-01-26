import os
import json
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
from langgraph.store.base import BaseStore

from app.mcp import SafeMCPClient
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

# --- Global RAG State ---
_retrievers_by_thread: Dict[str, object] = {}
_doc_info_by_thread: Dict[str, Dict[str, object]] = {}
_current_thread_id = contextvars.ContextVar("current_thread_id", default="default_thread")

# --- Tools ---
_ddg = DuckDuckGoSearchRun(region="us-en")


@tool
def search_tool(query: str) -> str:
    """
    Search the internet for current information about recent events, news, facts, or dates.
    Use when the user asks about current information, today's date, recent events, or general knowledge.
    Returns: Search results as a string.
    """
    try:
        result = _ddg.invoke(query)
        return f"Search results: {result}"
    except Exception as e:
        return f"Search failed: {str(e)}"


@tool
def rag_tool(query: str, config: RunnableConfig = None) -> str:
    """
    Retrieve relevant information from the uploaded PDF document. 
    Use this when the user asks questions about the content of their uploaded files.
    """
    # ✅ FIX BUG 3: Get thread_id from config (injected by LangGraph) or fall back to context var
    thread_id = None
    if config and "configurable" in config:
        thread_id = config["configurable"].get("thread_id")
    if not thread_id:
        thread_id = _current_thread_id.get()
    
    print(f"🔍 RAG tool called with thread_id: {thread_id}, query: {query}")
    retriever = _retrievers_by_thread.get(thread_id)
    doc_info = _doc_info_by_thread.get(thread_id)
    
    if retriever is None or doc_info is None:
        print(f"⚠️ No document found for thread {thread_id}")
        return "No document is currently loaded. Please upload a PDF first."
    
    try:
        docs = retriever.invoke(query)
        if not docs:
            return f"No relevant information found in {doc_info.get('filename')} for your query."
        
        context_parts = []
        for i, doc in enumerate(docs[:4], 1):
            page = doc.metadata.get('page', 'unknown')
            context_parts.append(f"[Excerpt {i} from page {page}]:\n{doc.page_content}\n")
        
        result = f"Found {len(docs)} relevant sections in {doc_info.get('filename')}:\n\n" + "\n".join(context_parts)
        print(f"✅ RAG tool returning {len(result)} chars")
        return result
    except Exception as e:
        print(f"❌ RAG tool error: {e}")
        import traceback
        traceback.print_exc()
        return f"Error retrieving from document: {str(e)}"

# --- State Definition ---
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# --- MCP Client ---
_mcp_client = SafeMCPClient()

# --- RAG Logic ---
def process_document(pdf_path: str, thread_id: str = "default_thread"):
    """Process a PDF document and create a retriever"""
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
        
        # ✅ FIX: Use a simpler in-memory approach if PGVector fails
        try:
            embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
            collection_name = f"sentinel_thread_{thread_id}"
            vector_store = PGVector.from_documents(
                documents=chunks,
                embedding=embeddings,
                connection=_pgvector_conn(POSTGRES_URL),
                collection_name=collection_name
            )
            retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 4})
            print("✅ PGVector store created")
        except Exception as pg_error:
            print(f"⚠️ PGVector failed, using FAISS fallback: {pg_error}")
            from langchain_community.vectorstores import FAISS
            vector_store = FAISS.from_documents(chunks, embeddings)
            retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 4})
        
        # Store document info
        _current_doc_info = {
            "filename": os.path.basename(pdf_path),
            "pages": len(docs),
            "chunks": len(chunks),
            "path": pdf_path,
            "thread_id": thread_id,
        }

        _retrievers_by_thread[thread_id] = retriever
        _doc_info_by_thread[thread_id] = _current_doc_info
        
        print("✅ RAG system ready!")
        return {
            'success': True,
            "filename": _current_doc_info["filename"],
            'info': _current_doc_info
        }
        
    except Exception as e:
        print(f"❌ Error processing document: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }

def get_rag_status(thread_id: str = "default_thread"):
    """Get current RAG system status."""
    doc_info = _doc_info_by_thread.get(thread_id)
    return {
        "has_document": doc_info is not None,
        "document_info": doc_info,
        "rag_active": thread_id in _retrievers_by_thread
    }

# --- Long-term Memory Logic ---
SYSTEM_PROMPT_TEMPLATE = """
You are Sentinel, a helpful AI assistant. Answer user questions clearly and concisely.

If user-specific memory is available, use it to personalize your responses.
User memory: {user_details_content}

## Available Tools
You have access to the following tools:

1. **rag_tool**: Search uploaded PDF documents for information.
   - Use when: User asks about document content or uploaded files

2. **search_tool**: Search the internet for current information.
   - Use when: User asks about dates, recent events, facts, or news
   - IMPORTANT: Use this tool ONCE, then answer based on the results. Do NOT call it multiple times.

3. **MCP Tools** (Finance & Expense Tracking):
{available_tools}

**CRITICAL RULES:**
1. When you call a tool, WAIT for the result and USE IT in your answer
2. DO NOT call the same tool multiple times for the same question
3. DO NOT make up data - if you used a tool and got results, use those results
4. If a tool returns "no data" or empty results, say so clearly - don't hallucinate
5. After using a tool, provide a direct answer based on the tool's output
6. **IMPORTANT**: For expense tools, always use NUMBERS for amounts (e.g., 50, not "50")
7. **IMPORTANT**: For date parameters, use YYYY-MM-DD format (e.g., "2024-01-15") or "today"

Always provide helpful, accurate, factual responses based on tool results.
"""

# ✅ FIX: Safe agent execution with error handling
async def agent(state: ChatState, config: RunnableConfig, store: BaseStore):
    user_id = config["configurable"].get("user_id", "default_user")
    thread_id = config["configurable"].get("thread_id", "default_thread")
    _current_thread_id.set(thread_id)
    
    print(f"🤖 Agent called for thread {thread_id}, {len(state['messages'])} messages")
    
    # Fetch long-term memories from the store
    namespace = ("user", user_id, "details")
    try:
        items = store.search(namespace)
        if items:
            user_details_content = "\n".join(f"- {it.value.get('data', '')}" for it in items)
        else:
            user_details_content = "No previous memories found."
    except Exception as e:
        print(f"⚠️ Store search failed: {e}")
        user_details_content = "No previous memories found."

    # ✅ FIX: Only load MCP tools selectively to avoid overwhelming Groq
    static_tools = [rag_tool, search_tool]
    mcp_tools = []
    
    # Check if user message mentions finance/expense keywords
    last_user_msg = ""
    for msg in reversed(state['messages']):
        if hasattr(msg, 'type') and msg.type == 'human':
            last_user_msg = str(msg.content).lower()
            break
    
    # Only load MCP tools if relevant to the query
    load_mcp = any(keyword in last_user_msg for keyword in [
        'expense', 'income', 'money', 'finance', 'spending', 'budget', 
        'salary', 'cost', 'price', 'pay', 'cash', 'dollar', 'rupee', 'rs',
        'spent', 'earn', 'transaction', 'payment', 'bill', 'purchase'
    ])
    
    if load_mcp:
        try:
            if not _mcp_client.get_tools():
                await _mcp_client.initialize()
            mcp_tools = _mcp_client.get_tools()
            print(f"💰 Loading {len(mcp_tools)} MCP tools (finance query detected in: '{last_user_msg[:60]}...')")
        except Exception as e:
            print(f"⚠️ MCP tool initialization failed: {e}")
    else:
        print(f"📝 Using only static tools (no finance keywords in: '{last_user_msg[:50]}...')")
    
    all_tools = static_tools + mcp_tools
    print(f"🔧 Agent has {len(all_tools)} tools available")
    
    # Build tool descriptions
    tool_descriptions = []
    if mcp_tools:
        tool_descriptions.append("\n**Available MCP Tools:**")
        for t in mcp_tools:
            desc = t.description if len(t.description) <= 100 else f"{t.description[:100]}..."
            tool_descriptions.append(f"   - **{t.name}**: {desc}")
        tool_descriptions.append("\n**YOU MUST use these tools when user asks about expenses or finances. DO NOT make up data.**")
    
    available_tools_text = "\n".join(tool_descriptions) if tool_descriptions else "   (No MCP tools loaded for this query)"

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        user_details_content=user_details_content,
        available_tools=available_tools_text
    )
    
    # Determine which model to use
    selected_model = config["configurable"].get("model", "llama-3.3-70b-versatile")
    
    model_mapping = {
        "llama-3.3-70b-versatile": "llama-3.3-70b-versatile",
        "grok-4.1-fast": "llama-3.1-70b-versatile"
    }
    
    groq_model = model_mapping.get(selected_model, "llama-3.3-70b-versatile")
    print(f"🧠 Using model: {groq_model}")
    
    # ✅ FIX: Lower temperature and add max retries to prevent loops
    model = ChatGroq(model=groq_model, temperature=0.1, timeout=30.0, max_retries=2)
    llm_with_tools = model.bind_tools(all_tools)
    
    # Filter and validate messages
    validated_messages = []
    for msg in state['messages']:
        if hasattr(msg, 'type') and msg.type == 'tool':
            if not msg.content or (isinstance(msg.content, list) and len(msg.content) == 0):
                continue
            if isinstance(msg.content, list):
                msg.content = str(msg.content)
        validated_messages.append(msg)
    
    # ✅ FIX: Limit conversation history to prevent context overflow
    max_messages = 10
    if len(validated_messages) > max_messages:
        print(f"⚠️ Truncating message history from {len(validated_messages)} to {max_messages}")
        validated_messages = validated_messages[-max_messages:]

    messages = [SystemMessage(content=system_prompt)] + validated_messages
    print(f"📨 Sending {len(messages)} messages to LLM")
    
    try:
        response = await llm_with_tools.ainvoke(messages)
        print(f"✅ LLM response received, has tool_calls: {bool(response.tool_calls)}")
        return {"messages": [response]}
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error in LLM invocation: {error_msg}")
        
        # ✅ FIX: If tool validation fails, try to fix the parameters and retry
        if "tool call validation failed" in error_msg and "expected number, but got string" in error_msg:
            print(f"🔧 Attempting to fix tool parameter types and retry...")
            try:
                # Get the last user message to extract the intent
                last_user_msg = None
                for msg in reversed(validated_messages):
                    if hasattr(msg, 'type') and msg.type == 'human':
                        last_user_msg = msg.content
                        break
                
                if last_user_msg and any(keyword in last_user_msg.lower() for keyword in ['expense', 'add', 'cost']):
                    # Extract amount from the message using regex
                    import re
                    amount_match = re.search(r'\b(\d+(?:\.\d+)?)\b', last_user_msg)
                    if amount_match:
                        amount = float(amount_match.group(1))
                        
                        # Extract description (everything after amount or before amount)
                        description_parts = re.split(r'\b\d+(?:\.\d+)?\b', last_user_msg)
                        description = ' '.join(description_parts).strip()
                        description = re.sub(r'\b(add|expense|for|the|today|of)\b', '', description, flags=re.IGNORECASE).strip()
                        if not description:
                            description = "expense"
                        
                        # Get today's date
                        from datetime import datetime
                        today = datetime.now().strftime('%Y-%m-%d')
                        
                        # Create a direct tool call message
                        from langchain_core.messages import AIMessage
                        tool_call_msg = AIMessage(
                            content="I'll add that expense for you.",
                            tool_calls=[{
                                "name": "add_expense",
                                "args": {
                                    "amount": amount,
                                    "description": description,
                                    "date": today,
                                    "category": "general"
                                },
                                "id": "manual_expense_add"
                            }]
                        )
                        print(f"🔧 Created manual tool call: amount={amount}, description='{description}'")
                        return {"messages": [tool_call_msg]}
            except Exception as retry_error:
                print(f"❌ Manual tool call creation failed: {retry_error}")
        
        # ✅ FIX: If Groq rejects function calling, retry without tools
        if "Failed to call a function" in error_msg or "function" in error_msg.lower():
            print(f"⚠️ Function calling failed, retrying without tools...")
            try:
                model_no_tools = ChatGroq(model=groq_model, temperature=0.1, timeout=30.0)
                response = await model_no_tools.ainvoke(messages)
                print(f"✅ Retry successful without tools")
                return {"messages": [response]}
            except Exception as retry_error:
                print(f"❌ Retry also failed: {retry_error}")
        
        import traceback
        traceback.print_exc()
        return {"messages": [AIMessage(content=f"I encountered an error: {str(e)}. Please try rephrasing your question.")]}

async def safe_tool_node(state: ChatState, config: RunnableConfig) -> ChatState:
    """Wrapper around tool node to ensure all tool messages have content and handle errors"""
    
    # ✅ FIX BUG 3: Set thread context for tool execution
    thread_id = config.get("configurable", {}).get("thread_id", "default_thread")
    _current_thread_id.set(thread_id)
    
    try:
        # ✅ FIX BUG 1: Always get fresh tools (don't cache) to ensure MCP tools are available
        static_tools = [rag_tool, search_tool]
        try:
            if not _mcp_client.get_tools():
                await _mcp_client.initialize()
            all_tools = static_tools + _mcp_client.get_tools()
        except Exception as e:
            print(f"⚠️ MCP tools unavailable in tool node: {e}")
            all_tools = static_tools
        
        # ✅ FIX: Validate and fix tool call parameters before execution
        if 'messages' in state and state['messages']:
            last_msg = state['messages'][-1]
            if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                for tool_call in last_msg.tool_calls:
                    tool_name = tool_call.get('name', '')
                    args = tool_call.get('args', {})
                    
                    # Fix common parameter type issues for MCP tools
                    if tool_name == 'add_expense':
                        if 'amount' in args and isinstance(args['amount'], str):
                            try:
                                # Convert string amount to float
                                args['amount'] = float(args['amount'])
                                print(f"🔧 Fixed add_expense amount: '{args['amount']}' -> {args['amount']}")
                            except ValueError:
                                print(f"⚠️ Could not convert amount '{args['amount']}' to number")
                    
                    elif tool_name in ['list_expenses', 'summarize', 'net_cashflow']:
                        # Fix date parameters if they're malformed
                        for date_param in ['start_date', 'end_date', 'date']:
                            if date_param in args and isinstance(args[date_param], str):
                                # Ensure date is in YYYY-MM-DD format
                                date_str = args[date_param]
                                if date_str and not date_str.count('-') == 2:
                                    # Try to fix common date formats
                                    from datetime import datetime
                                    try:
                                        if date_str.lower() == 'today':
                                            args[date_param] = datetime.now().strftime('%Y-%m-%d')
                                        elif '/' in date_str:
                                            # Convert MM/DD/YYYY to YYYY-MM-DD
                                            dt = datetime.strptime(date_str, '%m/%d/%Y')
                                            args[date_param] = dt.strftime('%Y-%m-%d')
                                    except:
                                        pass
        
        tool_node = ToolNode(all_tools)
        
        # ✅ FIX BUG 1 & 3: Pass config to tool node so tools receive thread_id
        result = await tool_node.ainvoke(state, config)
        
        # ✅ FIX: Validate and serialize tool messages properly
        if 'messages' in result:
            fixed_messages = []
            for msg in result['messages']:
                if hasattr(msg, 'type') and msg.type == 'tool':
                    # Ensure content is a string
                    if not msg.content:
                        msg.content = "Tool executed successfully"
                    elif isinstance(msg.content, list):
                        msg.content = str(msg.content)
                    elif isinstance(msg.content, dict):
                        # Convert dict to readable string
                        msg.content = json.dumps(msg.content, indent=2)
                    elif not isinstance(msg.content, str):
                        # Convert any other type to string
                        msg.content = str(msg.content)
                fixed_messages.append(msg)
            result['messages'] = fixed_messages
        
        return result
    except Exception as e:
        print(f"❌ Error in tool execution: {e}")
        import traceback
        traceback.print_exc()
        
        # ✅ FIX BUG 1: Get the actual tool_call_id from the last message
        last_msg = state['messages'][-1] if state['messages'] else None
        tool_call_id = "unknown"
        if last_msg and hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
            tool_call_id = last_msg.tool_calls[0].get('id', 'unknown')
        
        return {"messages": [ToolMessage(
            content=f"Tool execution failed: {str(e)}",
            tool_call_id=tool_call_id
        )]}

# --- Graph Builder ---
async def build_graph(checkpointer, store):
    # Initialize MCP client
    await _mcp_client.initialize()
    
    print("🔧 Building graph...")
    graph = StateGraph(ChatState)
    graph.add_node("agent", agent)
    graph.add_node("tools", safe_tool_node)
    graph.add_edge(START, "agent")
    
    # Add conditional edges with tool routing
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")

    print("✅ Compiling graph...")
    compiled_graph = graph.compile(checkpointer=checkpointer, store=store)
    print("✅ Graph compiled successfully")
    return compiled_graph

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