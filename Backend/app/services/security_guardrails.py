"""
security_guardrails.py
----------------------
Module de sécurité IA :
  - Guardrails d'entrée (détection d'injections de prompt)
  - Guardrails de sortie (filtrage sémantique anti-fuite de données)
  - Journalisation des alertes de sécurité IA
"""
import uuid
import re
from typing import Tuple, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.logs import AISecurityEvent, AIInteraction
from app.models.analytics import HRAlert
from app.models.enums import SecurityEventTypeEnum, AlertSeverityEnum


async def trigger_ai_security_alert(
    db: AsyncSession,
    interaction_id: uuid.UUID,
    event_type: SecurityEventTypeEnum,
    severity: AlertSeverityEnum,
    details: str
):
    """Enregistre un événement de sécurité IA et génère une alerte globale si nécessaire."""
    
    # Création de l'événement lié à l'interaction
    event = AISecurityEvent(
        interaction_id=interaction_id,
        event_type=event_type,
        severity=severity
    )
    db.add(event)
    
    # Si l'alerte est critique, on la remonte aux RH / Admins via HRAlert
    if severity in [AlertSeverityEnum.CRITIQUE, AlertSeverityEnum.FUITE_DONNEES]:
        alert = HRAlert(
            alert_type=f"ia_security_{event_type.value}",
            severity=severity,
            resolution_notes=f"Détails: {details}"
        )
        db.add(alert)
        
    await db.commit()


def check_input_guardrails(query: str) -> Tuple[bool, Optional[SecurityEventTypeEnum], str]:
    """
    Analyse l'entrée utilisateur pour détecter les tentatives de prompt injection 
    ou de manipulation de l'IA.
    Retourne (is_safe, event_type, raison).
    """
    query_lower = query.lower()
    
    # 1. Pattern Matching Basique pour les Injections
    injection_patterns = [
        r"ignore.*instructions",
        r"oubli.*règles",
        r"bypass",
        r"system prompt",
        r"tu es maintenant",
        r"mode développeur",
        r"donne.*accès",
        r"qui t'a programmé"
    ]
    
    for pattern in injection_patterns:
        if re.search(pattern, query_lower):
            return False, SecurityEventTypeEnum.PROMPT_INJECTION, "Tentative de Prompt Injection détectée"
            
    # 2. Requêtes sur des données interdites explicitement
    forbidden_topics = [
        "salaire de", "fiche de paie de", 
        "bulletin", "données médicales", 
        "numéro de sécurité sociale", "ssn", "iban"
    ]
    
    for topic in forbidden_topics:
        if topic in query_lower:
            return False, SecurityEventTypeEnum.UNAUTHORIZED_ACCESS, "Demande de données hautement confidentielles"
            
    return True, None, ""


def check_output_guardrails(llm_response: str) -> Tuple[bool, Optional[SecurityEventTypeEnum], str]:
    """
    Analyse la sortie du LLM avant de l'envoyer à l'utilisateur
    pour éviter les fuites de données (Data Leakage).
    Retourne (is_safe, event_type, raison).
    """
    
    # Recherche de numéros de sécurité sociale (format français basique)
    # 1 ou 2 suivi de 12 chiffres (avec ou sans espaces)
    ssn_pattern = r"\b[12][\s\.\-]?\d{2}[\s\.\-]?\d{2}[\s\.\-]?\d{2}[\s\.\-]?\d{3}[\s\.\-]?\d{3}[\s\.\-]?\d{2}\b"
    if re.search(ssn_pattern, llm_response):
        return False, SecurityEventTypeEnum.DATA_LEAK_RISK, "Fuite potentielle de Numéro de Sécurité Sociale"
        
    # Recherche de numéros de carte de crédit (basique)
    credit_card_pattern = r"\b(?:\d[ -]*?){13,16}\b"
    if re.search(credit_card_pattern, llm_response):
        return False, SecurityEventTypeEnum.DATA_LEAK_RISK, "Fuite potentielle de coordonnées bancaires"
        
    # IBAN Français (FR suivi de 2 chiffres puis 23 caractères)
    iban_pattern = r"FR\d{2}[ ]?\d{4}[ ]?\d{4}[ ]?\d{4}[ ]?\d{4}[ ]?\d{4}[ ]?\d{3}"
    if re.search(iban_pattern, llm_response.replace(" ", "")):
         return False, SecurityEventTypeEnum.DATA_LEAK_RISK, "Fuite potentielle d'IBAN"
         
    return True, None, ""
