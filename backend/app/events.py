"""
Event bus abstraction for monitoring system.
Supports in-process asyncio.Queue (default) and Redis (configurable).

Architecture:
- Monitoring sub-agent publishes events
- Alert notification system consumes events
- Non-blocking, fully async
"""

import asyncio
import json
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum


class EventType(str, Enum):
    """Event types for monitoring system"""
    MOTION_DETECTED = "motion_detected"
    PERSON_DETECTED = "person_detected"
    VEHICLE_DETECTED = "vehicle_detected"
    ALERT_CREATED = "alert_created"
    MODE_CHANGED = "mode_changed"
    JOB_STARTED = "job_started"
    JOB_STOPPED = "job_stopped"


@dataclass
class MonitoringEvent:
    """
    Standard event format for monitoring system.
    All events follow this schema.
    """
    event_type: str  # EventType enum value
    job_id: str
    timestamp: str  # ISO 8601 format
    data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MonitoringEvent":
        """Create event from dictionary"""
        return cls(**data)
    
    def to_json(self) -> str:
        """Serialize to JSON string"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> "MonitoringEvent":
        """Deserialize from JSON string"""
        return cls.from_dict(json.loads(json_str))


class EventBus(ABC):
    """Abstract event bus interface"""
    
    @abstractmethod
    async def publish(self, event: MonitoringEvent) -> None:
        """Publish an event to the bus"""
        pass
    
    @abstractmethod
    async def subscribe(
        self,
        event_types: list[str],
        callback: Callable[[MonitoringEvent], Awaitable[None]]
    ) -> None:
        """Subscribe to specific event types"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close connections and cleanup"""
        pass


class InProcessEventBus(EventBus):
    """
    In-process event bus using asyncio.Queue.
    Suitable for single-instance deployments and development.
    """
    
    def __init__(self, maxsize: int = 1000):
        self.queue: asyncio.Queue[MonitoringEvent] = asyncio.Queue(maxsize=maxsize)
        self.subscribers: Dict[str, list[Callable]] = {}
        self.running = False
        self._dispatch_task: Optional[asyncio.Task] = None
    
    async def publish(self, event: MonitoringEvent) -> None:
        """Publish event to queue (non-blocking)"""
        try:
            await self.queue.put(event)
        except asyncio.QueueFull:
            print(f"⚠️ Event queue full, dropping event: {event.event_type}")
    
    async def subscribe(
        self,
        event_types: list[str],
        callback: Callable[[MonitoringEvent], Awaitable[None]]
    ) -> None:
        """Register callback for specific event types"""
        for event_type in event_types:
            if event_type not in self.subscribers:
                self.subscribers[event_type] = []
            self.subscribers[event_type].append(callback)
        
        # Start dispatch loop if not already running
        if not self.running:
            await self.start()
    
    async def start(self) -> None:
        """Start event dispatcher"""
        if self.running:
            return
        
        self.running = True
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())
        print("✅ In-process event bus started")
    
    async def _dispatch_loop(self) -> None:
        """Internal event dispatch loop"""
        while self.running:
            try:
                # Wait for event with timeout to allow graceful shutdown
                event = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                
                # Dispatch to subscribers
                callbacks = self.subscribers.get(event.event_type, [])
                for callback in callbacks:
                    try:
                        await callback(event)
                    except Exception as e:
                        print(f"❌ Error in event callback: {e}")
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"❌ Error in dispatch loop: {e}")
                await asyncio.sleep(1)
    
    async def close(self) -> None:
        """Stop dispatcher and clear queue"""
        self.running = False
        if self._dispatch_task:
            await self._dispatch_task
        print("✅ In-process event bus stopped")


class RedisEventBus(EventBus):
    """
    Redis-based event bus using pub/sub.
    Suitable for multi-instance deployments.
    
    TODO: Implement when scaling is needed.
    Requires: redis[asyncio] package
    """
    
    def __init__(self, redis_url: str):
        raise NotImplementedError(
            "Redis event bus not yet implemented. "
            "Use InProcessEventBus for now."
        )
    
    async def publish(self, event: MonitoringEvent) -> None:
        raise NotImplementedError()
    
    async def subscribe(
        self,
        event_types: list[str],
        callback: Callable[[MonitoringEvent], Awaitable[None]]
    ) -> None:
        raise NotImplementedError()
    
    async def close(self) -> None:
        raise NotImplementedError()


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """
    Get or create the global event bus instance.
    
    Configuration via environment:
    - EVENT_BUS_TYPE=in_process (default)
    - EVENT_BUS_TYPE=redis (requires REDIS_URL)
    """
    global _event_bus
    
    if _event_bus is None:
        bus_type = os.getenv("EVENT_BUS_TYPE", "in_process")
        
        if bus_type == "redis":
            redis_url = os.getenv("REDIS_URL")
            if not redis_url:
                raise ValueError("REDIS_URL required for redis event bus")
            _event_bus = RedisEventBus(redis_url)
        else:
            _event_bus = InProcessEventBus()
    
    return _event_bus


async def close_event_bus() -> None:
    """Close the global event bus"""
    global _event_bus
    if _event_bus:
        await _event_bus.close()
        _event_bus = None