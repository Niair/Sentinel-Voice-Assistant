"""
Camera Query Tool for AI Integration
Allows AI to query current camera status and recent detections
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from langchain_core.tools import tool
from app.alert_history import alert_history
from app.monitoring_worker import MonitoringWorker
from app.detection import detector


@tool
def query_camera_status() -> str:
    """
    Query the current status of the camera monitoring system.

    Use this when user asks about:
    - "Is the camera working?"
    - "What's the camera status?"
    - "Is monitoring active?"
    - "Is the camera connected?"

    Returns information about camera availability, detection status, and recent activity.
    """
    try:
        # Get detector status
        detector_status = detector.get_status()

        return f"""Camera System Status:
- Detector: {"Active" if detector_status["initialized"] else "Not initialized"}
- Model: {detector_status.get("model", "Unknown")}
- YOLO Available: {"Yes" if detector_status["yolo_available"] else "No"}

The camera monitoring system is {"ready for detection" if detector_status["initialized"] else "initializing"}.
YOLO model {detector_status.get("model", "unknown")} is loaded for object detection."""
    except Exception as e:
        return f"Error querying camera status: {str(e)}"


@tool
async def get_recent_camera_detections(minutes: int = 5) -> str:
    """
    Get recent detections from the camera monitoring system.

    Use this when user asks:
    - "What do you see in the camera?"
    - "What did the camera detect?"
    - "Show me recent activity"
    - "Any movement detected?"
    - "Who is in front of the camera?"

    Also use this PROACTIVELY every few conversation turns to check for security events.

    Args:
        minutes: How many minutes back to check (default: 5)

    Returns summary of recent detections including persons, vehicles, and other objects.
    """
    try:
        alerts = await alert_history.get_recent_alerts(minutes=minutes)

        if not alerts:
            return f"No camera activity detected in the last {minutes} minutes. The camera is monitoring but no movement or objects have been detected recently."

        # Filter for detection events
        detection_alerts = [a for a in alerts if a.get("event_type") == "detection"]

        if not detection_alerts:
            return f"Camera is active but no objects detected in the last {minutes} minutes. Last activity: {alerts[0].get('description', 'Unknown')} at {alerts[0].get('timestamp', 'Unknown')}"

        # Build summary
        total_persons = sum(a.get("persons_count", 0) for a in detection_alerts)
        total_vehicles = sum(a.get("vehicles_count", 0) for a in detection_alerts)

        summary_parts = []
        if total_persons > 0:
            summary_parts.append(f"{total_persons} person(s)")
        if total_vehicles > 0:
            summary_parts.append(f"{total_vehicles} vehicle(s)")

        latest = detection_alerts[0]
        latest_time = latest.get("timestamp", "Unknown")
        latest_desc = latest.get("description", "Activity detected")

        return f"""Camera Detection Summary (last {minutes} minutes):
- Total Detections: {len(detection_alerts)} event(s)
- Objects Found: {", ".join(summary_parts) if summary_parts else "Activity detected"}

Most Recent Detection:
- Time: {latest_time}
- Description: {latest_desc}
- Severity: {latest.get("severity", "Unknown")}

The camera is actively monitoring and detecting {"movement and objects" if detection_alerts else "activity"}."""
    except Exception as e:
        return f"Error retrieving camera detections: {str(e)}"


@tool
async def get_camera_alert_summary() -> str:
    """
    Get a summary of all camera alerts and statistics.

    Use this when user asks:
    - "Show me camera alerts"
    - "Camera statistics"
    - "How many detections today?"
    - "Camera activity summary"

    Returns overall statistics about camera monitoring activity.
    """
    try:
        stats = await alert_history.get_stats()
        recent_alerts = await alert_history.get_recent_alerts(minutes=60)

        total_alerts = stats.get("total_alerts", 0)
        severity_breakdown = stats.get("severity_breakdown", {})

        # Count different types
        detection_count = len(
            [a for a in recent_alerts if a.get("event_type") == "detection"]
        )
        camera_events = len(
            [
                a
                for a in recent_alerts
                if a.get("event_type")
                in ["camera_connected", "camera_unavailable", "camera_disconnected"]
            ]
        )

        severity_lines = []
        for severity, count in sorted(severity_breakdown.items()):
            severity_lines.append(f"  - {severity}: {count} alert(s)")

        return f"""Camera Alert Summary:

Overall Statistics:
- Total Alerts (All Time): {total_alerts}
- Recent Alerts (Last Hour): {len(recent_alerts)}
- Detections (Last Hour): {detection_count}
- Camera Events (Last Hour): {camera_events}

Severity Breakdown:
{chr(10).join(severity_lines) if severity_lines else "  No severity data available"}

Current Status:
The camera monitoring system has recorded {total_alerts} total alerts.
In the last hour, there {"have been" if recent_alerts else "have been no"} detection events."""
    except Exception as e:
        return f"Error getting camera summary: {str(e)}"


# List of camera tools for easy import
camera_tools = [
    query_camera_status,
    get_recent_camera_detections,
    get_camera_alert_summary,
]
