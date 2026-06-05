"""
workflows.py
-------------
Modèles ORM pour les workflows agentiques :
  - onboarding_plans / onboarding_steps   (intégration 30 jours)
  - offboarding_workflows / offboarding_steps  (processus de sortie)
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.enums import (
    OffboardingReasonEnum,
    OffboardingStatusEnum,
    OffboardingStepTypeEnum,
    OnboardingStatusEnum,
)


# ══════════════════════════════════════════════════════════════════════════════
#  Onboarding
# ══════════════════════════════════════════════════════════════════════════════

class OnboardingPlan(Base):
    __tablename__ = "onboarding_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum(OnboardingStatusEnum, name="onboarding_status_enum", create_constraint=False, native_enum=False),
        default=OnboardingStatusEnum.DRAFT,
    )
    day_30_calendar: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # structure des 30 jours d'intégration
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relations
    steps: Mapped[list["OnboardingStep"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )


class OnboardingStep(Base):
    __tablename__ = "onboarding_steps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("onboarding_plans.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)  # ex: 'Remise du matériel'
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    is_alert_triggered: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relations
    plan: Mapped[OnboardingPlan] = relationship(back_populates="steps")


# ══════════════════════════════════════════════════════════════════════════════
#  Offboarding
# ══════════════════════════════════════════════════════════════════════════════

class OffboardingWorkflow(Base):
    __tablename__ = "offboarding_workflows"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False
    )
    departure_reason: Mapped[str] = mapped_column(
        Enum(OffboardingReasonEnum, name="offboarding_reason_enum", create_constraint=False, native_enum=False),
        nullable=False,
    )
    departure_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(OffboardingStatusEnum, name="offboarding_status_enum", create_constraint=False, native_enum=False),
        default=OffboardingStatusEnum.INITIATED,
    )
    knowledge_transfer_doc_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("generated_documents.id"), nullable=True
    )

    # Relations
    steps: Mapped[list["OffboardingStep"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )


class OffboardingStep(Base):
    __tablename__ = "offboarding_steps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("offboarding_workflows.id"), nullable=False
    )
    step_type: Mapped[str] = mapped_column(
        Enum(OffboardingStepTypeEnum, name="offboarding_step_type_enum", create_constraint=False, native_enum=False),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Relations
    workflow: Mapped[OffboardingWorkflow] = relationship(back_populates="steps")
