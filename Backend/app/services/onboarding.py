"""
onboarding.py
-------------
Service métier pour les workflows agentiques d'onboarding :
  - Génération automatique de plans sur 30 jours
  - Suivi des étapes
  - Alertes de retard
"""
import uuid
from datetime import timedelta, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.workflows import OnboardingPlan, OnboardingStep
from app.models.users import Employee
from app.models.enums import OnboardingStatusEnum


async def generate_onboarding_plan(db: AsyncSession, employee_id: uuid.UUID) -> OnboardingPlan:
    """
    Crée un plan d'intégration automatique sur 30 jours pour un nouvel employé.
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
        
    start_date = employee.hire_date or date.today()
    
    # 2. Création du plan principal
    plan = OnboardingPlan(
        employee_id=employee_id,
        status=OnboardingStatusEnum.IN_PROGRESS,
        day_30_calendar={
            "start_date": start_date.isoformat(),
            "end_date": (start_date + timedelta(days=30)).isoformat(),
            "milestones": ["Jour 1", "Semaine 1", "Mois 1"]
        }
    )
    
    db.add(plan)
    await db.flush() # Pour récupérer l'ID
    
    # 3. Génération des étapes standards
    steps_data = [
        {"title": "Accueil et présentation de l'entreprise", "delay_days": 0},
        {"title": "Configuration du matériel IT", "delay_days": 1},
        {"title": "Point avec le manager (Semaine 1)", "delay_days": 7},
        {"title": "Bilan d'étonnement (Mois 1)", "delay_days": 30},
    ]
    
    for step_info in steps_data:
        step_due_date = start_date + timedelta(days=step_info["delay_days"])
        step = OnboardingStep(
            plan_id=plan.id,
            title=step_info["title"],
            due_date=step_due_date
        )
        db.add(step)
        
    await db.commit()
    await db.refresh(plan)
    
    return plan


async def check_onboarding_delays(db: AsyncSession):
    """
    Vérifie les étapes en retard et déclenche des alertes (is_alert_triggered=True).
    Fonction prévue pour être appelée par un CRON ou Celery (Jalon 8).
    """
    today = date.today()
    
    stmt = select(OnboardingStep).where(
        OnboardingStep.completed_at == None,
        OnboardingStep.due_date < today,
        OnboardingStep.is_alert_triggered == False
    )
    
    result = await db.execute(stmt)
    delayed_steps = result.scalars().all()
    
    for step in delayed_steps:
        step.is_alert_triggered = True
        # Ici on pourrait également envoyer un e-mail ou créer un HRAlert
        
    if delayed_steps:
        await db.commit()
        
    return len(delayed_steps)
