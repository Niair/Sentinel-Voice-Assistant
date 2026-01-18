import os
import asyncio
from typing import TypedDict, Annotated, Optional
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
# In a production app, you might store this in a more robust way
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

# --- Graph Builder ---
async def build_graph(checkpointer):
    mcp_client = MultiServerMCPClient(SERVERS)
    try:
        mcp_tools = await mcp_client.get_tools()
    except Exception as e:
        print(f"Warning: Could not load MCP tools: {e}")
        mcp_tools = []
        
    all_tools = [search_tool, rag_tool] + list(mcp_tools)

    # Using a high-capability model for better tool use
    model = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.4)
    llm_with_tools = model.bind_tools(all_tools)

    async def agent(state: ChatState):
        # Add a system message if it's the start of the conversation
        messages = state['messages']
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    tool_node = ToolNode(all_tools)

    graph = StateGraph(ChatState)
    graph.add_node("agent", agent)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")

    return graph.compile(checkpointer=checkpointer)

# --- Singleton ---
_chatbot = None

async def get_chatbot():
    global _chatbot
    if _chatbot is None:
        conn = await aiosqlite.connect(DB_PATH)
        checkpointer = AsyncSqliteSaver(conn)
        _chatbot = await build_graph(checkpointer)
    return _chatbot
