"""
documents.py (API)
------------------
Endpoints pour la génération documentaire et la récupération sécurisée (déchiffrement).
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.users import Employee, User
from app.schemas.users import UserOut, Role
from app.schemas.documents import DocumentGenerateRequest, GeneratedDocumentOut
from app.services.documents import generate_document, export_to_pdf
from app.models.documents import GeneratedDocument
from app.core.crypto import decrypt_data

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/generate", response_model=GeneratedDocumentOut)
async def api_generate_document(
    request: DocumentGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: UserOut = Depends(require_roles("rh", "admin", "manager"))
):
    """
    Génère un document à partir d'un template et le chiffre en base.
    """
    try:
        # L'ID de l'utilisateur est passé depuis JWT ou Firebase. S'il n'est pas un vrai UUID, fallback.
        try:
            generated_by_uuid = uuid.UUID(user.id)
        except ValueError:
            generated_by_uuid = uuid.uuid4()
            
        doc = await generate_document(
            db, 
            request.template_id, 
            request.employee_id, 
            generated_by_uuid
        )
        return doc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la génération: {str(e)}"
        )


@router.get("/{document_id}/download")
async def api_download_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: UserOut = Depends(require_roles("rh", "admin", "manager", "collaborateur"))
):
    """
    Télécharge le PDF d'un document généré.
    Déchiffre le contenu AES-256 à la volée.
    """
    stmt = select(GeneratedDocument).where(GeneratedDocument.id == document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    
    if not doc or not doc.content_snapshot:
        raise HTTPException(status_code=404, detail="Document introuvable")
        
    # Vérification que le collaborateur ne télécharge que ses propres documents
    if user.role == Role.COLLABORATEUR:
        stmt_user = select(User.id).where(User.email == user.email)
        res_user = await db.execute(stmt_user)
        user_uuid = res_user.scalar_one_or_none()
        
        if not user_uuid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Utilisateur non trouvé dans la base locale."
            )
            
        stmt_emp = select(Employee.id).where(Employee.user_id == user_uuid)
        res_emp = await db.execute(stmt_emp)
        emp_id = res_emp.scalar_one_or_none()
        
        if not emp_id or doc.employee_id != emp_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès refusé : vous ne pouvez télécharger que vos propres documents."
            )
            
    try:
        # Déchiffrement AES-256
        plaintext = decrypt_data(doc.content_snapshot)
        
        # Génération du PDF
        pdf_bytes = export_to_pdf(plaintext)
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=document_{document_id}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du déchiffrement/génération: {str(e)}")
