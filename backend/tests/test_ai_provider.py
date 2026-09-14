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
