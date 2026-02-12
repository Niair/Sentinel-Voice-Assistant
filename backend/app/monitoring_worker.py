# backend/app/monitoring_worker.py

import asyncio
import logging
from datetime import datetime

# Optional OpenCV import (camera might not be available)
try:
    import cv2
except ImportError:
    cv2 = None  # Will raise CameraUnavailableError on start()

from app.events import publish_event
from app.models import MonitoringEventCreate, Severity  # ✅ FIX: Correct import

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
    Background task that monitors camera feed for events.
    
    Runs continuously in the background, independent of user requests.
    Emits events via the event bus when activity is detected.
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

    async def start(self) -> None:
        """
        Entry point for the background task.
        
        This runs indefinitely until stop() is called.
        Should be started with asyncio.create_task() in main.py.
        """
        logger.info("Monitoring worker starting (camera: %d)...", self.camera_index)
        self._running = True

        # Try to open camera
        try:
            self._camera = self._open_camera()
            logger.info("✅ Camera successfully opened")
        except CameraUnavailableError as exc:
            logger.warning("⚠️ Camera unavailable: %s", exc)
            await self._emit_camera_unavailable()
            # Continue running — camera might become available later

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
        if cv2 is None:
            raise CameraUnavailableError(
                "OpenCV is not installed. Install with: pip install opencv-python"
            )

        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            raise CameraUnavailableError(
                "Camera permission denied or device not found. "
                "Check camera permissions in system settings."
            )

        return cap

    async def _monitor_once(self) -> None:
        """
        Single monitoring iteration (one frame check).
        
        Steps:
        1. Read frame from camera
        2. Run detection logic
        3. Publish event if something detected
        """
        if self._camera is None:
            return  # Camera unavailable — skip this iteration

        # Read frame
        ret, frame = self._camera.read()
        if not ret:
            logger.debug("Failed to read camera frame")
            return

        # Run detection (placeholder stub for now)
        if self._simple_detection_stub(frame):
            event = MonitoringEventCreate(
                source="camera",
                event_type="motion",
                description="Suspicious movement detected",
                severity=Severity.LOW,  # ✅ FIX: Was MonitoringSeverity
                confidence=1.0,
                timestamp=datetime.utcnow(),
                metadata={"camera_index": self.camera_index},
            )
            await publish_event(event)

    def _simple_detection_stub(self, frame) -> bool:
        """
        Placeholder detection logic.
        
        TEMPORARY: Just simulates detection every ~20 seconds.
        REPLACE WITH: YOLO, OpenCV motion detection, or proper CV model.
        
        Args:
            frame: Numpy array (BGR image from OpenCV)
        
        Returns:
            True if something detected, False otherwise
        """
        # Simulate detection every ~20 cycles (20 seconds at 1 FPS)
        return datetime.utcnow().second % 20 == 0

    async def _emit_camera_unavailable(self) -> None:
        """
        Emit a system event when camera is not accessible.
        
        BUG FIX: 
            ❌ OLD: Had broken indentation (IndentationError)
            ✅ NEW: Clean, properly indented
        """
        event = MonitoringEventCreate(
            source="system",
            event_type="unknown",
            description="Camera unavailable. Please enable camera access.",
            severity=Severity.LOW,  # ✅ FIX: Was MonitoringSeverity
            confidence=1.0,
            timestamp=datetime.utcnow(),
            metadata={"camera_index": self.camera_index},
        )
        await publish_event(event)
