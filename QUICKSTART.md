# Sentinel AI Voice Assistant - Quick Start

## 🚀 Get Your Voice Assistant Running in 5 Minutes

### Step 1: Install FFmpeg (Required)
```powershell
# Windows (using Chocolatey)
choco install ffmpeg

# Or download from: https://ffmpeg.org/download.html
# Add to PATH after installation
```

### Step 2: Install Python Dependencies
```powershell
cd E:\_Projects\Sentinel\backend
pip install -r requirements.txt
```

**Note**: First-time installation will take a few minutes as it downloads all AI packages.

### Step 3: Configure Your API Keys

Edit the `.env` file in the project root:

```env
# Minimum required - Add at least ONE of these:
GEMINI_API_KEY=your_gemini_key_here
GROQ_API_KEY=your_groq_key_here

# Optional but recommended for voice output:
ELEVENLABS_API_KEY=your_elevenlabs_key_here
```

**Where to get API keys:**
- **Gemini**: https://makersuite.google.com/app/apikey
- **Groq**: https://console.groq.com/keys
- **ElevenLabs**: https://elevenlabs.io/app/settings/api-keys

### Step 4: Run the Server
```powershell
cd E:\_Projects\Sentinel\backend
python -m app.main
```

You should see:
```
 * Running on http://127.0.0.1:5000
```

### Step 5: Test Your Assistant

Open a new terminal and try:

```powershell
# Test health
curl http://localhost:5000/api/v1/system/health

# Test text chat
curl -X POST http://localhost:5000/api/v1/chat -H "Content-Type: application/json" -d "{\"text\": \"Hello! What can you do?\"}"
```

## 🎤 Quick Test with Python

Create a test file `test_assistant.py`:

```python
import requests

def test_chat():
    response = requests.post(
        "http://localhost:5000/api/v1/chat",
        json={"text": "Tell me about yourself"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Success!")
        print(f"Response: {data['text']}")
        print(f"LLM Used: {data['llm_used']}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.json())

if __name__ == "__main__":
    test_chat()
```

Run it:
```powershell
python test_assistant.py
```

## 🎯 What's Working

✅ **Text Chat** - Full conversational AI
✅ **Voice Input** - Speak in English, Hindi, or Hinglish
✅ **Voice Output** - Natural text-to-speech
✅ **Memory** - Remembers conversation context
✅ **Multi-LLM** - Automatic fallback if one fails

## 🔧 Troubleshooting

### "Module not found" errors
```powershell
pip install -r requirements.txt --upgrade
```

### "API key not configured"
Check your `.env` file has at least one LLM API key.

### "FFmpeg not found"
Ensure FFmpeg is installed and in your PATH. Restart terminal after installation.

### First STT use is slow
The Whisper model downloads on first use (~140MB). Subsequent uses are fast.

## 📚 Next Steps

1. **Read** `SETUP_GUIDE.md` for detailed API documentation
2. **Check** `IMPLEMENTATION_SUMMARY.md` for architecture overview
3. **Test** voice input using the examples in `SETUP_GUIDE.md`
4. **Build** a frontend or integrate with your app!

## 💡 Example Use Cases

```python
# Simple conversation
response = requests.post(
    "http://localhost:5000/api/v1/chat",
    json={"text": "What's the weather like?"}
)

# Hinglish query
response = requests.post(
    "http://localhost:5000/api/v1/chat",
    json={"text": "Mujhe ek joke sunao"}
)

# Get conversation history
history = requests.get("http://localhost:5000/api/v1/memory/history?limit=10")
```

## 🎉 You're Ready!

Your AI voice assistant is now running and ready to:
- Chat in text or voice
- Understand Hinglish
- Remember conversations
- Generate voice responses

Start building! 🚀
