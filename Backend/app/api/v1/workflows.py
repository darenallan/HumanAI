"""
workflows.py (API)
------------------
Endpoints pour les workflows agentiques (Onboarding & Offboarding).
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.schemas.users import UserOut
from app.schemas.workflows import (
    OnboardingPlanOut, 
    OnboardingGenerateRequest,
    OffboardingWorkflowOut,
    OffboardingInitiateRequest,
    OffboardingStepOut,
    OffboardingStepUpdate
)
from app.services.onboarding import generate_onboarding_plan, check_onboarding_delays
from app.services.offboarding import initiate_offboarding, complete_offboarding_step
from app.models.workflows import OnboardingPlan, OffboardingWorkflow, OffboardingStep

router = APIRouter(prefix="/workflows", tags=["Agentic Workflows"])


# ─── Onboarding ───────────────────────────────────────────────────────────────

@router.post("/onboarding", response_model=OnboardingPlanOut)
async def api_generate_onboarding(
    request: OnboardingGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: UserOut = Depends(require_roles("rh", "admin", "manager"))
):
    """
    Génère un plan d'intégration complet sur 30 jours pour un nouvel employé.
    """
    try:
        plan = await generate_onboarding_plan(db, request.employee_id)
        return plan
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/onboarding/check-delays")
async def api_check_onboarding_delays(
    db: AsyncSession = Depends(get_db),
    user: UserOut = Depends(require_roles("admin"))
):
    """
    Endpoint CRON manuel pour déclencher la vérification des retards.
    """
    delays_count = await check_onboarding_delays(db)
    return {"message": f"{delays_count} étapes en retard détectées et alertes déclenchées."}


# ─── Offboarding ──────────────────────────────────────────────────────────────

@router.post("/offboarding", response_model=OffboardingWorkflowOut)
async def api_initiate_offboarding(
    request: OffboardingInitiateRequest,
    db: AsyncSession = Depends(get_db),
    user: UserOut = Depends(require_roles("rh", "admin", "manager"))
):
    """
    Initie le processus d'offboarding (restitution, révocation, entretien).
    """
    try:
        workflow = await initiate_offboarding(
            db, 
            request.employee_id, 
            request.departure_reason, 
            request.departure_date
        )
        return workflow
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put("/offboarding/steps/{step_id}", response_model=OffboardingStepOut)
async def api_complete_offboarding_step(
    step_id: uuid.UUID,
    request: OffboardingStepUpdate,
    db: AsyncSession = Depends(get_db),
    user: UserOut = Depends(require_roles("rh", "admin", "manager"))
):
    """
    Marque une étape d'offboarding comme terminée (ex: IT restitution).
    """
    try:
        step = await complete_offboarding_step(db, step_id, request.notes)
        return step
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
