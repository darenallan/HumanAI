"""
documents.py
-------------
Schémas Pydantic pour les templates et documents générés.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import DocumentStatusEnum, DocumentTypeEnum


class DocumentTemplateCreate(BaseModel):
    name: str
    type: DocumentTypeEnum
    content_template: str | None = None
    allowed_roles: list[str] | None = None


class DocumentTemplateOut(BaseModel):
    id: UUID
    name: str
    type: DocumentTypeEnum
    content_template: str | None = None
    allowed_roles: list[str] | None = None
    model_config = {"from_attributes": True}


class DocumentGenerateRequest(BaseModel):
    template_id: UUID
    employee_id: UUID


class GeneratedDocumentOut(BaseModel):
    id: UUID
    employee_id: UUID
    template_id: UUID
    generated_by: UUID
    generated_at: datetime
    status: DocumentStatusEnum
    rh_validated_by: UUID | None = None
    rh_validated_at: datetime | None = None
    model_config = {"from_attributes": True}
