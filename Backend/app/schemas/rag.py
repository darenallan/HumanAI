"""
rag.py
------
Schémas Pydantic pour le module RAG (documents vectorisés).
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import RAGSourceTypeEnum, RoleEnum


class RAGDocumentCreate(BaseModel):
    title: str
    source_type: RAGSourceTypeEnum
    content_raw: str | None = None
    metadata_info: dict | None = None
    scope_roles: list[RoleEnum] | None = None  # rôles autorisés


class RAGDocumentOut(BaseModel):
    id: UUID
    title: str
    source_type: RAGSourceTypeEnum
    metadata_info: dict | None = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class RAGChunkOut(BaseModel):
    id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    token_count: int | None = None
    model_config = {"from_attributes": True}
