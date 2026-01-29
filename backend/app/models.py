"""
SQLAlchemy models for monitoring system.
Defines tables: monitoring_jobs, monitoring_events, monitoring_alerts
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    String, DateTime, Float, Boolean, Text, JSON, Enum as SQLEnum, ARRAY
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.database import Base


class MonitoringMode(str, enum.Enum):
    """Monitoring mode enum"""
    PASSIVE = "PASSIVE"
    ACTIVE = "ACTIVE"


class JobStatus(str, enum.Enum):
    """Job status enum"""
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EventType(str, enum.Enum):
    """Event detection type"""
    MOTION = "motion"
    PERSON = "person"
    VEHICLE = "vehicle"
    ANIMAL = "animal"
    PACKAGE = "package"
    UNKNOWN = "unknown"


class Severity(str, enum.Enum):
    """Alert severity level"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MonitoringJob(Base):
    """
    Tracks monitoring sessions (both PASSIVE and ACTIVE modes).
    A job represents a monitoring session with specific configuration.
    """
    __tablename__ = "monitoring_jobs"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    chat_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    
    mode: Mapped[MonitoringMode] = mapped_column(
        SQLEnum(MonitoringMode),
        nullable=False,
        default=MonitoringMode.PASSIVE
    )
    
    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    
    ends_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="For timed monitoring (e.g., 'monitor for 15 minutes')"
    )
    
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus),
        nullable=False,
        default=JobStatus.ACTIVE
    )
    
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Camera settings, detection thresholds, device IDs, etc."
    )
    
    def __repr__(self) -> str:
        return f"<MonitoringJob(id={self.id}, mode={self.mode}, status={self.status})>"


class MonitoringEvent(Base):
    """
    Raw detection events from vision model.
    High-frequency writes (multiple per second during detection).
    """
    __tablename__ = "monitoring_events"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="FK to monitoring_jobs (not enforced for performance)"
    )
    
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    
    event_type: Mapped[EventType] = mapped_column(
        SQLEnum(EventType),
        nullable=False
    )
    
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Model confidence score (0.0 - 1.0)"
    )
    
    severity: Mapped[Severity] = mapped_column(
        SQLEnum(Severity),
        nullable=False,
        default=Severity.LOW
    )
    
    event_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata",  # Column name in database stays "metadata"
        JSON,
        nullable=True,
        comment="bbox, frame_url, device_id, clip_path, etc."
    )
    
    def __repr__(self) -> str:
        return f"<MonitoringEvent(id={self.id}, type={self.event_type}, conf={self.confidence})>"


class MonitoringAlert(Base):
    """
    User-facing alerts (deduplicated and aggregated from events).
    Created only when:
    1. Mode is ACTIVE
    2. Severity threshold is met
    3. Temporal consensus is achieved
    """
    __tablename__ = "monitoring_alerts"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )
    
    event_ids: Mapped[List[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        nullable=False,
        comment="Source event IDs that triggered this alert"
    )
    
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    
    alert_type: Mapped[EventType] = mapped_column(
        SQLEnum(EventType),
        nullable=False
    )
    
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Human-readable alert message"
    )
    
    severity: Mapped[Severity] = mapped_column(
        SQLEnum(Severity),
        nullable=False
    )
    
    acknowledged: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    
    chat_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Chat thread where alert was sent (if any)"
    )
    
    event_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata",  # Column name in database stays "metadata"
        JSON,
        nullable=True,
        comment="Frame URLs, clip URLs, detection details, etc."
    )
    
    def __repr__(self) -> str:
        return f"<MonitoringAlert(id={self.id}, type={self.alert_type}, severity={self.severity})>"