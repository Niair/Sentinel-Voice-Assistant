# backend/app/events.py

import asyncio
import logging
from typing import AsyncIterator

from app.models import MonitoringEventCreate

logger = logging.getLogger(__name__)

# In-process async event queue
# LIMITATION: Works only within a single process. For distributed systems,
# replace with Redis Streams, Kafka, or RabbitMQ.
_event_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)  # Prevent memory overflow


# ==============================================================================
# PUBLIC API
# ==============================================================================

async def publish_event(event: MonitoringEventCreate) -> None:
    """
    Publish a monitoring event to the event bus.
    
    This is a non-blocking operation. Events are queued and consumed
    asynchronously by subscribers (e.g., AlertProcessor).
    
    Args:
        event: The monitoring event to publish
    
    Raises:
        asyncio.QueueFull: If queue is full (should rarely happen with maxsize=1000)
    
    Example:
        event = MonitoringEventCreate(
            source="camera",
            event_type="motion",
            description="Movement detected",
            severity=Severity.MEDIUM,
            timestamp=datetime.utcnow()
        )
        await publish_event(event)
    """
    try:
        await _event_queue.put(event)
        logger.debug("Event published: %s", event.description)
    except asyncio.QueueFull:
        logger.error("Event queue is full! Dropping event: %s", event.description)
        # In production, this should trigger an alert


# ==============================================================================
# SUBSCRIPTIONS
# ==============================================================================

async def subscribe_events() -> AsyncIterator[MonitoringEventCreate]:
    """
    Subscribe to the event stream.
    
    This is an async generator that yields events indefinitely.
    Consumers iterate over it in an infinite loop.
    
    BUG FIX:
        ❌ OLD (BROKEN): `return await _event_queue.get()`
           - This returns a SINGLE event, not a generator
           - Loop in AlertProcessor would only process one event then exit
        
        ✅ NEW (CORRECT): `while True: yield await _event_queue.get()`
           - Proper async generator
           - Yields events one at a time, forever
    
    Usage:
        async for event in subscribe_events():
            print(f"Received: {event.description}")
            # Process event...
    
    Yields:
        MonitoringEventCreate: Events as they arrive in the queue
    """
    while True:
        event = await _event_queue.get()
        yield event

# ==============================================================================
# UTILITIES (For Testing)
# ==============================================================================

def queue_size() -> int:
    """Return current number of events in queue (for monitoring)."""
    return _event_queue.qsize()


def is_queue_empty() -> bool:
    """Check if event queue is empty."""
    return _event_queue.empty()