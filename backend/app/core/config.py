from pydantic import field_validator
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

    # Conta de psicóloga criada/atualizada a cada start do container (ver
    # app/seed_admin.py) — opcional, útil para configurar o login pelas
    # variáveis do Portainer em vez de chamar /api/auth/register.
    admin_name: str | None = None
    admin_email: str | None = None
    admin_password: str | None = None

    @field_validator("database_url")
    @classmethod
    def _usar_driver_psycopg(cls, valor: str) -> str:
        # Railway/Heroku/Render entregam "postgres://" ou "postgresql://",
        # que o SQLAlchemy liga ao driver psycopg2 (não instalado). O projeto
        # usa psycopg 3: troca o esquema para "postgresql+psycopg://".
        for prefixo in ("postgres://", "postgresql://"):
            if valor.startswith(prefixo):
                return "postgresql+psycopg://" + valor[len(prefixo):]
        return valor


settings = Settings()
