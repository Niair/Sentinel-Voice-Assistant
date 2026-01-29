# Test Event Bus
import asyncio
from app.events import get_event_bus, MonitoringEvent, EventType

async def test():
    bus = get_event_bus()
    
    # Publisher
    event = MonitoringEvent(
        event_type=EventType.PERSON_DETECTED,
        job_id="test-job-123",
        timestamp="2026-01-29T12:00:00Z",
        data={"confidence": 0.85}
    )
    await bus.publish(event)
    
    # Subscriber
    async def handler(e: MonitoringEvent):
        print(f"Received: {e.event_type} - {e.data}")
    
    await bus.subscribe([EventType.PERSON_DETECTED], handler)
    await asyncio.sleep(2)
    
asyncio.run(test())