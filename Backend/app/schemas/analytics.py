"""
analytics.py
-------------
Schémas Pydantic pour les KPIs, engagement, désengagement et alertes.
"""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import (
    AlertSeverityEnum,
    KPIScopeEnum,
    RiskLevelEnum,
    SentimentEnum,
)


# ── KPI Snapshots ─────────────────────────────────────────────────────────────

class HRKPISnapshotOut(BaseModel):
    id: UUID
    scope_type: KPIScopeEnum
    scope_id: UUID
    period_month: int
    period_year: int
    headcount: int | None = None
    turnover_rate: float | None = None
    absenteeism_rate: float | None = None
    avg_age: float | None = None
    internal_mobility_count: int | None = None
    engagement_score: float | None = None
    model_config = {"from_attributes": True}


# ── Engagement Surveys ────────────────────────────────────────────────────────

class EngagementSurveyCreate(BaseModel):
    employee_id: UUID
    survey_date: date
    score: int  # 1-10
    sentiment: SentimentEnum | None = None
    is_anonymous: bool = False


class EngagementSurveyOut(BaseModel):
    id: UUID
    employee_id: UUID
    survey_date: date
    score: int
    sentiment: SentimentEnum | None = None
    is_anonymous: bool
    model_config = {"from_attributes": True}


# ── Annual Reviews ────────────────────────────────────────────────────────────

class AnnualReviewCreate(BaseModel):
    employee_id: UUID
    reviewer_id: UUID
    review_date: date
    rating: float | None = None
    workload_score: int | None = None  # 1-5
    notes: str | None = None


class AnnualReviewOut(BaseModel):
    id: UUID
    employee_id: UUID
    reviewer_id: UUID
    review_date: date
    rating: float | None = None
    workload_score: int | None = None
    model_config = {"from_attributes": True}


# ── Disengagement Signals ─────────────────────────────────────────────────────

class DisengagementSignalOut(BaseModel):
    id: UUID
    employee_id: UUID
    computed_at: datetime
    risk_score: float
    risk_level: RiskLevelEnum
    signals: dict | None = None
    action_plan: dict | None = None
    model_config = {"from_attributes": True}


# ── HR Alerts ─────────────────────────────────────────────────────────────────

class HRAlertOut(BaseModel):
    id: UUID
    employee_id: UUID | None = None
    alert_type: str
    severity: AlertSeverityEnum
    triggered_at: datetime
    resolved_at: datetime | None = None
    resolved_by: UUID | None = None
    is_read: bool
    resolution_notes: str | None = None
    model_config = {"from_attributes": True}
