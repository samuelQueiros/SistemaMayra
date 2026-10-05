from pydantic import BaseModel

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable

from app.services.ai.exceptions import AIConfigurationError
from app.services.ai.provedores import provedor


def get_chat_model(provider: str, model: str, api_key: str) -> BaseChatModel:
    """Instancia o chat model do LangChain para o provedor/modelo/chave
    informados — trocar de provedor não exige mexer no restante do
    sistema (SPEC.md seção 5). As credenciais já vêm resolvidas pelo
    chamador (configuração da psicóloga no banco, com fallback para o
    `.env` do servidor — ver app.services.ai.resolver). Provedores além de
    Claude/GPT/Gemini usam a API compatível com a OpenAI (ver
    `provedores.py`)."""

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model, api_key=api_key)

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model, api_key=api_key)

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=model, google_api_key=api_key)

    info = provedor(provider)
    if info is not None and info.base_url:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model, api_key=api_key, base_url=info.base_url)

    raise AIConfigurationError(f"Provedor de IA desconhecido: '{provider}'.")


def get_structured_model(provider: str, model: str, api_key: str, schema: type[BaseModel]) -> Runnable:
    """Chat model que devolve `schema` preenchido. Nos provedores
    compatíveis com a OpenAI (que nem sempre aceitam o modo "json_schema"
    da OpenAI), usa chamada de ferramenta, que todos suportam."""
    chat = get_chat_model(provider, model, api_key)
    if provider in ("anthropic", "openai", "google"):
        return chat.with_structured_output(schema)
    return chat.with_structured_output(schema, method="function_calling")
