"""
employees.py
-------------
Schémas Pydantic pour les collaborateurs, absences et payroll.
"""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import (
    AbsenceStatusEnum,
    AbsenceTypeEnum,
    ContractTypeEnum,
    EmployeeStatusEnum,
)


# ── Sites & Départements ──────────────────────────────────────────────────────

class SiteOut(BaseModel):
    id: UUID
    name: str
    location: str | None = None
    model_config = {"from_attributes": True}


class DepartmentOut(BaseModel):
    id: UUID
    name: str
    parent_id: UUID | None = None
    site_id: UUID | None = None
    model_config = {"from_attributes": True}


class PositionOut(BaseModel):
    id: UUID
    title: str
    department_id: UUID | None = None
    model_config = {"from_attributes": True}


# ── Employés ──────────────────────────────────────────────────────────────────

class EmployeeCreate(BaseModel):
    matricule: str
    full_name: str
    user_id: UUID
    position_id: UUID | None = None
    department_id: UUID | None = None
    hire_date: date | None = None
    contract_type: ContractTypeEnum | None = None
    salary_band: str | None = None


class EmployeeUpdate(BaseModel):
    full_name: str | None = None
    position_id: UUID | None = None
    department_id: UUID | None = None
    contract_type: ContractTypeEnum | None = None
    salary_band: str | None = None
    status: EmployeeStatusEnum | None = None


class EmployeeOut(BaseModel):
    id: UUID
    user_id: UUID
    matricule: str
    full_name: str
    position_id: UUID | None = None
    department_id: UUID | None = None
    hire_date: date | None = None
    contract_type: ContractTypeEnum | None = None
    status: EmployeeStatusEnum
    model_config = {"from_attributes": True}


# ── Absences ──────────────────────────────────────────────────────────────────

class AbsenceCreate(BaseModel):
    employee_id: UUID
    type: AbsenceTypeEnum
    start_date: date
    end_date: date
    motif: str | None = None


class AbsenceOut(BaseModel):
    id: UUID
    employee_id: UUID
    type: AbsenceTypeEnum
    start_date: date
    end_date: date
    duration_days: float | None = None
    motif: str | None = None
    status: AbsenceStatusEnum
    approved_by: UUID | None = None
    model_config = {"from_attributes": True}


# ── Payroll ───────────────────────────────────────────────────────────────────

class PayrollIndicatorOut(BaseModel):
    id: UUID
    employee_id: UUID
    month: int
    year: int
    gross_band: str
    net_band: str
    model_config = {"from_attributes": True}
