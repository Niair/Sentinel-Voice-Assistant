"""
Qdrant client wrapper for RAG system - FIXED & OPTIMIZED
"""

import os
from typing import List, Optional, Dict, Any
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from langchain_core.documents import Document
from dotenv import load_dotenv

# Handle langchain-google-genai import
try:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    GEMINI_EMBEDDINGS_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] langchain-google-genai import error: {e}")
    GEMINI_EMBEDDINGS_AVAILABLE = False
    GoogleGenerativeAIEmbeddings = None

load_dotenv()


class SafeQdrantClient:
    """
    Thread-safe Qdrant client wrapper.
    """

    def __init__(self):
        self._client: Optional[AsyncQdrantClient] = None
        self._embeddings: Optional[GoogleGenerativeAIEmbeddings] = None
        self._embedding_dim = 3072  # Google gemini-embedding-001
        self._initialized = False
        self.qdrant_url = os.getenv("QDRANT_URL")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY")

    async def initialize(self) -> None:
        """Initialize Qdrant client and embedding model"""
        if self._initialized:
            return

        try:
            if not self.qdrant_url or not self.qdrant_api_key:
                raise ValueError("QDRANT_URL and QDRANT_API_KEY must be set in .env")

            if not GEMINI_EMBEDDINGS_AVAILABLE:
                raise ImportError("langchain-google-genai is not installed.")

            # 1. Init Embeddings
            self._embeddings = GoogleGenerativeAIEmbeddings(
                model="gemini-embedding-001"
            )

            # 2. Init Qdrant Client (Enable gRPC for performance)
            self._client = AsyncQdrantClient(
                url=self.qdrant_url,
                api_key=self.qdrant_api_key,
                prefer_grpc=True,  # ✅ OPTIMIZATION: Faster data transfer
            )

            # 3. Verify Connection
            await self._client.get_collections()

            self._initialized = True
            print(f"[SUCCESS] Qdrant RAG system initialized (URL: {self.qdrant_url})")

        except Exception as e:
            print(f"[ERROR] Qdrant init failed: {e}")
            self._client = None
            raise

    def is_available(self) -> bool:
        return self._initialized and self._client is not None

    async def create_collection(self, collection_name: str) -> bool:
        if not self.is_available():
            return False
        try:
            if await self._client.collection_exists(collection_name):
                return True

            await self._client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self._embedding_dim, distance=Distance.COSINE
                ),
            )
            return True
        except Exception as e:
            print(f"[ERROR] Create collection failed: {e}")
            return False

    async def index_documents(
        self, collection_name: str, documents: List[Document], batch_size: int = 50
    ) -> Dict[str, Any]:
        """Index documents using upsert"""
        if not self.is_available():
            return {"success": False, "error": "Client not available"}

        try:
            await self.create_collection(collection_name)

            texts = [doc.page_content for doc in documents]
            metadatas = [doc.metadata for doc in documents]

            print(f"[INFO] Embedding {len(texts)} chunks...")
            embeddings = await self._embeddings.aembed_documents(texts)

            points = []
            for idx, (text, embedding, metadata) in enumerate(
                zip(texts, embeddings, metadatas)
            ):
                # Use a stable ID if possible, otherwise auto-generate or use int
                import uuid

                point_id = str(uuid.uuid4())

                points.append(
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload={
                            "text": text,
                            "metadata": metadata,
                            "page": metadata.get("page", 0),
                        },
                    )
                )

            # Batch Upload
            for i in range(0, len(points), batch_size):
                batch = points[i : i + batch_size]
                await self._client.upsert(
                    collection_name=collection_name,
                    points=batch,
                    wait=True,  # ✅ Ensure readable immediately
                )

            return {"success": True, "chunks_indexed": len(documents)}

        except Exception as e:
            print(f"[ERROR] Indexing failed: {e}")
            return {"success": False, "error": str(e)}

    async def search(
        self,
        collection_name: str,
        query: str,
        limit: int = 6,
        score_threshold: float = 0.3,
    ) -> List[Document]:
        """
        Search utilizing the correct query_points API
        """
        if not self.is_available():
            return []

        try:
            # 1. Embed Query
            query_embedding = await self._embeddings.aembed_query(query)

            # 2. Search using query_points (FIXED BUG)
            response = await self._client.query_points(
                collection_name=collection_name,
                query=query_embedding,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,
            )

            # 3. Parse Results
            documents = []
            # Note: response.points contains the ScoredPoint list
            for point in response.points:
                doc = Document(
                    page_content=point.payload.get("text", ""),
                    metadata={
                        **point.payload.get("metadata", {}),
                        "score": point.score,
                        "page": point.payload.get("page"),
                    },
                )
                documents.append(doc)

            return documents

        except Exception as e:
            print(f"[ERROR] Search failed: {e}")
            import traceback

            traceback.print_exc()
            return []

    async def collection_exists(self, collection_name: str) -> bool:
        if not self.is_available():
            return False
        try:
            return await self._client.collection_exists(collection_name)
        except Exception:
            return False

    async def delete_collection(self, collection_name: str):
        if self.is_available():
            await self._client.delete_collection(collection_name)


# Singleton
_qdrant_client: Optional[SafeQdrantClient] = None


def get_qdrant_client() -> SafeQdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = SafeQdrantClient()
    return _qdrant_client
