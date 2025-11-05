import os
from typing import List, Dict, Optional
from datetime import datetime
try:
    import chromadb
    from chromadb.config import Settings
except Exception:
    chromadb = None
    Settings = None
try:
    from langchain.schema import HumanMessage, AIMessage
except ImportError:
    from langchain_core.messages import HumanMessage, AIMessage
try:
    from langchain.embeddings import HuggingFaceEmbeddings
except ImportError:
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
    except Exception:
        HuggingFaceEmbeddings = None

class ConversationMemory:
    """
    Manages conversation history and context.
    Uses ChromaDB + embeddings when available, but degrades gracefully to in-memory only.
    """
    
    def __init__(
        self,
        collection_name: str = "conversation_history",
        persist_directory: str = "./data/chroma",
        enable_vector_store: bool = False
    ):
        """
        Initialize conversation memory.
        
        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory to persist the database
            enable_vector_store: If True, attempt to init Chroma + embeddings immediately
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)

        # Vector store components (lazy)
        self._client = None
        self._collection = None
        self._embeddings = None
        self._vector_ready = False
        self._vector_error: Optional[str] = None

        # In-memory session history
        self.session_history: List[Dict] = []

        if enable_vector_store:
            self._ensure_vector_store()

    def _ensure_vector_store(self):
        """Initialize ChromaDB and embeddings if possible; mark disabled on failure."""
        if self._vector_ready:
            return
        try:
            if chromadb is None or Settings is None:
                raise RuntimeError("ChromaDB not available")
            self._client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Conversation history with semantic search"}
            )
            if HuggingFaceEmbeddings is None:
                raise RuntimeError("Embeddings backend not available")
            self._embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            self._vector_ready = True
        except Exception as e:
            # Disable vector features on failure; proceed with in-memory only
            self._vector_ready = False
            self._vector_error = str(e)

    @property
    def vector_enabled(self) -> bool:
        return self._vector_ready

    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """
        Add a message to conversation history (always) and vector store (when ready).
        """
        timestamp = datetime.now().isoformat()

        # Add to session history
        message = {
            "role": role,
            "content": content,
            "timestamp": timestamp,
            "metadata": metadata or {}
        }
        self.session_history.append(message)

        # Best-effort add to vector database
        if self._vector_ready:
            try:
                doc_id = f"{role}_{timestamp}"
                self._collection.add(
                    documents=[content],
                    ids=[doc_id],
                    metadatas=[{
                        "role": role,
                        "timestamp": timestamp,
                        **(metadata or {})
                    }]
                )
            except Exception:
                # On failure, disable vectors to avoid blocking future requests
                self._vector_ready = False

    def get_recent_messages(
        self,
        limit: int = 10,
        include_metadata: bool = False
    ) -> List[Dict]:
        """Get recent messages from in-memory session history."""
        messages = self.session_history[-limit:]
        if not include_metadata:
            return [{"role": m["role"], "content": m["content"]} for m in messages]
        return messages

    def search_similar_conversations(
        self,
        query: str,
        limit: int = 5
    ) -> List[Dict]:
        """
        Best-effort semantic search; returns [] when vector store is disabled.
        """
        if not self._vector_ready:
            return []
        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=limit
            )
            if not results or not results.get("documents"):
                return []
            similar_messages = []
            for i, doc in enumerate(results["documents"][0]):
                similar_messages.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "distance": results["distances"][0][i] if results.get("distances") else None
                })
            return similar_messages
        except Exception:
            return []

    def get_context_for_prompt(
        self,
        current_query: str,
        recent_messages: int = 5,
        similar_messages: int = 3
    ) -> str:
        """Build context string combining recent and relevant history."""
        context_parts = []
        recent = self.get_recent_messages(limit=recent_messages)
        if recent:
            context_parts.append("Recent conversation:")
            for msg in recent:
                context_parts.append(f"{msg['role'].title()}: {msg['content']}")
        similar = self.search_similar_conversations(current_query, limit=similar_messages)
        if similar:
            context_parts.append("\nRelevant past context:")
            for msg in similar:
                role = msg["metadata"].get("role", "unknown") if msg.get("metadata") else "unknown"
                context_parts.append(f"{role.title()}: {msg['content']}")
        return "\n".join(context_parts)

    def clear_session(self):
        """Clear the current session history (not the vector database)."""
        self.session_history = []

    def delete_all_history(self):
        """Delete all conversation history from vector database if enabled."""
        if self._vector_ready and self._client is not None:
            try:
                self._client.delete_collection(self.collection_name)
                self._collection = self._client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"description": "Conversation history with semantic search"}
                )
            except Exception:
                # ignore
                pass
        self.session_history = []

    def get_langchain_messages(self, limit: int = 10) -> List:
        """Get recent messages in LangChain format."""
        messages = []
        recent = self.get_recent_messages(limit=limit)
        for msg in recent:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        return messages
