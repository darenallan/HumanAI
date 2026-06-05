import os
import logging
import firebase_admin
from firebase_admin import credentials

logger = logging.getLogger("app.core.firebase")

firebase_app = None

def init_firebase(credentials_path: str | None = None) -> bool:
    """
    Initialise le SDK Firebase Admin.
    Si le chemin vers le fichier de compte de service est fourni et existe,
    il est utilisé. Sinon, le SDK tente de se connecter via les variables d'environnement par défaut.
    """
    global firebase_app
    if firebase_app is not None:
        return True

    try:
        resolved_path = None
        if credentials_path:
            if os.path.isabs(credentials_path):
                resolved_path = credentials_path
            else:
                # Essayer par rapport au répertoire de travail courant (CWD)
                cwd_path = os.path.join(os.getcwd(), credentials_path)
                if os.path.exists(cwd_path):
                    resolved_path = cwd_path
                else:
                    # Essayer par rapport au dossier parent de app (racine du projet)
                    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    project_path = os.path.join(base_dir, credentials_path)
                    if os.path.exists(project_path):
                        resolved_path = project_path

        if resolved_path and os.path.exists(resolved_path):
            logger.info(f"Initialisation de Firebase avec le compte de service : {resolved_path}")
            cred = credentials.Certificate(resolved_path)
            firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialisé avec succès via fichier de compte de service.")
            return True
        else:
            # Tenter l'initialisation sans arguments (identifiants par défaut Google/Firebase)
            logger.info("Initialisation de Firebase avec les identifiants par défaut...")
            firebase_app = firebase_admin.initialize_app()
            logger.info("Firebase Admin SDK initialisé avec succès via les identifiants par défaut.")
            return True
    except Exception as e:
        logger.warning(
            f"Impossible d'initialiser Firebase Admin SDK : {e}. "
            "Le backend utilisera le mode Mock / Fallback si configuré."
        )
        return False

def get_firebase_app():
    return firebase_app
