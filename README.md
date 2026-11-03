# HumanAI — assistant RH intelligent

Projet **Ydays 2026** : plateforme RH qui automatise l'onboarding et l'offboarding, gère les documents RH et répond aux questions des employés grâce à un assistant IA (RAG) appuyé sur la base documentaire de l'entreprise.

## Contenu

| Dossier | Rôle |
|---|---|
| `Backend/` | API **FastAPI** : authentification (Firebase), documents, RAG, workflows d'onboarding et d'offboarding, analytique, administration, journal d'audit, garde-fous de sécurité |
| `ia_rh/` | Prototype du module IA RH (API, journaux, données d'exemple) |
| `Document_projet/` | Cahier des charges, architecture de la base, documentation API et DevOps, présentation |
| `humanai_schema.sql` | Schéma de la base |

Stack : Python, FastAPI, SQLAlchemy (asyncio), PostgreSQL, Redis, MinIO, Firebase, OpenAI ou Anthropic (LLM).

## Démarrer (API)

```bash
cd Backend
cp .env.example .env        # renseigner les variables
pip install -r requirements.txt
uvicorn app.main:app --reload
```

> ⚠️ `Backend/.env`, `Backend/constfirebase.txt` et `Backend/humanai.db` sont versionnés dans ce dépôt public. S'ils contiennent de vraies clés, il faut les révoquer, puis retirer ces fichiers du dépôt et de son historique.

> Licence : aucune licence n'est déclarée dans ce dépôt (tous droits réservés par défaut).
