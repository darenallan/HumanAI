"""
analytics.py
-------------
Modèles ORM pour le module analytique et prédictif :
  - hr_kpi_snapshots        (indicateurs RH agrégés)
  - engagement_surveys      (enquêtes d'engagement)
  - annual_reviews          (entretiens annuels)
  - disengagement_signals   (scoring de risque burnout/départ)
  - hr_alerts               (alertes RH et sécurité)
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, Numeric, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.enums import (
    AlertSeverityEnum,
    KPIScopeEnum,
    RiskLevelEnum,
    SentimentEnum,
)


class HRKPISnapshot(Base):
    __tablename__ = "hr_kpi_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    scope_type: Mapped[str] = mapped_column(
        Enum(KPIScopeEnum, name="kpi_scope_enum", create_constraint=False, native_enum=False),
        nullable=False,
    )
    scope_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    period_month: Mapped[int] = mapped_column(Integer, nullable=False)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    headcount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    turnover_rate: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    absenteeism_rate: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    avg_age: Mapped[float | None] = mapped_column(Numeric(5, 1), nullable=True)
    payroll_mass_band: Mapped[str | None] = mapped_column(Text, nullable=True)  # chiffré en prod
    internal_mobility_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    engagement_score: Mapped[float | None] = mapped_column(Numeric(3, 1), nullable=True)  # 0-10


class EngagementSurvey(Base):
    __tablename__ = "engagement_surveys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False
    )
    survey_date: Mapped[date] = mapped_column(Date, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-10
    sentiment: Mapped[str | None] = mapped_column(
        Enum(SentimentEnum, name="sentiment_enum", create_constraint=False, native_enum=False),
        nullable=True,
    )
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False)


class AnnualReview(Base):
    __tablename__ = "annual_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    review_date: Mapped[date] = mapped_column(Date, nullable=False)
    rating: Mapped[float | None] = mapped_column(Numeric(3, 1), nullable=True)
    workload_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)  # chiffré en prod


class DisengagementSignal(Base):
    __tablename__ = "disengagement_signals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False
    )
    computed_at: Mapped[datetime] = mapped_column(server_default=func.now())
    risk_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)  # 0-100
    risk_level: Mapped[str] = mapped_column(
        Enum(RiskLevelEnum, name="risk_level_enum", create_constraint=False, native_enum=False),
        nullable=False,
    )
    signals: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # ex: {absenteeism: 0.8, survey: 0.3, workload: 0.9}
    action_plan: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # plan d'action recommandé par l'agent IA


class HRAlert(Base):
    __tablename__ = "hr_alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True
    )
    alert_type: Mapped[str] = mapped_column(Text, nullable=False)  # ex: disengagement_risk
    severity: Mapped[str] = mapped_column(
        Enum(AlertSeverityEnum, name="alert_severity_enum", create_constraint=False, native_enum=False),
        nullable=False,
    )
    triggered_at: Mapped[datetime] = mapped_column(server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
