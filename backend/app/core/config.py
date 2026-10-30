from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Valores de exemplo dos arquivos .env.example / portainer.env.example — o
# servidor de produção se recusa a subir com eles.
_SEGREDOS_DE_EXEMPLO = {"change-me", "troque-por-um-segredo-forte", "gere-com-openssl-rand-hex-32"}


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

    # Cadastro público (/api/auth/register). Em produção fica desligado por
    # padrão: a conta da psicóloga vem do ADMIN_* (seed_admin.py). Sem isso,
    # qualquer pessoa na internet criaria conta — e usaria a chave de IA do
    # servidor (fallback do .env).
    allow_registration: bool | None = None

    @property
    def em_producao(self) -> bool:
        return self.env.strip().lower() in ("production", "producao", "prod")

    @property
    def cadastro_publico(self) -> bool:
        return self.allow_registration if self.allow_registration is not None else not self.em_producao

    @model_validator(mode="after")
    def _exigir_segredo_forte_em_producao(self) -> "Settings":
        if self.em_producao:
            fraco = self.jwt_secret in _SEGREDOS_DE_EXEMPLO or len(self.jwt_secret) < 32
            if fraco:
                raise ValueError(
                    "JWT_SECRET fraco ou de exemplo em produção. Gere um com "
                    "`openssl rand -hex 32` e defina no .env / variáveis da stack."
                )
        return self

    @field_validator("database_url")
    @classmethod
    def _usar_driver_psycopg(cls, valor: str) -> str:
        # Railway/Heroku/Render entregam "postgres://" ou "postgresql://",
        # que o SQLAlchemy liga ao driver psycopg2 (não instalado). O projeto
        # usa psycopg 3: troca o esquema para "postgresql+psycopg://".
        for prefixo in ("postgres://", "postgresql://"):
            if valor.startswith(prefixo):
                return "postgresql+psycopg://" + valor[len(prefixo) :]
        return valor


settings = Settings()
