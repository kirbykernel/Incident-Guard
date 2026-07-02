# ============================================================
# IncidentGuard — rotas de webhooks
# POST /webhooks/alertmanager      → recebe alertas do Prometheus
# POST /webhooks/security          → recebe eventos de Trivy/Gitleaks/OPA
# POST /webhooks/falco             → recebe eventos de runtime do Falco
#
# Autenticação: header X-API-Key (não JWT — são serviços, não humanos)
# ============================================================

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.settings import get_settings
from app.models.models import Incident, Severity, Source, WebhookEvent
from app.schemas.schemas import (
    AlertmanagerWebhook,
    FalcoWebhook,
    SecurityWebhook,
    WebhookEventResponse,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
settings = get_settings()


# ----------------------------------------------------------
# Validação de API Key (dependência compartilhada)
# ----------------------------------------------------------

def _validate_api_key(expected: str, received: str | None) -> None:
    """Valida API Key de forma segura. Levanta 401 se inválida."""
    if not received or received != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida ou ausente",
        )


# ----------------------------------------------------------
# Alertmanager
# ----------------------------------------------------------

@router.post(
    "/alertmanager",
    response_model=WebhookEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def alertmanager_webhook(
    body: AlertmanagerWebhook,
    x_api_key: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Recebe payload do Alertmanager e cria incidente para alertas "firing".
    Alertas "resolved" são registrados mas não criam novos incidentes.
    """
    _validate_api_key(settings.ALERTMANAGER_API_KEY, x_api_key)

    # Mapeia severity do Alertmanager para o nosso enum
    severity_map = {
        "critical": Severity.CRITICAL,
        "high":     Severity.HIGH,
        "warning":  Severity.MEDIUM,
        "info":     Severity.LOW,
    }

    incident_id = None

    # Cria incidente apenas para alertas ativos
    firing_alerts = [a for a in body.alerts if a.status == "firing"]

    if firing_alerts:
        first = firing_alerts[0]
        raw_severity = first.labels.get("severity", "info").lower()
        severity = severity_map.get(raw_severity, Severity.LOW)

        title = first.annotations.get("summary") or first.labels.get("alertname", "Alerta sem título")
        description = first.annotations.get("description")

        incident = Incident(
            title=title,
            description=description,
            severity=severity,
            source=Source.ALERTMANAGER,
        )
        db.add(incident)
        await db.flush()
        incident_id = incident.id

    # Registra o evento bruto independente de criar incidente
    event = WebhookEvent(
        source="alertmanager",
        payload=body.model_dump(mode="json"),
        processed=True,
        incident_id=incident_id,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


# ----------------------------------------------------------
# Security Scanner (Trivy, Gitleaks, OPA/Gatekeeper)
# ----------------------------------------------------------

@router.post(
    "/security",
    response_model=WebhookEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def security_webhook(
    body: SecurityWebhook,
    x_api_key: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Recebe eventos de segurança dos scanners do pipeline CI/CD.
    Cria incidente para severidades CRITICAL e HIGH automaticamente.
    """
    _validate_api_key(settings.SECURITY_SCANNER_API_KEY, x_api_key)

    incident_id = None

    # Apenas crítico e alto geram incidente automático
    if body.severity in (Severity.CRITICAL, Severity.HIGH):
        incident = Incident(
            title=body.title,
            description=body.description,
            severity=body.severity,
            source=Source.SECURITY_SCANNER,
        )
        db.add(incident)
        await db.flush()
        incident_id = incident.id

    event = WebhookEvent(
        source=body.source,
        payload=body.model_dump(mode="json"),
        processed=True,
        incident_id=incident_id,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


# ----------------------------------------------------------
# Falco — runtime security
# ----------------------------------------------------------

@router.post(
    "/falco",
    response_model=WebhookEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def falco_webhook(
    body: FalcoWebhook,
    x_api_key: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Recebe eventos de comportamento anômalo em runtime detectados pelo Falco.
    """
    _validate_api_key(settings.FALCO_API_KEY, x_api_key)

    # Mapeia prioridade do Falco para severity
    priority_map = {
        "EMERGENCY": Severity.CRITICAL,
        "ALERT":     Severity.CRITICAL,
        "CRITICAL":  Severity.CRITICAL,
        "ERROR":     Severity.HIGH,
        "WARNING":   Severity.MEDIUM,
        "NOTICE":    Severity.LOW,
        "INFO":      Severity.LOW,
        "DEBUG":     Severity.LOW,
    }
    severity = priority_map.get(body.priority.upper(), Severity.MEDIUM)

    incident = Incident(
        title=f"[Falco] {body.rule}",
        description=body.output,
        severity=severity,
        source=Source.FALCO,
    )
    db.add(incident)
    await db.flush()

    event = WebhookEvent(
        source="falco",
        payload=body.model_dump(mode="json"),
        processed=True,
        incident_id=incident.id,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event
