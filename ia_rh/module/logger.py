import json
from datetime import datetime


def log_interaction(user_id, role, question, intent, status):
    """
    Enregistre chaque interaction avec l'assistant IA dans un fichier JSONL.
    """
    log = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "role": role,
        "question": question,
        "intent": intent,
        "status": status
    }

    with open("ai_logs.json", "a", encoding="utf-8") as file:
        file.write(json.dumps(log, ensure_ascii=False) + "\n")
