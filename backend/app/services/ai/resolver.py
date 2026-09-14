from app.core.config import settings
from app.core.security import decrypt_secret
from app.models.ai_settings import AISettings
from app.services.ai.exceptions import AIConfigurationError


def resolve_ai_credentials(ai_settings: AISettings | None) -> tuple[str, str, str]:
    """Resolve provedor/modelo/chave a usar: prioriza a configuração da
    própria psicóloga (tela de Configurações); se ela não tiver
    configurado nada, cai para o `.env` do servidor (uso administrativo/
    ambiente de desenvolvimento)."""

    if ai_settings is not None:
        return ai_settings.provider, ai_settings.model, decrypt_secret(ai_settings.api_key)

    provider = settings.ai_provider
    model = settings.ai_model
    chaves_por_provedor = {
        "anthropic": settings.anthropic_api_key,
        "openai": settings.openai_api_key,
        "google": settings.google_api_key,
    }
    api_key = chaves_por_provedor.get(provider)
    if not api_key:
        raise AIConfigurationError(
            "Nenhuma chave de IA configurada. Configure em \"Configurações\" "
            "dentro do sistema, ou defina ANTHROPIC_API_KEY/OPENAI_API_KEY/"
            "GOOGLE_API_KEY no .env do servidor."
        )
    return provider, model, api_key
