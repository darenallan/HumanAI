"""
documents.py
------------
Modèles ORM pour la génération documentaire :
  - document_templates    (modèles de documents avec variables)
  - generated_documents   (documents générés, historisés et chiffrés)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.enums import DocumentStatusEnum, DocumentTypeEnum


class DocumentTemplate(Base):
    __tablename__ = "document_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(
        Enum(DocumentTypeEnum, name="document_type_enum", create_constraint=False, native_enum=False),
        nullable=False,
    )
    content_template: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # template avec variables {{employee.name}}, etc.
    allowed_roles: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), nullable=True
    )  # rôles pouvant générer ce type de document

    # Relations
    generated_documents: Mapped[list["GeneratedDocument"]] = relationship(
        back_populates="template"
    )


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_templates.id"), nullable=False
    )
    generated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    generated_at: Mapped[datetime] = mapped_column(server_default=func.now())
    content_snapshot: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # contenu final — chiffré avec pgcrypto en production
    status: Mapped[str] = mapped_column(
        Enum(DocumentStatusEnum, name="document_status_enum", create_constraint=False, native_enum=False),
        default=DocumentStatusEnum.DRAFT,
    )
    rh_validated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    rh_validated_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relations
    template: Mapped[DocumentTemplate] = relationship(back_populates="generated_documents")
