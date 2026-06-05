"""
audit.py
--------
Service de journalisation d'audit immuable.
Enregistre (append-only) toutes les actions critiques de l'application
conformément aux exigences RGPD et de traçabilité.
"""
import uuid
from typing import Optional
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.logs import AuditLog


async def log_audit_action(
    db: AsyncSession,
    user_id: uuid.UUID,
    action: str,
    entity_type: str,
    entity_id: Optional[uuid.UUID] = None,
    details: Optional[dict] = None,
    request: Optional[Request] = None
) -> AuditLog:
    """
    Crée une entrée d'audit immuable.
    
    Args:
        db: Session asynchrone SQLAlchemy
        user_id: L'UUID de l'utilisateur ayant effectué l'action
        action: L'action effectuée (ex: 'READ', 'WRITE', 'EXPORT', 'DELETE')
        entity_type: Le type d'entité concernée (ex: 'employee', 'document', 'alert')
        entity_id: L'ID de l'entité concernée
        details: Informations contextuelles supplémentaires (JSON)
        request: Requête FastAPI (optionnel) pour extraire l'IP
    """
    
    ip_address = None
    if request:
        if request.client:
            ip_address = request.client.host
        # Fallback pour proxy/load balancer
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ip_address = forwarded_for.split(",")[0].strip()
            
    log_entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=ip_address,
        details=details
    )
    
    db.add(log_entry)
    await db.commit()
    await db.refresh(log_entry)
    
    return log_entry
