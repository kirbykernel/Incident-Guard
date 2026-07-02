# ============================================================
# IncidentGuard — rotas de incidentes
# GET    /incidents          → lista paginada
# POST   /incidents          → cria incidente manual
# GET    /incidents/{id}     → detalhe
# PATCH  /incidents/{id}     → atualiza status/campos
# ============================================================

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import Incident, Source, Status
from app.schemas.schemas import (
    IncidentCreate,
    IncidentListResponse,
    IncidentResponse,
    IncidentUpdate,
)

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=IncidentListResponse)
async def list_incidents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    severity: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    """
    Lista incidentes com paginação e filtros opcionais.
    Requer autenticação JWT.
    """
    query = select(Incident).order_by(Incident.created_at.desc())

    if severity:
        query = query.where(Incident.severity == severity)
    if status_filter:
        query = query.where(Incident.status == status_filter)

    # Total para paginação
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    # Página atual
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    incidents = result.scalars().all()

    return IncidentListResponse(
        items=incidents,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(
    body: IncidentCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Cria incidente manual.
    O criador é o usuário autenticado via JWT.
    """
    incident = Incident(
        title=body.title,
        description=body.description,
        severity=body.severity,
        source=Source.MANUAL,
        created_by=uuid.UUID(user_id),
        assigned_to=body.assigned_to,
    )
    db.add(incident)
    await db.flush()
    await db.refresh(incident)
    return incident


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    """Retorna detalhe de um incidente pelo ID."""
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()

    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente não encontrado")

    return incident


@router.patch("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: uuid.UUID,
    body: IncidentUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    """
    Atualiza campos de um incidente.
    Ao resolver (status=resolved), registra resolved_at automaticamente.
    """
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()

    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente não encontrado")

    update_data = body.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(incident, field, value)

    # Registra timestamp de resolução automaticamente
    if body.status == Status.RESOLVED and not incident.resolved_at:
        incident.resolved_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(incident)
    return incident
