"""
Test script for Jina AI Embeddings with Qdrant
Tests embedding generation, storage, and querying

Usage:
    cd backend
    uv run python tests/test_jina_embeddings.py

This script will:
1. Load the PDF from _assets/
2. Create chunks with larger size (2000 chars)
3. Generate embeddings using Jina AI
4. Store in Qdrant
5. Allow you to ask questions
6. Save embeddings to uploads/ folder for easy cleanup
"""

import asyncio
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from langchain_community.document_loaders import PyMuPDFLoader

# from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Load environment variables
load_dotenv()

# Configuration
# Get project root (3 levels up from backend/tests/test_jina_embeddings.py)
PROJECT_ROOT = Path(__file__).parent.parent.parent
PDF_PATH = (
    PROJECT_ROOT
    / "_assets"
    / "Building Machine Learning Systems with Python - Second Edition.pdf"
)
UPLOADS_DIR = Path("uploads")
COLLECTION_NAME = "test_jina_embeddings"
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 200


class JinaEmbeddingTester:
    """Test class for Jina AI embeddings with Qdrant."""

    def __init__(self):
        self.qdrant_url = os.getenv("QDRANT_URL")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY")
        self.jina_api_key = os.getenv("JINA_AI")

        if not self.jina_api_key:
            raise ValueError("JINA_AI API key not found in .env file")

        self.client: AsyncQdrantClient = None
        self.embedding_dim = 768  # Jina embeddings v2 base dimension

    async def initialize(self):
        """Initialize Qdrant client."""
        print("🚀 Initializing Jina AI Embedding Test...")
        print(f"   Qdrant URL: {self.qdrant_url}")
        print(f"   Jina API Key: {self.jina_api_key[:10]}...")

        self.client = AsyncQdrantClient(
            url=self.qdrant_url, api_key=self.qdrant_api_key, prefer_grpc=True
        )

        # Test connection
        await self.client.get_collections()
        print("✅ Qdrant connection successful!")

    async def create_collection(self):
        """Create or recreate test collection."""
        print(f"\n📁 Creating collection: {COLLECTION_NAME}")

        # Delete if exists
        try:
            await self.client.delete_collection(COLLECTION_NAME)
            print("   Deleted existing collection")
        except:
            pass

        # Create new collection
        await self.client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=self.embedding_dim, distance=Distance.COSINE
            ),
        )
        print("✅ Collection created")

    def load_pdf(self) -> List[Document]:
        """Load PDF and return documents."""
        print(f"\n📄 Loading PDF: {PDF_PATH}")

        if not PDF_PATH.exists():
            raise FileNotFoundError(f"PDF not found at {PDF_PATH}")

        loader = PyMuPDFLoader(str(PDF_PATH))
        docs = loader.load()
        print(f"✅ Loaded {len(docs)} pages from PDF")
        return docs

    def create_chunks(self, docs: List[Document]) -> List[Document]:
        """Split documents into chunks."""
        print(f"\n✂️  Creating chunks...")
        print(f"   Chunk size: {CHUNK_SIZE}")
        print(f"   Chunk overlap: {CHUNK_OVERLAP}")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
        )

        chunks = splitter.split_documents(docs)
        avg_chars = (
            int(sum(len(chunk.page_content) for chunk in chunks) / len(chunks))
            if chunks
            else 0
        )
        print(f"✅ Created {len(chunks)} chunks (avg ~{avg_chars} chars/chunk)")
        return chunks

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Jina AI API directly."""
        import aiohttp

        print(f"\n🤖 Generating embeddings with Jina AI...")
        print(f"   Total texts: {len(texts)}")

        embeddings = []
        batch_size = 100  # Jina AI batch limit

        async with aiohttp.ClientSession() as session:
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(texts) + batch_size - 1) // batch_size

                print(
                    f"   Processing batch {batch_num}/{total_batches} ({len(batch)} texts)..."
                )

                async with session.post(
                    "https://api.jina.ai/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.jina_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"input": batch, "model": "jina-embeddings-v2-base-en"},
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Jina API error: {error_text}")

                    data = await response.json()
                    batch_embeddings = [item["embedding"] for item in data["data"]]
                    embeddings.extend(batch_embeddings)

        print(f"✅ Generated {len(embeddings)} embeddings")
        return embeddings

    def save_embeddings_to_file(
        self, chunks: List[Document], embeddings: List[List[float]]
    ):
        """Save embeddings to uploads folder for easy cleanup."""
        print(f"\n💾 Saving embeddings to uploads folder...")

        UPLOADS_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"jina_embeddings_{timestamp}.json"
        filepath = UPLOADS_DIR / filename

        data = {
            "timestamp": timestamp,
            "pdf_name": PDF_PATH.name,
            "total_chunks": len(chunks),
            "embedding_dim": self.embedding_dim,
            "chunks": [
                {
                    "text": chunk.page_content[:200] + "...",  # Truncate for file size
                    "metadata": chunk.metadata,
                    "embedding_preview": emb[:5],  # First 5 values
                }
                for chunk, emb in zip(chunks, embeddings)
            ],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        print(f"✅ Saved to: {filepath}")
        print(f"   File size: {filepath.stat().st_size / 1024:.1f} KB")
        return filepath

    async def store_in_qdrant(
        self, chunks: List[Document], embeddings: List[List[float]]
    ):
        """Store chunks and embeddings in Qdrant."""
        print(f"\n📤 Storing in Qdrant...")

        points = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            points.append(
                PointStruct(
                    id=idx,
                    vector=embedding,
                    payload={
                        "text": chunk.page_content,
                        "metadata": chunk.metadata,
                        "page": chunk.metadata.get("page", 0),
                    },
                )
            )

        # Upload in batches
        batch_size = 50
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            await self.client.upsert(
                collection_name=COLLECTION_NAME, points=batch, wait=True
            )

        print(f"✅ Stored {len(points)} points in Qdrant")

    async def search(self, query: str, limit: int = 5) -> List[Dict]:
        """Search for similar documents."""
        print(f"\n🔍 Searching for: '{query}'")

        # Generate query embedding
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.jina.ai/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {self.jina_api_key}",
                    "Content-Type": "application/json",
                },
                json={"input": [query], "model": "jina-embeddings-v2-base-en"},
            ) as response:
                data = await response.json()
                query_embedding = data["data"][0]["embedding"]

        # Search Qdrant
        results = await self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_embedding,
            limit=limit,
            with_payload=True,
        )

        print(f"✅ Found {len(results.points)} results\n")
        return results.points

    async def cleanup(self):
        """Cleanup - delete collection."""
        print(f"\n🧹 Cleaning up...")
        try:
            await self.client.delete_collection(COLLECTION_NAME)
            print("✅ Collection deleted")
        except Exception as e:
            print(f"   Note: {e}")


async def interactive_test():
    """Run interactive test session."""
    tester = JinaEmbeddingTester()

    try:
        # Initialize
        await tester.initialize()
        await tester.create_collection()

        # Load and process PDF
        docs = tester.load_pdf()
        chunks = tester.create_chunks(docs)

        # Generate embeddings
        texts = [chunk.page_content for chunk in chunks]
        embeddings = await tester.generate_embeddings(texts)

        # Save to file
        tester.save_embeddings_to_file(chunks, embeddings)

        # Store in Qdrant
        await tester.store_in_qdrant(chunks, embeddings)

        print("\n" + "=" * 70)
        print("✅ TEST COMPLETE - Embeddings working perfectly!")
        print("=" * 70)

        # Interactive query loop
        print("\n📝 You can now ask questions about the PDF.")
        print("   Type your question and press Enter.")
        print("   Type 'quit' to exit and cleanup.\n")

        while True:
            query = input("Your question: ").strip()

            if query.lower() in ["quit", "exit", "q"]:
                break

            if not query:
                continue

            try:
                results = await tester.search(query, limit=3)

                print("\n📚 Top Results:")
                print("-" * 70)
                for i, point in enumerate(results, 1):
                    score = point.score
                    text = point.payload.get("text", "")[:300]
                    page = point.payload.get("page", "N/A")
                    print(f"\n{i}. [Score: {score:.3f}] [Page: {page}]")
                    print(f"   {text}...")
                print("\n" + "-" * 70)

            except Exception as e:
                print(f"❌ Search error: {e}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Cleanup
        await tester.cleanup()
        print("\n👋 Test session complete!")


if __name__ == "__main__":
    print("🧪 Jina AI Embeddings Test Script")
    print("=" * 70)
    print(f"PDF: {PDF_PATH.name}")
    print(f"Collection: {COLLECTION_NAME}")
    print("=" * 70 + "\n")

    asyncio.run(interactive_test())
