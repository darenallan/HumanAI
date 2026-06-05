from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr


# ── Rôles RBAC ────────────────────────────────────────────────────────────────
class Role(str, Enum):
    COLLABORATEUR = "collaborateur"
    MANAGER       = "manager"
    RH            = "rh"
    DIRECTION     = "direction"
    ADMIN         = "admin"
    QVT           = "qvt"


# ── User ──────────────────────────────────────────────────────────────────────
class UserOut(BaseModel):
    """Données utilisateur retournées à l'API (sans données sensibles)."""
    id: str
    email: str
    full_name: str
    role: Role
    is_active: bool
    department_id: str | None = None   # nécessaire pour le RLS PostgreSQL
    firebase_uid: str | None = None    # UID Firebase (si authentifié via Firebase)


class UserInDB(UserOut):
    """User complet en base (mémoire pour l'instant)."""
    password_hash: str
    failed_attempts: int = 0
    locked_until: Optional[str] = None  # ISO datetime si verrouillé


# ── Auth ──────────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int   # secondes avant expiration de l'access token
    user: UserOut


class TokenPayload(BaseModel):
    sub: str          # user_id
    email: str
    role: str
    jti: str          # JWT ID — utilisé pour la blacklist
    type: str         # "access" | "refresh"
