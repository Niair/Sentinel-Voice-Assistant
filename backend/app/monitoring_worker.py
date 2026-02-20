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

        # Smart notification tracking to prevent spam
        self._last_person_count = 0
        self._last_notification_time = None
        self._session_active = False
        self._notification_cooldown = 300  # 5 minutes between notifications

        # Anti-spam for camera status notifications
        self._has_sent_connected_notification = False
        self._last_status_notification_time = None
        self._status_notification_cooldown = (
            300  # 5 minutes between status notifications
        )

        # Smart person tracking for intelligent notifications
        self._person_count_history = []  # Last 10 frames for pattern detection
        self._last_gemini_analysis_time = None
        self._gemini_analysis_cooldown = 30  # Analyze with Gemini every 30 seconds max
        self._last_scene_description = ""
        self._last_threat_assessment = None
        self._vision_enabled = True  # Toggle for Gemini Vision analysis

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

        # Store frame for vision analysis tools
        from app.camera_tools import set_captured_frame

        set_captured_frame(frame)

        # Run YOLO detection
        detection_result = detector.detect_security_threats(frame)

        # Check if we have detections
        persons_count = len(detection_result["persons"])
        vehicles_count = len(detection_result["vehicles"])
        animals_count = len(detection_result["animals"])

        # Track person count history for pattern detection
        self._person_count_history.append(persons_count)
        if len(self._person_count_history) > 10:
            self._person_count_history.pop(0)

        # Smart notification logic - only notify on suspicious/important activity
        current_time = datetime.utcnow()
        should_notify = False
        notification_reason = ""
        threat_assessment = ""
        gemini_description = None

        # Intelligent Gemini Vision analysis (rate-limited)
        if persons_count > 0 and self._vision_enabled:
            can_analyze = True
            if self._last_gemini_analysis_time:
                time_since_last_analysis = (
                    current_time - self._last_gemini_analysis_time
                ).total_seconds()
                if time_since_last_analysis < self._gemini_analysis_cooldown:
                    can_analyze = False

            if can_analyze:
                gemini_description = await self._analyze_scene_with_gemini(frame)
                self._last_gemini_analysis_time = current_time

        if persons_count > 0:
            self._last_detection_time = current_time

            # Assess threat level and importance
            is_suspicious = False
            importance_score = 0

            # Factor 1: Multiple people (could be crowd or intrusion)
            if persons_count >= 3:
                is_suspicious = True
                importance_score += 3
                threat_assessment = f"Multiple people detected ({persons_count}) - possible intrusion or gathering"

            # Factor 2: Person + Vehicle (suspicious combo)
            elif persons_count > 0 and vehicles_count > 0:
                is_suspicious = True
                importance_score += 2
                threat_assessment = (
                    "Person near vehicle - check for suspicious activity"
                )

            # Factor 3: Animal detection (unusual)
            elif animals_count > 0 and persons_count == 0:
                is_suspicious = True
                importance_score += 1
                threat_assessment = "Animal detected in monitored area"

            # Factor 4: Rapid person count change (someone joined/left quickly)
            elif (
                self._session_active
                and abs(persons_count - self._last_person_count) >= 2
            ):
                is_suspicious = True
                importance_score += 2
                if persons_count > self._last_person_count:
                    threat_assessment = f"Multiple people joined suddenly ({self._last_person_count} -> {persons_count})"
                else:
                    threat_assessment = f"Multiple people left suddenly ({self._last_person_count} -> {persons_count})"

            # Factor 5: New session with single person (notify but lower priority)
            elif not self._session_active and persons_count == 1:
                # Only notify if enough time passed since last notification
                if self._last_notification_time:
                    time_since_last = (
                        current_time - self._last_notification_time
                    ).total_seconds()
                    if time_since_last > self._notification_cooldown:
                        is_suspicious = True
                        importance_score += 1
                        threat_assessment = "Person entered monitored area"
                else:
                    is_suspicious = True
                    importance_score += 1
                    threat_assessment = "Person entered monitored area"

            # Factor 6: Use Gemini's threat assessment if available
            if gemini_description and "THREAT DETECTED" in gemini_description:
                is_suspicious = True
                importance_score += 3
                self._last_threat_assessment = gemini_description
                logger.warning(
                    f"[CAMERA] Gemini detected threat: {gemini_description[:100]}"
                )

            # Decide whether to notify based on importance
            if is_suspicious and importance_score >= 2:
                should_notify = True
                notification_reason = threat_assessment
                logger.info(f"[CAMERA] SUSPICIOUS: {threat_assessment}")
            elif is_suspicious and importance_score == 1:
                # Lower priority - check cooldown
                if self._last_notification_time:
                    time_since_last = (
                        current_time - self._last_notification_time
                    ).total_seconds()
                    if time_since_last > self._notification_cooldown:
                        should_notify = True
                        notification_reason = threat_assessment
                        logger.info(f"[CAMERA] Activity: {threat_assessment}")
                else:
                    should_notify = True
                    notification_reason = threat_assessment
                    logger.info(f"[CAMERA] Activity: {threat_assessment}")

            self._session_active = True

        else:
            # No persons detected - session ended
            if self._session_active:
                self._session_active = False
                logger.info("[CAMERA] Area cleared - no persons detected")

        # Update tracking
        self._last_person_count = persons_count

        # Create alert event (always save to history, but conditionally notify)
        if detection_result["total_detections"] > 0:
            threat_level = detection_result["threat_level"]

            # Determine severity based on threat level
            if threat_level == "medium":
                severity = Severity.MEDIUM
            elif threat_level == "high":
                severity = Severity.HIGH
            else:
                severity = Severity.LOW

            # Build description based on what's detected
            if persons_count == 1:
                description = "👤 Person detected by camera"
            elif persons_count > 1:
                description = f"👥 {persons_count} people detected by camera"
            elif vehicles_count > 0:
                description = f"🚗 {vehicles_count} vehicle(s) detected"
            elif animals_count > 0:
                description = f"🐕 Animal detected"
            else:
                description = "Activity detected"

            # Add urgency for high threat
            if threat_level == "high":
                description = f"⚠️ {description} - Multiple detections!"

            # Enhance description with Gemini analysis if available
            if gemini_description:
                if "THREAT DETECTED" in gemini_description:
                    # Extract key info from threat assessment
                    threat_type = "unknown"
                    if "weapon" in gemini_description.lower():
                        threat_type = "weapon"
                    elif "knife" in gemini_description.lower():
                        threat_type = "knife"
                    elif "suspicious" in gemini_description.lower():
                        threat_type = "suspicious object"
                    description = (
                        f"🚨 THREAT: {threat_type.upper()} detected! {description}"
                    )
                    severity = Severity.HIGH
                elif len(gemini_description) < 200:
                    # Add context from Gemini's scene description
                    description = f"{description} | {gemini_description}"

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
                timestamp=current_time,
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

            # Broadcast via WebSocket ONLY for important notifications
            if should_notify:
                await self._broadcast_detection_alert(
                    event, detection_result, notification_reason
                )
                self._last_notification_time = current_time
                logger.info(
                    f"[CAMERA] Notification sent: {description} (reason: {notification_reason})"
                )

            # Store in alert history (always save)
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
        self,
        event: MonitoringEventCreate,
        detection_result: dict,
        notification_reason: str = "",
    ):
        """Broadcast detection alert via WebSocket with smart reasoning"""

        # Ensure we have a description
        base_description = event.description or "Camera Alert"

        # Build smart description with reason
        if notification_reason:
            smart_description = f"{base_description} | {notification_reason}"
        else:
            smart_description = base_description

        alert_data = {
            "type": "detection",
            "event_type": "detection",
            "severity": event.severity.value if event.severity else "MEDIUM",
            "description": smart_description,
            "timestamp": event.timestamp.isoformat()
            if event.timestamp
            else datetime.utcnow().isoformat(),
            "camera_index": self.camera_index,
            "threat_level": detection_result.get("threat_level", "low"),
            "persons_detected": len(detection_result.get("persons", [])),
            "vehicles_detected": len(detection_result.get("vehicles", [])),
            "total_detections": detection_result.get("total_detections", 0),
            "reason": notification_reason or "Activity detected",
        }

        await alert_ws_manager.broadcast_alert(alert_data)
        logger.info(f"[CAMERA] Smart alert broadcast: {smart_description}")
        logger.debug(f"[CAMERA] Full alert data: {alert_data}")

    async def _emit_camera_connected(self) -> None:
        """Emit event when camera is successfully connected and working"""
        # Only send WebSocket notification ONCE per app session
        should_broadcast = not self._has_sent_connected_notification

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

        # Only broadcast via WebSocket once per session (prevents spam)
        if should_broadcast:
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
            self._has_sent_connected_notification = True
            logger.info("[CAMERA] Camera connected notification sent (first time)")
        else:
            logger.info(
                "[CAMERA] Camera reconnected (notification suppressed to prevent spam)"
            )

        # Always add to alert history (for logs/debugging)
        await alert_history.add_alert(
            {
                "camera_id": f"camera_{self.camera_index}",
                "event_type": "camera_connected",
                "description": "Camera connected and working",
                "severity": "LOW",
                "status": "connected",
            }
        )

    async def _emit_camera_unavailable(self, error_message: str) -> None:
        """Emit a system event when camera is not accessible"""
        # Debounce: Only send status notification every 5 minutes
        current_time = datetime.utcnow()
        should_broadcast = True

        if self._last_status_notification_time:
            time_since_last = (
                current_time - self._last_status_notification_time
            ).total_seconds()
            if time_since_last < self._status_notification_cooldown:
                should_broadcast = False
                logger.debug(
                    f"[CAMERA] Unavailable notification debounced ({time_since_last:.0f}s since last)"
                )

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

        # Only broadcast if debouncing allows
        if should_broadcast:
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
            self._last_status_notification_time = current_time

        # Always add to alert history
        await alert_history.add_alert(
            {
                "camera_id": f"camera_{self.camera_index}",
                "event_type": "camera_unavailable",
                "description": error_message,
                "severity": "MEDIUM",
                "status": "unavailable",
            }
        )

        if should_broadcast:
            logger.warning("[CAMERA] Camera unavailable notification sent")
        else:
            logger.debug("[CAMERA] Camera unavailable (notification debounced)")

    async def _emit_camera_disconnected(self) -> None:
        """Emit event when camera disconnects during operation"""
        # Debounce: Only send status notification every 5 minutes
        current_time = datetime.utcnow()
        should_broadcast = True

        if self._last_status_notification_time:
            time_since_last = (
                current_time - self._last_status_notification_time
            ).total_seconds()
            if time_since_last < self._status_notification_cooldown:
                should_broadcast = False
                logger.debug(
                    f"[CAMERA] Disconnected notification debounced ({time_since_last:.0f}s since last)"
                )

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

        # Only broadcast if debouncing allows
        if should_broadcast:
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
            self._last_status_notification_time = current_time

        # Always add to alert history
        await alert_history.add_alert(
            {
                "camera_id": f"camera_{self.camera_index}",
                "event_type": "camera_disconnected",
                "description": "Camera disconnected unexpectedly",
                "severity": "MEDIUM",
                "status": "disconnected",
            }
        )

        if should_broadcast:
            logger.warning("[CAMERA] Camera disconnected notification sent")
        else:
            logger.debug("[CAMERA] Camera disconnected (notification debounced)")

    async def _analyze_scene_with_gemini(self, frame) -> str:
        """
        Use Gemini Vision to analyze the current scene for threats and context.

        This is called when persons are detected by YOLO, but rate-limited
        to avoid excessive API calls (once every 30 seconds max).

        Args:
            frame: OpenCV frame to analyze

        Returns:
            Analysis result string, or empty string if analysis failed
        """
        try:
            from app.vision_tools import analyze_frame_for_threats, describe_scene
            import base64

            # Encode frame to base64
            import cv2

            _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frame_base64 = base64.b64encode(bytes(buffer)).decode("utf-8")

            # First, check for threats
            threat_result = await analyze_frame_for_threats.ainvoke(
                {"frame_base64": frame_base64}
            )

            # If threat detected, use that as the description
            if "THREAT DETECTED" in threat_result:
                self._last_threat_assessment = threat_result
                logger.warning(
                    f"[CAMERA-VISION] Threat detected: {threat_result[:100]}"
                )
                return threat_result

            # Otherwise, get a scene description
            scene_result = await describe_scene.ainvoke({"frame_base64": frame_base64})
            self._last_scene_description = scene_result

            logger.info(f"[CAMERA-VISION] Scene: {scene_result[:80]}...")
            return scene_result

        except Exception as e:
            logger.error(f"[CAMERA-VISION] Gemini analysis failed: {e}")
            # Don't let Gemini failures break the monitoring
            return ""

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
            "last_scene_description": self._last_scene_description,
            "vision_enabled": self._vision_enabled,
            "person_count_history": self._person_count_history[-5:]
            if self._person_count_history
            else [],
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
