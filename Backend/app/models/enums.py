"""
enums.py
--------
Énumérations PostgreSQL partagées par l'ensemble des modèles ORM.
Conformes à l'Architecture BDD v2 (FirebaseAuth).
"""
import enum


class RoleEnum(str, enum.Enum):
    COLLABORATEUR = "collaborateur"
    MANAGER = "manager"
    RH = "rh"
    DIRECTION = "direction"
    ADMIN = "admin"
    QVT = "qvt"


class ContractTypeEnum(str, enum.Enum):
    CDI = "CDI"
    CDD = "CDD"
    STAGE = "stage"
    CONSULTANT = "consultant"


class EmployeeStatusEnum(str, enum.Enum):
    ACTIF = "actif"
    INACTIF = "inactif"
    EN_SORTIE = "en_sortie"


class AbsenceTypeEnum(str, enum.Enum):
    CONGE_PAYE = "congé_payé"
    MALADIE = "maladie"
    SANS_SOLDE = "sans_solde"
    AUTRE = "autre"


class AbsenceStatusEnum(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class OnboardingStatusEnum(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"


class OffboardingReasonEnum(str, enum.Enum):
    DEMISSION = "démission"
    LICENCIEMENT = "licenciement"
    FIN_CONTRAT = "fin_contrat"
    RETRAITE = "retraite"


class OffboardingStatusEnum(str, enum.Enum):
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class OffboardingStepTypeEnum(str, enum.Enum):
    MATERIEL = "materiel"
    ACCES = "acces"
    ADMIN = "admin"
    TRANSFERT = "transfert"
    CLOTURE = "cloture"


class DocumentTypeEnum(str, enum.Enum):
    ATTESTATION = "attestation"
    FORMULAIRE = "formulaire"
    SYNTHESE = "synthèse"
    COURRIER = "courrier"
    OFFBOARDING = "offboarding"


class DocumentStatusEnum(str, enum.Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    ARCHIVED = "archived"


class KPIScopeEnum(str, enum.Enum):
    GLOBAL = "global"
    DEPARTMENT = "department"
    SITE = "site"
    TEAM = "team"


class SentimentEnum(str, enum.Enum):
    POSITIF = "positif"
    NEUTRE = "neutre"
    NEGATIF = "négatif"


class RiskLevelEnum(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertSeverityEnum(str, enum.Enum):
    ANOMALIE = "anomalie"
    REPETEE = "répétée"
    CRITIQUE = "critique"
    FUITE_DONNEES = "fuite_données"


class SecurityEventTypeEnum(str, enum.Enum):
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    PROMPT_INJECTION = "prompt_injection"
    REPEATED_ATTEMPT = "repeated_attempt"
    DATA_LEAK_RISK = "data_leak_risk"


class RAGSourceTypeEnum(str, enum.Enum):
    POLICY = "policy"
    CONVENTION = "convention"
    GUIDE = "guide"
    PROCEDURE = "procedure"
    FAQ = "faq"
