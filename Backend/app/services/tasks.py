"""
tasks.py
--------
Scripts de tâches d'arrière-plan (Background Tasks) et maintenance (CRON).
Ces tâches déchargent le flux HTTP principal pour améliorer les performances.
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.logs import AIInteraction
from app.services.onboarding import check_onboarding_delays
from app.services.analytics import compute_global_kpis

logger = logging.getLogger(__name__)


async def run_daily_maintenance(db: AsyncSession):
    """
    Exécute les opérations de maintenance quotidienne.
    Idéalement lancé par un ordonnanceur externe (CRON, Celery Beat)
    ou via un script ponctuel.
    """
    logger.info("Début de la maintenance quotidienne...")
    
    # 1. Vérification des retards d'intégration
    try:
        delays = await check_onboarding_delays(db)
        logger.info(f"Vérification Onboarding : {delays} alertes déclenchées.")
    except Exception as e:
        logger.error(f"Erreur check_onboarding_delays : {e}")
        
    # 2. Nettoyage des logs IA obsolètes (rétention de 365 jours par défaut)
    try:
        retention_date = datetime.now() - timedelta(days=365)
        stmt = delete(AIInteraction).where(AIInteraction.timestamp < retention_date)
        result = await db.execute(stmt)
        await db.commit()
        logger.info(f"Nettoyage des logs IA : {result.rowcount} enregistrements supprimés.")
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage des logs IA : {e}")


async def bg_compute_mass_kpis(db: AsyncSession, year: int, month: int):
    """
    Tâche d'arrière-plan pour le calcul asynchrone des KPIs (qui peut être long).
    Permet à l'API de répondre immédiatement (202 Accepted).
    """
    try:
        logger.info(f"Début du calcul asynchrone des KPIs pour {month}/{year}")
        await compute_global_kpis(db, year, month)
        logger.info("Calcul asynchrone des KPIs terminé avec succès.")
    except Exception as e:
        logger.error(f"Échec du calcul asynchrone des KPIs : {e}")
