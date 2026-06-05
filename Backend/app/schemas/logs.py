"""
logs.py
-------
Schémas Pydantic pour la supervision IA, la sécurité et l'audit.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import AlertSeverityEnum, SecurityEventTypeEnum


# ── AI Interactions ───────────────────────────────────────────────────────────

class AIInteractionOut(BaseModel):
    id: UUID
    user_id: UUID
    session_id: UUID
    timestamp: datetime
    response_summary: str | None = None
    role_at_time: str | None = None
    data_scope_requested: list[str] | None = None
    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    message: str
    session_id: UUID | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: UUID
    sources: list[str] | None = None


# ── AI Security ───────────────────────────────────────────────────────────────

class AISecurityRuleCreate(BaseModel):
    name: str
    condition_logic: dict | None = None
    severity: AlertSeverityEnum
    is_active: bool = True


class AISecurityRuleOut(BaseModel):
    id: UUID
    name: str
    condition_logic: dict | None = None
    severity: AlertSeverityEnum
    is_active: bool
    model_config = {"from_attributes": True}


class AISecurityEventOut(BaseModel):
    id: UUID
    interaction_id: UUID
    event_type: SecurityEventTypeEnum
    severity: AlertSeverityEnum
    triggered_rule: UUID | None = None
    admin_notified_at: datetime | None = None
    model_config = {"from_attributes": True}


# ── Audit Logs ────────────────────────────────────────────────────────────────

class AuditLogOut(BaseModel):
    id: UUID
    user_id: UUID
    action: str
    entity_type: str
    entity_id: UUID | None = None
    timestamp: datetime
    ip_address: str | None = None
    details: dict | None = None
    model_config = {"from_attributes": True}


# ── Data Consents ─────────────────────────────────────────────────────────────

class DataConsentCreate(BaseModel):
    employee_id: UUID
    purpose: str


class DataConsentOut(BaseModel):
    id: UUID
    employee_id: UUID
    purpose: str
    granted_at: datetime
    revoked_at: datetime | None = None
    model_config = {"from_attributes": True}
