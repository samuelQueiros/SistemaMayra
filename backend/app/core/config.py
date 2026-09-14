from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "development"
    database_url: str = "sqlite:///./dev.db"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24

    ai_provider: str = "anthropic"
    ai_model: str = "claude-sonnet-5"
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    google_api_key: str | None = None

    # Storage de arquivos (fotos de pacientes, PDFs) — opcional. Sem isso
    # configurado, tudo fica em disco local (backend/storage/...), como
    # sempre foi. Preenchendo s3_bucket, passa a usar um bucket compatível
    # com S3 (AWS, Cloudflare R2, Backblaze B2...) — ver DEPLOY.md.
    s3_bucket: str | None = None
    s3_endpoint_url: str | None = None
    s3_region: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None


settings = Settings()
