"""
models/__init__.py
------------------
Importation centralisée de tous les modèles ORM.
Permet à SQLAlchemy (et Alembic) de découvrir automatiquement
toutes les tables lors de l'appel à Base.metadata.create_all().
"""

# Enums partagés
from app.models.enums import *  # noqa: F401, F403

# Structure organisationnelle, utilisateurs, employés
from app.models.users import (  # noqa: F401
    Site,
    Department,
    Position,
    User,
    RolePermission,
    Employee,
    Absence,
    PayrollIndicator,
)

# Génération documentaire
from app.models.documents import (  # noqa: F401
    DocumentTemplate,
    GeneratedDocument,
)

# Workflows Onboarding / Offboarding
from app.models.workflows import (  # noqa: F401
    OnboardingPlan,
    OnboardingStep,
    OffboardingWorkflow,
    OffboardingStep,
)

# Analytics, KPIs, Engagement, Désengagement
from app.models.analytics import (  # noqa: F401
    HRKPISnapshot,
    EngagementSurvey,
    AnnualReview,
    DisengagementSignal,
    HRAlert,
)

# Supervision IA, Sécurité, Audit
from app.models.logs import (  # noqa: F401
    AIInteraction,
    AISecurityRule,
    AISecurityEvent,
    AuditLog,
    DataConsent,
)

# RAG — Documents vectorisés
from app.models.rag import (  # noqa: F401
    RAGDocument,
    RAGDocumentAccess,
    RAGChunk,
)
