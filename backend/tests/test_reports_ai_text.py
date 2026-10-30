import app.api.reports as reports_module
from app.services.ai.exceptions import AIConfigurationError
from app.services.ai.schemas import ReportSections
from tests.helpers import registrar_e_logar
from tests.test_templates import TEMPLATE_VALIDO

RESPOSTAS_VALIDAS = {"comunicacao": {"iniciativa_social": 3}}


def _criar_relatorio(client, headers):
    patient = client.post(
        "/api/patients", json={"name": "Paciente Teste", "birth_date": "2020-05-10"}, headers=headers
    ).json()
    template = client.post("/api/templates", json=TEMPLATE_VALIDO, headers=headers).json()
    report = client.post(
        f"/api/patients/{patient['id']}/reports",
        json={"template_id": template["id"], "answers": RESPOSTAS_VALIDAS},
        headers=headers,
    ).json()
    return report["id"]


def _configurar_ia(client, headers):
    client.put(
        "/api/settings/ai",
        json={"provider": "anthropic", "model": "claude-sonnet-5", "api_key": "chave-de-teste-1234"},
        headers=headers,
    )


def test_gera_texto_via_ia_e_salva_no_laudo(client, monkeypatch):
    headers = registrar_e_logar(client)
    _configurar_ia(client, headers)
    report_id = _criar_relatorio(client, headers)

    resposta_falsa = ReportSections(
        introducao="Introdução de teste.",
        analise_por_area="Análise de teste.",
        conclusao="Conclusão de teste.",
    )
    chamada = {}

    def fake_generate_report_text(**kwargs):
        chamada.update(kwargs)
        return resposta_falsa

    monkeypatch.setattr(reports_module, "generate_report_text", fake_generate_report_text)

    response = client.post(f"/api/reports/{report_id}/generate-text", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert "Introdução de teste." in body["generated_text"]
    assert "Análise de teste." in body["generated_text"]
    assert "Conclusão de teste." in body["generated_text"]
    assert chamada["patient_name"] == "Paciente Teste"
    assert chamada["template_name"] == TEMPLATE_VALIDO["name"]
    assert chamada["provider"] == "anthropic"
    assert chamada["api_key"] == "chave-de-teste-1234"


def test_sem_configuracao_de_ia_retorna_500_com_mensagem_clara(client):
    headers = registrar_e_logar(client)
    report_id = _criar_relatorio(client, headers)
    # Não configurou IA nem em "Configurações" nem tem chave no .env de
    # teste — deve falhar de forma clara, sem derrubar o resto do sistema.

    response = client.post(f"/api/reports/{report_id}/generate-text", headers=headers)

    assert response.status_code == 500
    assert "Configurações" in response.json()["detail"]


def test_erro_do_provedor_de_ia_retorna_500_com_mensagem_clara(client, monkeypatch):
    headers = registrar_e_logar(client)
    _configurar_ia(client, headers)
    report_id = _criar_relatorio(client, headers)

    def fake_generate_report_text(**kwargs):
        raise AIConfigurationError("Provedor de IA desconhecido: 'anthropic'.")

    monkeypatch.setattr(reports_module, "generate_report_text", fake_generate_report_text)

    response = client.post(f"/api/reports/{report_id}/generate-text", headers=headers)

    assert response.status_code == 500


def test_erro_generico_do_provedor_de_ia_retorna_502_com_mensagem_clara(client, monkeypatch):
    headers = registrar_e_logar(client)
    _configurar_ia(client, headers)
    report_id = _criar_relatorio(client, headers)

    def fake_generate_report_text(**kwargs):
        raise RuntimeError("Error code: 401 - invalid x-api-key")

    monkeypatch.setattr(reports_module, "generate_report_text", fake_generate_report_text)

    response = client.post(f"/api/reports/{report_id}/generate-text", headers=headers)

    assert response.status_code == 502
    assert "Configurações" in response.json()["detail"]


def test_outro_psicologo_nao_gera_texto_de_laudo_alheio(client):
    headers_a = registrar_e_logar(client, email="a@example.com")
    headers_b = registrar_e_logar(client, email="b@example.com")
    report_id = _criar_relatorio(client, headers_a)

    response = client.post(f"/api/reports/{report_id}/generate-text", headers=headers_b)

    assert response.status_code == 404


def test_psicologa_edita_e_salva_o_texto_revisado(client):
    headers = registrar_e_logar(client)
    report_id = _criar_relatorio(client, headers)

    response = client.put(
        f"/api/reports/{report_id}/text",
        json={"generated_text": "Texto revisado manualmente pela psicóloga."},
        headers=headers,
    )

    assert response.status_code == 200
    # A resposta é o resumo leve; o texto salvo está no laudo completo.
    assert "generated_text" not in response.json()
    salvo = client.get(f"/api/reports/{report_id}", headers=headers).json()
    assert salvo["generated_text"] == "Texto revisado manualmente pela psicóloga."


def test_outro_psicologo_nao_edita_texto_de_laudo_alheio(client):
    headers_a = registrar_e_logar(client, email="a@example.com")
    headers_b = registrar_e_logar(client, email="b@example.com")
    report_id = _criar_relatorio(client, headers_a)

    response = client.put(
        f"/api/reports/{report_id}/text",
        json={"generated_text": "Tentativa indevida."},
        headers=headers_b,
    )

    assert response.status_code == 404
