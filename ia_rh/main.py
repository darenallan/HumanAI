from module.intent_classifier import classify_intent
from module.permission_checker import check_permission
from module.document_retriever import retrieve_context
from module.response_generator import generate_response
from module.logger import log_interaction


def ai_hr_assistant(user_id: int, role: str, question: str):
    """
    Fonction principale de l'assistant IA RH.
    Elle orchestre les différents modules :
    - classification de l'intention
    - vérification des permissions
    - recherche documentaire
    - génération de réponse
    - journalisation
    """

    intent = classify_intent(question)

    has_permission = check_permission(role, intent)

    if not has_permission:
        log_interaction(
            user_id=user_id,
            role=role,
            question=question,
            intent=intent,
            status="denied"
        )

        return {
            "status": "denied",
            "intent": intent,
            "answer": "Je ne peux pas fournir cette information, car elle est confidentielle ou hors de votre périmètre d'autorisation."
        }

    context_docs = retrieve_context(intent)
    answer = generate_response(context_docs)

    log_interaction(
        user_id=user_id,
        role=role,
        question=question,
        intent=intent,
        status="success"
    )

    return {
        "status": "success",
        "intent": intent,
        "answer": answer
    }


if __name__ == "__main__":
    print("Assistant IA RH - Prototype MVP")
    print("--------------------------------")

    user_id = 1
    role = "collaborateur"

    while True:
        question = input("\nPose ta question RH ou tape 'exit' pour quitter : ")

        if question.lower() == "exit":
            print("Fin de la session.")
            break

        response = ai_hr_assistant(user_id, role, question)

        print("\nStatut :", response["status"])
        print("Intention détectée :", response["intent"])
        print("Réponse :")
        print(response["answer"])