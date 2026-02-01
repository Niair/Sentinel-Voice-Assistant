"""
DeepSeek API Test Script
Tests if DeepSeek API key is working with LangChain

Run: python tests/test_deepseek.py
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

print("=" * 70)
print("DEEPSEEK API TEST")
print("=" * 70)

# Test 1: Check API key is set
print("\n1. Checking environment variable...")
api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    print("❌ DEEPSEEK_API_KEY not found in .env file")
    print("\nAdd to backend/.env:")
    print("DEEPSEEK_API_KEY=your_key_here")
    sys.exit(1)

print(f"✅ DEEPSEEK_API_KEY is set ({api_key[:10]}...)")

# Test 2: Test with LangChain OpenAI-compatible interface
print("\n2. Testing DeepSeek with LangChain (OpenAI-compatible)...")

try:
    from langchain_openai import ChatOpenAI
    
    # DeepSeek uses OpenAI-compatible API
    # Base URL: https://api.deepseek.com
    llm = ChatOpenAI(
        model="deepseek-chat",  # DeepSeek's main model
        openai_api_key=api_key,
        openai_api_base="https://api.deepseek.com",
        temperature=0.7,
        max_tokens=100
    )
    
    print("✅ DeepSeek client created")
    
    # Test 3: Simple completion
    print("\n3. Testing simple completion...")
    response = llm.invoke("Say 'Hello, I am DeepSeek!' and nothing else.")
    
    print(f"✅ Response received: {response.content}")
    
    # Test 4: Test streaming
    print("\n4. Testing streaming...")
    print("Response: ", end="", flush=True)
    
    for chunk in llm.stream("Count from 1 to 5, one number per line."):
        print(chunk.content, end="", flush=True)
    
    print("\n✅ Streaming works!")
    
    # Test 5: Check token usage (if available)
    print("\n5. Testing with response metadata...")
    response = llm.invoke("What is 2+2?")
    print(f"✅ Answer: {response.content}")
    
    if hasattr(response, 'response_metadata'):
        print(f"   Metadata: {response.response_metadata}")
    
    print("\n" + "=" * 70)
    print("🎉 ALL TESTS PASSED!")
    print("=" * 70)
    print("\nDeepSeek is working correctly with LangChain!")
    print("\nYou can now use it in your graph.py:")
    print("""
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="deepseek-chat",
    openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
    openai_api_base="https://api.deepseek.com",
    temperature=0.7
)
""")
    
except ImportError as e:
    print(f"❌ Missing package: {e}")
    print("\nInstall with: uv pip install langchain-openai")
    sys.exit(1)
    
except Exception as e:
    print(f"\n❌ DeepSeek API test failed: {e}")
    print("\nPossible issues:")
    print("1. Invalid API key - check your DeepSeek dashboard")
    print("2. API key not activated - may need to verify email")
    print("3. Rate limit exceeded - wait a moment and retry")
    print("4. Network issue - check internet connection")
    
    import traceback
    print("\nFull error:")
    traceback.print_exc()
    sys.exit(1)