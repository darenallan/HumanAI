-- ============================================================
-- HumaNai — Schéma PostgreSQL complet
-- Stack  : PostgreSQL 16 · pgvector · pgcrypto · pg_trgm
-- Projet : YDAYS 2026 | Ynov Campus Casablanca
-- Version: v2 — FirebaseAuth
-- ============================================================
-- Ordre d'exécution : ce fichier est auto-suffisant.
-- Lancer : psql -U <user> -d <db> -f humanai_schema.sql
-- ============================================================


-- ============================================================
-- 0. EXTENSIONS
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- chiffrement colonnes sensibles
CREATE EXTENSION IF NOT EXISTS vector;     -- pgvector pour le RAG
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- recherche full-text optimisée


-- ============================================================
-- 1. TYPES ENUM
-- ============================================================

CREATE TYPE user_role AS ENUM (
  'collaborateur', 'manager', 'rh', 'direction', 'admin', 'qvt'
);

CREATE TYPE contract_type AS ENUM (
  'CDI', 'CDD', 'stage', 'consultant'
);

CREATE TYPE employee_status AS ENUM (
  'actif', 'inactif', 'en_sortie'
);

CREATE TYPE absence_type AS ENUM (
  'conge_paye', 'maladie', 'sans_solde', 'autre'
);

CREATE TYPE absence_status AS ENUM (
  'pending', 'approved', 'rejected'
);

CREATE TYPE onboarding_status AS ENUM (
  'draft', 'active', 'completed'
);

CREATE TYPE departure_reason AS ENUM (
  'demission', 'licenciement', 'fin_contrat', 'retraite'
);

CREATE TYPE offboarding_status AS ENUM (
  'initiated', 'in_progress', 'completed'
);

CREATE TYPE offboarding_step_type AS ENUM (
  'materiel', 'acces', 'admin', 'transfert', 'cloture'
);

CREATE TYPE document_type AS ENUM (
  'attestation', 'formulaire', 'synthese', 'courrier', 'offboarding'
);

CREATE TYPE document_status AS ENUM (
  'draft', 'validated', 'archived'
);

CREATE TYPE kpi_scope_type AS ENUM (
  'global', 'department', 'site', 'team'
);

CREATE TYPE survey_sentiment AS ENUM (
  'positif', 'neutre', 'negatif'
);

CREATE TYPE risk_level AS ENUM (
  'low', 'medium', 'high', 'critical'
);

CREATE TYPE alert_severity AS ENUM (
  'anomalie', 'repetee', 'critique', 'fuite_donnees'
);

CREATE TYPE ai_event_type AS ENUM (
  'unauthorized_access', 'prompt_injection', 'repeated_attempt', 'data_leak_risk'
);

CREATE TYPE rag_source_type AS ENUM (
  'policy', 'convention', 'guide', 'procedure', 'faq'
);


-- ============================================================
-- 2. TRIGGER HELPER : updated_at automatique
-- ============================================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- 3. GESTION DES UTILISATEURS & ACCÈS
-- ============================================================

