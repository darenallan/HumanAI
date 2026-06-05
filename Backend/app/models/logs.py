"""
logs.py
-------
Modèles ORM pour la supervision et l'audit :
  - ai_interactions       (logs chiffrés des échanges avec l'assistant IA)
  - ai_security_events    (événements de sécurité IA détectés)
  - ai_security_rules     (règles configurables par les admins)
  - audit_logs            (journal d'audit immuable — append-only)
  - data_consents         (consentements RGPD des collaborateurs)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Enum, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.enums import AlertSeverityEnum, SecurityEventTypeEnum


# ══════════════════════════════════════════════════════════════════════════════
#  Supervision de l'assistant IA
# ══════════════════════════════════════════════════════════════════════════════

class AIInteraction(Base):
    __tablename__ = "ai_interactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )  # regroupement des échanges d'une session
    timestamp: Mapped[datetime] = mapped_column(server_default=func.now())
    query_text: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # chiffré avec pgcrypto en production
    response_summary: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # résumé non-sensible de la réponse
    role_at_time: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # rôle de l'utilisateur au moment de la requête
    data_scope_requested: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), nullable=True
    )  # modules/tables consultés

    # Relations
    security_events: Mapped[list["AISecurityEvent"]] = relationship(
        back_populates="interaction"
    )


class AISecurityRule(Base):
    __tablename__ = "ai_security_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)  # ex: 'Accès paie hors RH'
    condition_logic: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # règle configurable par les admins
    severity: Mapped[str] = mapped_column(
        Enum(AlertSeverityEnum, name="alert_severity_enum", create_constraint=False, native_enum=False),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relations
    security_events: Mapped[list["AISecurityEvent"]] = relationship(
        back_populates="triggered_rule_rel"
    )


class AISecurityEvent(Base):
    __tablename__ = "ai_security_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    interaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_interactions.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(
        Enum(SecurityEventTypeEnum, name="security_event_type_enum", create_constraint=False, native_enum=False),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        Enum(AlertSeverityEnum, name="alert_severity_enum", create_constraint=False, native_enum=False),
        nullable=False,
    )
    triggered_rule: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_security_rules.id"), nullable=True
    )
    admin_notified_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relations
    interaction: Mapped[AIInteraction] = relationship(back_populates="security_events")
    triggered_rule_rel: Mapped[AISecurityRule | None] = relationship(
        back_populates="security_events"
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Audit & Conformité RGPD
# ══════════════════════════════════════════════════════════════════════════════

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    action: Mapped[str] = mapped_column(Text, nullable=False)  # READ, WRITE, DELETE, EXPORT
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)  # employee, document, alert
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(server_default=func.now())
    ip_address: Mapped[str | None] = mapped_column(Text, nullable=True)  # INET en prod
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class DataConsent(Base):
    __tablename__ = "data_consents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False
    )
    purpose: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # finalité du traitement (analytics, surveys…)
    granted_at: Mapped[datetime] = mapped_column(server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)
