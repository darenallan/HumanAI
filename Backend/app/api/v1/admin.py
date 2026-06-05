"""
admin.py (API)
--------------
Endpoints pour l'administration et la supervision de la sécurité (logs d'audit, alertes, etc.).
"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import require_roles
from app.schemas.users import UserOut
from app.models.logs import AuditLog, AISecurityEvent, AIInteraction
from app.schemas.logs import AuditLogOut, AISecurityEventOut, AIInteractionOut

router = APIRouter(prefix="/admin", tags=["Admin Supervision"])


@router.get("/audit-logs", response_model=list[AuditLogOut])
async def get_audit_logs(
    db: AsyncSession = Depends(get_db),
    user: UserOut = Depends(require_roles("admin"))
):
    """
    Récupère les logs d'audit système. Réservé aux administrateurs.
    """
    try:
        stmt = select(AuditLog).order_by(AuditLog.timestamp.desc())
        result = await db.execute(stmt)
        logs = result.scalars().all()
        return logs
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des logs d'audit : {str(e)}"
        )


@router.get("/security-events", response_model=list[AISecurityEventOut])
async def get_security_events(
    db: AsyncSession = Depends(get_db),
    user: UserOut = Depends(require_roles("admin"))
):
    """
    Récupère les alertes et événements de sécurité IA. Réservé aux administrateurs.
    """
    try:
        stmt = select(AISecurityEvent).order_by(AISecurityEvent.created_at.desc())
        result = await db.execute(stmt)
        events = result.scalars().all()
        return events
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des événements de sécurité : {str(e)}"
        )


@router.post("/security-events/{event_id}/notify", response_model=AISecurityEventOut)
async def acknowledge_security_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: UserOut = Depends(require_roles("admin"))
):
    """
    Accuse réception d'un événement de sécurité IA. Réservé aux administrateurs.
    """
    stmt = select(AISecurityEvent).where(AISecurityEvent.id == event_id)
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Événement de sécurité introuvable."
        )
        
    try:
        event.admin_notified_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(event)
        return event
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la mise à jour de l'événement : {str(e)}"
        )


@router.get("/interactions", response_model=list[AIInteractionOut])
async def get_ai_interactions(
    db: AsyncSession = Depends(get_db),
    user: UserOut = Depends(require_roles("admin"))
):
    """
    Récupère l'historique complet des interactions IA. Réservé aux administrateurs.
    """
    try:
        stmt = select(AIInteraction).order_by(AIInteraction.timestamp.desc())
        result = await db.execute(stmt)
        interactions = result.scalars().all()
        return interactions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des interactions IA : {str(e)}"
        )
