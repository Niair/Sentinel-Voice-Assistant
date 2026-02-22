"""
Comprehensive API Test Script for Sentinel AI
Tests Ollama, OpenRouter, and NVIDIA APIs with LangChain/LangGraph
"""

import os
import asyncio
from dotenv import load_dotenv

load_dotenv()


async def test_nvidia_api():
    """Test NVIDIA NIM API (current vision model)."""
    print("\n" + "=" * 60)
    print("TESTING NVIDIA NIM API")
    print("=" * 60)

    api_key = os.getenv("NVEDIAKIMIK2_API_KEY")
    if not api_key:
        print("ERROR: NVEDIAKIMIK2_API_KEY not found in .env")
        return {"success": False, "models": [], "vision": None}

    print(f"API Key: {api_key[:20]}...")

    try:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        from langchain_core.messages import HumanMessage

        vision_models = [
            "meta/llama-3.2-11b-vision-instruct",
            "nvidia/nemotron-nano-12b-v2-vl",
        ]

        text_models = [
            "meta/llama-3.1-8b-instruct",
            "nvidia/llama-3.1-nemotron-70b-instruct",
        ]

        working_models = []

        for model in vision_models + text_models:
            try:
                print(f"\nTrying model: {model}")
                llm = ChatNVIDIA(
                    model=model,
                    nvidia_api_key=api_key,
                    temperature=0.1,
                    max_completion_tokens=100,
                )

                response = await llm.ainvoke(
                    [HumanMessage(content="Say 'Hello from NVIDIA!' in one line.")]
                )

                print(f"SUCCESS with {model}!")
                print(f"Response: {response.content[:100]}...")
                working_models.append(model)

            except Exception as e:
                print(f"Failed with {model}: {str(e)[:100]}")

        vision_model = (
            vision_models[0]
            if any(m in working_models for m in vision_models)
            else None
        )
        return {
            "success": len(working_models) > 0,
            "models": working_models,
            "vision": vision_model,
        }

    except Exception as e:
        print(f"ERROR: {e}")
        return {"success": False, "models": [], "vision": None}


def test_ollama_api_sync():
    """Test Ollama Cloud API using OllamaLLM (the working way)."""
    print("\n" + "=" * 60)
    print("TESTING OLLAMA CLOUD API")
    print("=" * 60)

    api_key = os.getenv("OLLAMA_API_KEY")
    if not api_key:
        print("ERROR: OLLAMA_API_KEY not found in .env")
        return {"success": False, "model": None, "all_models": []}

    print(f"API Key: {api_key[:20]}...")

    from langchain_ollama import OllamaLLM

    cloud_models = [
        "qwen3-coder:480b-cloud",
        "minimax-m2.5:cloud",
        "kimi-k2.5:cloud",
        "glm-5:cloud",
        "qwen3.5:cloud",
    ]

    for model in cloud_models:
        try:
            print(f"\nTrying model: {model}")
            llm = OllamaLLM(model=model)

            response = llm.invoke("Say 'Hello from Ollama!' in one line.")

            print(f"SUCCESS with {model}!")
            print(f"Response: {response[:150]}...")
            return {"success": True, "model": model, "all_models": cloud_models}

        except Exception as e:
            print(f"Failed with {model}: {str(e)[:100]}")

    return {"success": False, "model": None, "all_models": cloud_models}


def test_ollama_langgraph():
    """Test Ollama with LangGraph."""
    print("\n" + "=" * 60)
    print("TESTING OLLAMA WITH LANGGRAPH")
    print("=" * 60)

    from typing import TypedDict
    from langchain_ollama import OllamaLLM
    from langgraph.graph import StateGraph

    class State(TypedDict):
        input: str
        output: str

    llm = OllamaLLM(model="qwen3-coder:480b-cloud")

    def chatbot(state: State):
        response = llm.invoke(state["input"])
        return {"output": response}

    graph = StateGraph(State)
    graph.add_node("chatbot", chatbot)
    graph.set_entry_point("chatbot")
    graph.set_finish_point("chatbot")
    app = graph.compile()

    try:
        result = app.invoke({"input": "Explain what a helper agent does in 2 lines"})
        print(f"SUCCESS with LangGraph!")
        print(f"Response: {result['output'][:200]}...")
        return {"success": True}
    except Exception as e:
        print(f"Failed: {str(e)[:100]}")
        return {"success": False}


