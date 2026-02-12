import enum
from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field


# ==============================================================================
# ENUMS
# ==============================================================================

class MonitoringMode(str, enum.Enum):
    """Monitoring mode for jobs."""
    PASSIVE = "PASSIVE"
    ACTIVE = "ACTIVE"


class JobStatus(str, enum.Enum):
    """Job execution status."""
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EventType(str, enum.Enum):
    """Detection event types from vision model."""
    MOTION = "motion"
    PERSON = "person"
    VEHICLE = "vehicle"
    ANIMAL = "animal"
    PACKAGE = "package"
    UNKNOWN = "unknown"


class MonitoringSeverity(str, enum.Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Alias for backwards compatibility (some code uses 'Severity')
Severity = MonitoringSeverity


# ==============================================================================
# PYDANTIC SCHEMAS (Data Transfer Objects)
# ==============================================================================

class MonitoringEventCreate(BaseModel):
    """
    Lightweight event schema emitted by monitoring workers.
    
    Not all events are persisted to the database — the AlertProcessor
    filters based on severity and deduplication rules.
    
    Used by:
    - MonitoringWorker (camera monitoring)
    - Event bus (publish/subscribe)
    - AlertProcessor (filtering)
    """
    source: str = Field(default="camera", description="Event source (e.g., 'camera', 'system')")
    event_type: str = Field(default="unknown", description="Type of detection")
    description: str = Field(..., description="Human-readable event description")
    severity: MonitoringSeverity = Field(..., description="Event severity level")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Model confidence (0-1)")
    timestamp: datetime = Field(..., description="When the event occurred")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional event data")

    class Config:
        json_schema_extra = {
            "example": {
                "source": "camera",
                "event_type": "motion",
                "description": "Movement detected in living room",
                "severity": "medium",
                "confidence": 0.87,
                "timestamp": "2025-02-12T14:30:00Z",
                "metadata": {"camera_index": 0, "bbox": [100, 200, 300, 400]}
            }
        }


class MonitoringEventResponse(BaseModel):
    """
    Event schema returned by API endpoints.
    Includes database fields like ID.
    """
    id: str
    source: str
    event_type: str
    description: str
    severity: MonitoringSeverity
    confidence: float
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class AlertResponse(BaseModel):
    """
    Alert schema for API responses.
    """
    id: str
    job_id: str
    alert_type: EventType
    message: str
    severity: MonitoringSeverity
    timestamp: datetime
    acknowledged: bool
    metadata: Optional[Dict[str, Any]] = None