"""
security.py
-----------
Module de sécurité centralisé pour l'application HumaNai.

Contient :
  - Hashing argon2id (OWASP 2024)
  - Création / vérification JWT (access + refresh)
  - Blacklist in-memory des tokens révoqués (→ Redis en production)
  - Dépendance FastAPI `get_current_user` : authentification unifiée
    (Firebase ID token → JWT local → Mock dev)
  - Factory `require_roles(...)` : vérification RBAC
"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from jose import jwt, JWTError as _JWTError
from firebase_admin import auth as firebase_auth

from app.config.config import settings

JWTError = _JWTError  # alias propre pour les imports externes
logger = logging.getLogger("app.core.security")


# ══════════════════════════════════════════════════════════════════════════════
#  Argon2id — Hashing de mots de passe (OWASP 2024)
# ══════════════════════════════════════════════════════════════════════════════

_ph = PasswordHasher(
    time_cost=2,        # 2 itérations
    memory_cost=65536,  # 64 MB
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


# ══════════════════════════════════════════════════════════════════════════════
#  JWT — Tokens d'accès et de rafraîchissement
# ══════════════════════════════════════════════════════════════════════════════

def _build_token(user_id: str, email: str, role: str, token_type: str, expire: datetime) -> tuple[str, str]:
    """Construit un JWT signé. Retourne (token, jti)."""
    jti = str(uuid.uuid4())
    payload = {
        "sub":   user_id,
        "email": email,
        "role":  role,
        "jti":   jti,
        "type":  token_type,
        "exp":   expire,
        "iat":   datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti


def create_access_token(user_id: str, email: str, role: str) -> tuple[str, str]:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return _build_token(user_id, email, role, "access", expire)


def create_refresh_token(user_id: str, email: str, role: str) -> tuple[str, str]:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return _build_token(user_id, email, role, "refresh", expire)


def decode_token(token: str) -> dict:
    """Décode et valide un JWT. Lève JWTError si invalide/expiré."""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


# ══════════════════════════════════════════════════════════════════════════════
#  Blacklist in-memory (→ Redis SADD/SISMEMBER en production)
# ══════════════════════════════════════════════════════════════════════════════

_REVOKED_JTIS: set[str] = set()


def revoke_token(jti: str) -> None:
    _REVOKED_JTIS.add(jti)


def is_revoked(jti: str) -> bool:
    return jti in _REVOKED_JTIS


# ══════════════════════════════════════════════════════════════════════════════
#  Dépendances FastAPI — Authentification & RBAC
# ══════════════════════════════════════════════════════════════════════════════

from fastapi import Depends, HTTPException, status  # noqa: E402
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials  # noqa: E402

from app.schemas.users import UserOut  # noqa: E402

# Import différé du mock store pour éviter les imports circulaires
_mock_store = None


def _get_mock_store():
    """Charge le store mock à la demande (lazy import)."""
    global _mock_store
    if _mock_store is None:
        from app.models import mock_users
        _mock_store = mock_users
    return _mock_store


# Schémas de récupération du token Bearer
security_scheme = HTTPBearer(auto_error=False)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def _extract_token(
    credentials: HTTPAuthorizationCredentials | None,
    oauth2_token: str | None,
) -> str:
    """Extrait le token Bearer depuis les headers HTTP."""
    if credentials:
        return credentials.credentials
    if oauth2_token:
        return oauth2_token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token d'authentification manquant",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ── Stratégie 1 : Mock tokens (développement uniquement) ─────────────────────

_MOCK_TOKEN_MAP = {
    "collaborateur": "alice@rh-corp.com",
    "buyer":         "alice@rh-corp.com",
    "client":        "alice@rh-corp.com",
    "manager":       "bob@rh-corp.com",
    "seller":        "bob@rh-corp.com",
    "vendeur":       "bob@rh-corp.com",
    "admin":         "admin@rh-corp.com",
    "rh":            "alice@rh-corp.com",
}


def _try_mock_auth(token: str) -> UserOut | None:
    """
    Authentification mock pour le développement local.
    Activée UNIQUEMENT si settings.DEBUG est True.
    Tokens acceptés : 'mock-token-{role}' ou 'mock-id-token'.
    """
    if not settings.DEBUG:
        return None

    if not (token.startswith("mock-token-") or token == "mock-id-token"):
        return None

    logger.debug("Mode MOCK activé (DEBUG=True) — token : %s", token)

    # Déterminer l'email mock à partir du suffixe du token
    email = "admin@rh-corp.com"  # défaut
    token_lower = token.lower()
    for keyword, mapped_email in _MOCK_TOKEN_MAP.items():
        if keyword in token_lower:
            email = mapped_email
            break

    # Vérifier aussi si le token contient directement un nom d'utilisateur
    for test_email in ["alice@rh-corp.com", "bob@rh-corp.com", "admin@rh-corp.com"]:
        if test_email.split("@")[0] in token_lower:
            email = test_email

    store = _get_mock_store()
    user = store.get_user_by_email(email)
    if not user:
        return None

    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
    )


# ── Stratégie 2 : Firebase ID Token + Custom Claims ──────────────────────────

def _try_firebase_auth(token: str) -> UserOut | None:
    """
    Vérifie un Firebase ID token et extrait les Custom Claims (role, dept_id).

    Flux conforme à la documentation DevOps :
      1. Vérification du token via firebase_admin.auth.verify_id_token()
      2. Extraction des Custom Claims : role, dept_id
      3. Recherche de l'utilisateur en base locale par email
      4. Retour d'un UserOut enrichi avec department_id et firebase_uid

    Si le rôle n'est pas dans les Custom Claims Firebase, on utilise
    le rôle stocké en base locale (fallback pour la transition).
    """
    try:
        decoded = firebase_auth.verify_id_token(token)
    except Exception as e:
        logger.debug("Token non-Firebase ou invalide : %s", e)
        return None

    email = decoded.get("email")
    firebase_uid = decoded.get("uid")

    if not email:
        logger.warning("Token Firebase valide mais sans email — uid=%s", firebase_uid)
        return None

    # Extraction des Custom Claims Firebase (définis par set-custom-claims.js)
    firebase_role = decoded.get("role")       # ex: 'rh', 'manager', 'collaborateur'
    firebase_dept_id = decoded.get("dept_id")  # ex: 'dept-456'

    # Recherche de l'utilisateur en base locale
    store = _get_mock_store()
    user = store.get_user_by_email(email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Utilisateur Firebase ({email}) non enregistré en base locale. "
                   f"Contactez l'administrateur pour créer votre profil.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé",
        )

    # Le rôle Firebase Custom Claim a priorité sur le rôle en base locale
    effective_role = firebase_role if firebase_role else user.role

    logger.info(
        "Authentification Firebase réussie — email=%s, uid=%s, role=%s (claim=%s)",
        email, firebase_uid, effective_role, firebase_role,
    )

    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=effective_role,
        is_active=user.is_active,
        department_id=firebase_dept_id,
        firebase_uid=firebase_uid,
    )


# ── Stratégie 3 : JWT local (access token signé par le backend) ──────────────

def _try_jwt_auth(token: str) -> UserOut | None:
    """
    Décode un JWT local (access token) signé par le backend.
    Vérifie l'expiration, le type et la blacklist.
    """
    try:
        payload = decode_token(token)
    except JWTError:
        return None

    if payload.get("type") != "access":
        return None

    jti = payload.get("jti")
    if not jti or is_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token révoqué — veuillez vous reconnecter",
            headers={"WWW-Authenticate": "Bearer"},
        )

    store = _get_mock_store()
    user = store.get_user_by_id(payload.get("sub", ""))
    if not user or not user.is_active:
        return None

    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Dépendance principale : get_current_user
# ══════════════════════════════════════════════════════════════════════════════

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    oauth2_token: str | None = Depends(oauth2_scheme),
) -> UserOut:
    """
    Dépendance d'authentification unifiée pour toutes les routes.

    Ordre d'évaluation :
      1. Mock tokens (si DEBUG=True) — développement local hors-ligne
      2. Firebase ID Token — vérification + extraction Custom Claims
      3. JWT local — access token signé par le backend

    Retourne un UserOut enrichi avec department_id et firebase_uid
    pour permettre l'injection du contexte RLS dans les routes.
    """
    token = _extract_token(credentials, oauth2_token)

    # 1. Mock (développement uniquement)
    result = _try_mock_auth(token)
    if result:
        return result

    # 2. Firebase ID Token
    result = _try_firebase_auth(token)
    if result:
        return result

    # 3. JWT local
    result = _try_jwt_auth(token)
    if result:
        return result

    # Aucune stratégie n'a fonctionné
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Factory RBAC : require_roles(...)
# ══════════════════════════════════════════════════════════════════════════════

def require_roles(*roles: str):
    """
    Dependency factory RBAC.

    Usage :
        @router.get("/rh/rapports")
        async def rapport(user = Depends(require_roles("rh", "admin"))):
            ...
    """
    async def _check(current_user: UserOut = Depends(get_current_user)) -> UserOut:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accès refusé. Rôles autorisés : {', '.join(roles)}",
            )
        return current_user
    return _check
