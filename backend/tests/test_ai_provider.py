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
