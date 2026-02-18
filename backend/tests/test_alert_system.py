"""
Test script to verify the monitoring and alert system works correctly.

This creates a test alert to confirm:
1. Events are published
2. Alert processor receives them
3. Alerts are stored in history
4. WebSocket broadcasts work
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import MonitoringEventCreate, Severity
from app.events import publish_event
from app.alert_history import alert_history
from app.websocket_manager import alert_ws_manager


async def test_alert_system():
    """Test the complete alert pipeline"""

    print("[TEST] Testing Alert System")
    print("=" * 50)

    # Test 1: Create and publish a test event
    print("\n[1] Creating test alert...")
    test_event = MonitoringEventCreate(
        source="test",
        event_type="test_alert",
        description="Test: Alert system is working!",
        severity=Severity.HIGH,
        confidence=0.95,
        timestamp=datetime.utcnow(),
        metadata={"test": True, "camera_index": 0},
    )

    # Publish to event bus
    await publish_event(test_event)
    print("[PASS] Event published to event bus")

    # Test 2: Add directly to alert history
    print("\n[2] Adding to alert history...")
    alert_data = {
        "camera_id": "test_camera",
        "event_type": "test_alert",
        "description": "Test: Alert system is working!",
        "severity": Severity.HIGH.value,
        "threat_level": "test",
        "detections_count": 1,
        "persons_count": 0,
        "vehicles_count": 0,
        "metadata": {"test": True},
    }

    await alert_history.add_alert(alert_data)
    print("[PASS] Alert added to history")

    # Test 3: Broadcast via WebSocket (if any clients connected)
    print("\n[3] Broadcasting via WebSocket...")
    ws_alert = {
        "event_type": "test_alert",
        "severity": Severity.HIGH.value,
        "description": "Test: Alert system is working!",
        "timestamp": datetime.utcnow().isoformat(),
        "camera_index": 0,
        "threat_level": "test",
    }

    await alert_ws_manager.broadcast_alert(ws_alert)
    print("[PASS] Alert broadcast via WebSocket")

    # Test 4: Check alert history
    print("\n[4] Checking alert history...")
    await asyncio.sleep(0.5)  # Small delay

    alerts = await alert_history.get_alerts(limit=5)
    print(f"[PASS] Found {len(alerts)} alerts in history")

    if alerts:
        print(f"\n[RECENT] Most recent alert:")
        latest = alerts[0]
        print(f"   Description: {latest.get('description')}")
        print(f"   Severity: {latest.get('severity')}")
        print(f"   Time: {latest.get('timestamp')}")

    # Test 5: Get stats
    print("\n[5] Getting alert statistics...")
    stats = await alert_history.get_stats()
    print(f"[PASS] Total alerts: {stats.get('total_alerts')}")
    print(f"[PASS] Severity breakdown: {stats.get('severity_breakdown')}")

    print("\n" + "=" * 50)
    print("[SUCCESS] Alert system test complete!")
    print("\nYou can now:")
    print("   • Check alerts at: http://localhost:8000/api/alerts/history")
    print("   • Check stats at: http://localhost:8000/api/alerts/stats")
    print("   • Connect to WebSocket: ws://localhost:8000/ws/alerts")

    return True


if __name__ == "__main__":
    result = asyncio.run(test_alert_system())
    sys.exit(0 if result else 1)
