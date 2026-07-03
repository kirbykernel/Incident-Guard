# ============================================================
# IncidentGuard — schemas Pydantic v2
# Separa o contrato da API (schemas) dos models do banco.
# Nunca exponha o model SQLAlchemy diretamente em rotas.
# ============================================================

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, field_validator, ConfigDict

from app.models.models import Role, Severity, Source, Status


# ----------------------------------------------------------
# Auth
# ----------------------------------------------------------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Senha não pode ser vazia")
        return v


# ----------------------------------------------------------
# User
# ----------------------------------------------------------

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: Role = Role.VIEWER

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Senha deve ter ao menos 8 caracteres")
        return v


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: Role
    is_active: bool
    created_at: datetime


# ----------------------------------------------------------
# Incident
# ----------------------------------------------------------

class IncidentCreate(BaseModel):
    title: str
    description: str | None = None
    severity: Severity
    source: Source = Source.MANUAL
    assigned_to: uuid.UUID | None = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Título não pode ser vazio")
        return v.strip()


class IncidentUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    severity: Severity | None = None
    status: Status | None = None
    assigned_to: uuid.UUID | None = None


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    severity: Severity
    status: Status
    source: Source
    created_by: uuid.UUID | None
    assigned_to: uuid.UUID | None
    created_at: datetime
    resolved_at: datetime | None


class IncidentListResponse(BaseModel):
    items: list[IncidentResponse]
    total: int
    page: int
    page_size: int


# ----------------------------------------------------------
# Webhook — Alertmanager
# ----------------------------------------------------------

class AlertmanagerAlert(BaseModel):
    """Estrutura de um alerta individual do Alertmanager."""
    status: str                          # "firing" ou "resolved"
    labels: dict[str, str]
    annotations: dict[str, str] = {}
    startsAt: datetime
    endsAt: datetime | None = None
    generatorURL: str = ""


class AlertmanagerWebhook(BaseModel):
    """Payload completo enviado pelo Alertmanager."""
    version: str
    groupKey: str
    status: str
    receiver: str
    alerts: list[AlertmanagerAlert]
    commonLabels: dict[str, str] = {}
    commonAnnotations: dict[str, str] = {}


# ----------------------------------------------------------
# Webhook — Security Scanner (Trivy, Gitleaks, OPA)
# ----------------------------------------------------------

class SecurityWebhook(BaseModel):
    """Payload de eventos de segurança dos scanners."""
    source: str                          # "trivy", "gitleaks", "opa"
    severity: Severity
    title: str
    description: str | None = None
    resource: str | None = None          # imagem, arquivo, policy
    metadata: dict[str, Any] = {}


# ----------------------------------------------------------
# Webhook — Falco
# ----------------------------------------------------------

class FalcoWebhook(BaseModel):
    """Payload de evento de runtime do Falco."""
    rule: str
    priority: str
    output: str
    output_fields: dict[str, Any] = {}
    time: datetime


# ----------------------------------------------------------
# WebhookEvent
# ----------------------------------------------------------

class WebhookEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    processed: bool
    incident_id: uuid.UUID | None
    received_at: datetime


# ----------------------------------------------------------
# Health check
# ----------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    environment: str
    version: str = "1.0.0"