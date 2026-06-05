def generate_response(context_docs: list):
    """
    Génère une réponse à partir des documents RH trouvés.
    """

    if not context_docs:
        return (
            "Je n'ai pas trouvé d'information RH validée sur ce sujet. "
            "Veuillez contacter un référent RH pour obtenir une réponse personnalisée."
        )

    source = context_docs[0]["title"]
    content = context_docs[0]["content"]

    response = f"""
D'après le document RH validé : {source}

{content}

Si votre situation est particulière, veuillez contacter un référent RH.
"""

    return response.strip()