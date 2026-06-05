"""
analytics.py (API)
------------------
Endpoints pour les tableaux de bord analytiques et le scoring de désengagement.
"""
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import require_roles
from app.schemas.users import UserOut
from app.schemas.analytics import HRKPISnapshotOut, DisengagementSignalOut, HRAlertOut
from app.services.analytics import compute_global_kpis, compute_disengagement_risk
from app.models.analytics import HRKPISnapshot, DisengagementSignal, HRAlert
from app.core.cache import get_cache, set_cache, delete_cache

router = APIRouter(prefix="/analytics", tags=["HR Analytics & Predictive"])


@router.post("/kpis", response_model=HRKPISnapshotOut)
async def api_compute_kpis(
    year: int,
    month: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: UserOut = Depends(require_roles("rh", "direction", "admin"))
):
    """
    Calcule et génère un snapshot des KPIs pour un mois et une année donnés.
    Invalide le cache.
    """
    try:
        snapshot = await compute_global_kpis(db, year, month)
        # Nettoyage asynchrone du cache via BackgroundTasks
        background_tasks.add_task(delete_cache, "kpis_history")
        return snapshot
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du calcul des KPIs: {str(e)}"
        )


@router.get("/kpis", response_model=List[HRKPISnapshotOut])
async def api_get_kpis(
    db: AsyncSession = Depends(get_db),
    user: UserOut = Depends(require_roles("rh", "direction", "admin"))
):
    """
    Récupère l'historique des KPIs avec mise en cache Redis.
    """
    # 1. Vérification du cache Redis
    cached_kpis = await get_cache("kpis_history")
    if cached_kpis:
        return cached_kpis
        
    # 2. Si pas en cache, on calcule depuis la BDD
    stmt = select(HRKPISnapshot).order_by(HRKPISnapshot.period_year.desc(), HRKPISnapshot.period_month.desc())
    result = await db.execute(stmt)
    kpis = result.scalars().all()
    
    # 3. On enregistre dans le cache pour 1h (3600s) si au moins un KPI existe
    if kpis:
        # On doit convertir les objets ORM en dictionnaires pour json.dumps dans set_cache
        kpi_list = []
        for kpi in kpis:
            kpi_dict = {
                "id": str(kpi.id),
                "scope_type": kpi.scope_type,
                "scope_id": str(kpi.scope_id),
                "period_month": kpi.period_month,
                "period_year": kpi.period_year,
                "headcount": kpi.headcount,
                "turnover_rate": float(kpi.turnover_rate) if kpi.turnover_rate else None,
                "absenteeism_rate": float(kpi.absenteeism_rate) if kpi.absenteeism_rate else None,
                "avg_age": float(kpi.avg_age) if kpi.avg_age else None,
                "payroll_mass_band": kpi.payroll_mass_band,
                "internal_mobility_count": kpi.internal_mobility_count,
                "engagement_score": float(kpi.engagement_score) if kpi.engagement_score else None
            }
            kpi_list.append(kpi_dict)
        await set_cache("kpis_history", kpi_list, expire_seconds=3600)
        
    return kpis


@router.post("/disengagement/{employee_id}", response_model=DisengagementSignalOut)
async def api_compute_disengagement(
    employee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: UserOut = Depends(require_roles("rh", "manager", "qvt", "admin"))
):
    """
    Calcule le score de risque de désengagement d'un collaborateur à l'instant T.
    """
    try:
        signal = await compute_disengagement_risk(db, employee_id)
        return signal
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du calcul du score: {str(e)}"
        )


@router.post("/disengagement/mass-scoring/")
async def api_mass_disengagement_scoring(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: UserOut = Depends(require_roles("rh", "direction", "admin"))
):
    """
    Déclenche le calcul asynchrone du score de désengagement pour tous les employés actifs.
    Utilise BackgroundTasks pour décharger la requête HTTP principale.
    """
    from app.models.users import Employee
    stmt = select(Employee.id).where(Employee.status == "actif")
    result = await db.execute(stmt)
    employee_ids = result.scalars().all()
    
    for emp_id in employee_ids:
        background_tasks.add_task(compute_disengagement_risk, db, emp_id)
        
    return {"message": f"Scoring en cours d'exécution en arrière-plan pour {len(employee_ids)} employés."}


@router.get("/alerts", response_model=List[HRAlertOut])
async def api_get_alerts(
    db: AsyncSession = Depends(get_db),
    user: UserOut = Depends(require_roles("rh", "manager", "qvt", "admin"))
):
    """
    Récupère les alertes RH actives (ex: risque critique de départ).
    """
    stmt = select(HRAlert).where(HRAlert.resolved_at == None).order_by(HRAlert.triggered_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()
