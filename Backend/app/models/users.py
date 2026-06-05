"""
users.py
--------
Modèles ORM SQLAlchemy pour :
  - sites, departments, positions  (structure organisationnelle)
  - users, roles_permissions       (comptes et RBAC)
  - employees                      (données RH collaborateurs)
  - absences                       (congés et absences)
  - payroll_indicators             (indicateurs de paie agrégés)

Le store in-memory (mock) est conservé en bas du fichier pour assurer
la compatibilité ascendante avec les routes de démonstration existantes.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.enums import (
    AbsenceStatusEnum,
    AbsenceTypeEnum,
    ContractTypeEnum,
    EmployeeStatusEnum,
    RoleEnum,
)


# ══════════════════════════════════════════════════════════════════════════════
#  Structure organisationnelle
# ══════════════════════════════════════════════════════════════════════════════

class Site(Base):
    __tablename__ = "sites"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(Text, nullable=True)

    # Relations
    departments: Mapped[list["Department"]] = relationship(back_populates="site")


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True
    )
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id"), nullable=True
    )

    # Relations
    site: Mapped[Site | None] = relationship(back_populates="departments")
    parent: Mapped["Department | None"] = relationship(remote_side=[id])
    positions: Mapped[list["Position"]] = relationship(back_populates="department")
    users: Mapped[list["User"]] = relationship(back_populates="department")
    employees: Mapped[list["Employee"]] = relationship(back_populates="department")


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True
    )

    # Relations
    department: Mapped[Department | None] = relationship(back_populates="positions")
    employees: Mapped[list["Employee"]] = relationship(back_populates="position")


# ══════════════════════════════════════════════════════════════════════════════
#  Utilisateurs & RBAC
# ══════════════════════════════════════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    firebase_uid: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_name: Mapped[str] = mapped_column(Text, nullable=False, default="")
    role: Mapped[str] = mapped_column(
        Enum(RoleEnum, name="role_enum", create_constraint=False, native_enum=False),
        nullable=False,
        default=RoleEnum.COLLABORATEUR,
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True
    )
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )

    # Relations
    department: Mapped[Department | None] = relationship(back_populates="users")
    manager: Mapped["User | None"] = relationship(remote_side=[id])
    employee: Mapped["Employee | None"] = relationship(back_populates="user", uselist=False)


class RolePermission(Base):
    __tablename__ = "roles_permissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    role: Mapped[str] = mapped_column(
        Enum(RoleEnum, name="role_enum", create_constraint=False, native_enum=False),
        nullable=False,
    )
    module: Mapped[str] = mapped_column(Text, nullable=False)  # ex: paie, absences, dashboard
    can_read: Mapped[bool] = mapped_column(Boolean, default=False)
    can_write: Mapped[bool] = mapped_column(Boolean, default=False)
    can_export: Mapped[bool] = mapped_column(Boolean, default=False)


# ══════════════════════════════════════════════════════════════════════════════
#  Données RH Core — Collaborateurs
# ══════════════════════════════════════════════════════════════════════════════

class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    matricule: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    position_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("positions.id"), nullable=True
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True
    )
    hire_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    contract_type: Mapped[str | None] = mapped_column(
        Enum(ContractTypeEnum, name="contract_type_enum", create_constraint=False, native_enum=False),
        nullable=True,
    )
    salary_band: Mapped[str | None] = mapped_column(Text, nullable=True)  # chiffré avec pgcrypto en prod
    status: Mapped[str] = mapped_column(
        Enum(EmployeeStatusEnum, name="employee_status_enum", create_constraint=False, native_enum=False),
        default=EmployeeStatusEnum.ACTIF,
    )
    sirh_sync_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relations
    user: Mapped[User] = relationship(back_populates="employee")
    position: Mapped[Position | None] = relationship(back_populates="employees")
    department: Mapped[Department | None] = relationship(back_populates="employees")
    absences: Mapped[list["Absence"]] = relationship(back_populates="employee")
    payroll_indicators: Mapped[list["PayrollIndicator"]] = relationship(back_populates="employee")


class Absence(Base):
    __tablename__ = "absences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(
        Enum(AbsenceTypeEnum, name="absence_type_enum", create_constraint=False, native_enum=False),
        nullable=False,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    duration_days: Mapped[float | None] = mapped_column(Numeric(5, 1), nullable=True)
    motif: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(AbsenceStatusEnum, name="absence_status_enum", create_constraint=False, native_enum=False),
        default=AbsenceStatusEnum.PENDING,
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    sirh_sync_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relations
    employee: Mapped[Employee] = relationship(back_populates="absences")


class PayrollIndicator(Base):
    __tablename__ = "payroll_indicators"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False
    )
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    gross_band: Mapped[str] = mapped_column(Text, nullable=False)   # chiffré en prod
    net_band: Mapped[str] = mapped_column(Text, nullable=False)     # chiffré en prod

    # Relations
    employee: Mapped[Employee] = relationship(back_populates="payroll_indicators")


