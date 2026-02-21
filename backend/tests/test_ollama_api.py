"""
Test script for Ollama API via LangChain.
Tests if the API key works and lists available models.
"""

import os
import asyncio
from dotenv import load_dotenv

load_dotenv()


async def test_ollama_api():
    """Test Ollama API connection."""
    api_key = os.getenv("OLLAMA_API_KEY")
    base_url = "https://api.ollama.ai/v1"

    if not api_key:
        print("ERROR: OLLAMA_API_KEY not found in .env")
        return False

    print(f"API Key: {api_key[:20]}...")
    print(f"Base URL: {base_url}")
    print()

    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage

        print("Testing with langchain_openai (OpenAI-compatible)...")

        llm = ChatOpenAI(
            model="qwen3.5:cloud",
            openai_api_key=api_key,
            openai_api_base=base_url,
            temperature=0.1,
        )

        message = HumanMessage(content="Say 'Hello, I am working!' in one line.")
        response = await llm.ainvoke([message])

        print(f"Response: {response.content}")
        print()
        print("SUCCESS: Ollama API is working!")
        return True

    except Exception as e:
        print(f"ERROR: {e}")

        print("\nTrying alternative models...")
        models = ["minimax-m2.5", "qwen3.5:cloud", "glm-5", "mistral"]

        for model in models:
            try:
                print(f"\nTrying model: {model}")
                llm = ChatOpenAI(
                    model=model,
                    openai_api_key=api_key,
                    openai_api_base=base_url,
                    temperature=0.1,
                )
                response = await llm.ainvoke([message])
                print(f"SUCCESS with {model}: {response.content[:100]}...")
                return True
            except Exception as e2:
                print(f"Failed with {model}: {str(e2)[:100]}")

        return False


async def list_ollama_models():
    """Try to list available models."""
    import httpx

    api_key = os.getenv("OLLAMA_API_KEY")
    base_url = "https://api.ollama.ai/v1"

    print("\nListing available models...")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30.0,
            )
            if response.status_code == 200:
                data = response.json()
                print("Available models:")
                for model in data.get("data", []):
                    print(f"  - {model.get('id', 'unknown')}")
            else:
                print(f"Could not list models: {response.status_code}")
    except Exception as e:
        print(f"Error listing models: {e}")


if __name__ == "__main__":
    print("=" * 50)
    print("OLLAMA API TEST")
    print("=" * 50)
    print()

    success = asyncio.run(test_ollama_api())

    if success:
        asyncio.run(list_ollama_models())

    print("\n" + "=" * 50)
    print("Test complete!")
    print("=" * 50)
