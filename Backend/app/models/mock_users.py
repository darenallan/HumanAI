"""
mock_users.py
-------------
Store in-memory — 3 utilisateurs de test avec rôles différents.
Séparé des modèles ORM pour éviter les imports circulaires avec security.py.
À supprimer quand la BDD PostgreSQL sera en place.
"""
from __future__ import annotations

from app.schemas.users import UserInDB, Role
from app.core.security import hash_password


_MOCK_USERS = [
    {
        "id":        "usr_001",
        "email":     "alice@rh-corp.com",
        "full_name": "Alice Dupont",
        "role":      Role.RH,
        "password":  "RH@Secure2025!",
        "is_active": True,
    },
    {
        "id":        "usr_002",
        "email":     "bob@rh-corp.com",
        "full_name": "Bob Martin",
        "role":      Role.MANAGER,
        "password":  "Manager@Secure2025!",
        "is_active": True,
    },
    {
        "id":        "usr_003",
        "email":     "admin@rh-corp.com",
        "full_name": "Admin Système",
        "role":      Role.ADMIN,
        "password":  "Admin@Secure2025!",
        "is_active": True,
    },
]

USERS_DB: dict[str, UserInDB] = {}


def _init() -> None:
    for u in _MOCK_USERS:
        USERS_DB[u["email"]] = UserInDB(
            id=u["id"],
            email=u["email"],
            full_name=u["full_name"],
            role=u["role"],
            is_active=u["is_active"],
            password_hash=hash_password(u["password"]),
        )


_init()


def get_user_by_email(email: str) -> UserInDB | None:
    return USERS_DB.get(email.lower().strip())


def get_user_by_id(user_id: str) -> UserInDB | None:
    return next((u for u in USERS_DB.values() if u.id == user_id), None)


def increment_failed_attempts(email: str) -> None:
    user = USERS_DB.get(email)
    if user:
        user.failed_attempts += 1


def reset_failed_attempts(email: str) -> None:
    user = USERS_DB.get(email)
    if user:
        user.failed_attempts = 0


def list_users() -> list[UserInDB]:
    return list(USERS_DB.values())
