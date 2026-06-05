"""
cache.py
--------
Module de gestion du cache Redis pour alléger la charge de la base de données
et accélérer les temps de réponse sur les calculs coûteux (KPIs, requêtes RAG répétées).
"""
import json
import logging
from typing import Any, Optional

import redis.asyncio as redis
from app.config.config import settings

logger = logging.getLogger(__name__)

# Initialisation du client Redis
# On utilise decode_responses=True pour récupérer des strings directement
try:
    redis_client = redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True
    )
except Exception as e:
    logger.warning(f"Impossible d'initialiser Redis: {e}")
    redis_client = None


async def get_cache(key: str) -> Optional[Any]:
    """Récupère une valeur du cache Redis."""
    if not redis_client:
        return None
        
    try:
        val = await redis_client.get(key)
        if val:
            return json.loads(val)
        return None
    except Exception as e:
        logger.error(f"Erreur de lecture Redis pour la clé {key}: {e}")
        return None


async def set_cache(key: str, value: Any, expire_seconds: int = 3600) -> bool:
    """Enregistre une valeur dans le cache Redis avec une durée de vie (TTL)."""
    if not redis_client:
        return False
        
    try:
        val_str = json.dumps(value)
        await redis_client.set(key, val_str, ex=expire_seconds)
        return True
    except Exception as e:
        logger.error(f"Erreur d'écriture Redis pour la clé {key}: {e}")
        return False


async def delete_cache(key: str) -> bool:
    """Supprime une clé du cache."""
    if not redis_client:
        return False
        
    try:
        await redis_client.delete(key)
        return True
    except Exception as e:
        logger.error(f"Erreur de suppression Redis pour la clé {key}: {e}")
        return False
