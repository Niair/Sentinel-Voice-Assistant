"""
Test script for event system.

Tests the publish/subscribe pattern for monitoring events.
"""

import sys
from pathlib import Path

# Add backend directory to Python path so 'app' module can be imported
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import asyncio
from datetime import datetime

from app.events import publish_event, subscribe_events
from app.models import MonitoringEventCreate, Severity


async def producer():
    """Simulate camera worker publishing events."""
    print("\n📤 PRODUCER: Starting...")
    
    for i in range(3):
        event = MonitoringEventCreate(
            source="test",
            event_type="motion",
            description=f"Test event {i}",
            severity=Severity.MEDIUM,
            confidence=0.85,
            timestamp=datetime.utcnow(),
            metadata={"test_id": i}
        )
        await publish_event(event)
        print(f"✅ Published: {event.description} (severity: {event.severity.value})")
        await asyncio.sleep(0.5)
    
    print("📤 PRODUCER: Finished\n")


async def consumer():
    """Simulate alert processor consuming events."""
    print("\n📥 CONSUMER: Listening for events...")
    
    count = 0
    async for event in subscribe_events():
        print(f"📥 Received: {event.description} | Severity: {event.severity.value} | Confidence: {event.confidence}")
        count += 1
        
        if count >= 3:
            print("📥 CONSUMER: Got 3 events, stopping\n")
            break


async def main():
    """Run producer and consumer concurrently."""
    print("=" * 60)
    print("🧪 EVENT SYSTEM TEST")
    print("=" * 60)
    
    try:
        # Run both tasks concurrently
        await asyncio.gather(
            consumer(),
            producer()
        )
        
        print("=" * 60)
        print("✅ TEST PASSED: Event system working correctly!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())