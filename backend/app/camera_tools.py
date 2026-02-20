"""
Camera Query Tool for AI Integration
Allows AI to query current camera status and recent detections
"""

import asyncio
import base64
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from langchain_core.tools import tool
from app.alert_history import alert_history
from app.monitoring_worker import MonitoringWorker
from app.detection import detector

_last_captured_frame = None
_last_frame_time = None


def set_captured_frame(frame):
    """Store the last captured frame from monitoring worker."""
    global _last_captured_frame, _last_frame_time
    _last_captured_frame = frame
    _last_frame_time = datetime.utcnow()


def get_captured_frame():
    """Get the last captured frame."""
    return _last_captured_frame


def get_captured_frame_base64() -> Optional[str]:
    """Get the last captured frame as base64 string."""
    global _last_captured_frame
    if _last_captured_frame is None:
        return None
    try:
        import cv2

        _, buffer = cv2.imencode(
            ".jpg", _last_captured_frame, [cv2.IMWRITE_JPEG_QUALITY, 85]
        )
        return base64.b64encode(bytes(buffer)).decode("utf-8")
    except Exception:
        return None
    try:
        import cv2

        _, buffer = cv2.imencode(
            ".jpg", _last_captured_frame, [cv2.IMWRITE_JPEG_QUALITY, 85]
        )
        return base64.b64encode(buffer).decode("utf-8")
    except Exception:
        return None


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


@tool
def capture_current_frame() -> str:
    """
    Capture a frame from the camera for visual analysis.

    IMPORTANT: Only use this tool when user EXPLICITLY asks about camera view.
    NEVER use for casual conversation like "hello" or "how are you".

    Use this ONLY when:
    - User EXPLICITLY asks: "What do you see right now?", "Show me the camera"
    - User asks about appearance, outfit, or emotional state
    - User asks about security or threats

    Returns base64-encoded frame data that can be analyzed by vision tools.
    """
    global _last_captured_frame, _last_frame_time

    if _last_captured_frame is None:
        return "No frame available. Camera may not be active yet."

    frame_base64 = get_captured_frame_base64()
    if frame_base64 is None:
        return "Failed to encode frame for analysis."

    time_ago = ""
    if _last_frame_time:
        seconds_ago = (datetime.utcnow() - _last_frame_time).total_seconds()
        time_ago = f" (captured {seconds_ago:.1f}s ago)"

    return f"FRAME_CAPTURED:{frame_base64}|Frame captured successfully{time_ago}. Use this with vision analysis tools."


@tool
async def analyze_current_scene() -> str:
    """
    Capture and analyze the current camera scene using AI vision.

    IMPORTANT: Only use this tool when user EXPLICITLY asks about camera/scene.
    NEVER use for casual conversation like "hello" or "how are you".

    Use this ONLY when:
    - User EXPLICITLY asks: "What's happening right now?", "What do you see?"
    - User asks about people count, activity, or scene description

    Returns a human-readable description of what the camera sees.
    """
    from app.vision_tools import describe_scene

    frame_base64 = get_captured_frame_base64()
    if frame_base64 is None:
        return "No frame available. Camera may not be active yet."

    return await describe_scene.ainvoke({"frame_base64": frame_base64})


@tool
async def check_for_threats() -> str:
    """
    Analyze current camera frame for security threats (weapons, suspicious objects).

    IMPORTANT: Only use this tool when user EXPLICITLY asks about security/threats.
    NEVER use for casual conversation like "hello" or "how are you".

    Use this ONLY when:
    - User EXPLICITLY asks: "Is everything safe?", "Check for threats", "Any weapons?"
    - User asks about security or dangerous situations

    Returns threat analysis with severity level.
    """
    from app.vision_tools import analyze_frame_for_threats

    frame_base64 = get_captured_frame_base64()
    if frame_base64 is None:
        return "No frame available. Camera may not be active yet."

    return await analyze_frame_for_threats.ainvoke({"frame_base64": frame_base64})