async def test_openrouter_api():
    """Test OpenRouter API."""
    print("\n" + "=" * 60)
    print("TESTING OPENROUTER API")
    print("=" * 60)

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not found in .env")
        return {"success": False, "models": []}

    print(f"API Key: {api_key[:20]}...")

    base_url = "https://openrouter.ai/api/v1"

    free_models = [
        "meta-llama/llama-3.3-70b-instruct:free",
        "qwen/qwen3-next-80b-a3b-instruct:free",
        "google/gemma-3-12b-it:free",
        "deepseek/deepseek-r1-0528:free",
        "arcee-ai/trinity-large-preview:free",
        "mistralai/mistral-small-3.1-24b-instruct:free",
        "z-ai/glm-4.5-air:free",
        "nvidia/nemotron-3-nano-30b-a3b:free",
    ]

    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage

    message = HumanMessage(content="Say 'Hello from OpenRouter!' in one line.")
    working_models = []

    for model in free_models:
        try:
            print(f"\nTrying model: {model}")

            llm = ChatOpenAI(
                model=model,
                openai_api_key=api_key,
                openai_api_base=base_url,
                temperature=0.1,
                max_completion_tokens=100,
                default_headers={
                    "HTTP-Referer": "https://sentinel-ai.local",
                    "X-Title": "Sentinel AI Assistant",
                },
            )

            response = await llm.ainvoke([message])

            print(f"SUCCESS with {model}!")
            print(f"Response: {response.content[:100]}...")
            working_models.append(model)

            if len(working_models) >= 3:
                break

        except Exception as e:
            print(f"Failed: {str(e)[:100]}")

    return {"success": len(working_models) > 0, "models": working_models}


async def list_openrouter_models():
    """List available models on OpenRouter."""
    import httpx

    api_key = os.getenv("OPENROUTER_API_KEY")

    print("\n" + "=" * 60)
    print("FETCHING OPENROUTER FREE MODELS")
    print("=" * 60)

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

                print(f"\nFound {len(free_models)} FREE models:\n")

                for model in free_models[:30]:
                    model_id = model.get("id", "unknown")
                    print(f"  - {model_id}")

                if len(free_models) > 30:
                    print(f"  ... and {len(free_models) - 30} more")

            else:
                print(f"Error: {response.status_code}")

    except Exception as e:
        print(f"Error: {e}")


def main():
    print("=" * 60)
    print("SENTINEL AI - COMPREHENSIVE API TEST")
    print("=" * 60)

    results = {}

    results["nvidia"] = asyncio.run(test_nvidia_api())

    results["ollama"] = test_ollama_api_sync()

    if results["ollama"]["success"]:
        results["ollama_langgraph"] = test_ollama_langgraph()

    results["openrouter"] = asyncio.run(test_openrouter_api())

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    print(f"\n{'=' * 20} NVIDIA API {'=' * 20}")
    if results["nvidia"]["success"]:
        print(f"Status: WORKING")
        print(f"Models: {results['nvidia']['models']}")
        print(f"Vision Model: {results['nvidia'].get('vision', 'N/A')}")
    else:
        print("Status: FAILED")

    print(f"\n{'=' * 20} OLLAMA API {'=' * 20}")
    if results["ollama"]["success"]:
        print(f"Status: WORKING")
        print(f"Working Model: {results['ollama']['model']}")
        print(f"Available Cloud Models: {results['ollama']['all_models']}")
        if results.get("ollama_langgraph", {}).get("success"):
            print("LangGraph Integration: WORKING")
    else:
        print("Status: FAILED")

    print(f"\n{'=' * 20} OPENROUTER API {'=' * 20}")
    if results["openrouter"]["success"]:
        print(f"Status: WORKING")
        print(f"Working Models: {results['openrouter']['models']}")
        asyncio.run(list_openrouter_models())
    else:
        print("Status: FAILED")

    print("\n" + "=" * 60)
    print("RECOMMENDATIONS FOR SENTINEL MULTI-AGENT SYSTEM")
    print("=" * 60)

    print("""
+-------------------------------------------------------------+
|                    AGENT MODEL ASSIGNMENT                   |
+-------------------------------------------------------------+
|                                                             |
|  MAIN AGENT (Chat):                                         |
|  +-----------------------------------------------------+   |
|  |  Option 1: Groq Llama-3.3-70B (current)            |   |
|  |  Option 2: Ollama qwen3-coder:480b-cloud           |   |
|  |  Option 3: OpenRouter llama-3.3-70b-instruct:free  |   |
|  +-----------------------------------------------------+   |
|                                                             |
|  SECURITY AGENT (Vision):                                   |
|  +-----------------------------------------------------+   |
|  |  NVIDIA: meta/llama-3.2-11b-vision-instruct         |   |
|  |  (Works great for camera/threat analysis)          |   |
|  +-----------------------------------------------------+   |
|                                                             |
|  HELPER AGENT (Categorization):                             |
|  +-----------------------------------------------------+   |
|  |  Option 1: Ollama minimax-m2.5:cloud                |   |
|  |  Option 2: Ollama glm-5:cloud                       |   |
|  |  Option 3: OpenRouter qwen3-next-80b:free           |   |
|  +-----------------------------------------------------+   |
|                                                             |
|  NOTE: Using NVIDIA for helper agent does NOT affect       |
|        security agent - they use different API calls       |
|                                                             |
+-------------------------------------------------------------+
""")

    print("\n" + "=" * 60)
    print("QWEN2-VL-7B LOCAL MODEL LOCATION")
    print("=" * 60)
    print("""
If you want to delete the local Qwen2-VL-7B model:
  Location: C:\\Users\\Nihal\\.cache\\huggingface\\hub\\
  Look for: models--Qwen--Qwen2-VL-7B-Instruct

NOTE: You don't need local Qwen2-VL if using NVIDIA vision API!
      The NVIDIA vision model is working well and has no quota issues.
""")


if __name__ == "__main__":
    main()
