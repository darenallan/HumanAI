"""
rag.py (API)
------------
Endpoints pour le module RAG (upload de document et chat RH).
"""
import uuid
from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.schemas.users import UserOut
from app.schemas.rag import RAGDocumentOut
from app.schemas.logs import ChatRequest, ChatResponse
from app.models.enums import RoleEnum
from app.models.logs import AIInteraction
from app.services.rag import ingest_document, ask_rag
from app.services.audit import log_audit_action

router = APIRouter(prefix="/rag", tags=["RAG AI Assistant"])


@router.post("/documents/ingest", response_model=RAGDocumentOut)
async def api_ingest_document(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(...),
    allowed_roles: str = Form("collaborateur,manager,rh,direction,admin,qvt"),
    db: AsyncSession = Depends(get_db),
    user: UserOut = Depends(require_roles("rh", "admin"))
):
    """
    Upload et ingère un document RH (PDF, DOCX, TXT) dans la base RAG.
    Réservé aux RH et Administrateurs.
    """
    if not file.filename.endswith((".pdf", ".docx", ".doc", ".txt", ".md")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seuls les formats PDF, DOCX et TXT sont supportés."
        )
        
    file_bytes = await file.read()
    
    try:
        roles_list = [RoleEnum(r.strip().lower()) for r in allowed_roles.split(",") if r.strip()]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rôle invalide spécifié. Rôles supportés: {[e.value for e in RoleEnum]}"
        )

    try:
        doc = await ingest_document(db, title, file_bytes, file.filename, roles_list)
        
        # Audit Log
        try:
            u_id = uuid.UUID(user.id)
        except ValueError:
            u_id = uuid.uuid4()
            
        await log_audit_action(
            db=db,
            user_id=u_id,
            action="WRITE",
            entity_type="rag_document",
            entity_id=doc.id,
            details={"filename": file.filename, "roles": allowed_roles},
            request=request
        )
        
        return doc
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne serveur.")


@router.post("/chat", response_model=ChatResponse)
async def api_chat(
    request: ChatRequest,
    fastapi_request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserOut = Depends(get_current_user)
):
    """
    Pose une question à l'assistant IA RH avec vérification Guardrails.
    """
    session_id = request.session_id or uuid.uuid4()
    
    # ── Tracer l'interaction (Audit / Parent Event pour Guardrails) ──
    try:
        user_uuid = uuid.UUID(user.id)
    except ValueError:
        user_uuid = uuid.uuid4()
        
    interaction_log = AIInteraction(
        user_id=user_uuid,
        session_id=session_id,
        query_text=request.message,
        role_at_time=user.role.value
    )
    db.add(interaction_log)
    await db.flush() # Récupérer l'ID pour les Guardrails
    
    # Appel au service RAG avec Guardrails
    result = await ask_rag(db, request.message, user.role.value, user_uuid, interaction_log.id)
    
    # Mise à jour de l'interaction
    interaction_log.response_summary = result["status"]
    interaction_log.data_scope_requested = result.get("sources", [])
    await db.commit()
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["answer"])
        
    return ChatResponse(
        response=result["answer"],
        session_id=session_id,
        sources=result.get("sources", [])
    )
