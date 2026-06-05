"""
populate_rag.py
---------------
Script d'initialisation pour charger et vectoriser des documents RH de test dans la base RAG.
Usage : python scripts/populate_rag.py
"""
import sys
import os
import asyncio
import logging

# Ajouter le dossier parent au path pour pouvoir importer le module app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.config import settings
from app.core.database import _get_async_session_factory, close_async_engine
from app.services.rag import ingest_document
from app.models.enums import RoleEnum
from app.models.rag import RAGDocument
from sqlalchemy import select

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("scripts.populate_rag")

MOCK_DOCUMENTS = [
    {
        "title": "Règlement Intérieur HumaNai 2026",
        "filename": "reglement_interieur_2026.txt",
        "roles": [RoleEnum.COLLABORATEUR, RoleEnum.MANAGER, RoleEnum.RH, RoleEnum.DIRECTION, RoleEnum.ADMIN],
        "content": """REGLEMENT INTERIEUR DE HUMANAI
Dernière mise à jour : Janvier 2026.

1. HORAIRES DE TRAVAIL & PRESENCE
Les horaires de travail habituels sont de 9h00 à 18h00, avec une heure de pause déjeuner flexible entre 12h00 et 14h00.
Toute absence non planifiée doit être signalée au responsable direct et au service RH avant 10h00 le jour même. Les justificatifs d'absence (certificat médical, etc.) doivent être transmis sous 48 heures.

2. TELETRAVAIL
La politique de télétravail autorise jusqu'à 2 jours de télétravail par semaine pour les postes éligibles, après accord du manager. Un forfait d'équipement de 150 EUR est alloué lors de l'intégration pour l'aménagement du poste de travail à domicile.

3. SECURITE ET CONFIDENTIALITE
Tous les collaborateurs ont l'obligation de verrouiller leur session informatique dès qu'ils s'éloignent de leur poste de travail. L'usage de supports externes non approuvés par l'équipe IT (clés USB, disques durs) est strictement interdit sur le réseau de l'entreprise.
Toutes les données relatives aux clients et aux collaborateurs sont strictement confidentielles et régies par notre charte RGPD interne.
"""
    },
    {
        "title": "Guide de la Mutuelle Santé Collective",
        "filename": "guide_mutuelle_sante.txt",
        "roles": [RoleEnum.COLLABORATEUR, RoleEnum.MANAGER, RoleEnum.RH, RoleEnum.DIRECTION, RoleEnum.ADMIN],
        "content": """GUIDE DE LA MUTUELLE SANTE COLLECTIVE - AXA / HUMANAI
Mise à jour : 2026.

L'entreprise HumaNai fournit à l'ensemble de ses salariés une complémentaire santé collective obligatoire à compter de leur premier jour d'intégration.

1. TAUX DE COTISATION & PARTICIPATION EMPLOYEUR
La cotisation mensuelle de base est prise en charge à hauteur de 60% par HumaNai et 40% par le salarié (prélevé directement sur le bulletin de paie).
Cotisation isolée (salarié seul) : 55 EUR / mois (Part employeur : 33 EUR, Part salarié : 22 EUR).
Option famille (conjoint et enfants) : +40 EUR / mois (Prise en charge à 50% par l'employeur).

2. REMBOURSEMENTS MAJEURS
- Soins de médecine générale : Remboursement à 100% de la base de remboursement de la Sécurité Sociale.
- Optique : Forfait annuel de 300 EUR pour les montures et verres simples, et jusqu'à 500 EUR pour les verres complexes.
- Dentaire : Prise en charge des soins courants à 100% et forfait couronne de 450 EUR par dent.
- Médecines douces (ostéopathie, psychologie) : Remboursement de 4 séances par an à hauteur de 40 EUR par séance.
"""
    },
    {
        "title": "Charte RH - Avantages et QVT",
        "filename": "charte_qvt_2026.txt",
        "roles": [RoleEnum.COLLABORATEUR, RoleEnum.MANAGER, RoleEnum.RH, RoleEnum.DIRECTION, RoleEnum.ADMIN, RoleEnum.QVT],
        "content": """CHARTE QUALITE DE VIE AU TRAVAIL (QVT) ET AVANTAGES SOCIAUX
Année de référence : 2026.

Chez HumaNai, la santé physique et mentale de nos collaborateurs est au cœur de nos priorités.

1. TITRES RESTAURANT (TICKET RESTO)
Chaque collaborateur bénéficie de titres-restaurant d'une valeur faciale de 10 EUR par jour travaillé. L'employeur prend en charge 60% de cette valeur (soit 6 EUR par jour), le reste étant à la charge du collaborateur (4 EUR par jour).

2. SPORT ET BIEN-ETRE
- Abonnement Gymlib : Prise en charge à hauteur de 50% sur l'abonnement mensuel de sport.
- Fruits frais : Des corbeilles de fruits frais biologiques sont livrées chaque mardi et jeudi dans les espaces communs.
- Soutien psychologique : L'accès à la plateforme d'écoute et de soutien psychologique "Moka.care" est 100% gratuit et anonyme pour tous les salariés.

3. CONGES SPECIAUX ET FAMILLE
- Congé second parent : HumaNai maintient à 100% le salaire net des collaborateurs durant l'intégralité du congé de paternité et d'accueil de l'enfant.
- Congé enfant malade : Attribution de 3 jours de congés rémunérés par an par enfant de moins de 12 ans sur présentation d'un justificatif médical.
"""
    }
]

async def main():
    logger.info("Démarrage du script d'initialisation du RAG...")
    
    # Importer tous les modèles pour être sûr qu'ils soient enregistrés sur Base
    import app.models
    
    from app.core.database import Base, _get_async_engine
    
    engine = _get_async_engine()
    if engine is not None:
        logger.info("Création des tables dans la base de données...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
    session_factory = _get_async_session_factory()
    if session_factory is None:
        logger.error("La session de base de données n'a pas pu être initialisée. Vérifiez DATABASE_URL dans votre fichier .env.")
        sys.exit(1)
        
    async with session_factory() as db:
        for doc_info in MOCK_DOCUMENTS:
            # Vérifier si le document existe déjà en base pour éviter les doublons
            stmt = select(RAGDocument).where(RAGDocument.title == doc_info["title"])
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                logger.info(f"Le document '{doc_info['title']}' existe déjà en base de données. Passage.")
                continue
                
            logger.info(f"Ingestion du document : {doc_info['title']}...")
            try:
                # Convertir le contenu texte en bytes
                content_bytes = doc_info["content"].encode("utf-8")
                
                # Appeler le service d'ingestion RAG
                doc = await ingest_document(
                    db=db,
                    title=doc_info["title"],
                    file_bytes=content_bytes,
                    filename=doc_info["filename"],
                    allowed_roles=doc_info["roles"]
                )
                await db.commit()
                logger.info(f"✔ Document '{doc_info['title']}' ingéré avec succès (ID: {doc.id})")
            except Exception as e:
                await db.rollback()
                logger.error(f"✖ Échec de l'ingestion pour '{doc_info['title']}' : {str(e)}")
                
    # Fermer le moteur
    await close_async_engine()
    logger.info("Script d'initialisation du RAG terminé.")

if __name__ == "__main__":
    asyncio.run(main())
