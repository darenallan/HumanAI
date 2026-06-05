"""
rag.py
------
Modèles ORM pour le module RAG (Retrieval-Augmented Generation) :
  - rag_documents         (documents source indexés)
  - rag_document_access   (contrôle d'accès par rôle)
  - rag_chunks            (segments vectorisés avec embedding pgvector)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.enums import RAGSourceTypeEnum, RoleEnum


class RAGDocument(Base):
    __tablename__ = "rag_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(
        Enum(RAGSourceTypeEnum, name="rag_source_type_enum", create_constraint=False, native_enum=False),
        nullable=False,
    )
    content_raw: Mapped[str | None] = mapped_column(Text, nullable=True)  # texte original extrait
    metadata_info: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # {filename, version, valid_from, valid_to, scope}
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    # Relations
    access_rules: Mapped[list["RAGDocumentAccess"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    chunks: Mapped[list["RAGChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class RAGDocumentAccess(Base):
    __tablename__ = "rag_document_access"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rag_documents.id"), nullable=False
    )
    allowed_role: Mapped[str] = mapped_column(
        Enum(RoleEnum, name="role_enum", create_constraint=False, native_enum=False),
        nullable=False,
    )

    # Relations
    document: Mapped[RAGDocument] = relationship(back_populates="access_rules")


class RAGChunk(Base):
    """
    Segment vectorisé d'un document RAG.

    La colonne `embedding` stocke le vecteur dense généré par le modèle
    d'embedding (ex: text-embedding-3-small → 1536 dimensions).

    En production avec pgvector installé, elle utiliserait le type
    `Vector(1536)`. Ici nous stockons en JSONB (liste de floats) pour
    permettre le développement local sans l'extension pgvector.
    L'index HNSW sera ajouté via le script SQL d'initialisation DevOps.
    """
    __tablename__ = "rag_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rag_documents.id"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)  # position dans le document
    content: Mapped[str] = mapped_column(Text, nullable=False)  # texte du chunk (300-500 tokens)
    embedding: Mapped[list | None] = mapped_column(
        JSONB, nullable=True
    )  # vecteur float — Vector(1536) en prod avec pgvector
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relations
    document: Mapped[RAGDocument] = relationship(back_populates="chunks")
