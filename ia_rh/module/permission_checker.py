PERMISSIONS = {
    "collaborateur": [
        "conges",
        "absence",
        "procedure_interne",
        "document_rh",
        "general"
    ],
    "manager": [
        "conges",
        "absence",
        "procedure_interne",
        "document_rh",
        "general",
        "indicateurs_equipe"
    ],
    "rh": [
        "conges",
        "absence",
        "paie",
        "procedure_interne",
        "document_rh",
        "onboarding",
        "offboarding",
        "general",
        "indicateurs_rh"
    ],
    "admin": [
        "conges",
        "absence",
        "paie",
        "procedure_interne",
        "document_rh",
        "onboarding",
        "offboarding",
        "general",
        "logs",
        "security"
    ]
}


def check_permission(role: str, intent: str) -> bool:
    """
    Vérifie si le rôle utilisateur a le droit d'accéder à l'intention demandée.
    """

    if intent in ["donnee_confidentielle", "prompt_injection"]:
        return False

    allowed_intents = PERMISSIONS.get(role, [])
    return intent in allowed_intents