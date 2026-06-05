"""
database.py
-----------
Connexion asynchrone à PostgreSQL via SQLAlchemy 2.0.
Inclut :
- Moteur async (create_async_engine) pour FastAPI
- Moteur sync optionnel (create_engine) pour Alembic / scripts utilitaires
- Classe de base déclarative (Base) pour les modèles ORM
- Dépendance FastAPI `get_db` : générateur de session async
- Helper `set_rls_context` : injecte le contexte utilisateur dans la
  session PostgreSQL pour activer le Row-Level Security (RLS)
"""
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass

from sqlalchemy import create_engine, text, event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from app.config.config import settings

import sqlite3
import json

sqlite3.register_adapter(list, lambda l: json.dumps(l))
sqlite3.register_adapter(dict, lambda d: json.dumps(d))

logger = logging.getLogger("app.core.database")


# ── Compatibilité SQLite pour le développement local ───────────────────────
import json
from sqlalchemy.types import TypeDecorator, TEXT, JSON
from sqlalchemy.dialects import postgresql

class SafeArray(TypeDecorator):
    impl = TEXT
    cache_ok = True

    def __init__(self, item_type, *args, **kwargs):
        self.item_type = item_type
        super().__init__(*args, **kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            # On récupère le vrai ARRAY de PG en évitant la récursion infinie
            from sqlalchemy.dialects.postgresql.array import ARRAY as PG_ARRAY
            return dialect.type_descriptor(PG_ARRAY(self.item_type))
        return dialect.type_descriptor(TEXT())

    def process_bind_param(self, value, dialect):
        if dialect.name == "postgresql":
            return value
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if dialect.name == "postgresql":
            return value
        if value is None:
            return None
        try:
            return json.loads(value)
        except Exception:
            return []

class SafeJSONB(TypeDecorator):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql.json import JSONB as PG_JSONB
            return dialect.type_descriptor(PG_JSONB())
        return dialect.type_descriptor(JSON())

# Appliquer le monkeypatch avant l'import des modèles par l'application
postgresql.ARRAY = SafeArray
postgresql.JSONB = SafeJSONB


# ── Génération automatique des UUIDs en Python pour SQLite/Compatibilité ───
@event.listens_for(Session, "before_flush")
def generate_uuids_before_flush(session, flush_context, instances):
    import uuid
    for obj in session.new:
        mapper = obj.__mapper__
        for key, column in mapper.columns.items():
            if column.primary_key and "uuid" in str(column.type).lower():
                if getattr(obj, key) is None:
                    setattr(obj, key, uuid.uuid4())


# ── Classe de base pour les modèles ORM ──────────────────────────────────────
class Base(DeclarativeBase):
    """Classe de base déclarative SQLAlchemy 2.0 pour tous les modèles."""
    pass


# ── Moteur asynchrone (utilisé par FastAPI) ───────────────────────────────────
_async_engine = None
_async_session_factory = None


def _get_async_engine():
    global _async_engine
    if _async_engine is None and settings.DATABASE_URL:
        _async_engine = create_async_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            echo=settings.DEBUG,
            pool_size=10,
            max_overflow=20,
        )
        if "sqlite" in settings.DATABASE_URL:
            @event.listens_for(_async_engine.sync_engine, "connect")
            def register_sqlite_functions(dbapi_connection, connection_record):
                import uuid
                dbapi_connection.create_function("gen_random_uuid", 0, lambda: str(uuid.uuid4()))
        logger.info("Moteur async initialisé : %s", settings.DATABASE_URL.split("@")[-1])
    return _async_engine


def _get_async_session_factory():
    global _async_session_factory
    engine = _get_async_engine()
    if _async_session_factory is None and engine is not None:
        _async_session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


# ── Moteur synchrone (utilisé par Alembic / scripts) ─────────────────────────
_sync_engine = None
_sync_session_factory = None


def get_sync_engine():
    global _sync_engine
    if _sync_engine is None and settings.DATABASE_URL_SYNC:
        _sync_engine = create_engine(
            settings.DATABASE_URL_SYNC,
            pool_pre_ping=True,
            echo=settings.DEBUG,
        )
        if "sqlite" in settings.DATABASE_URL_SYNC:
            @event.listens_for(_sync_engine, "connect")
            def register_sqlite_functions_sync(dbapi_connection, connection_record):
                import uuid
                dbapi_connection.create_function("gen_random_uuid", 0, lambda: str(uuid.uuid4()))
    return _sync_engine


def get_sync_session_factory():
    global _sync_session_factory
    engine = get_sync_engine()
    if _sync_session_factory is None and engine is not None:
        _sync_session_factory = sessionmaker(
            autocommit=False, autoflush=False, bind=engine
        )
    return _sync_session_factory


# ── Dépendance FastAPI (générateur de session async) ──────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dépendance FastAPI qui ouvre une session async par requête HTTP
    et la ferme automatiquement à la fin.
    """
    factory = _get_async_session_factory()
    if factory is None:
        # Fallback : pas de BDD configurée (mode mock)
        logger.warning("DATABASE_URL non configurée — session BDD non disponible.")
        yield None  # type: ignore[arg-type]
        return

    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Intercepteur RLS (Row-Level Security) ─────────────────────────────────────
@dataclass
class RLSContext:
    """Contexte utilisateur injecté dans la session PostgreSQL pour le RLS."""
    user_id: str
    role: str
    department_id: str = ""


async def set_rls_context(session: AsyncSession, ctx: RLSContext) -> None:
    """
    Configure les variables de session PostgreSQL utilisées par les
    politiques Row-Level Security (RLS).

    Doit être appelé au début de chaque transaction après authentification.
    Les valeurs sont valides pour la durée de la transaction courante
    grâce à SET LOCAL.

    Paramètres :
        session  — la session async SQLAlchemy courante
        ctx      — le contexte utilisateur (id, rôle, département)
    """
    if session is None:
        return

    await session.execute(
        text("SET LOCAL app.current_user_id = :uid"),
        {"uid": ctx.user_id},
    )
    await session.execute(
        text("SET LOCAL app.current_role = :role"),
        {"role": ctx.role},
    )
    await session.execute(
        text("SET LOCAL app.current_dept_id = :dept_id"),
        {"dept_id": ctx.department_id},
    )
    logger.debug(
        "RLS context défini — user=%s, role=%s, dept=%s",
        ctx.user_id, ctx.role, ctx.department_id,
    )


# ── Utilitaires de cycle de vie ───────────────────────────────────────────────
async def close_async_engine() -> None:
    """Ferme proprement le moteur async (à appeler au shutdown de l'app)."""
    global _async_engine, _async_session_factory
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
        _async_session_factory = None
        logger.info("Moteur PostgreSQL async fermé.")