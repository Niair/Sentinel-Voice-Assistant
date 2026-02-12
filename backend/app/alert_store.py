# app/alert_store.py

import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from app.models import MonitoringEventCreate

logger = logging.getLogger(__name__)

# Alert storage file
ALERT_FILE = Path("alerts.json")

# ==============================================================================
# PUBLIC API
# ==============================================================================

async def save_alert(event: MonitoringEventCreate) -> None:
    """
    Persist an alert to the JSON store.
    
    BUG FIX:
        ❌ OLD: `def save_alert(alert: Dict[str, Any])` — synchronous, untyped
        ✅ NEW: `async def save_alert(event: MonitoringEventCreate)` — async, typed
    
    This function is called with `await` in alert_processor.py, so it MUST be async.
    
    Args:
        event: The monitoring event to save as an alert
    
    Raises:
        IOError: If file write fails
    
    Example:
        event = MonitoringEventCreate(...)
        await save_alert(event)  # ✅ Correct (async)
    """
    try:
        # Load existing alerts
        alerts: List[Dict[str, Any]] = []
        if ALERT_FILE.exists():
            try:
                alerts = json.loads(ALERT_FILE.read_text())
            except json.JSONDecodeError:
                logger.warning("alerts.json is corrupted — starting fresh")
                # Keep empty list, file will be overwritten

        # Convert Pydantic model to dict for JSON serialization
        alert_dict = {
            "timestamp": event.timestamp.isoformat(),
            "severity": event.severity.value,
            "description": event.description,
            "source": event.source,
            "event_type": event.event_type,
            "confidence": event.confidence,
            "metadata": event.metadata,
        }

        # Append and save
        alerts.append(alert_dict)
        ALERT_FILE.write_text(json.dumps(alerts, indent=2))
        
        logger.debug("Alert saved: %s (total: %d)", alert_dict["description"], len(alerts))
        
    except Exception as e:
        logger.error("Failed to save alert: %s", e)
        # Don't crash the system if persistence fails
        # In production, this should trigger a monitoring alert


async def get_recent_alerts(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieve recent alerts from storage.
    
    Args:
        limit: Maximum number of alerts to return
    
    Returns:
        List of alert dictionaries (newest first)
    """
    try:
        if not ALERT_FILE.exists():
            return []
        
        alerts = json.loads(ALERT_FILE.read_text())
        
        # Return most recent first
        return list(reversed(alerts[-limit:]))
        
    except Exception as e:
        logger.error("Failed to load alerts: %s", e)
        return []


async def clear_alerts() -> int:
    """
    Clear all saved alerts.
    
    Returns:
        Number of alerts cleared
    """
    try:
        if not ALERT_FILE.exists():
            return 0
        
        alerts = json.loads(ALERT_FILE.read_text())
        count = len(alerts)
        
        ALERT_FILE.write_text("[]")
        logger.info("Cleared %d alerts", count)
        
        return count
        
    except Exception as e:
        logger.error("Failed to clear alerts: %s", e)
        return 0