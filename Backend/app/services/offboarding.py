"""
offboarding.py
--------------
Service métier pour les workflows agentiques d'offboarding :
  - Initiation du processus de sortie
  - Restitution du matériel
  - Révocation automatique des accès
"""
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.workflows import OffboardingWorkflow, OffboardingStep
from app.models.users import Employee
from app.models.enums import OffboardingReasonEnum, OffboardingStatusEnum, OffboardingStepTypeEnum


async def initiate_offboarding(
    db: AsyncSession, 
    employee_id: uuid.UUID, 
    departure_reason: OffboardingReasonEnum, 
    departure_date: date
) -> OffboardingWorkflow:
    """
    Initie le workflow de départ d'un collaborateur.
    """
    
    # 1. Vérifier que l'employé existe
    stmt_employee = select(Employee).where(Employee.id == employee_id)
    result = await db.execute(stmt_employee)
    employee = result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Employé introuvable."
        )
        
    # 2. Création du workflow principal
    workflow = OffboardingWorkflow(
        employee_id=employee_id,
        departure_reason=departure_reason,
        departure_date=departure_date,
        status=OffboardingStatusEnum.INITIATED
    )
    
    db.add(workflow)
    await db.flush()
    
    # 3. Création des tâches standards
    steps_data = [
        OffboardingStepTypeEnum.IT_RESTITUTION,
        OffboardingStepTypeEnum.ACCESS_REVOCATION,
        OffboardingStepTypeEnum.EXIT_INTERVIEW
    ]
    
    for step_type in steps_data:
        step = OffboardingStep(
            workflow_id=workflow.id,
            step_type=step_type
        )
        db.add(step)
        
    await db.commit()
    await db.refresh(workflow)
    
    return workflow


async def complete_offboarding_step(
    db: AsyncSession, 
    step_id: uuid.UUID, 
    notes: str = None
) -> OffboardingStep:
    """
    Marque une étape d'offboarding comme complétée.
    """
    from datetime import datetime
    
    stmt = select(OffboardingStep).where(OffboardingStep.id == step_id)
    result = await db.execute(stmt)
    step = result.scalar_one_or_none()
    
    if not step:
        raise HTTPException(status_code=404, detail="Étape introuvable.")
        
    step.completed_at = datetime.now()
    if notes:
        step.notes = notes
        
    await db.commit()
    await db.refresh(step)
    
    # Si c'était ACCESS_REVOCATION, on pourrait désactiver l'utilisateur lié ici (Jalon 8)
    
    return step
