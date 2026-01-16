# GAIP

      git status
      
      git add .
      
      git commit -m "Day-
      
      git push -u origin main

# once
pip install uv

# per project
uv venv -p 3.11
.venv\Scripts\activate
uv pip install -r requirements.txt

-----------------------------------------------------------------------------------

# Sentinel AI Assistant

A modern, responsive web application that provides an AI-powered chat interface using LangChain and LangGraph for intelligent conversation management.

## Features

- **Modern Web Interface**: Built with HTML5, CSS3, and vanilla JavaScript
- **AI Integration**: Powered by LangChain and LangGraph for intelligent conversations
- **Multiple AI Models**: Support for Gemini and Groq AI models
- **Responsive Design**: Mobile-first approach with clean, modern UI
- **Real-time Chat**: Seamless conversation experience with typing indicators
- **Conversation History**: Persistent chat history with clear functionality
- **Rate Limiting**: Built-in API protection against abuse
- **Comprehensive Testing**: Unit and integration tests included
- **Security**: Input validation, CORS protection, and secure configuration

## Quick Start

### Prerequisites

- Python 3.8+
- Git

### 1. Clone the Repository

```bash
git clone <repository-url>
cd sentinel
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### 3. Frontend Setup

The frontend is ready to use as-is. For development:

```bash
cd frontend
# Open index.html directly in browser
# Or use a development server
python -m http.server 3000  # Python 3
```

### 4. Run the Application

#### Backend
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python app/main.py
```

#### Frontend
Open `frontend/index.html` in your browser or use a local server:
```bash
cd frontend
python -m http.server 3000
```

Visit `http://localhost:3000` to access the application.

## Configuration

### Environment Variables

Create a `.env` file in the backend directory with the following variables:

```env
# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
FLASK_PORT=5000
FLASK_HOST=127.0.0.1
SECRET_KEY=your-secret-key-here

# AI API Keys (Required)
GEMINI_API_KEY=your-gemini-api-key
GROQ_API_KEY=your-groq-api-key

# Optional AI Services
ELEVENLABS_API_KEY=your-elevenlabs-api-key
OPENAI_API_KEY=your-openai-api-key

# Vector Database
VECTORDB_PROVIDER=chromadb
VECTORDB_URL=http://localhost:8000

# Monitoring (Optional)
LANGSMITH_API_KEY=your-langsmith-api-key
LANGSMITH_PROJECT=sentinel-ai
```

### API Keys Setup

1. **Google Gemini**: Get API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. **Groq**: Get API key from [Groq Console](https://console.groq.com/keys)
3. **ElevenLabs** (Optional): Get API key from [ElevenLabs](https://elevenlabs.io/app/sound-effects)

## API Documentation

### Base URL
```
http://localhost:5000/api/v1
```

### Endpoints

#### AI Chat
- **POST** `/ai/chat` - Send a chat message
- **GET** `/ai/models` - Get available AI models
- **GET** `/ai/history` - Get conversation history
- **POST** `/ai/clear-history` - Clear conversation history

#### System
- **GET** `/system/health` - Health check
- **GET** `/system/status` - Detailed system status
- **GET** `/system/config` - Configuration info

### Example Request

```bash
curl -X POST http://localhost:5000/api/v1/ai/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, how are you?",
    "model": "gemini"
  }'
```

## Testing

### Backend Tests

```bash
cd backend
python run_tests.py
```

### Frontend Tests

Manual testing in browser or use automated testing tools like Cypress.

## Architecture

```
Sentinel/
├── frontend/                 # Frontend application
│   ├── index.html           # Main HTML structure
│   ├── styles.css           # Modern CSS3 styling
│   ├── app.js              # Vanilla JavaScript application
│   ├── sw.js               # Service worker for offline support
│   └── manifest.json        # PWA configuration
├── backend/                 # Python backend application
│   ├── app/                # Main application package
│   │   ├── main.py         # Flask application factory
│   │   ├── config.py       # Configuration management
│   │   ├── routes/         # API route blueprints
│   │   │   ├── ai_routes.py    # AI-related endpoints
│   │   │   └── system_routes.py # System endpoints
│   │   ├── services/       # Business logic services
│   │   │   └── ai_service.py   # AI service with LangChain/LangGraph
│   │   └── utils/          # Utility functions
│   │       └── validators.py   # Input validation utilities
│   ├── tests/              # Test suite
│   │   └── test_backend.py # Backend tests
│   ├── run_tests.py        # Test runner script
│   └── requirements.txt    # Python dependencies
└── .env.example            # Environment variables template
```

## Development

### Project Structure

The application follows a modular architecture:

- **Frontend**: Pure HTML5, CSS3, and JavaScript with PWA support
- **Backend**: Flask application with LangChain/LangGraph integration
- **AI Service**: Intelligent conversation management with workflow orchestration
- **Security**: Input validation, rate limiting, and CORS protection

### Adding New Features

1. **Backend**: Add new routes in `routes/` directory
2. **Frontend**: Update `app.js` and `index.html`
3. **Tests**: Add corresponding tests in `tests/` directory

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable names
- Add docstrings to functions and classes
- Keep functions focused and modular

## Deployment

### Production Considerations

1. **Security**: Use environment variables for sensitive data
2. **Performance**: Enable caching and optimize assets
3. **Monitoring**: Set up logging and health checks
4. **Scaling**: Consider containerization with Docker

### Docker Deployment (Future)

```dockerfile
# Example Dockerfile for backend
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app/main.py"]
```

## Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure all required API keys are set in `.env`
2. **CORS Issues**: Check CORS configuration in Flask app
3. **Rate Limiting**: Adjust limits in configuration if needed
4. **Memory Issues**: Monitor system resources and adjust accordingly

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new features
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review existing issues
3. Create a new issue with detailed information

---

**Built with ❤️ using modern web technologies and AI/ML frameworks**