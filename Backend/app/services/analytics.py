"""
analytics.py
------------
Service métier pour le module Analytique et Prédictif :
  - Calcul des KPIs RH globaux ou par département (absentéisme, turnover)
  - Modèle prédictif de désengagement (burnout/départ)
  - Génération d'alertes RH
"""
import uuid
from datetime import date, datetime, timedelta

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.analytics import (
    HRKPISnapshot, 
    EngagementSurvey, 
    AnnualReview, 
    DisengagementSignal, 
    HRAlert
)
from app.models.users import Employee, Absence
from app.models.enums import KPIScopeEnum, RiskLevelEnum, AlertSeverityEnum, AbsenceTypeEnum


# ─── KPIs RH ──────────────────────────────────────────────────────────────────

async def compute_global_kpis(db: AsyncSession, year: int, month: int) -> HRKPISnapshot:
    """
    Calcule et enregistre les KPIs globaux pour un mois donné.
    (Dans une vraie implémentation, les formules de turnover/absentéisme seraient plus complexes)
    """
    
    # Effectif actif
    stmt_headcount = select(func.count(Employee.id)).where(Employee.status == "actif")
    headcount = (await db.execute(stmt_headcount)).scalar() or 0
    
    # Age moyen (approximation simpliste si on avait la date de naissance, ici on mock)
    avg_age = 35.5
    
    # Absentéisme (jours d'absence sur le mois / jours ouvrés * effectif)
    # Mock du calcul pour l'exemple
    absenteeism_rate = 3.2 
    
    # Turnover
    turnover_rate = 5.1
    
    # Engagement moyen
    stmt_engagement = select(func.avg(EngagementSurvey.score)).where(
        func.extract('year', EngagementSurvey.survey_date) == year,
        func.extract('month', EngagementSurvey.survey_date) == month
    )
    engagement_score = (await db.execute(stmt_engagement)).scalar() or 0.0

    snapshot = HRKPISnapshot(
        scope_type=KPIScopeEnum.GLOBAL,
        scope_id=uuid.UUID(int=0), # ID fictif pour "Global"
        period_month=month,
        period_year=year,
        headcount=headcount,
        turnover_rate=turnover_rate,
        absenteeism_rate=absenteeism_rate,
        avg_age=avg_age,
        engagement_score=round(engagement_score, 1)
    )
    
    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)
    
    return snapshot


# ─── SCORING DE DÉSENGAGEMENT ─────────────────────────────────────────────────

async def compute_disengagement_risk(db: AsyncSession, employee_id: uuid.UUID) -> DisengagementSignal:
    """
    Analyse les signaux faibles pour calculer un score de risque de désengagement (0-100).
    Facteurs pris en compte :
      - Baisse de la note d'engagement récente
      - Augmentation des absences courtes (maladie)
      - Charge de travail élevée (Annual Review)
    """
    
    risk_score = 0.0
    signals = {}
    
    # 1. Analyse des absences récentes (6 derniers mois)
    six_months_ago = date.today() - timedelta(days=180)
    stmt_absences = select(func.count(Absence.id)).where(
        Absence.employee_id == employee_id,
        Absence.start_date >= six_months_ago,
        Absence.type == AbsenceTypeEnum.MALADIE
    )
    maladie_count = (await db.execute(stmt_absences)).scalar() or 0
    
    if maladie_count >= 3:
        risk_score += 30
        signals["absences_frequentes"] = "3+ arrêts maladie sur 6 mois"
    elif maladie_count > 0:
        risk_score += 10
        
    # 2. Analyse des enquêtes d'engagement (dernière enquête)
    stmt_survey = select(EngagementSurvey).where(
        EngagementSurvey.employee_id == employee_id
    ).order_by(EngagementSurvey.survey_date.desc()).limit(1)
    survey = (await db.execute(stmt_survey)).scalar_one_or_none()
    
    if survey:
        if survey.score <= 4:
            risk_score += 40
            signals["low_engagement"] = f"Dernier score très faible: {survey.score}/10"
        elif survey.score <= 6:
            risk_score += 20
            
    # 3. Analyse des reviews annuelles (charge de travail)
    stmt_review = select(AnnualReview).where(
        AnnualReview.employee_id == employee_id
    ).order_by(AnnualReview.review_date.desc()).limit(1)
    review = (await db.execute(stmt_review)).scalar_one_or_none()
    
    if review and review.workload_score and review.workload_score >= 4:
        risk_score += 30
        signals["high_workload"] = "Surcharge de travail signalée"
        
    # Cap à 100
    risk_score = min(risk_score, 100.0)
    
    # Détermination du niveau
    if risk_score >= 80:
        level = RiskLevelEnum.CRITICAL
    elif risk_score >= 50:
        level = RiskLevelEnum.HIGH
    elif risk_score >= 25:
        level = RiskLevelEnum.MEDIUM
    else:
        level = RiskLevelEnum.LOW
        
    action_plan = None
    if level in [RiskLevelEnum.HIGH, RiskLevelEnum.CRITICAL]:
        action_plan = {
            "step_1": "Planifier un entretien RH 'Stay Interview'",
            "step_2": "Vérifier la charge de travail avec le manager",
            "step_3": "Proposer des congés ou de la flexibilité"
        }
        
    # Enregistrement du signal
    signal = DisengagementSignal(
        employee_id=employee_id,
        risk_score=risk_score,
        risk_level=level,
        signals=signals,
        action_plan=action_plan
    )
    db.add(signal)
    
    # Création d'alerte si critique
    if level == RiskLevelEnum.CRITICAL:
        alert = HRAlert(
            employee_id=employee_id,
            alert_type="disengagement_risk",
            severity=AlertSeverityEnum.CRITIQUE
        )
        db.add(alert)
        
    await db.commit()
    await db.refresh(signal)
    
    return signal
