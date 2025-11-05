from flask import Blueprint, jsonify
from ..integrations.gemini_client import GeminiClient
from ..integrations.groq_client import GroqClient
from ..integrations.stt_client import STTClient
from ..integrations.tts_client import TTSClient
from ..config import Config

system_bp = Blueprint('system_bp', __name__)

@system_bp.route('/api/v1/system/health')
def health_check():
    """Basic health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "Sentinel Voice Assistant"
    }), 200


@system_bp.route('/api/v1/system/integrations')
def system_integrations():
    """
    Check health of all API integrations.
    Returns status for each service.
    """
    integrations_status = {}
    overall_status = "healthy"
    
    # Check Gemini
    try:
        if Config.GEMINI_API_KEY:
            gemini = GeminiClient()
            gemini_healthy = gemini.health_check()
            integrations_status['gemini'] = {
                "status": "healthy" if gemini_healthy else "unhealthy",
                "configured": True
            }
            if not gemini_healthy:
                overall_status = "degraded"
        else:
            integrations_status['gemini'] = {
                "status": "not_configured",
                "configured": False
            }
            overall_status = "degraded"
    except Exception as e:
        integrations_status['gemini'] = {
            "status": "error",
            "error": str(e),
            "configured": bool(Config.GEMINI_API_KEY)
        }
        overall_status = "degraded"
    
    # Check Groq
    try:
        if Config.GROQ_API_KEY:
            groq = GroqClient()
            groq_healthy = groq.health_check()
            integrations_status['groq'] = {
                "status": "healthy" if groq_healthy else "unhealthy",
                "configured": True
            }
            if not groq_healthy:
                overall_status = "degraded"
        else:
            integrations_status['groq'] = {
                "status": "not_configured",
                "configured": False
            }
    except Exception as e:
        integrations_status['groq'] = {
            "status": "error",
            "error": str(e),
            "configured": bool(Config.GROQ_API_KEY)
        }
    
    # Check STT (Whisper - local, always available)
    try:
        stt = STTClient()
        stt_healthy = stt.health_check()
        integrations_status['stt'] = {
            "status": "healthy" if stt_healthy else "unhealthy",
            "provider": "whisper",
            "configured": True
        }
        if not stt_healthy:
            overall_status = "degraded"
    except Exception as e:
        integrations_status['stt'] = {
            "status": "error",
            "error": str(e),
            "provider": "whisper",
            "configured": True
        }
        overall_status = "degraded"
    
    # Check TTS (ElevenLabs)
    try:
        if Config.ELEVENLABS_API_KEY:
            tts = TTSClient()
            tts_healthy = tts.health_check()
            integrations_status['tts'] = {
                "status": "healthy" if tts_healthy else "unhealthy",
                "provider": "elevenlabs",
                "configured": True
            }
            if not tts_healthy:
                overall_status = "degraded"
        else:
            integrations_status['tts'] = {
                "status": "not_configured",
                "provider": "elevenlabs",
                "configured": False
            }
    except Exception as e:
        integrations_status['tts'] = {
            "status": "error",
            "error": str(e),
            "provider": "elevenlabs",
            "configured": bool(Config.ELEVENLABS_API_KEY)
        }
    
    return jsonify({
        "overall_status": overall_status,
        "integrations": integrations_status,
        "message": "All critical services operational" if overall_status == "healthy" else "Some services are degraded"
    }), 200


@system_bp.route('/api/v1/system/config')
def system_config():
    """
    Get current system configuration (without exposing secrets).
    """
    return jsonify({
        "llm": {
            "primary": "gemini" if Config.GEMINI_API_KEY else None,
            "fallback": "groq" if Config.GROQ_API_KEY else None
        },
        "voice": {
            "stt": "whisper",
            "tts": "elevenlabs" if Config.ELEVENLABS_API_KEY else None
        },
        "memory": {
            "provider": Config.VECTORDB_PROVIDER or "chromadb",
            "enabled": True
        }
    }), 200
