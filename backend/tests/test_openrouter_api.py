"""
Test script for OpenRouter API via LangChain.
Tests if the API key works and lists available models.
"""

import os
import asyncio
from dotenv import load_dotenv

load_dotenv()


async def test_openrouter_api():
    """Test OpenRouter API connection."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    base_url = "https://openrouter.ai/api/v1"

    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not found in .env")
        return False

    print(f"API Key: {api_key[:20]}...")
    print(f"Base URL: {base_url}")
    print()

    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage

        print("Testing with langchain_openai (OpenAI-compatible)...")

        free_models = [
            "arcee-ai/trinity-large-preview:free",
            "nvidia/nemotron-3-nano-30b-a3b:free",
            "google/gemma-3-12b-it:free",
            "deepseek/deepseek-r1-0528:free",
            "upstage/solar-pro-3:free",
            "z-ai/glm-4.5-air:free",
        ]

        message = HumanMessage(content="Say 'Hello from OpenRouter!' in one line.")

        for model in free_models:
            try:
                print(f"\nTrying model: {model}")

                llm = ChatOpenAI(
                    model=model,
                    openai_api_key=api_key,
                    openai_api_base=base_url,
                    temperature=0.1,
                    default_headers={
                        "HTTP-Referer": "https://sentinel-ai.local",
                        "X-Title": "Sentinel AI Assistant",
                    },
                )

                response = await llm.ainvoke([message])
                print(f"SUCCESS with {model}!")
                print(f"Response: {response.content[:150]}...")
                return True

            except Exception as e:
                print(f"Failed with {model}: {str(e)[:100]}")

        print("\nAll free models failed. Trying paid models...")

        paid_models = [
            "anthropic/claude-3-haiku",
            "openai/gpt-3.5-turbo",
            "google/gemini-pro",
        ]

        for model in paid_models:
            try:
                print(f"\nTrying model: {model}")
                llm = ChatOpenAI(
                    model=model,
                    openai_api_key=api_key,
                    openai_api_base=base_url,
                    temperature=0.1,
                )
                response = await llm.ainvoke([message])
                print(f"SUCCESS with {model}!")
                print(f"Response: {response.content[:150]}...")
                return True
            except Exception as e:
                print(f"Failed: {str(e)[:100]}")

        return False

    except Exception as e:
        print(f"ERROR: {e}")
        return False


async def list_openrouter_models():
    """List available free models on OpenRouter."""
    import httpx

    api_key = os.getenv("OPENROUTER_API_KEY")

    print("\nFetching available models from OpenRouter...")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30.0,
            )

            if response.status_code == 200:
                data = response.json()
                models = data.get("data", [])

                free_models = [m for m in models if ":free" in m.get("id", "")]

                print(f"\nFound {len(free_models)} FREE models:")
                print("-" * 60)

                for model in free_models[:20]:
                    model_id = model.get("id", "unknown")
                    name = model.get("name", model_id)
                    print(f"  {model_id}")

                if len(free_models) > 20:
                    print(f"  ... and {len(free_models) - 20} more")

            else:
                print(f"Error: {response.status_code}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    print("=" * 50)
    print("OPENROUTER API TEST")
    print("=" * 50)
    print()

    success = asyncio.run(test_openrouter_api())

    if success:
        asyncio.run(list_openrouter_models())

    print("\n" + "=" * 50)
    print("Test complete!")
    print("=" * 50)
