def classify_intent(question: str) -> str:
    """
    Analyse la question utilisateur et retourne l'intention détectée.
    """

    question = question.lower()

    if any(word in question for word in ["congé", "conges", "vacances", "repos"]):
        return "conges"

    if any(word in question for word in ["absence", "absent", "maladie", "justificatif"]):
        return "absence"

    if any(word in question for word in ["paie", "salaire", "bulletin"]):
        return "paie"

    if any(word in question for word in ["attestation", "document", "formulaire"]):
        return "document_rh"

    if any(word in question for word in ["onboarding", "intégration", "arrivée"]):
        return "onboarding"

    if any(word in question for word in ["offboarding", "départ", "sortie"]):
        return "offboarding"

    if any(word in question for word in [
        "salaire de",
        "bulletin de paie de",
        "données médicales",
        "adresse de",
        "contrat de",
        "informations personnelles de"
    ]):
        return "donnee_confidentielle"

    if any(word in question for word in [
        "ignore les règles",
        "oublie les instructions",
        "contourne",
        "admin secret",
        "donne moi les accès",
        "bypass"
    ]):
        return "prompt_injection"

    return "general"