-- 3.1 Sites géographiques
CREATE TABLE sites (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL,
  location    TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3.2 Départements (hiérarchie via parent_id)
CREATE TABLE departments (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL,
  parent_id   UUID REFERENCES departments(id) ON DELETE SET NULL,
  site_id     UUID REFERENCES sites(id) ON DELETE SET NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3.3 Utilisateurs — liaison avec Firebase Auth via firebase_uid
CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email         TEXT NOT NULL UNIQUE,
  firebase_uid  TEXT NOT NULL UNIQUE,     -- clé de liaison compte Firebase
  role          user_role NOT NULL DEFAULT 'collaborateur',
  department_id UUID REFERENCES departments(id) ON DELETE SET NULL,
  manager_id    UUID REFERENCES users(id) ON DELETE SET NULL,  -- auto-référence
  is_active     BOOLEAN NOT NULL DEFAULT true,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3.4 Permissions RBAC par rôle et module applicatif
CREATE TABLE roles_permissions (
  role        user_role NOT NULL,
  module      TEXT      NOT NULL,   -- ex: paie, absences, dashboard, rag_docs
  can_read    BOOLEAN   NOT NULL DEFAULT false,
  can_write   BOOLEAN   NOT NULL DEFAULT false,
  can_export  BOOLEAN   NOT NULL DEFAULT false,
  PRIMARY KEY (role, module)
);

-- 3.5 Postes / intitulés de poste
CREATE TABLE positions (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title      TEXT NOT NULL UNIQUE,
  grade      TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ============================================================
-- 4. DONNÉES COLLABORATEURS (Core RH)
-- ============================================================

-- 4.1 Fiche collaborateur
-- COLONNES CHIFFRÉES (pgcrypto, côté application) :
--   salary_band : pgp_sym_encrypt(value, current_setting('app.encryption_key'))
CREATE TABLE employees (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID        NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  matricule       TEXT        NOT NULL UNIQUE,  -- identifiant RH interne
  full_name       TEXT        NOT NULL,
  position_id     UUID        REFERENCES positions(id) ON DELETE SET NULL,
  department_id   UUID        REFERENCES departments(id) ON DELETE SET NULL,
  hire_date       DATE        NOT NULL,
  contract_type   contract_type NOT NULL,
  -- Calculé automatiquement : ancienneté en années entières
  seniority_years NUMERIC     GENERATED ALWAYS AS (
                    EXTRACT(YEAR FROM AGE(CURRENT_DATE, hire_date))
                  ) STORED,
  salary_band     TEXT,        -- !! ENCRYPTED via pgcrypto !!
  status          employee_status NOT NULL DEFAULT 'actif',
  sirh_sync_id    TEXT,        -- prêt pour intégration SIRH future
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_employees_updated_at
  BEFORE UPDATE ON employees
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 4.2 Absences
CREATE TABLE absences (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id   UUID          NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  type          absence_type  NOT NULL,
  start_date    DATE          NOT NULL,
  end_date      DATE          NOT NULL,
  -- Calculé automatiquement : nombre de jours calendaires
  duration_days NUMERIC       GENERATED ALWAYS AS (end_date - start_date + 1) STORED,
  status        absence_status NOT NULL DEFAULT 'pending',
  approved_by   UUID          REFERENCES users(id) ON DELETE SET NULL,
  sirh_sync_id  TEXT,
  created_at    TIMESTAMPTZ   NOT NULL DEFAULT now(),
  CONSTRAINT absences_dates_check CHECK (end_date >= start_date)
);

-- 4.3 Indicateurs de paie (agrégés — pas de montants exacts)
-- COLONNES CHIFFRÉES : gross_band, net_band
CREATE TABLE payroll_indicators (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  month       INT  NOT NULL CHECK (month BETWEEN 1 AND 12),
  year        INT  NOT NULL CHECK (year >= 2000),
  gross_band  TEXT NOT NULL,   -- !! ENCRYPTED !!
  net_band    TEXT NOT NULL,   -- !! ENCRYPTED !!
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (employee_id, month, year)
);


-- ============================================================
-- 5. ONBOARDING & OFFBOARDING
-- ============================================================

-- 5.1 Plan d'onboarding — généré par l'agent IA (queue: onboarding-gen)
CREATE TABLE onboarding_plans (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id     UUID             NOT NULL UNIQUE REFERENCES employees(id) ON DELETE CASCADE,
  status          onboarding_status NOT NULL DEFAULT 'draft',
  day_30_calendar JSONB,           -- structure des 30 jours d'intégration
  created_at      TIMESTAMPTZ      NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ      NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_onboarding_plans_updated_at
  BEFORE UPDATE ON onboarding_plans
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 5.2 Étapes d'onboarding
CREATE TABLE onboarding_steps (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_id            UUID        NOT NULL REFERENCES onboarding_plans(id) ON DELETE CASCADE,
  title              TEXT        NOT NULL,  -- 'Remise du matériel', 'Réunion équipe'
  due_date           DATE,
  completed_at       TIMESTAMPTZ,
  is_alert_triggered BOOLEAN     NOT NULL DEFAULT false,  -- alerte si étape non faite
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5.3 Templates documentaires (créés avant generated_documents)
CREATE TABLE document_templates (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name             TEXT          NOT NULL,
  type             document_type NOT NULL,
  content_template TEXT          NOT NULL,  -- variables {{employee.name}}, etc.
  allowed_roles    user_role[]   NOT NULL DEFAULT '{}',
  created_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_document_templates_updated_at
  BEFORE UPDATE ON document_templates
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 5.4 Documents générés
-- COLONNES CHIFFRÉES : content_snapshot
CREATE TABLE generated_documents (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id      UUID            NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  template_id      UUID            REFERENCES document_templates(id) ON DELETE SET NULL,
  generated_by     UUID            NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  generated_at     TIMESTAMPTZ     NOT NULL DEFAULT now(),
  content_snapshot TEXT,            -- !! ENCRYPTED !!
  status           document_status NOT NULL DEFAULT 'draft',
  rh_validated_by  UUID            REFERENCES users(id) ON DELETE SET NULL,
  rh_validated_at  TIMESTAMPTZ,
  created_at       TIMESTAMPTZ     NOT NULL DEFAULT now()
);

-- 5.5 Workflow d'offboarding
--     Dépend de generated_documents (knowledge_transfer_doc_id)
CREATE TABLE offboarding_workflows (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id               UUID               NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  departure_reason          departure_reason   NOT NULL,
  departure_date            DATE               NOT NULL,
  status                    offboarding_status NOT NULL DEFAULT 'initiated',
  knowledge_transfer_doc_id UUID               REFERENCES generated_documents(id) ON DELETE SET NULL,
  created_at                TIMESTAMPTZ        NOT NULL DEFAULT now(),
  updated_at                TIMESTAMPTZ        NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_offboarding_workflows_updated_at
  BEFORE UPDATE ON offboarding_workflows
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 5.6 Étapes d'offboarding
CREATE TABLE offboarding_steps (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_id  UUID                  NOT NULL REFERENCES offboarding_workflows(id) ON DELETE CASCADE,
  step_type    offboarding_step_type NOT NULL,
  completed_at TIMESTAMPTZ,
  assigned_to  UUID                  REFERENCES users(id) ON DELETE SET NULL,
  created_at   TIMESTAMPTZ           NOT NULL DEFAULT now()
);


-- ============================================================
-- 6. ANALYTICS & KPIs
-- ============================================================

-- 6.1 Snapshots KPI (scope : global / department / site / team)
-- COLONNES CHIFFRÉES : payroll_mass_band
CREATE TABLE hr_kpi_snapshots (
  id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scope_type              kpi_scope_type NOT NULL,
  scope_id                UUID           NOT NULL,  -- ref dynamique département/site/équipe
  period_month            INT            NOT NULL CHECK (period_month BETWEEN 1 AND 12),
  period_year             INT            NOT NULL CHECK (period_year >= 2000),
  headcount               INT            NOT NULL DEFAULT 0,
  turnover_rate           NUMERIC(5,2),   -- en %
  absenteeism_rate        NUMERIC(5,2),   -- en %
  avg_age                 NUMERIC(5,1),
  payroll_mass_band       TEXT,           -- !! ENCRYPTED !!
  internal_mobility_count INT             NOT NULL DEFAULT 0,
  engagement_score        NUMERIC(3,1)    CHECK (engagement_score BETWEEN 0 AND 10),
  computed_at             TIMESTAMPTZ     NOT NULL DEFAULT now(),
  UNIQUE (scope_type, scope_id, period_month, period_year)
);

-- 6.2 Enquêtes d'engagement
CREATE TABLE engagement_surveys (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID             REFERENCES employees(id) ON DELETE SET NULL,  -- nullable si anonyme
  survey_date DATE             NOT NULL,
  score       INT              NOT NULL CHECK (score BETWEEN 1 AND 10),
  sentiment   survey_sentiment NOT NULL,
  is_anonymous BOOLEAN         NOT NULL DEFAULT false,
  created_at  TIMESTAMPTZ      NOT NULL DEFAULT now()
);

-- 6.3 Entretiens annuels
-- COLONNES CHIFFRÉES : notes
CREATE TABLE annual_reviews (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id    UUID        NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  reviewer_id    UUID        NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  review_date    DATE        NOT NULL,
  rating         NUMERIC(3,1) CHECK (rating BETWEEN 0 AND 10),
  workload_score INT          CHECK (workload_score BETWEEN 1 AND 5),
  notes          TEXT,        -- !! ENCRYPTED !!
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ============================================================
-- 7. DÉTECTION DÉSENGAGEMENT & ALERTES
-- ============================================================

-- 7.1 Signaux de désengagement (calculés par l'agent IA)
CREATE TABLE disengagement_signals (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID        NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  risk_score  NUMERIC(5,2) NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
  risk_level  risk_level   NOT NULL,
  signals     JSONB        NOT NULL DEFAULT '{}',  -- {absenteeism: 0.8, survey: 0.3, ...}
  action_plan JSONB,                               -- plan d'action recommandé par l'IA
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 7.2 Alertes RH
CREATE TABLE hr_alerts (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID           REFERENCES employees(id) ON DELETE SET NULL,
  alert_type  TEXT           NOT NULL,   -- disengagement_risk, unauthorized_access...
  severity    alert_severity NOT NULL,
  triggered_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
  resolved_at  TIMESTAMPTZ,
  resolved_by  UUID          REFERENCES users(id) ON DELETE SET NULL,
  is_read      BOOLEAN       NOT NULL DEFAULT false,
  created_at   TIMESTAMPTZ   NOT NULL DEFAULT now()
);


-- ============================================================
-- 8. SUPERVISION IA
-- ============================================================

-- 8.1 Règles de sécurité IA (configurables par admin)
CREATE TABLE ai_security_rules (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name             TEXT           NOT NULL UNIQUE,   -- 'Accès paie hors RH'
  condition_logic  JSONB          NOT NULL,           -- règle configurable
  severity         alert_severity NOT NULL,
  is_active        BOOLEAN        NOT NULL DEFAULT true,
  created_at       TIMESTAMPTZ    NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ    NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_ai_security_rules_updated_at
  BEFORE UPDATE ON ai_security_rules
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 8.2 Interactions avec l'assistant IA
-- COLONNES CHIFFRÉES : query_text
CREATE TABLE ai_interactions (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id              UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  session_id           UUID        NOT NULL,   -- regroupement des échanges d'une session
  timestamp            TIMESTAMPTZ NOT NULL DEFAULT now(),
  query_text           TEXT,                   -- !! ENCRYPTED !!
  response_summary     TEXT,                   -- résumé non-sensible de la réponse
  role_at_time         TEXT        NOT NULL,   -- rôle de l'utilisateur au moment de la requête
  data_scope_requested TEXT[]      NOT NULL DEFAULT '{}'  -- modules/tables consultés
);

-- 8.3 Événements de sécurité IA
CREATE TABLE ai_security_events (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  interaction_id    UUID           NOT NULL REFERENCES ai_interactions(id) ON DELETE CASCADE,
  event_type        ai_event_type  NOT NULL,
  severity          alert_severity NOT NULL,
  triggered_rule    UUID           REFERENCES ai_security_rules(id) ON DELETE SET NULL,
  admin_notified_at TIMESTAMPTZ,
  created_at        TIMESTAMPTZ    NOT NULL DEFAULT now()
);


-- ============================================================
-- 9. AUDIT & CONFORMITÉ
-- ============================================================

-- 9.1 Journal d'audit — APPEND-ONLY (aucun UPDATE/DELETE via RLS)
CREATE TABLE audit_logs (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID        REFERENCES users(id) ON DELETE SET NULL,
  action      TEXT        NOT NULL,   -- READ, WRITE, DELETE, EXPORT
  entity_type TEXT        NOT NULL,   -- employee, document, alert
  entity_id   UUID        NOT NULL,
  timestamp   TIMESTAMPTZ NOT NULL DEFAULT now(),
  ip_address  INET,
  details     JSONB       NOT NULL DEFAULT '{}'
);

-- 9.2 Consentements RGPD
CREATE TABLE data_consents (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID        NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  purpose     TEXT        NOT NULL,   -- analytics, surveys…
  granted_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_at  TIMESTAMPTZ,
  UNIQUE (employee_id, purpose)
);


-- ============================================================
-- 10. pgvector — MODULE RAG
-- ============================================================

-- 10.1 Documents sources RH
CREATE TABLE rag_documents (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title       TEXT            NOT NULL,
  source_type rag_source_type NOT NULL,
  content_raw TEXT            NOT NULL,   -- texte original extrait
  metadata    JSONB           NOT NULL DEFAULT '{}',  -- {filename, version, valid_from, valid_to, scope}
  created_at  TIMESTAMPTZ     NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ     NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_rag_documents_updated_at
  BEFORE UPDATE ON rag_documents
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 10.2 Contrôle d'accès RBAC sur les documents RAG
CREATE TABLE rag_document_access (
  document_id  UUID      NOT NULL REFERENCES rag_documents(id) ON DELETE CASCADE,
  allowed_role user_role NOT NULL,
  PRIMARY KEY (document_id, allowed_role)
);

-- 10.3 Chunks vectorisés
--   embedding : vector(1536) = OpenAI text-embedding-3-small
--   Pour modèle local, remplacer par vector(768)
CREATE TABLE rag_chunks (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID        NOT NULL REFERENCES rag_documents(id) ON DELETE CASCADE,
  chunk_index INT         NOT NULL,
  content     TEXT        NOT NULL,        -- 300-500 tokens par chunk
  embedding   vector(1536) NOT NULL,
  token_count INT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (document_id, chunk_index)
);


-- ============================================================
-- 11. INDEX
-- ============================================================

-- Utilisateurs
CREATE INDEX idx_users_firebase_uid   ON users(firebase_uid);
CREATE INDEX idx_users_role           ON users(role);
CREATE INDEX idx_users_department_id  ON users(department_id);
CREATE INDEX idx_users_is_active      ON users(is_active) WHERE is_active = true;

-- Employés
CREATE INDEX idx_employees_user_id      ON employees(user_id);
CREATE INDEX idx_employees_department   ON employees(department_id);
CREATE INDEX idx_employees_status       ON employees(status);
CREATE INDEX idx_employees_hire_date    ON employees(hire_date);
CREATE INDEX idx_employees_contract     ON employees(contract_type);

-- Absences
CREATE INDEX idx_absences_employee      ON absences(employee_id);
CREATE INDEX idx_absences_status        ON absences(status);
CREATE INDEX idx_absences_dates         ON absences(start_date, end_date);

-- Paie
CREATE INDEX idx_payroll_employee       ON payroll_indicators(employee_id);
CREATE INDEX idx_payroll_period         ON payroll_indicators(year, month);

-- Onboarding / Offboarding
CREATE INDEX idx_onboarding_plans_emp   ON onboarding_plans(employee_id);
CREATE INDEX idx_onboarding_steps_plan  ON onboarding_steps(plan_id);
CREATE INDEX idx_onboarding_steps_due   ON onboarding_steps(due_date);
CREATE INDEX idx_offboarding_emp        ON offboarding_workflows(employee_id);
CREATE INDEX idx_offboarding_status     ON offboarding_workflows(status);

-- Documents
CREATE INDEX idx_generated_docs_emp     ON generated_documents(employee_id);
CREATE INDEX idx_generated_docs_status  ON generated_documents(status);
CREATE INDEX idx_generated_docs_gen_at  ON generated_documents(generated_at DESC);

-- KPI
CREATE INDEX idx_kpi_scope              ON hr_kpi_snapshots(scope_type, scope_id);
CREATE INDEX idx_kpi_period             ON hr_kpi_snapshots(period_year, period_month);

-- Alertes
CREATE INDEX idx_hr_alerts_employee     ON hr_alerts(employee_id);
CREATE INDEX idx_hr_alerts_severity     ON hr_alerts(severity);
CREATE INDEX idx_hr_alerts_unread       ON hr_alerts(is_read) WHERE is_read = false;
CREATE INDEX idx_hr_alerts_triggered    ON hr_alerts(triggered_at DESC);

-- Désengagement
CREATE INDEX idx_disengagement_emp      ON disengagement_signals(employee_id);
CREATE INDEX idx_disengagement_level    ON disengagement_signals(risk_level);
CREATE INDEX idx_disengagement_date     ON disengagement_signals(computed_at DESC);

-- IA
CREATE INDEX idx_ai_interactions_user   ON ai_interactions(user_id);
CREATE INDEX idx_ai_interactions_sess   ON ai_interactions(session_id);
CREATE INDEX idx_ai_interactions_ts     ON ai_interactions(timestamp DESC);
CREATE INDEX idx_ai_sec_events_inter    ON ai_security_events(interaction_id);

-- Audit
CREATE INDEX idx_audit_logs_user        ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_entity      ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_ts          ON audit_logs(timestamp DESC);

-- RAG
CREATE INDEX idx_rag_chunks_doc         ON rag_chunks(document_id);
CREATE INDEX idx_rag_docs_source        ON rag_documents(source_type);

-- Full-text search (pg_trgm)
CREATE INDEX idx_employees_name_trgm    ON employees USING GIN (full_name gin_trgm_ops);
CREATE INDEX idx_rag_docs_title_trgm    ON rag_documents USING GIN (title gin_trgm_ops);
CREATE INDEX idx_rag_chunks_content_trgm ON rag_chunks USING GIN (content gin_trgm_ops);

-- HNSW vectoriel (pgvector) — meilleure précision, recommandé pour RAG d'entreprise
-- Pas de phase d'entraînement, meilleure précision que IVFFlat sur petits volumes dynamiques
CREATE INDEX idx_rag_chunks_embedding_hnsw ON rag_chunks
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);


-- ============================================================
-- 12. ROW-LEVEL SECURITY (RLS)
-- ============================================================
-- Prérequis : l'application DOIT SET les variables de session
-- à chaque transaction avant toute requête :
--   SET LOCAL app.current_user_id = '<uuid>';
--   SET LOCAL app.current_role    = '<role>';
-- ============================================================

ALTER TABLE employees            ENABLE ROW LEVEL SECURITY;
ALTER TABLE absences             ENABLE ROW LEVEL SECURITY;
ALTER TABLE payroll_indicators   ENABLE ROW LEVEL SECURITY;
ALTER TABLE generated_documents  ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_interactions      ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs           ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_chunks           ENABLE ROW LEVEL SECURITY;

-- employees : collaborateur = soi-même | manager = son département | rh/admin/direction = tout
CREATE POLICY employees_select ON employees
  FOR SELECT USING (
    user_id = current_setting('app.current_user_id', true)::uuid
    OR current_setting('app.current_role', true) IN ('rh', 'admin', 'direction')
    OR (
      current_setting('app.current_role', true) = 'manager'
      AND department_id = (
        SELECT department_id FROM users
        WHERE id = current_setting('app.current_user_id', true)::uuid
      )
    )
  );

CREATE POLICY employees_write ON employees
  FOR ALL USING (
    current_setting('app.current_role', true) IN ('rh', 'admin')
  );

-- absences
CREATE POLICY absences_select ON absences
  FOR SELECT USING (
    employee_id = (
      SELECT id FROM employees
      WHERE user_id = current_setting('app.current_user_id', true)::uuid
    )
    OR current_setting('app.current_role', true) IN ('rh', 'admin', 'direction', 'manager')
  );

-- payroll_indicators : rh, direction, admin uniquement
CREATE POLICY payroll_rh_only ON payroll_indicators
  FOR ALL USING (
    current_setting('app.current_role', true) IN ('rh', 'direction', 'admin')
  );

-- generated_documents
CREATE POLICY docs_select ON generated_documents
  FOR SELECT USING (
    employee_id = (
      SELECT id FROM employees
      WHERE user_id = current_setting('app.current_user_id', true)::uuid
    )
    OR current_setting('app.current_role', true) IN ('rh', 'admin', 'direction')
  );

-- ai_interactions : admin uniquement
CREATE POLICY ai_interactions_admin ON ai_interactions
  FOR ALL USING (
    current_setting('app.current_role', true) = 'admin'
  );

-- audit_logs : lecture admin uniquement | INSERT ouvert à l'application
CREATE POLICY audit_logs_select ON audit_logs
  FOR SELECT USING (
    current_setting('app.current_role', true) = 'admin'
  );

CREATE POLICY audit_logs_insert ON audit_logs
  FOR INSERT WITH CHECK (true);  -- seul INSERT autorisé pour toute l'application

-- rag_chunks : filtrés par rag_document_access (RBAC documentaire)
CREATE POLICY rag_chunks_rbac ON rag_chunks
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM rag_document_access rda
      WHERE rda.document_id = rag_chunks.document_id
        AND rda.allowed_role = current_setting('app.current_role', true)::user_role
    )
  );


-- ============================================================
-- 13. DONNÉES INITIALES (seed)
-- ============================================================

-- Matrice des permissions par défaut
INSERT INTO roles_permissions (role, module, can_read, can_write, can_export) VALUES
  ('admin',         'paie',       true,  true,  true),
  ('admin',         'absences',   true,  true,  true),
  ('admin',         'dashboard',  true,  true,  true),
  ('admin',         'rag_docs',   true,  true,  true),
  ('admin',         'audit',      true,  false, true),
  ('rh',            'paie',       true,  true,  true),
  ('rh',            'absences',   true,  true,  true),
  ('rh',            'dashboard',  true,  true,  true),
  ('rh',            'rag_docs',   true,  true,  false),
  ('direction',     'paie',       true,  false, true),
  ('direction',     'absences',   true,  false, true),
  ('direction',     'dashboard',  true,  false, true),
  ('direction',     'rag_docs',   true,  false, false),
  ('manager',       'absences',   true,  true,  false),
  ('manager',       'dashboard',  true,  false, false),
  ('manager',       'rag_docs',   true,  false, false),
  ('collaborateur', 'absences',   true,  true,  false),
  ('collaborateur', 'rag_docs',   true,  false, false),
  ('qvt',           'absences',   true,  false, false),
  ('qvt',           'dashboard',  true,  false, false)
ON CONFLICT (role, module) DO NOTHING;

-- Règles de sécurité IA par défaut
INSERT INTO ai_security_rules (name, condition_logic, severity) VALUES
  (
    'Accès paie hors RH',
    '{"module": "paie", "allowed_roles": ["rh", "direction", "admin"]}',
    'critique'
  ),
  (
    'Tentatives répétées refusées',
    '{"max_attempts": 5, "window_seconds": 60}',
    'repetee'
  ),
  (
    'Injection de prompt détectée',
    '{"keywords": ["ignore previous", "jailbreak", "system prompt", "bypass"]}',
    'critique'
  )
ON CONFLICT (name) DO NOTHING;


-- ============================================================
-- FIN DU SCHÉMA
-- HumaNai v2 — PostgreSQL 16 + pgvector + pgcrypto + pg_trgm
-- YDAYS 2026 | Ynov Campus Casablanca
-- ============================================================
