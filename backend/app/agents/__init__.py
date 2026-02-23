"""
Agents package for multi-agent security system.

Contains:
- Security Agent: NVIDIA llama-3.2-vision for fast vision analysis
- Helper Agent: Ollama Qwen 3.5 for verification, formatting, and notifications
- Notification Tool: Smart notifications and email alerts
"""

from app.agents.security_agent import SecurityAgent, get_security_agent
from app.agents.helper_agent import (
    HelperAgent,
    get_helper_agent,
    ThreatCategory,
    QueryType,
)
from app.agents.notification_tool import (
    generate_notification,
    send_alert_email,
    format_email_report,
    SessionTracker,
    get_session_tracker,
)

__all__ = [
    # Security Agent
    "SecurityAgent",
    "get_security_agent",
    # Helper Agent
    "HelperAgent",
    "get_helper_agent",
    "ThreatCategory",
    "QueryType",
    # Notification Tool
    "generate_notification",
    "send_alert_email",
    "format_email_report",
    "SessionTracker",
    "get_session_tracker",
]
