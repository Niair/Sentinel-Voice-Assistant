# app/db_models.py

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
import enum

from sqlalchemy import (
    DateTime, Float, Boolean, Text, JSON,
    Enum as SQLEnum, ARRAY
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class MonitoringMode(str, enum.Enum):
    PASSIVE = "PASSIVE"
    ACTIVE = "ACTIVE"


class JobStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EventType(str, enum.Enum):
    MOTION = "motion"
    PERSON = "person"
    VEHICLE = "vehicle"
    ANIMAL = "animal"
    PACKAGE = "package"
    UNKNOWN = "unknown"


class Severity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MonitoringJob(Base):
    __tablename__ = "monitoring_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    chat_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    mode: Mapped[MonitoringMode] = mapped_column(SQLEnum(MonitoringMode), default=MonitoringMode.PASSIVE)
    status: Mapped[JobStatus] = mapped_column(SQLEnum(JobStatus), default=JobStatus.ACTIVE)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)


class MonitoringEvent(Base):
    __tablename__ = "monitoring_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    event_type: Mapped[EventType] = mapped_column(SQLEnum(EventType))
    confidence: Mapped[float] = mapped_column(Float)
    severity: Mapped[Severity] = mapped_column(SQLEnum(Severity))
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)


class MonitoringAlert(Base):
    __tablename__ = "monitoring_alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)

    event_ids: Mapped[List[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    alert_type: Mapped[EventType] = mapped_column(SQLEnum(EventType))
    message: Mapped[str] = mapped_column(Text)
    severity: Mapped[Severity] = mapped_column(SQLEnum(Severity))
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)