import json
import os


LOG_FILE = "ai_logs.jsonl"


def read_ai_logs():
    """
    Lit le fichier de logs IA et retourne la liste des interactions.
    """

    if not os.path.exists(LOG_FILE):
        return []

    logs = []

    with open(LOG_FILE, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if line:
                try:
                    logs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    return logs


def get_all_logs():
    """
    Retourne tous les logs de l'assistant IA.
    """

    logs = read_ai_logs()

    return {
        "status": "success",
        "total_logs": len(logs),
        "logs": logs
    }


def classify_alert_level(log):
    """
    Classe le niveau de gravité d'une interaction suspecte.
    """

    intent = log.get("intent")
    status = log.get("status")

    if intent == "prompt_injection":
        return "critical"

    if intent == "donnee_confidentielle":
        return "high"

    if status == "denied":
        return "medium"

    return "low"


def get_security_alerts():
    """
    Retourne uniquement les interactions considérées comme suspectes.
    """

    logs = read_ai_logs()

    suspicious_logs = []

    for log in logs:
        intent = log.get("intent")
        status = log.get("status")

        if status == "denied" or intent in ["donnee_confidentielle", "prompt_injection"]:
            alert = {
                "timestamp": log.get("timestamp"),
                "user_id": log.get("user_id"),
                "role": log.get("role"),
                "question": log.get("question"),
                "intent": intent,
                "status": status,
                "alert_level": classify_alert_level(log)
            }

            suspicious_logs.append(alert)

    return {
        "status": "success",
        "total_alerts": len(suspicious_logs),
        "alerts": suspicious_logs
    }