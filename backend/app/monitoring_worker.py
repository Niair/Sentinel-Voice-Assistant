"""
Enhanced Monitoring Worker with YOLO Detection
Background task that monitors camera feed using computer vision
"""

import asyncio
import logging
import time
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
    - Alert history storage (only status changes, not every retry)
    - Graceful handling when camera unavailable with auto-retry every 10s
    - Frame capture verification to detect "ghost" cameras
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
        self._last_camera_status = None  # Track status changes
        self._retry_count = 0
        self._max_retries_before_wait = 3  # Try 3 times quickly, then wait 10s

    async def start(self) -> None:
        """
        Entry point for the background task.

        This runs indefinitely until stop() is called.
        Should be started with asyncio.create_task() in main.py.
        """
        logger.info(
            "[CAMERA] Monitoring worker starting (camera: %d)...", self.camera_index
        )
        self._running = True

        # Main monitoring loop with auto-retry
        while self._running:
            try:
                if not self._camera_available:
                    # Try to open camera
                    await self._try_open_camera()
                else:
                    # Camera is open, monitor for events
                    await self._monitor_once()

            except Exception as exc:
                logger.exception("[CAMERA] Monitoring error: %s", exc)
                # Don't crash — keep trying

            await asyncio.sleep(self.poll_interval)

        logger.info("[CAMERA] Monitoring worker stopped")

    async def _try_open_camera(self) -> None:
        """Try to open camera with retry logic"""
        try:
            if self._retry_count < self._max_retries_before_wait:
                # Quick retries initially
                logger.info(
                    f"[CAMERA] Attempting to open camera (attempt {self._retry_count + 1})..."
                )
                self._camera = self._open_camera()
                self._camera_available = True
                self._retry_count = 0

                # Camera opened successfully!
                if self._last_camera_status != "connected":
                    await self._emit_camera_connected()
                    self._last_camera_status = "connected"

            else:
                # Wait 10 seconds before retrying
                logger.info(
                    "[CAMERA] Camera not available, waiting 10s before retry..."
                )
                await asyncio.sleep(10)
                self._retry_count = 0  # Reset retry count

        except CameraUnavailableError as exc:
            self._retry_count += 1
            logger.warning(
                f"[CAMERA] Camera unavailable (attempt {self._retry_count}): {exc}"
            )

            # Only emit alert on status change
            if self._last_camera_status != "unavailable":
                await self._emit_camera_unavailable(str(exc))
                self._last_camera_status = "unavailable"

    def stop(self) -> None:
        """
        Gracefully stop the worker.

        Releases camera hardware and exits the monitoring loop.
        """
        logger.info("[CAMERA] Stopping monitoring worker...")
        self._running = False

        if self._camera is not None:
            self._camera.release()
            self._camera = None
            logger.info("[CAMERA] Camera released")

    def _open_camera(self):
        """
        Attempt to open the camera device with frame capture verification.

        This tests if the camera can actually capture frames (not just open).
        Prevents "ghost" cameras that appear in device list but don't work.

        Returns:
            cv2.VideoCapture: Opened camera object

        Raises:
            CameraUnavailableError: If camera cannot be accessed or capture frames
        """
        if not CV2_AVAILABLE:
            raise CameraUnavailableError(
                "OpenCV is not installed. Install with: pip install opencv-python"
            )

        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            raise CameraUnavailableError(
                "No camera detected. Please connect a USB camera to enable monitoring."
            )

        # NEW: Test frame capture (try 3 times with 200ms delays)
        # This catches "ghost" cameras that open but can't capture
        frame_captured = False
        for attempt in range(3):
            ret, frame = cap.read()
            if ret and frame is not None and frame.size > 0:
                frame_captured = True
                logger.info(
                    f"[CAMERA] Frame capture test passed (attempt {attempt + 1})"
                )
                break
            time.sleep(0.2)  # 200ms between attempts

        if not frame_captured:
            cap.release()
            raise CameraUnavailableError(
                "Camera detected but cannot capture video frames. "
                "Please check camera permissions or connect a working camera."
            )

        logger.info("[CAMERA] Camera opened and verified successfully")
        return cap

    async def _monitor_once(self) -> None:
        """
        Single monitoring iteration with YOLO detection.

        Steps:
        1. Read frame from camera
        2. Verify camera is still working (handle disconnections)
        3. Run YOLO object detection
        4. Analyze detections for security threats
        5. Broadcast alerts if needed
        """
        if not self._camera_available or self._camera is None:
            return

        # Read frame
        ret, frame = self._camera.read()
        if not ret or frame is None:
            # Camera stopped working!
            logger.warning(
                "[CAMERA] Failed to read frame - camera may have disconnected"
            )
            self._camera_available = False
            if self._camera:
                self._camera.release()
                self._camera = None

            # Emit disconnection alert
            if self._last_camera_status != "disconnected":
                await self._emit_camera_disconnected()
                self._last_camera_status = "disconnected"
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
            "type": "detection",
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
        logger.info(f"[CAMERA] Detection alert broadcast: {event.description}")

    async def _emit_camera_connected(self) -> None:
        """Emit event when camera is successfully connected and working"""
        event = MonitoringEventCreate(
            source="system",
            event_type="camera_connected",
            description="[SUCCESS] Camera connected and working! Monitoring is now active.",
            severity=Severity.LOW,  # LOW = informational
            confidence=1.0,
            timestamp=datetime.utcnow(),
            metadata={
                "camera_index": self.camera_index,
                "status": "connected",
                "message": "Camera is ready for monitoring",
            },
        )
        await publish_event(event)

        # Broadcast via WebSocket
        await alert_ws_manager.broadcast_alert(
            {
                "type": "camera_status",
                "event_type": "camera_connected",
                "severity": "LOW",
                "description": "Camera connected and working!",
                "timestamp": datetime.utcnow().isoformat(),
                "camera_index": self.camera_index,
                "status": "connected",
                "message": "Camera is ready for monitoring",
            }
        )

        # Add to alert history
        await alert_history.add_alert(
            {
                "camera_id": f"camera_{self.camera_index}",
                "event_type": "camera_connected",
                "description": "Camera connected and working",
                "severity": "LOW",
                "status": "connected",
            }
        )

        logger.info("[CAMERA] Camera connected notification sent")

    async def _emit_camera_unavailable(self, error_message: str) -> None:
        """Emit a system event when camera is not accessible"""
        event = MonitoringEventCreate(
            source="system",
            event_type="camera_unavailable",
            description=f"[WARNING] {error_message}",
            severity=Severity.MEDIUM,
            confidence=1.0,
            timestamp=datetime.utcnow(),
            metadata={
                "camera_index": self.camera_index,
                "error": error_message,
                "action_required": "Connect a USB camera or check permissions",
            },
        )
        await publish_event(event)

        # Broadcast via WebSocket
        await alert_ws_manager.broadcast_alert(
            {
                "type": "camera_status",
                "event_type": "camera_unavailable",
                "severity": "MEDIUM",
                "description": error_message,
                "timestamp": datetime.utcnow().isoformat(),
                "camera_index": self.camera_index,
                "status": "unavailable",
                "action_required": "Connect a USB camera or check permissions",
                "retry_in_seconds": 10,
            }
        )

        # Add to alert history
        await alert_history.add_alert(
            {
                "camera_id": f"camera_{self.camera_index}",
                "event_type": "camera_unavailable",
                "description": error_message,
                "severity": "MEDIUM",
                "status": "unavailable",
            }
        )

        logger.warning("[CAMERA] Camera unavailable notification sent")

    async def _emit_camera_disconnected(self) -> None:
        """Emit event when camera disconnects during operation"""
        event = MonitoringEventCreate(
            source="system",
            event_type="camera_disconnected",
            description="[WARNING] Camera disconnected unexpectedly. Will retry every 10 seconds.",
            severity=Severity.MEDIUM,
            confidence=1.0,
            timestamp=datetime.utcnow(),
            metadata={
                "camera_index": self.camera_index,
                "status": "disconnected",
            },
        )
        await publish_event(event)

        # Broadcast via WebSocket
        await alert_ws_manager.broadcast_alert(
            {
                "type": "camera_status",
                "event_type": "camera_disconnected",
                "severity": "MEDIUM",
                "description": "Camera disconnected unexpectedly",
                "timestamp": datetime.utcnow().isoformat(),
                "camera_index": self.camera_index,
                "status": "disconnected",
                "retry_in_seconds": 10,
            }
        )

        # Add to alert history
        await alert_history.add_alert(
            {
                "camera_id": f"camera_{self.camera_index}",
                "event_type": "camera_disconnected",
                "description": "Camera disconnected unexpectedly",
                "severity": "MEDIUM",
                "status": "disconnected",
            }
        )

        logger.warning("[CAMERA] Camera disconnected notification sent")

    def get_status(self) -> dict:
        """Get current monitoring status"""
        is_capturing = False
        if self._camera_available and self._camera:
            # Quick test if camera is still responding
            ret, _ = self._camera.read()
            is_capturing = ret

        return {
            "running": self._running,
            "camera_available": self._camera_available,
            "camera_capturing": is_capturing,
            "camera_index": self.camera_index,
            "poll_interval": self.poll_interval,
            "retry_count": self._retry_count,
            "last_status": self._last_camera_status,
            "detector_status": detector.get_status(),
            "last_detection": self._last_detection_time.isoformat()
            if self._last_detection_time
            else None,
        }

    async def open_camera_manual(self) -> bool:
        """
        Manually trigger camera opening (called when user clicks "Open Camera" in UI)

        Returns:
            bool: True if camera opened successfully, False otherwise
        """
        if self._camera_available:
            logger.info("[CAMERA] Camera already open")
            return True

        logger.info("[CAMERA] Manual camera open requested")
        self._retry_count = 0  # Reset retry count for fresh attempt

        try:
            self._camera = self._open_camera()
            self._camera_available = True
            self._retry_count = 0

            if self._last_camera_status != "connected":
                await self._emit_camera_connected()
                self._last_camera_status = "connected"

            return True

        except CameraUnavailableError as e:
            logger.error(f"[CAMERA] Manual open failed: {e}")
            await self._emit_camera_unavailable(str(e))
            return False
