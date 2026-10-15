from dataclasses import dataclass

from pydantic import BaseModel

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable

from app.services.ai.exceptions import AIConfigurationError
from app.services.ai.provedores import provedor


@dataclass(frozen=True)
class LimitesDaChamada:
    """Teto de tempo e de tamanho de uma chamada à IA. Sem isso valiam os
    padrões dos SDKs: até 10 min (OpenAI) ou sem limite nenhum (Anthropic) por
    chamada, resposta do tamanho máximo do modelo e retentativas próprias de
    cada SDK somadas às nossas — uma geração podia ficar presa por muitos
    minutos sem resposta para a tela."""

    timeout_s: float = 240
    max_tokens: int = 32_000
    # Raciocínio curto nos modelos que "pensam" antes de responder (GPT-5, o3...):
    # para transcrever um PDF não precisa de mais, e fica bem mais rápido.
    raciocinio_leve: bool = False


LIMITES_PADRAO = LimitesDaChamada()


def _modelo_de_raciocinio_openai(model: str) -> bool:
    nome = model.lower()
    return (nome.startswith("gpt-5") or nome[:2] in ("o1", "o3", "o4")) and "chat" not in nome


def get_chat_model(provider: str, model: str, api_key: str, limites: LimitesDaChamada = LIMITES_PADRAO) -> BaseChatModel:
    """Instancia o chat model do LangChain para o provedor/modelo/chave
    informados — trocar de provedor não exige mexer no restante do
    sistema (SPEC.md seção 5). As credenciais já vêm resolvidas pelo
    chamador (configuração da psicóloga no banco, com fallback para o
    `.env` do servidor — ver app.services.ai.resolver). Provedores além de
    Claude/GPT/Gemini usam a API compatível com a OpenAI (ver
    `provedores.py`). As retentativas ficam só com o sistema
    (`chains._invocar_com_retentativas`), por isso `max_retries=0` aqui."""

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=model, api_key=api_key, timeout=limites.timeout_s, max_tokens=limites.max_tokens, max_retries=0
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        extras = {"reasoning_effort": "low"} if limites.raciocinio_leve and _modelo_de_raciocinio_openai(model) else {}
        return ChatOpenAI(
            model=model, api_key=api_key, timeout=limites.timeout_s, max_tokens=limites.max_tokens, max_retries=0, **extras
        )

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            timeout=limites.timeout_s,
            max_output_tokens=limites.max_tokens,
            max_retries=0,
        )

    info = provedor(provider)
    if info is not None and info.base_url:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=info.base_url,
            timeout=limites.timeout_s,
            max_tokens=limites.max_tokens,
            max_retries=0,
        )

    raise AIConfigurationError(f"Provedor de IA desconhecido: '{provider}'.")


def get_structured_model(
    provider: str, model: str, api_key: str, schema: type[BaseModel], limites: LimitesDaChamada = LIMITES_PADRAO
) -> Runnable:
    """Chat model que devolve `schema` preenchido. Nos provedores
    compatíveis com a OpenAI (que nem sempre aceitam o modo "json_schema"
    da OpenAI), usa chamada de ferramenta, que todos suportam."""
    chat = get_chat_model(provider, model, api_key, limites)
    if provider in ("anthropic", "openai", "google"):
        return chat.with_structured_output(schema)
    return chat.with_structured_output(schema, method="function_calling")
