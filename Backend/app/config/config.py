from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Plateforme IA RH"
    DEBUG: bool = False

    # ── Base de données PostgreSQL ────────────────────────────────────────
    # Format : postgresql+asyncpg://user:password@host:port/dbname
    DATABASE_URL: str = ""
    # Format synchrone (utilisé par Alembic / scripts utilitaires)
    DATABASE_URL_SYNC: str = ""

    # ── Redis ─────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT ───────────────────────────────────────────────────────────────
    # En production : openssl rand -hex 32
    JWT_SECRET_KEY: str = "dev-secret-change-in-production-openssl-rand-hex-32"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Sécurité brute force ──────────────────────────────────────────────
    MAX_FAILED_ATTEMPTS: int = 5
    MAX_LOGIN_PER_MINUTE: int = 5   # rate limit par IP

    # ── Chiffrement des données sensibles (pgcrypto / AES-256) ────────────
    # Doit faire exactement 32 caractères en production
    APP_ENCRYPTION_KEY: str = "dev-key-change-me-32-chars-min!!"

    # ── Firebase ──────────────────────────────────────────────────────────
    FIREBASE_CREDENTIALS_PATH: str | None = None
    FIREBASE_PROJECT_ID: str | None = None

    # ── Intelligence Artificielle (LLM / RAG) ─────────────────────────────
    LLM_PROVIDER: str = "openai"                       # openai | anthropic | local
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    EMBEDDING_MODEL: str = "text-embedding-3-small"    # modèle d'embedding pour pgvector

    # ── MinIO (stockage de documents générés) ─────────────────────────────
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ROOT_USER: str = "humanai_minio"
    MINIO_ROOT_PASSWORD: str = "CHANGE_ME_minio_password"
    MINIO_BUCKET_DOCUMENTS: str = "humanai-documents"
    MINIO_BUCKET_RAG: str = "humanai-rag-sources"

    # ── CORS ──────────────────────────────────────────────────────────────
    # Liste d'origines séparées par des virgules
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:3002,http://127.0.0.1:3002,http://localhost:8000,http://127.0.0.1:8000"


    @property
    def cors_origins_list(self) -> list[str]:
        """Renvoie les origines CORS sous forme de liste Python."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
