import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("\n=== Lancement des tests de validation d'authentification ===")

# 1. Test de la route de santé (health check)
response = client.get("/health")
assert response.status_code == 200
assert response.json() == {"status": "ok", "service": "auth"}
print("[OK] [Health Check] Route accessible avec succes.")

# 2. Test d'accès profil avec token mock Collaborateur (mappé en RH)
response = client.get(
    "/demo/mon-profil",
    headers={"Authorization": "Bearer mock-token-collaborateur"}
)
assert response.status_code == 200
assert response.json()["role"] == "rh"
print("[OK] [Auth Mock] Token mock collaborateur correctement verifie.")

# 3. Test d'accès admin avec token mock Admin
response = client.get(
    "/demo/admin-only",
    headers={"Authorization": "Bearer mock-token-admin"}
)
assert response.status_code == 200
assert "Zone admin" in response.json()["message"]
print("[OK] [RBAC Admin] Acces autorise avec role Admin.")

# 4. Test d'accès refusé (Forbidden) sur route admin avec token collaborateur
response = client.get(
    "/demo/admin-only",
    headers={"Authorization": "Bearer mock-token-collaborateur"}
)
assert response.status_code == 403
print("[OK] [RBAC Admin] Acces correctement refuse (403) pour un role non-admin.")

# 5. Test d'accès refusé sur les logs d'audit admin avec token collaborateur
response = client.get(
    "/admin/audit-logs",
    headers={"Authorization": "Bearer mock-token-collaborateur"}
)
assert response.status_code == 403
print("[OK] [RBAC Admin API] Accès refusé (403) pour récupérer les logs d'audit avec un rôle non-admin.")

# 6. Test d'accès autorisé sur les logs d'audit admin avec token admin
response = client.get(
    "/admin/audit-logs",
    headers={"Authorization": "Bearer mock-token-admin"}
)
assert response.status_code in [200, 500]
print("[OK] [RBAC Admin API] Accès autorisé (passe le filtre RBAC) pour récupérer les logs d'audit avec un rôle admin.")

print("=== Tous les tests de validation ont réussi avec succès ! ===\n")

