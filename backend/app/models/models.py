# ============================================================
# IncidentGuard — models SQLAlchemy
# Reflete exatamente o diagrama de classes UML.
# ============================================================

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey,
    String, Text, JSON, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ----------------------------------------------------------
# Enumerações (espelham o diagrama UML)
# ----------------------------------------------------------

class Role(str, PyEnum):
    ADMIN   = "admin"
    ANALYST = "analyst"
    VIEWER  = "viewer"


class Severity(str, PyEnum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"


class Status(str, PyEnum):
    OPEN        = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED    = "resolved"
    CLOSED      = "closed"


class Source(str, PyEnum):
    ALERTMANAGER     = "alertmanager"
    SECURITY_SCANNER = "security_scanner"
    FALCO            = "falco"
    SYNTHETIC        = "synthetic"
    MANUAL           = "manual"


# ----------------------------------------------------------
# Tabela: users
# ----------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(
        Enum(Role, name="role_enum"), nullable=False, default=Role.VIEWER
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relacionamentos
    created_incidents: Mapped[list["Incident"]] = relationship(
        "Incident", foreign_keys="Incident.created_by", back_populates="creator"
    )
    assigned_incidents: Mapped[list["Incident"]] = relationship(
        "Incident", foreign_keys="Incident.assigned_to", back_populates="assignee"
    )


# ----------------------------------------------------------
# Tabela: incidents
# ----------------------------------------------------------

class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, name="severity_enum"), nullable=False
    )
    status: Mapped[Status] = mapped_column(
        Enum(Status, name="status_enum"), nullable=False, default=Status.OPEN
    )
    source: Mapped[Source] = mapped_column(
        Enum(Source, name="source_enum"), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relacionamentos
    creator: Mapped["User | None"] = relationship(
        "User", foreign_keys=[created_by], back_populates="created_incidents"
    )
    assignee: Mapped["User | None"] = relationship(
        "User", foreign_keys=[assigned_to], back_populates="assigned_incidents"
    )
    webhook_event: Mapped["WebhookEvent | None"] = relationship(
        "WebhookEvent", back_populates="incident", uselist=False
    )


# ----------------------------------------------------------
# Tabela: api_keys
# ----------------------------------------------------------

class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    service: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    webhook_events: Mapped[list["WebhookEvent"]] = relationship(
        "WebhookEvent", back_populates="api_key"
    )


# ----------------------------------------------------------
# Tabela: webhook_events
# ----------------------------------------------------------

class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True
    )
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    incident: Mapped["Incident | None"] = relationship(
        "Incident", back_populates="webhook_event"
    )
    api_key: Mapped["APIKey | None"] = relationship(
        "APIKey", back_populates="webhook_events"
    )
