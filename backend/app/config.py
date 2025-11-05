import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
    ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')
    WHISPER_API_KEY = os.environ.get('WHISPER_API_KEY')
    LANGSMITH_API_KEY = os.environ.get('LANGSMITH_API_KEY')
    VECTORDB_PROVIDER = os.environ.get('VECTORDB_PROVIDER')
    VECTORDB_URL = os.environ.get('VECTORDB_URL')
    S3_BUCKET = os.environ.get('S3_BUCKET')