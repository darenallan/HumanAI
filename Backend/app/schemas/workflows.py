"""
workflows.py
-------------
Schémas Pydantic pour les workflows d'onboarding et d'offboarding.
"""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import (
    OffboardingReasonEnum,
    OffboardingStatusEnum,
    OffboardingStepTypeEnum,
    OnboardingStatusEnum,
)


# ── Onboarding ────────────────────────────────────────────────────────────────

class OnboardingPlanOut(BaseModel):
    id: UUID
    employee_id: UUID
    status: OnboardingStatusEnum
    day_30_calendar: dict | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class OnboardingStepOut(BaseModel):
    id: UUID
    plan_id: UUID
    title: str
    due_date: date | None = None
    completed_at: datetime | None = None
    is_alert_triggered: bool
    model_config = {"from_attributes": True}


class OnboardingStepUpdate(BaseModel):
    completed_at: datetime | None = None


class OnboardingGenerateRequest(BaseModel):
    employee_id: UUID


# ── Offboarding ───────────────────────────────────────────────────────────────

class OffboardingInitiateRequest(BaseModel):
    employee_id: UUID
    departure_reason: OffboardingReasonEnum
    departure_date: date


class OffboardingWorkflowOut(BaseModel):
    id: UUID
    employee_id: UUID
    departure_reason: OffboardingReasonEnum
    departure_date: date
    status: OffboardingStatusEnum
    knowledge_transfer_doc_id: UUID | None = None
    model_config = {"from_attributes": True}


class OffboardingStepOut(BaseModel):
    id: UUID
    workflow_id: UUID
    step_type: OffboardingStepTypeEnum
    completed_at: datetime | None = None
    notes: str | None = None
    assigned_to: UUID | None = None
    model_config = {"from_attributes": True}


class OffboardingStepUpdate(BaseModel):
    completed_at: datetime | None = None
    notes: str | None = None
