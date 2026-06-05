"""
router.py
---------
Routes d'authentification :
  POST /auth/login    — connexion, retourne access + refresh token
  POST /auth/refresh  — rotation du refresh token
  POST /auth/logout   — révocation de l'access token
  GET  /auth/me       — profil de l'utilisateur connecté
"""
from __future__ import annotations
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from fastapi.security import OAuth2PasswordBearer

from app.config.config import settings
from app.core.security import (
    get_current_user,
    oauth2_scheme,
    create_access_token,
    create_refresh_token,
    decode_token,
    is_revoked,
    revoke_token,
    verify_password,
    JWTError,
)
from app.schemas.users import LoginRequest, RefreshRequest, Token, UserOut
from app.models.mock_users import (
    get_user_by_email,
    get_user_by_id,
    increment_failed_attempts,
    reset_failed_attempts,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ── Rate limiter in-memory (→ Redis en production) ────────────────────────────
_ip_log: dict[str, list[float]] = {}


def _check_rate_limit(ip: str) -> None:
    now = datetime.now(timezone.utc).timestamp()
    window = [t for t in _ip_log.get(ip, []) if now - t < 60]
    if len(window) >= settings.MAX_LOGIN_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de tentatives de connexion. Réessayez dans 60 secondes.",
        )
    window.append(now)
    _ip_log[ip] = window


# ── /login ────────────────────────────────────────────────────────────────────
@router.post("/login", response_model=Token)
async def login(request: Request, body: LoginRequest) -> Token:
    _check_rate_limit(request.client.host)

    # Message générique — ne pas révéler si l'email existe
    _invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Email ou mot de passe incorrect",
    )

    user = get_user_by_email(body.email)
    if not user:
        raise _invalid

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Compte désactivé")

    if user.failed_attempts >= settings.MAX_FAILED_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Compte verrouillé après trop d'échecs. Contactez l'administrateur.",
        )

    if not verify_password(body.password, user.password_hash):
        increment_failed_attempts(body.email)
        raise _invalid

    reset_failed_attempts(body.email)

    access_token, _  = create_access_token(user.id, user.email, user.role)
    refresh_token, _ = create_refresh_token(user.id, user.email, user.role)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
        ),
    )


# ── /refresh ──────────────────────────────────────────────────────────────────
@router.post("/refresh", response_model=Token)
async def refresh(body: RefreshRequest) -> Token:
    _invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token invalide ou expiré",
    )

    try:
        payload = decode_token(body.refresh_token)
    except JWTError:
        raise _invalid

    if payload.get("type") != "refresh":
        raise _invalid

    jti = payload.get("jti")
    if not jti or is_revoked(jti):
        raise _invalid

    user = get_user_by_id(payload.get("sub", ""))
    if not user or not user.is_active:
        raise _invalid

    # Rotation : on révoque l'ancien refresh token
    revoke_token(jti)

    access_token, _      = create_access_token(user.id, user.email, user.role)
    new_refresh_token, _ = create_refresh_token(user.id, user.email, user.role)

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
        ),
    )


# ── /logout ───────────────────────────────────────────────────────────────────
@router.post("/logout")
async def logout(
    _: UserOut = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
) -> Response:
    try:
        payload = decode_token(token)
        jti = payload.get("jti")
        if jti:
            revoke_token(jti)
    except JWTError:
        pass
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── /me ───────────────────────────────────────────────────────────────────────
@router.get("/me", response_model=UserOut)
async def me(current_user: UserOut = Depends(get_current_user)) -> UserOut:
    return current_user
