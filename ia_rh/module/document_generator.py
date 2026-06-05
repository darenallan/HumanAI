import json
from datetime import datetime


def load_employees():
    """
    Charge les informations des employés depuis employees.json.
    """

    with open("employees.json", "r", encoding="utf-8") as file:
        return json.load(file)


def find_employee_by_user_id(user_id: int):
    """
    Recherche un employé par son user_id.
    """

    employees = load_employees()

    for employee in employees:
        if employee["user_id"] == user_id:
            return employee

    return None


def generate_work_certificate(employee: dict):
    """
    Génère une attestation de travail simple.
    """

    civilite = "Monsieur" if employee["gender"] == "M" else "Madame"

    today = datetime.now().strftime("%d/%m/%Y")

    content = f"""
ATTESTATION DE TRAVAIL

Nous certifions que {civilite} {employee["first_name"]} {employee["last_name"]} occupe le poste de {employee["position"]} au sein du département {employee["department"]}.

Date d'entrée dans l'entreprise : {employee["start_date"]}
Type de contrat : {employee["contract_type"]}

Cette attestation est générée automatiquement par la plateforme IA RH et doit être validée par le service Ressources Humaines avant toute utilisation officielle.

Fait le {today}

Service Ressources Humaines
"""

    return content.strip()


def generate_document(user_id: int, role: str, document_type: str):
    """
    Génère un document RH selon le type demandé.
    """

    allowed_roles = ["collaborateur", "manager", "rh", "admin"]

    if role not in allowed_roles:
        return {
            "status": "denied",
            "message": "Votre rôle ne permet pas de générer ce document."
        }

    employee = find_employee_by_user_id(user_id)

    if employee is None:
        return {
            "status": "not_found",
            "message": "Aucun employé trouvé pour cet utilisateur."
        }

    if document_type == "attestation_travail":
        content = generate_work_certificate(employee)

        return {
            "status": "success",
            "document_type": document_type,
            "requires_hr_validation": True,
            "content": content
        }

    return {
        "status": "unsupported_document",
        "message": "Type de document non pris en charge pour le moment."
    }