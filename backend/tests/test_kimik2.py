import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path to allow imports if needed
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

def test_nvidia_kimik2():
    print("=" * 70)
    print("NVIDIA KIMI K2 API TEST")
    print("=" * 70)

    # 1. Get API Key
    api_key = os.getenv("NVEDIAKIMIK2_API_KEY")
    if not api_key:
        print("❌ Error: NVEDIAKIMIK2_API_KEY not found in .env file.")
        return

    print(f"✅ Found API Key: {api_key[:10]}...{api_key[-5:]}")

    # 2. Try to import langchain_nvidia_ai_endpoints
    try:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
    except Exception as e:
        print(f"❌ Error: Could not import 'langchain_nvidia_ai_endpoints'.")
        print(f"   Reason: {str(e)}")
        print("\nFix: Use 'uv run' to ensure you are using the correct environment:")
        print("   uv run python tests/test_kimik2.py")
        return

    # 3. Initialize Model
    # Based on the model list, the correct ID is 'moonshotai/kimi-k2-instruct' or 'moonshotai/kimi-k2-thinking'
    model_name = "meta/llama-3.3-70b-instruct"
    
    print(f"🔄 Connecting to NVIDIA NIM with model: {model_name}...")
    
    try:
        # Initialize the LLM
        llm = ChatNVIDIA(
            model=model_name,
            nvidia_api_key=api_key,
            temperature=0.7,
            max_completion_tokens=1024
        )

        # 4. Test Invocation
        test_prompt = "Hello! Can you introduce yourself and confirm you are the Kimi K2 model?"
        print(f"📝 Sending test prompt: '{test_prompt}'")
        
        response = llm.invoke(test_prompt)
        
        print("\n" + "=" * 50)
        print("AI RESPONSE:")
        print("=" * 50)
        print(response.content)
        print("=" * 50)
        
        print("\n✅ Test completed successfully!")

    except Exception as e:
        print(f"\n❌ API Call Failed: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Check if the model name is correct for your NVIDIA NIM subscription.")
        print("2. Verify your API key has access to this specific model.")
        print("3. Check your internet connection.")
        
        # Try to list available models if the invocation fails
        try:
            print("\n🔄 Attempting to list available models from your NVIDIA account...")
            available_models = [m.id for m in ChatNVIDIA.get_available_models(nvidia_api_key=api_key)]
            print(f"📋 Available Models: {available_models}")
        except:
            pass

if __name__ == "__main__":
    test_nvidia_kimik2()
