import app.api.templates as templates_module
from app.services.ai.exceptions import AIConfigurationError
from app.services.ai.schemas import (
    ExtractedClassificationRange,
    ExtractedTemplateArea,
    ExtractedTemplateDraft,
    ExtractedTemplateField,
)
from tests.helpers import registrar_e_logar

RASCUNHO_VALIDO = ExtractedTemplateDraft(
    name="Escala De Teste Importada",
    rule_type="sum_threshold",
    areas=[
        ExtractedTemplateArea(
            key="area_1",
            label="Área 1",
            fields=[ExtractedTemplateField(key="score", label="Pontuação", type="scale", min=0, max=4, weight=1)],
        )
    ],
    classification_ranges=[],
    chart_type="bar",
)


def _configurar_ia(client, headers):
    client.put(
        "/api/settings/ai",
        json={"provider": "anthropic", "model": "claude-sonnet-5", "api_key": "chave-de-teste-1234"},
        headers=headers,
    )


def _upload(client, headers, *, filename="escala.txt", content=b"Texto de exemplo da escala."):
    return client.post(
        "/api/templates/import",
        headers=headers,
        files={"file": (filename, content, "text/plain")},
    )


def test_importa_documento_e_devolve_rascunho_valido(client, monkeypatch):
    headers = registrar_e_logar(client)
    _configurar_ia(client, headers)

    chamada = {}

    def fake_extract(**kwargs):
        chamada.update(kwargs)
        return RASCUNHO_VALIDO

    monkeypatch.setattr(templates_module, "extract_template_from_document", fake_extract)

    response = _upload(client, headers)

    assert response.status_code == 200
    body = response.json()
    assert body["draft_schema_json"]["name"] == "Escala De Teste Importada"
    assert body["validation_errors"] != []  # sem classification_ranges -> inválido para sum_threshold
    assert chamada["provider"] == "anthropic"
    assert "Texto de exemplo" in chamada["document_text"]


def test_rascunho_com_faixas_de_classificacao_nao_gera_erros_de_validacao(client, monkeypatch):
    headers = registrar_e_logar(client)
    _configurar_ia(client, headers)

    rascunho = RASCUNHO_VALIDO.model_copy(
        update={
            "classification_ranges": [
                ExtractedClassificationRange(label="Baixo", min=0, max=4),
                ExtractedClassificationRange(label="Alto", min=5, max=20),
            ]
        }
    )
    monkeypatch.setattr(templates_module, "extract_template_from_document", lambda **kwargs: rascunho)

    response = _upload(client, headers)

    assert response.status_code == 200
    assert response.json()["validation_errors"] == []


def test_formato_de_arquivo_nao_suportado_retorna_400(client):
    headers = registrar_e_logar(client)

    response = _upload(client, headers, filename="escala.png", content=b"nao e um documento de texto")

    assert response.status_code == 400


def test_sem_configuracao_de_ia_retorna_500_com_mensagem_clara(client):
    headers = registrar_e_logar(client)

    response = _upload(client, headers)

    assert response.status_code == 500
    assert "Configurações" in response.json()["detail"]


def test_erro_do_provedor_de_ia_retorna_502_com_mensagem_clara(client, monkeypatch):
    headers = registrar_e_logar(client)
    _configurar_ia(client, headers)

    def fake_extract(**kwargs):
        raise RuntimeError("Error code: 401 - invalid x-api-key")

    monkeypatch.setattr(templates_module, "extract_template_from_document", fake_extract)

    response = _upload(client, headers)

    assert response.status_code == 502
    assert "Configurações" in response.json()["detail"]


def test_erro_de_configuracao_de_ia_retorna_500(client, monkeypatch):
    headers = registrar_e_logar(client)
    _configurar_ia(client, headers)

    def fake_extract(**kwargs):
        raise AIConfigurationError("Provedor de IA desconhecido: 'anthropic'.")

    monkeypatch.setattr(templates_module, "extract_template_from_document", fake_extract)

    response = _upload(client, headers)

    assert response.status_code == 500


def test_exige_autenticacao(client):
    response = _upload(client, headers={})

    assert response.status_code == 401


def test_outro_psicologo_nao_reaproveita_configuracao_de_ia_de_outro(client, monkeypatch):
    headers_a = registrar_e_logar(client, email="a@example.com")
    headers_b = registrar_e_logar(client, email="b@example.com")
    _configurar_ia(client, headers_a)
    monkeypatch.setattr(templates_module, "extract_template_from_document", lambda **kwargs: RASCUNHO_VALIDO)

    response = _upload(client, headers_b)

    # B não configurou IA nem tem chave no .env de teste.
    assert response.status_code == 500