@tool
async def get_outfit_advice() -> str:
    """
    Get fashion advice based on the current camera view.

    IMPORTANT: Only use this tool when user EXPLICITLY asks about outfit/appearance.
    NEVER use for casual conversation like "hello" or "how are you".

    Use this ONLY when:
    - User EXPLICITLY asks: "How does my outfit look?", "Rate my outfit"
    - User asks about clothing, fashion, or appearance advice

    Returns fashion analysis and suggestions.
    """
    from app.vision_tools import analyze_outfit

    frame_base64 = get_captured_frame_base64()
    if frame_base64 is None:
        return "No frame available. Camera may not be active yet. Please stand in front of the camera."

    return await analyze_outfit.ainvoke({"frame_base64": frame_base64})


@tool
async def what_is_happening() -> str:
    """
    Get a comprehensive understanding of what's happening in the camera view.

    IMPORTANT: Only use this tool when user EXPLICITLY asks about scene/camera.
    NEVER use for casual conversation like "hello" or "how are you".

    Use this ONLY when:
    - User EXPLICITLY asks: "What's happening?", "What's going on?", "What do you see?"
    - User asks for a situation report or complete scene analysis

    Returns comprehensive analysis including people, activities, objects, and safety.
    """
    from app.vision_tools import understand_scene

    frame_base64 = get_captured_frame_base64()
    if frame_base64 is None:
        return "No frame available. Camera may not be active yet."

    return await understand_scene.ainvoke({"frame_base64": frame_base64})


@tool
async def how_do_i_look() -> str:
    """
    Analyze the user's appearance and emotional state from the camera.

    IMPORTANT: Only use this tool when user EXPLICITLY asks about appearance/mood.
    NEVER use for casual conversation like "hello" or "how are you".

    Use this ONLY when:
    - User EXPLICITLY asks: "How do I look?", "How's my appearance?"
    - User asks about mood, emotions, or if they look tired/crying
    - User wants complete personal analysis (appearance + emotions)

    Returns complete analysis of appearance, emotions, and mood.
    """
    from app.vision_tools import analyze_person

    frame_base64 = get_captured_frame_base64()
    if frame_base64 is None:
        return "No frame available. Camera may not be active yet. Please stand in front of the camera."

    return await analyze_person.ainvoke({"frame_base64": frame_base64})


@tool
async def detect_emotional_state() -> str:
    """
    Detect the user's emotional state from facial expressions and body language.

    IMPORTANT: Only use this tool when user EXPLICITLY asks about emotions/mood.
    NEVER use for casual conversation like "hello" or "how are you".

    Use this ONLY when:
    - User EXPLICITLY asks: "What's my mood?", "How am I feeling?", "Do I look sad?"
    - User mentions crying, stress, or asks about emotional state
    - User wants emotional awareness or facial expression analysis

    Returns detailed emotional analysis including signs of crying, stress, etc.
    """
    from app.vision_tools import detect_emotions

    frame_base64 = get_captured_frame_base64()
    if frame_base64 is None:
        return "No frame available. Camera may not be active yet. Please stand in front of the camera."

    return await detect_emotions.ainvoke({"frame_base64": frame_base64})


@tool
async def what_are_people_doing() -> str:
    """
    Detect and classify human activities in the camera frame.

    IMPORTANT: Only use this tool when user EXPLICITLY asks about activities.
    NEVER use for casual conversation like "hello" or "how are you".

    Use this ONLY when:
    - User EXPLICITLY asks: "What are they doing?", "What are people doing?"
    - User asks about suspicious behavior or human activities

    Returns activity classification with assessment.
    """
    from app.vision_tools import detect_activity

    frame_base64 = get_captured_frame_base64()
    if frame_base64 is None:
        return "No frame available. Camera may not be active yet."

    return await detect_activity.ainvoke({"frame_base64": frame_base64})


# List of camera tools for easy import
camera_tools = [
    query_camera_status,
    get_recent_camera_detections,
    get_camera_alert_summary,
    capture_current_frame,
    analyze_current_scene,
    check_for_threats,
    get_outfit_advice,
    what_is_happening,
    how_do_i_look,
    detect_emotional_state,
    what_are_people_doing,
]
