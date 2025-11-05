# Sentinel AI Voice Assistant - Setup Guide

## Quick Start

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ (for frontend)
- FFmpeg (for audio processing)
- Conda (activated environment)

### 2. Install FFmpeg (Required for audio processing)

**Windows:**
```powershell
# Using Chocolatey
choco install ffmpeg

# Or download from: https://ffmpeg.org/download.html
```

**Linux/Mac:**
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg
```

### 3. Backend Setup

```powershell
# Navigate to backend directory
cd E:\_Projects\Sentinel\backend

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure API Keys

Copy `.env.example` to `.env` and fill in your API keys:

```env
FLASK_ENV=development
SECRET_KEY=your_secret_key_here
PORT=5000

# Required: At least one LLM API key
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key

# Optional but recommended for TTS
ELEVENLABS_API_KEY=your_elevenlabs_api_key

# Optional
LANGSMITH_API_KEY=your_langsmith_api_key

# Vector DB (uses local ChromaDB by default)
VECTORDB_PROVIDER=chromadb
```

### 5. Run the Backend

```powershell
cd backend
python -m app.main
```

The backend will start on `http://localhost:5000`

### 6. Test the API

**Health Check:**
```powershell
curl http://localhost:5000/api/v1/system/health
```

**Integration Check:**
```powershell
curl http://localhost:5000/api/v1/system/integrations
```

## API Endpoints

### Chat Endpoints

#### 1. Text/Voice Chat (Unified)
```http
POST /api/v1/chat
Content-Type: application/json

{
  "text": "Hello, what can you do?",
  "return_audio": false
}
```

**With Voice Input:**
```json
{
  "audio": "<base64_encoded_audio>",
  "audio_format": "wav",
  "return_audio": true,
  "voice_id": "21m00Tcm4TlvDq8ikWAM"
}
```

**Response:**
```json
{
  "text": "Hi! I'm Sentinel, your AI voice assistant...",
  "llm_used": "Gemini",
  "success": true,
  "audio": "<base64_audio>",
  "audio_format": "mp3"
}
```

#### 2. Voice-Only Chat (File Upload)
```http
POST /api/v1/chat/voice
Content-Type: multipart/form-data

audio: <audio_file>
voice_id: 21m00Tcm4TlvDq8ikWAM (optional)
```

Returns audio file directly.

### Memory Endpoints

#### Clear Memory
```http
POST /api/v1/memory/clear
```

#### Get Conversation History
```http
GET /api/v1/memory/history?limit=10
```

### System Endpoints

#### Health Check
```http
GET /api/v1/system/health
```

#### Integration Status
```http
GET /api/v1/system/integrations
```

#### System Configuration
```http
GET /api/v1/system/config
```

## Features

### ✅ Implemented
- **Multi-LLM Support**: Gemini (primary) + Groq (fallback)
- **Voice Input**: Whisper-based STT with Hinglish support
- **Voice Output**: ElevenLabs TTS with multiple voices
- **Conversation Memory**: ChromaDB vector storage with semantic search
- **Context Awareness**: Remembers and retrieves relevant past conversations
- **Audio Processing**: File format conversion, encoding/decoding
- **Health Monitoring**: Comprehensive health checks for all services
- **Flexible API**: Support for text, voice, and hybrid inputs

### 🚧 To Be Implemented
- Task automation tools (email, weather, flight booking)
- Frontend React UI with voice recording
- LangGraph for complex multi-step tasks
- MCP server integration
- Advanced Hinglish preprocessing
- Notification system

## Usage Examples

### Python Example

```python
import requests
import base64

# Text chat
response = requests.post(
    "http://localhost:5000/api/v1/chat",
    json={"text": "Tell me a joke", "return_audio": False}
)
print(response.json()["text"])

# Voice chat with audio input
with open("audio.wav", "rb") as f:
    audio_base64 = base64.b64encode(f.read()).decode()

response = requests.post(
    "http://localhost:5000/api/v1/chat",
    json={
        "audio": audio_base64,
        "audio_format": "wav",
        "return_audio": True
    }
)

# Save response audio
if "audio" in response.json():
    audio_bytes = base64.b64decode(response.json()["audio"])
    with open("response.mp3", "wb") as f:
        f.write(audio_bytes)
```

### JavaScript Example

```javascript
// Text chat
const response = await fetch('http://localhost:5000/api/v1/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    text: 'What is the weather like?',
    return_audio: false
  })
});

const data = await response.json();
console.log(data.text);

// Voice chat with recording
const audioBlob = await recordAudio(); // Your recording function
const reader = new FileReader();
reader.readAsDataURL(audioBlob);
reader.onloadend = async () => {
  const base64Audio = reader.result.split(',')[1];
  
  const response = await fetch('http://localhost:5000/api/v1/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      audio: base64Audio,
      audio_format: 'wav',
      return_audio: true
    })
  });
  
  const data = await response.json();
  // Play response audio
  const audioElement = new Audio(`data:audio/mp3;base64,${data.audio}`);
  audioElement.play();
};
```

## Hinglish Support

The assistant natively understands Hinglish (Hindi + English mix) thanks to:
- **Whisper**: Multilingual STT model with excellent Hindi support
- **Gemini/Groq**: LLMs trained on multilingual data
- **ElevenLabs**: Multilingual TTS supporting Hindi pronunciation

Example queries that work:
- "Mujhe ek joke sunao"
- "What is aaj ka weather?"
- "Email bhejo mere boss ko"
- "Flight book karo Mumbai to Delhi"

## Troubleshooting

### Whisper Model Download
First time using STT will download the Whisper model (~140MB for base model).

### Memory Issues
If you encounter memory issues with Whisper, use a smaller model:
```python
stt_client = STTClient(model_size="tiny")  # Faster, less accurate
```

### API Key Errors
Check your `.env` file and ensure at least one LLM API key is set.

### Audio Format Issues
Ensure FFmpeg is installed and in your system PATH.

## Next Steps

1. **Configure your `.env` file** with API keys
2. **Run the backend** and test with curl/Postman
3. **Try voice commands** using the `/api/v1/chat/voice` endpoint
4. **Build a frontend** or integrate with existing applications
5. **Add custom tools** for task automation

## Support

For issues or questions:
1. Check the logs in the console
2. Test integrations at `/api/v1/system/integrations`
3. Review the README.md for project architecture
