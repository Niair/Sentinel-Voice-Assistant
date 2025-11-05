"""
Interactive Chat with Sentinel AI Voice Assistant
Run this to have a conversation with your AI!
"""

import requests
import sys
import json

BASE_URL = "http://localhost:5000"

def check_server():
    """Check if server is running"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/system/health", timeout=2)
        return response.status_code == 200
    except:
        return False

def check_config():
    """Check if AI is configured"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/system/integrations", timeout=5)
        data = response.json()
        
        # Check if at least one LLM is configured
        gemini_ok = data['integrations'].get('gemini', {}).get('status') == 'healthy'
        groq_ok = data['integrations'].get('groq', {}).get('status') == 'healthy'
        
        return gemini_ok or groq_ok, data
    except:
        return False, {}

def chat(message):
    """Send a message to the AI"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/chat",
            json={"text": message, "return_audio": False},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('text', 'No response'), data.get('llm_used', 'unknown')
        else:
            return f"Error: {response.status_code}", "error"
    except requests.exceptions.Timeout:
        return "Request timed out. The AI might be processing...", "timeout"
    except Exception as e:
        return f"Error: {str(e)}", "error"

def main():
    print("="*60)
    print("  SENTINEL AI VOICE ASSISTANT - Interactive Chat")
    print("="*60)
    
    # Check if server is running
    print("\n🔍 Checking server status...")
    if not check_server():
        print("❌ Server is not running!")
        print("\nPlease start the server in another terminal:")
        print("   cd E:\\_Projects\\Sentinel\\backend")
        print("   python -m app.main")
        sys.exit(1)
    
    print("✅ Server is running!")
    
    # Check configuration
    print("\n🔍 Checking AI configuration...")
    configured, config_data = check_config()
    
    if not configured:
        print("⚠️  AI is not configured yet!")
        print("\nTo configure:")
        print("1. Get an API key:")
        print("   - Gemini: https://makersuite.google.com/app/apikey")
        print("   - Groq: https://console.groq.com/keys")
        print("\n2. Add it to E:\\_Projects\\Sentinel\\.env:")
        print("   GEMINI_API_KEY=your_key_here")
        print("\n3. Restart the server")
        
        proceed = input("\n⚠️  Continue anyway to test (will fail)? (y/n): ")
        if proceed.lower() != 'y':
            sys.exit(0)
    else:
        print("✅ AI is configured!")
        
        # Show which LLM is available
        if config_data.get('integrations', {}).get('gemini', {}).get('status') == 'healthy':
            print("   Primary: Google Gemini")
        if config_data.get('integrations', {}).get('groq', {}).get('status') == 'healthy':
            print("   Fallback: Groq")
    
    print("\n" + "="*60)
    print("  Ready to chat! Type 'quit' or 'exit' to stop")
    print("  Try: 'Tell me a joke' or 'Mujhe ek joke sunao' (Hinglish)")
    print("="*60 + "\n")
    
    # Chat loop
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
                print("\nAI: Goodbye! Have a great day!")
                break
            
            # Send to AI
            print("AI: ", end="", flush=True)
            response, llm = chat(user_input)
            print(f"{response}")
            
            if llm not in ['error', 'timeout']:
                print(f"    (powered by {llm})\n")
            else:
                print()
        
        except KeyboardInterrupt:
            print("\n\nAI: Goodbye! Have a great day!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            break
    
    print("\n" + "="*60)
    print("  Chat session ended")
    print("="*60)

if __name__ == "__main__":
    main()
