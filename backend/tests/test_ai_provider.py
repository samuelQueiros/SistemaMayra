import pytest

from app.services.ai.exceptions import AIConfigurationError
from app.services.ai.provider import get_chat_model


@pytest.mark.parametrize(
    "provider, expected_class",
    [
        ("anthropic", "ChatAnthropic"),
        ("openai", "ChatOpenAI"),
        ("google", "ChatGoogleGenerativeAI"),
    ],
)
def test_get_chat_model_instancia_a_classe_certa_por_provedor(provider, expected_class):
    model = get_chat_model(provider, "modelo-qualquer", "chave-fake")

    assert type(model).__name__ == expected_class


def test_provedor_desconhecido_gera_erro_de_configuracao():
    with pytest.raises(AIConfigurationError):
        get_chat_model("isso-nao-existe", "modelo", "chave")


from app.services.ai.provedores import PROVEDORES  # noqa: E402
from app.services.ai.provider import get_structured_model  # noqa: E402
from app.services.ai.schemas import ReportSections  # noqa: E402


@pytest.mark.parametrize("provider", [p for p in PROVEDORES if PROVEDORES[p].base_url])
def test_provedores_compativeis_com_openai_usam_o_endereco_proprio(provider):
    model = get_chat_model(provider, "modelo-qualquer", "chave-fake")
    assert type(model).__name__ == "ChatOpenAI"
    assert model.openai_api_base == PROVEDORES[provider].base_url


def test_todo_provedor_tem_modelo_sugerido_e_link_da_chave():
    for p in PROVEDORES.values():
        assert p.modelos and p.link_chave.startswith("https://"), p.id
        assert p.leitura_pdf in ("nativa", "imagens", "texto")
        # sem conector próprio, precisa do endereço compatível com a OpenAI
        assert p.id in ("anthropic", "openai", "google") or p.base_url, p.id


@pytest.mark.parametrize("provider", list(PROVEDORES))
def test_saida_estruturada_funciona_para_todos(provider):
    assert get_structured_model(provider, "modelo-qualquer", "chave-fake", ReportSections) is not None


# --- limites por chamada --------------------------------------------------------

from app.services.ai.provider import LimitesDaChamada  # noqa: E402

LIMITES = LimitesDaChamada(timeout_s=99, max_tokens=1234, raciocinio_leve=True)


@pytest.mark.parametrize(
    "provider, campo_timeout, campo_tokens",
    [
        ("anthropic", "default_request_timeout", "max_tokens"),
        ("openai", "request_timeout", "max_tokens"),
        ("google", "timeout", "max_output_tokens"),
        ("openrouter", "request_timeout", "max_tokens"),
    ],
)
def test_limites_chegam_a_cada_conector_sem_retentativas_do_sdk(provider, campo_timeout, campo_tokens):
    model = get_chat_model(provider, "modelo-qualquer", "chave-fake", LIMITES)
    assert getattr(model, campo_timeout) == 99
    assert getattr(model, campo_tokens) == 1234
    assert model.max_retries == 0


def test_sem_limites_explicitos_ainda_ha_teto_de_tempo():
    # Antes: Claude sem tempo-limite nenhum e resposta do tamanho máximo do modelo.
    model = get_chat_model("anthropic", "claude-sonnet-5", "chave-fake")
    assert model.default_request_timeout is not None and model.max_tokens <= 32_000


@pytest.mark.parametrize(
    "provider, modelo, esperado",
    [
        ("openai", "gpt-5", "low"),
        ("openai", "o3-mini", "low"),
        ("openai", "gpt-5-chat-latest", None),
        ("openai", "gpt-4o", None),
        ("openrouter", "openai/gpt-5", None),
    ],
)
def test_raciocinio_leve_so_em_modelos_de_raciocinio_da_openai(provider, modelo, esperado):
    assert get_chat_model(provider, modelo, "chave-fake", LIMITES).reasoning_effort == esperado


@pytest.mark.parametrize(
    "modelo, nivel, orcamento",
    [
        ("gemini-3.6-flash", "low", None),
        ("gemini-3-pro-preview", "low", None),
        ("gemini-2.5-pro", None, 1024),
        ("gemini-2.0-flash", None, None),
    ],
)
def test_raciocinio_leve_no_gemini(modelo, nivel, orcamento):
    # Sem isso o Gemini 3 pensa no nível "high" em todo agente do Laudo Por IA.
    model = get_chat_model("google", modelo, "chave-fake", LIMITES)
    assert model.thinking_level == nivel
    assert model.thinking_budget == orcamento


def test_gemini_sem_raciocinio_leve_usa_o_padrao_do_modelo():
    model = get_chat_model("google", "gemini-3.6-flash", "chave-fake")
    assert model.thinking_level is None and model.thinking_budget is None
