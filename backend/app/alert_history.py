"""
Alert History Manager
Stores and retrieves alert history with filtering capabilities
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import json
from pathlib import Path
import asyncio


class AlertHistory:
    """
    In-memory alert history storage with optional persistence.

    Features:
    - Store alerts with timestamps
    - Filter by time range, severity, camera
    - Automatic cleanup of old alerts
    - JSON persistence for reload
    """

    def __init__(self, max_history: int = 1000, persist_file: Optional[str] = None):
        """
        Initialize alert history

        Args:
            max_history: Maximum number of alerts to keep in memory
            persist_file: Optional file path to persist alerts (None = memory only)
        """
        self.alerts: List[Dict[str, Any]] = []
        self.max_history = max_history
        self.persist_file = Path(persist_file) if persist_file else None
        self._lock = asyncio.Lock()

        # Load persisted alerts if available
        if self.persist_file and self.persist_file.exists():
            self._load_from_file()

    async def add_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add new alert to history

        Args:
            alert: Alert dictionary with event details

        Returns:
            Alert with added timestamp and ID
        """
        async with self._lock:
            # Add metadata
            enriched_alert = {
                **alert,
                "id": f"alert_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}",
                "timestamp": datetime.utcnow().isoformat(),
                "received_at": datetime.utcnow().isoformat(),
            }

            self.alerts.append(enriched_alert)

            # Cleanup old alerts if exceeded max (silently)
            if len(self.alerts) > self.max_history:
                self.alerts.pop(0)

            # Persist to file if configured
            if self.persist_file:
                await self._save_to_file()

            return enriched_alert

    async def get_alerts(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        severity: Optional[str] = None,
        camera_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Query alert history with filters

        Args:
            start_time: Filter alerts after this time
            end_time: Filter alerts before this time
            severity: Filter by severity level (LOW, MEDIUM, HIGH)
            camera_id: Filter by specific camera
            limit: Maximum number of alerts to return
            offset: Number of alerts to skip (for pagination)

        Returns:
            List of matching alerts (most recent first)
        """
        async with self._lock:
            filtered = self.alerts.copy()

            # Apply filters
            if start_time:
                filtered = [
                    a
                    for a in filtered
                    if datetime.fromisoformat(a["timestamp"]) >= start_time
                ]

            if end_time:
                filtered = [
                    a
                    for a in filtered
                    if datetime.fromisoformat(a["timestamp"]) <= end_time
                ]

            if severity:
                filtered = [
                    a
                    for a in filtered
                    if a.get("severity", "").upper() == severity.upper()
                ]

            if camera_id:
                filtered = [a for a in filtered if a.get("camera_id") == camera_id]

            # Sort by timestamp (newest first) and apply pagination
            filtered.sort(key=lambda x: x["timestamp"], reverse=True)

            return filtered[offset : offset + limit]

    async def get_recent_alerts(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get alerts from last N minutes"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        return await self.get_alerts(start_time=cutoff_time, limit=1000)

    async def get_stats(self) -> Dict[str, Any]:
        """Get alert statistics"""
        async with self._lock:
            total = len(self.alerts)

            # Count by severity
            severity_counts = {}
            for alert in self.alerts:
                sev = alert.get("severity", "UNKNOWN")
                severity_counts[sev] = severity_counts.get(sev, 0) + 1

            # Last alert time
            last_alert = self.alerts[-1]["timestamp"] if self.alerts else None

            return {
                "total_alerts": total,
                "severity_breakdown": severity_counts,
                "last_alert": last_alert,
                "max_history": self.max_history,
            }

    async def clear_old_alerts(self, days: int = 7):
        """Remove alerts older than specified days"""
        async with self._lock:
            cutoff = datetime.utcnow() - timedelta(days=days)
            original_count = len(self.alerts)
            self.alerts = [
                a
                for a in self.alerts
                if datetime.fromisoformat(a["timestamp"]) >= cutoff
            ]
            removed = original_count - len(self.alerts)
            print(f"[INFO] Cleared {removed} alerts older than {days} days")

            if self.persist_file:
                await self._save_to_file()

    async def _save_to_file(self):
        """Persist alerts to file"""
        if not self.persist_file:
            return

        try:
            with open(self.persist_file, "w") as f:
                json.dump(self.alerts, f, indent=2)
        except Exception as e:
            print(f"[WARNING] Failed to save alerts to file: {e}")

    def _load_from_file(self):
        """Load alerts from file"""
        try:
            with open(self.persist_file, "r") as f:
                self.alerts = json.load(f)
            print(f"[INFO] Loaded {len(self.alerts)} alerts from {self.persist_file}")
        except Exception as e:
            print(f"[WARNING] Failed to load alerts from file: {e}")
            self.alerts = []


# Singleton instance
alert_history = AlertHistory(
    max_history=1000, persist_file="uploads/alert_history.json"
)
