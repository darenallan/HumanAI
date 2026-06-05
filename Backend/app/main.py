"""
main.py
-------
Point d'entrée de l'application.
Inclut le router d'auth + 3 routes démo pour illustrer le RBAC.
"""
from fastapi import FastAPI, Depends
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.core.security import get_current_user, require_roles
from app.schemas.users import UserOut
from app.core.firebase import init_firebase
from app.config.config import settings

# Initialiser le SDK Firebase Admin
init_firebase(settings.FIREBASE_CREDENTIALS_PATH)

app = FastAPI(
    title="Plateforme IA RH — Auth Service",
    description="JWT (access 15min + refresh 7j) · argon2id · RBAC · Blacklist",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
from app.api.v1.rag import router as rag_router
app.include_router(rag_router)

from app.api.v1.documents import router as documents_router
app.include_router(documents_router)

from app.api.v1.workflows import router as workflows_router
app.include_router(workflows_router)

from app.api.v1.analytics import router as analytics_router
app.include_router(analytics_router)

from app.api.v1.admin import router as admin_router
app.include_router(admin_router)


@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/docs")


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "service": "auth"}


# ── Routes démo RBAC ──────────────────────────────────────────────────────────
# Ces routes montrent comment utiliser require_roles() dans les autres modules.

@app.get("/demo/mon-profil", tags=["Demo RBAC"])
async def demo_profil(user: UserOut = Depends(get_current_user)):
    """Accessible par tous les rôles (token valide suffit)."""
    return {"message": f"Bonjour {user.full_name}", "role": user.role}


@app.get("/demo/tableau-de-bord-manager", tags=["Demo RBAC"])
async def demo_manager(user: UserOut = Depends(require_roles("manager", "rh", "admin"))):
    """Accessible uniquement par manager, rh ou admin."""
    return {"message": f"Dashboard manager — accès autorisé pour {user.full_name}", "role": user.role}


@app.get("/demo/espace-rh", tags=["Demo RBAC"])
async def demo_rh(user: UserOut = Depends(require_roles("rh", "admin"))):
    """Accessible uniquement par rh ou admin."""
    return {"message": f"Espace RH — accès autorisé pour {user.full_name}", "role": user.role}


@app.get("/demo/admin-only", tags=["Demo RBAC"])
async def demo_admin(user: UserOut = Depends(require_roles("admin"))):
    """Accessible uniquement par admin."""
    return {"message": f"Zone admin — accès autorisé pour {user.full_name}", "role": user.role}
