import json


def load_documents():
    """
    Charge les documents RH depuis le fichier JSON.
    """

    with open("documents_rh.json", "r", encoding="utf-8") as file:
        return json.load(file)


def retrieve_context(intent: str):
    """
    Recherche les documents RH correspondant à l'intention détectée.
    """

    documents = load_documents()
    results = []

    for doc in documents:
        if doc["category"] == intent:
            results.append(doc)

    return results