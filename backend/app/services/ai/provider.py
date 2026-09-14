from langchain_core.language_models.chat_models import BaseChatModel

from app.services.ai.exceptions import AIConfigurationError


def get_chat_model(provider: str, model: str, api_key: str) -> BaseChatModel:
    """Instancia o chat model do LangChain para o provedor/modelo/chave
    informados — trocar de provedor não exige mexer no restante do
    sistema (SPEC.md seção 5). As credenciais já vêm resolvidas pelo
    chamador (configuração da psicóloga no banco, com fallback para o
    `.env` do servidor — ver app.services.ai.resolver)."""

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model, api_key=api_key)

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model, api_key=api_key)

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=model, google_api_key=api_key)

    raise AIConfigurationError(f"Provedor de IA desconhecido: '{provider}'.")
