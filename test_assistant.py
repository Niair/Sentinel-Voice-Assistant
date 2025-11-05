"""
Test script for Sentinel AI Voice Assistant
Run this after starting the server to verify everything works.
"""

import requests
import json
import sys

BASE_URL = "http://localhost:5000"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_health():
    """Test basic health endpoint"""
    print_section("Testing Health Endpoint")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/system/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed!")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            return True
        else:
            print(f"❌ Health check failed with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Is it running?")
        print("   Run: cd backend && python -m app.main")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_integrations():
    """Test integration status"""
    print_section("Testing Integration Status")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/system/integrations", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"Overall Status: {data['overall_status'].upper()}")
            print(f"\nIntegrations:")
            for service, status in data['integrations'].items():
                emoji = "✅" if status['status'] == 'healthy' else "⚠️" if status['status'] == 'not_configured' else "❌"
                print(f"  {emoji} {service.upper()}: {status['status']}")
                if 'error' in status:
                    print(f"     Error: {status['error']}")
            return True
        else:
            print(f"❌ Integration check failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_config():
    """Test configuration endpoint"""
    print_section("Testing Configuration")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/system/config", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("Configuration:")
            print(f"  Primary LLM: {data['llm']['primary'] or 'Not configured'}")
            print(f"  Fallback LLM: {data['llm']['fallback'] or 'Not configured'}")
            print(f"  STT Provider: {data['voice']['stt']}")
            print(f"  TTS Provider: {data['voice']['tts'] or 'Not configured'}")
            print(f"  Memory: {data['memory']['provider']}")
            return True
        else:
            print(f"❌ Config check failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_chat(text="Hello! Can you introduce yourself?"):
    """Test text chat endpoint"""
    print_section("Testing Text Chat")
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/chat",
            json={"text": text, "return_audio": False},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success', False):
                print("✅ Chat test passed!")
                print(f"\nYour message: {text}")
                print(f"Assistant response: {data['text']}")
                print(f"LLM used: {data['llm_used']}")
                return True
            else:
                print("❌ Chat failed")
                print(f"Error: {data.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ Chat test failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_memory():
    """Test memory endpoints"""
    print_section("Testing Memory")
    try:
        # Get history
        response = requests.get(f"{BASE_URL}/api/v1/memory/history?limit=5", timeout=5)
        if response.status_code == 200:
            history = response.json()['history']
            print(f"✅ Memory retrieval works! Found {len(history)} messages")
            if history:
                print("\nRecent conversation:")
                for msg in history[-3:]:
                    print(f"  {msg['role']}: {msg['content'][:50]}...")
            return True
        else:
            print(f"❌ Memory test failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    print("\n" + "="*60)
    print("  SENTINEL AI VOICE ASSISTANT - TEST SUITE")
    print("="*60)
    
    # Run tests
    results = {}
    results['health'] = test_health()
    
    if not results['health']:
        print("\n❌ Server is not running. Start it with:")
        print("   cd E:\\_Projects\\Sentinel\\backend")
        print("   python -m app.main")
        sys.exit(1)
    
    results['integrations'] = test_integrations()
    results['config'] = test_config()
    results['chat'] = test_chat()
    results['memory'] = test_memory()
    
    # Summary
    print_section("TEST SUMMARY")
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test_name, passed_test in results.items():
        emoji = "✅" if passed_test else "❌"
        print(f"{emoji} {test_name.replace('_', ' ').title()}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your voice assistant is ready to use!")
        print("\n📚 Next steps:")
        print("   1. Add your API keys to .env file")
        print("   2. Restart the server")
        print("   3. Try voice commands (see SETUP_GUIDE.md)")
    elif results['integrations'] and not results['chat']:
        print("\n⚠️  Server is running but LLM is not configured.")
        print("   Add at least one API key to .env:")
        print("   - GEMINI_API_KEY (from https://makersuite.google.com/app/apikey)")
        print("   - GROQ_API_KEY (from https://console.groq.com/keys)")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
