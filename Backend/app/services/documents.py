"""
documents.py
------------
Service métier pour la génération documentaire :
  - Remplacement de variables dans les templates
  - Génération de PDF
  - Chiffrement symétrique avant stockage
"""
import uuid
import tempfile
import os
from datetime import datetime

from fpdf import FPDF
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.documents import DocumentTemplate, GeneratedDocument
from app.models.users import Employee
from app.models.enums import DocumentStatusEnum
from app.core.crypto import encrypt_data


async def generate_document(
    db: AsyncSession,
    template_id: uuid.UUID,
    employee_id: uuid.UUID,
    generated_by: uuid.UUID
) -> GeneratedDocument:
    """
    Génère un document personnalisé pour un employé à partir d'un template.
    1. Récupère le template et l'employé
    2. Remplace les variables (ex: {{full_name}})
    3. Chiffre le contenu avec AES-256
    4. Enregistre en base
    """
    
    # Récupération du template
    stmt_template = select(DocumentTemplate).where(DocumentTemplate.id == template_id)
    result_template = await db.execute(stmt_template)
    template = result_template.scalar_one_or_none()
    
    if not template or not template.content_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Template introuvable ou vide."
        )
        
    # Récupération de l'employé
    stmt_employee = select(Employee).where(Employee.id == employee_id)
    result_employee = await db.execute(stmt_employee)
    employee = result_employee.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Employé introuvable."
        )
        
    # Remplacement des variables
    # (En production, on utiliserait un vrai moteur de template comme Jinja2)
    content = template.content_template
    
    replacements = {
        "{{full_name}}": employee.full_name,
        "{{matricule}}": employee.matricule,
        "{{hire_date}}": employee.hire_date.strftime("%d/%m/%Y") if employee.hire_date else "N/A",
        "{{date}}": datetime.now().strftime("%d/%m/%Y")
    }
    
    for key, val in replacements.items():
        content = content.replace(key, str(val))
        
    # Chiffrement AES-256
    encrypted_content = encrypt_data(content)
    
    # Création de l'enregistrement en base
    doc = GeneratedDocument(
        employee_id=employee_id,
        template_id=template_id,
        generated_by=generated_by,
        content_snapshot=encrypted_content,
        status=DocumentStatusEnum.DRAFT
    )
    
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    
    return doc


def export_to_pdf(plaintext_content: str) -> bytes:
    """
    Génère un fichier PDF à partir du texte.
    Retourne les bytes du PDF généré.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Encodage latin-1 pour fpdf de base
    safe_text = plaintext_content.encode('latin-1', 'replace').decode('latin-1')
    
    pdf.multi_cell(0, 10, txt=safe_text)
    
    # Sauvegarde temporaire pour récupérer les bytes
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        tmp_path = tmp.name
        
    with open(tmp_path, "rb") as f:
        pdf_bytes = f.read()
        
    os.remove(tmp_path)
    return pdf_bytes
