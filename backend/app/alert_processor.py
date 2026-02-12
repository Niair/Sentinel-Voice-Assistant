# backend/app/alert_processor.py

import logging
from datetime import datetime, timedelta
from typing import Dict

from app.events import subscribe_events
from app.models import MonitoringSeverity, MonitoringEventCreate
from app.alert_store import save_alert

logger = logging.getLogger(__name__)


class AlertProcessor:
    """
    Event consumer that filters and processes monitoring events.
    
    Decision Logic:
    1. Importance filter: Only MEDIUM or HIGH severity
    2. Deduplication: Suppress repeated alerts within cooldown window
    3. Persistence: Save to alert store
    4. Notification: Emit to frontend (via logging/websocket/etc.)
    """

    def __init__(self, cooldown_seconds: int = 60) -> None:
        """
        Initialize alert processor.
        
        Args:
            cooldown_seconds: Minimum time between duplicate alerts (default: 60s)
        """
        # Tracks last alert time per description (for deduplication)
        self._cooldown: Dict[str, datetime] = {}
        self.cooldown_window = timedelta(seconds=cooldown_seconds)
        
        logger.info("AlertProcessor initialized (cooldown: %ds)", cooldown_seconds)

    async def start(self) -> None:
        """
        Start listening for monitoring events.
        
        This is the main event loop. It runs indefinitely, processing
        events as they arrive from the event bus.
        
        BUG FIX:
            ❌ OLD: Had TWO `start()` methods (duplicate!)
            ✅ NEW: Single clean implementation
        """
        logger.info("Alert processor started — listening for events...")

        async for event in subscribe_events():
            try:
                await self._handle_event(event)
            except Exception as exc:
                logger.exception("Alert processing failed: %s", exc)
                # Don't crash the processor — keep listening

    async def _handle_event(self, event: MonitoringEventCreate) -> None:
        """
        Main decision logic for a single event.
        
        Flow:
        1. Check importance (severity filter)
        2. Check for duplicates (cooldown check)
        3. Save to persistent store
        4. Emit notification
        5. Update cooldown tracker
        """
        # Step 1: Filter by importance
        if not self._is_important(event):
            logger.debug("Ignored unimportant event: %s", event.description)
            return

        # Step 2: Suppress duplicates
        if self._is_duplicate(event):
            logger.debug("Duplicate alert suppressed: %s", event.description)
            return

        # Step 3: Persist to alert store
        await save_alert(event)  # ✅ FIX: save_alert is now async

        # Step 4: Notify user (frontend handles UI)
        await self._emit_notification(event)

        # Step 5: Update cooldown to prevent immediate duplicates
        self._cooldown[event.description] = datetime.utcnow()

    def _is_important(self, event: MonitoringEventCreate) -> bool:
        """
        Filter events by severity.
        
        Only MEDIUM and HIGH severity events become alerts.
        LOW severity events are ignored (too noisy).
        
        Args:
            event: The event to evaluate
        
        Returns:
            True if event should trigger an alert
        """
        return event.severity in {MonitoringSeverity.HIGH, MonitoringSeverity.MEDIUM}

    def _is_duplicate(self, event: MonitoringEventCreate) -> bool:
        """
        Check if this alert was recently sent.
        
        Prevents alert spam by suppressing identical alerts
        within the cooldown window.
        
        Args:
            event: The event to check
        
        Returns:
            True if this is a duplicate (should be suppressed)
        """
        last_time = self._cooldown.get(event.description)
        if not last_time:
            return False  # Never seen before

        time_since_last = datetime.utcnow() - last_time
        return time_since_last < self.cooldown_window

    async def _emit_notification(self, event: MonitoringEventCreate) -> None:
        """
        Emit a user-facing notification.
        
        Current implementation: Logs to console.
        
        Future enhancements:
        - WebSocket push to frontend
        - Email/SMS notifications
        - Push notifications (mobile app)
        
        Args:
            event: The alert event to notify about
        """
        logger.info(
            "🚨 ALERT: %s | Severity: %s | Confidence: %.2f",
            event.description,
            event.severity.value,
            event.confidence,
        )
        # Frontend can subscribe to these logs or use a WebSocket connection