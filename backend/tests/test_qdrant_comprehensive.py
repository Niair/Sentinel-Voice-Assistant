"""
Comprehensive Qdrant RAG Test Suite
Tests connection, indexing, AND retrieval quality

Run from backend directory: python tests/test_qdrant_comprehensive.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.qdrant_manager import get_qdrant_client
from langchain_core.documents import Document


async def test_1_connection():
    """Test 1: Qdrant connection"""
    print("\n" + "=" * 70)
    print("TEST 1: Qdrant Connection")
    print("=" * 70)
    
    try:
        client = get_qdrant_client()
        await client.initialize()
        
        if client.is_available():
            print("✅ Qdrant connection successful!")
            print(f"   URL: {client.qdrant_url}")
            return True
        else:
            print("❌ Qdrant client not available")
            return False
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False


async def test_2_collection_operations():
    """Test 2: Collection creation and management"""
    print("\n" + "=" * 70)
    print("TEST 2: Collection Operations")
    print("=" * 70)
    
    try:
        client = get_qdrant_client()
        test_collection = "test_sentinel_collection_" + str(asyncio.get_event_loop().time()).replace(".", "_")
        
        # Create collection
        print(f"Creating collection '{test_collection}'...")
        success = await client.create_collection(test_collection)
        if not success:
            print("❌ Failed to create collection")
            return False
        print("✅ Collection created")
        
        # Verify exists
        exists = await client.collection_exists(test_collection)
        if not exists:
            print("❌ Collection doesn't exist after creation")
            return False
        print("✅ Collection verified to exist")
        
        # Delete collection (cleanup)
        print(f"Cleaning up test collection...")
        await client.delete_collection(test_collection)
        print("✅ Collection deleted")
        
        return True
        
    except Exception as e:
        print(f"❌ Collection operations test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_3_document_indexing():
    """Test 3: Document indexing and basic search"""
    print("\n" + "=" * 70)
    print("TEST 3: Document Indexing & Basic Search")
    print("=" * 70)
    
    try:
        client = get_qdrant_client()
        test_collection = "test_rag_" + str(asyncio.get_event_loop().time()).replace(".", "_")
        
        # Create test documents with specific content
        test_docs = [
            Document(
                page_content="Sentinel is a voice-first AI assistant with monitoring capabilities. It uses LangGraph for orchestration.",
                metadata={"page": 1, "source": "test.pdf"}
            ),
            Document(
                page_content="The monitoring system uses computer vision to detect people and objects in real-time using YOLO models.",
                metadata={"page": 2, "source": "test.pdf"}
            ),
            Document(
                page_content="LangGraph orchestrates the chat, RAG, and monitoring workflows. It provides state management and routing.",
                metadata={"page": 3, "source": "test.pdf"}
            ),
            Document(
                page_content="Push-to-talk voice input uses Groq Whisper for speech-to-text conversion with low latency.",
                metadata={"page": 4, "source": "test.pdf"}
            ),
        ]
        
        # Index documents
        print(f"Indexing {len(test_docs)} test documents...")
        result = await client.index_documents(test_collection, test_docs)
        
        if not result.get("success"):
            print(f"❌ Indexing failed: {result.get('error')}")
            return False
        
        print(f"✅ Indexed {result['chunks_indexed']} documents")
        
        # Test searches with different queries
        test_queries = [
            ("What is Sentinel?", "Sentinel"),
            ("How does monitoring work?", "monitoring"),
            ("What is LangGraph used for?", "LangGraph"),
            ("How does voice input work?", "Whisper"),
        ]
        
        print("\nTesting search queries...")
        all_passed = True
        
        for query, expected_term in test_queries:
            print(f"\n🔍 Query: '{query}'")
            results = await client.search(
                collection_name=test_collection,
                query=query,
                limit=2,
                score_threshold=0.2  # Low threshold for testing
            )
            
            if results:
                print(f"   ✅ Found {len(results)} results:")
                for i, doc in enumerate(results, 1):
                    score = doc.metadata.get('score', 0.0)
                    content_preview = doc.page_content[:80] + "..." if len(doc.page_content) > 80 else doc.page_content
                    print(f"      {i}. [score={score:.3f}] {content_preview}")
                    print(f"         Page: {doc.metadata.get('page')}")
                
                # Verify expected term is in at least one result
                found_term = any(expected_term.lower() in doc.page_content.lower() for doc in results)
                if found_term:
                    print(f"   ✅ Found expected term '{expected_term}' in results")
                else:
                    print(f"   ⚠️ Expected term '{expected_term}' not found in top results")
                    all_passed = False
            else:
                print("   ❌ No results found")
                all_passed = False
        
        # Cleanup
        print(f"\nCleaning up test collection...")
        await client.delete_collection(test_collection)
        print("✅ Collection deleted")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Document indexing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_4_retrieval_quality():
    """Test 4: Detailed retrieval quality test"""
    print("\n" + "=" * 70)
    print("TEST 4: Retrieval Quality (Critical Test)")
    print("=" * 70)
    
    try:
        client = get_qdrant_client()
        test_collection = "test_quality_" + str(asyncio.get_event_loop().time()).replace(".", "_")
        
        # Create a mini academic paper with authors
        test_docs = [
            Document(
                page_content=(
                    "Attention Is All You Need\n\n"
                    "Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, "
                    "Llion Jones, Aidan N. Gomez, Łukasz Kaiser, Illia Polosukhin\n\n"
                    "Google Brain, Google Research, University of Toronto\n\n"
                    "Emails: {avaswani, noam, niki}@google.com"
                ),
                metadata={"page": 1, "source": "attention_paper.pdf", "section": "authors"}
            ),
            Document(
                page_content=(
                    "Abstract: The dominant sequence transduction models are based on complex "
                    "recurrent or convolutional neural networks. We propose a new simple network "
                    "architecture based entirely on attention mechanisms, dispensing with recurrence "
                    "and convolutions entirely."
                ),
                metadata={"page": 1, "source": "attention_paper.pdf", "section": "abstract"}
            ),
            Document(
                page_content=(
                    "The Transformer model architecture uses self-attention to compute "
                    "representations of input and output without using sequence-aligned "
                    "RNNs or convolution. This allows for more parallelization."
                ),
                metadata={"page": 3, "source": "attention_paper.pdf", "section": "architecture"}
            ),
        ]
        
        print(f"Indexing {len(test_docs)} test documents...")
        result = await client.index_documents(test_collection, test_docs)
        
        if not result.get("success"):
            print(f"❌ Indexing failed: {result.get('error')}")
            return False
        
        print(f"✅ Indexed {result['chunks_indexed']} documents")
        
        # Critical test: Can we find the authors?
        print("\n🔍 CRITICAL TEST: Finding author names")
        print("   Query: 'Who are the authors and what are their emails?'")
        
        results = await client.search(
            collection_name=test_collection,
            query="Who are the authors and what are their emails?",
            limit=3,
            score_threshold=0.2
        )
        
        if not results:
            print("   ❌ FAILED: No results found for author query")
            await client.delete_collection(test_collection)
            return False
        
        print(f"   ✅ Found {len(results)} results")
        
        # Check if we found the authors
        found_authors = False
        found_emails = False
        
        for i, doc in enumerate(results, 1):
            score = doc.metadata.get('score', 0.0)
            print(f"\n   Result {i} [score={score:.3f}]:")
            print(f"   {doc.page_content[:150]}...")
            
            if "Vaswani" in doc.page_content or "Shazeer" in doc.page_content:
                found_authors = True
                print("   ✅ Contains author names!")
            
            if "@google.com" in doc.page_content or "Emails:" in doc.page_content:
                found_emails = True
                print("   ✅ Contains email information!")
        
        # Cleanup
        await client.delete_collection(test_collection)
        
        if found_authors and found_emails:
            print("\n✅ CRITICAL TEST PASSED: Successfully found authors and emails")
            return True
        elif found_authors:
            print("\n⚠️ Partial success: Found authors but not emails")
            return True
        else:
            print("\n❌ CRITICAL TEST FAILED: Could not find author information")
            return False
        
    except Exception as e:
        print(f"❌ Retrieval quality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n" + "🧪" * 35)
    print("QDRANT RAG COMPREHENSIVE TEST SUITE")
    print("🧪" * 35 + "\n")
    
    results = []
    
    # Test 1: Connection
    results.append(("Connection", await test_1_connection()))
    
    if not results[0][1]:
        print("\n❌ Connection failed - stopping tests")
        print("   Check QDRANT_URL and QDRANT_API_KEY in .env")
        return False
    
    # Test 2: Collection operations
    results.append(("Collection Ops", await test_2_collection_operations()))
    
    # Test 3: Indexing & Search
    results.append(("Indexing & Search", await test_3_document_indexing()))
    
    # Test 4: Retrieval Quality (CRITICAL)
    results.append(("Retrieval Quality", await test_4_retrieval_quality()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"\nTests Passed: {passed_count}/{total_count}")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed! Qdrant RAG is ready for production!")
        print("\nNext steps:")
        print("1. Update your graph.py with Qdrant code")
        print("2. Update your main.py with async endpoints")
        print("3. Test with a real PDF upload")
        return True
    else:
        print(f"\n⚠️ {total_count - passed_count} test(s) failed")
        print("   Review errors above and fix issues before proceeding")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)