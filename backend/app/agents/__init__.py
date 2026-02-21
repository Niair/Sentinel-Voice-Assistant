"""
Agents package for multi-agent security system.

Contains:
- Security Agent: Qwen2-VL-7B for vision analysis
- Helper Agent: Notification categorization and anti-spam
"""

from app.agents.security_agent import SecurityAgent, get_security_agent

__all__ = [
    "SecurityAgent",
    "get_security_agent",
]
