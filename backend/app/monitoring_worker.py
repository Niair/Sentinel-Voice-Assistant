"""
Enhanced Monitoring Worker with YOLO Detection
Background task that monitors camera feed using computer vision
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

# Optional OpenCV import (camera might not be available)
try:
    import cv2

    CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    CV2_AVAILABLE = False

from app.events import publish_event
from app.models import MonitoringEventCreate, Severity
from app.websocket_manager import alert_ws_manager
from app.alert_history import alert_history
from app.detection import detector

logger = logging.getLogger(__name__)


# ==============================================================================
# EXCEPTIONS
# ==============================================================================


class CameraUnavailableError(Exception):
    """Raised when the camera cannot be accessed."""

    pass


# ==============================================================================
# MONITORING WORKER
# ==============================================================================


class MonitoringWorker:
    """
    Background task that monitors camera feed for events using YOLO.

    Features:
    - Real-time object detection (persons, vehicles, etc.)
    - WebSocket alerts for instant notifications
    - Alert history storage
    - Graceful handling when camera unavailable
    """

    def __init__(self, camera_index: int = 0, poll_interval: float = 1.0) -> None:
        """
        Initialize the monitoring worker.

        Args:
            camera_index: OS camera index (0 = default webcam)
            poll_interval: Seconds between frame checks (1.0 = 1 FPS)
        """
        self.camera_index = camera_index
        self.poll_interval = poll_interval
        self._running = False
        self._camera = None
        self._camera_available = False
        self._last_detection_time = None

    async def start(self) -> None:
        """
        Entry point for the background task.

        This runs indefinitely until stop() is called.
        Should be started with asyncio.create_task() in main.py.
        """
        logger.info("🎥 Monitoring worker starting (camera: %d)...", self.camera_index)
        self._running = True

        # Try to open camera
        try:
            self._camera = self._open_camera()
            self._camera_available = True
            logger.info("✅ Camera successfully opened")
        except CameraUnavailableError as exc:
            logger.warning("⚠️ Camera unavailable: %s", exc)
            await self._emit_camera_unavailable()
            self._camera_available = False

        # Main monitoring loop
        while self._running:
            try:
                await self._monitor_once()
            except Exception as exc:
                logger.exception("Monitoring error: %s", exc)
                # Don't crash — keep trying

            await asyncio.sleep(self.poll_interval)

        logger.info("Monitoring worker stopped")

    def stop(self) -> None:
        """
        Gracefully stop the worker.

        Releases camera hardware and exits the monitoring loop.
        """
        logger.info("Stopping monitoring worker...")
        self._running = False

        if self._camera is not None:
            self._camera.release()
            logger.info("Camera released")

    # ═══════════════════════════════════════════════════════════════════════
    # PRIVATE METHODS
    # ═══════════════════════════════════════════════════════════════════════

    def _open_camera(self):
        """
        Attempt to open the camera device.

        Returns:
            cv2.VideoCapture: Opened camera object

        Raises:
            CameraUnavailableError: If camera cannot be accessed
        """
        if not CV2_AVAILABLE:
            raise CameraUnavailableError(
                "OpenCV is not installed. Install with: pip install opencv-python"
            )

        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            raise CameraUnavailableError(
                "No camera detected. Please connect a camera to use monitoring features."
            )

        return cap

    async def _monitor_once(self) -> None:
        """
        Single monitoring iteration with YOLO detection.

        Steps:
        1. Read frame from camera
        2. Run YOLO object detection
        3. Analyze detections for security threats
        4. Broadcast alerts if needed
        """
        if not self._camera_available or self._camera is None:
            return  # Camera unavailable — skip this iteration

        # Read frame
        ret, frame = self._camera.read()
        if not ret:
            logger.debug("Failed to read camera frame")
            return

        # Run YOLO detection
        detection_result = detector.detect_security_threats(frame)

        # Check if we have detections
        if detection_result["total_detections"] > 0:
            self._last_detection_time = datetime.utcnow()

            # Create alert event
            threat_level = detection_result["threat_level"]

            # Determine severity based on threat level
            if threat_level == "medium":
                severity = Severity.MEDIUM
            elif threat_level == "high":
                severity = Severity.HIGH
            else:
                severity = Severity.LOW

            # Build description
            persons_count = len(detection_result["persons"])
            vehicles_count = len(detection_result["vehicles"])

            description_parts = []
            if persons_count > 0:
                description_parts.append(f"{persons_count} person(s) detected")
            if vehicles_count > 0:
                description_parts.append(f"{vehicles_count} vehicle(s) detected")

            description = (
                " | ".join(description_parts)
                if description_parts
                else "Activity detected"
            )

            # Create event
            event = MonitoringEventCreate(
                source="camera",
                event_type="detection",
                description=description,
                severity=severity,
                confidence=max(
                    [d["confidence"] for d in detection_result["all_detections"]]
                    + [0.5]
                ),
                timestamp=datetime.utcnow(),
                metadata={
                    "camera_index": self.camera_index,
                    "threat_level": threat_level,
                    "detections": detection_result["all_detections"],
                    "persons_count": persons_count,
                    "vehicles_count": vehicles_count,
                },
            )

            # Publish to event bus
            await publish_event(event)

            # Broadcast via WebSocket for real-time notifications
            await self._broadcast_detection_alert(event, detection_result)

            # Store in alert history
            await alert_history.add_alert(
                {
                    "camera_id": f"camera_{self.camera_index}",
                    "event_type": "detection",
                    "description": description,
                    "severity": severity.value,
                    "threat_level": threat_level,
                    "detections_count": detection_result["total_detections"],
                    "persons_count": persons_count,
                    "vehicles_count": vehicles_count,
                    "metadata": event.metadata,
                }
            )

    async def _broadcast_detection_alert(
        self, event: MonitoringEventCreate, detection_result: dict
    ):
        """Broadcast detection alert via WebSocket"""
        alert_data = {
            "event_type": "detection",
            "severity": event.severity.value,
            "description": event.description,
            "timestamp": event.timestamp.isoformat(),
            "camera_index": self.camera_index,
            "threat_level": detection_result["threat_level"],
            "persons_detected": len(detection_result["persons"]),
            "vehicles_detected": len(detection_result["vehicles"]),
            "total_detections": detection_result["total_detections"],
        }

        await alert_ws_manager.broadcast_alert(alert_data)
        logger.info(f"🚨 Detection alert broadcast: {event.description}")

    async def _emit_camera_unavailable(self) -> None:
        """
        Emit a system event when camera is not accessible.
        This will be shown to the user so they know to connect a camera.
        """
        event = MonitoringEventCreate(
            source="system",
            event_type="camera_unavailable",
            description="No camera detected. Please connect a camera to enable monitoring.",
            severity=Severity.MEDIUM,  # Medium so it passes the filter
            confidence=1.0,
            timestamp=datetime.utcnow(),
            metadata={
                "camera_index": self.camera_index,
                "help_text": "Connect a USB webcam or enable camera permissions",
            },
        )
        await publish_event(event)

        # Also broadcast via WebSocket
        await alert_ws_manager.broadcast_alert(
            {
                "event_type": "camera_unavailable",
                "severity": "MEDIUM",
                "description": "No camera detected. Please connect a camera to enable monitoring.",
                "timestamp": datetime.utcnow().isoformat(),
                "camera_index": self.camera_index,
                "help_text": "Connect a USB webcam or enable camera permissions",
            }
        )

        logger.warning("📹 Camera unavailable notification sent")

    def get_status(self) -> dict:
        """Get current monitoring status"""
        return {
            "running": self._running,
            "camera_available": self._camera_available,
            "camera_index": self.camera_index,
            "poll_interval": self.poll_interval,
            "detector_status": detector.get_status(),
            "last_detection": self._last_detection_time.isoformat()
            if self._last_detection_time
            else None,
        }
