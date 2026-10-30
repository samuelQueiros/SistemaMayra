import app.api.reports as reports_module
from app.services.ai.exceptions import AIConfigurationError
from app.services.ai.schemas import ConclusionAndInterventions
from tests.helpers import registrar_e_logar
from tests.test_templates import TEMPLATE_VALIDO

RESPOSTAS_VALIDAS = {"comunicacao": {"iniciativa_social": 3}}


def _criar_relatorio(client, headers):
    patient = client.post(
        "/api/patients", json={"name": "Fictício Teste Da Silva", "birth_date": "2020-05-10"}, headers=headers
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


def _payload_conclusao(**extra):
    dados = {
        "patient_name": "Fictício Teste Da Silva",
        "estudo_de_caso": "Estudo de caso fictício de teste.",
        "observacoes_clinicas": "Observações fictícias de teste.",
        "habilidades_avaliadas": "Atenção sustentada: dificuldade importante.",
        "protocolos_utilizados": "SNAP-IV: 9/18 itens de desatenção.",
        "hipotese_selecionada": "TDAH - Transtorno Fictício De Atenção",
    }
    dados.update(extra)
    return dados


def test_gera_conclusao_e_sugestoes_via_ia_a_partir_dos_dados_do_paciente(client, monkeypatch):
    headers = registrar_e_logar(client)
    _configurar_ia(client, headers)
    report_id = _criar_relatorio(client, headers)

    resposta_falsa = ConclusionAndInterventions(
        consideracoes_finais="Considerações finais de teste, individualizadas.",
        sugestoes_intervencao="Sugestões de intervenção de teste, individualizadas.",
    )
    chamada = {}

    def fake_generate_conclusion_and_interventions(**kwargs):
        chamada.update(kwargs)
        return resposta_falsa

    monkeypatch.setattr(
        reports_module, "generate_conclusion_and_interventions", fake_generate_conclusion_and_interventions
    )

    response = client.post(
        f"/api/reports/{report_id}/generate-conclusion",
        headers=headers,
        json=_payload_conclusao(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["consideracoes_finais"] == "Considerações finais de teste, individualizadas."
    assert body["sugestoes_intervencao"] == "Sugestões de intervenção de teste, individualizadas."
    # Confirma que os dados curados do paciente (não um catálogo genérico)
    # é o que chega até a chamada de IA.
    assert chamada["patient_name"] == "Fictício Teste Da Silva"
    assert chamada["estudo_de_caso"] == "Estudo de caso fictício de teste."
    assert chamada["hipotese_selecionada"] == "TDAH - Transtorno Fictício De Atenção"
    assert chamada["provider"] == "anthropic"
    assert chamada["api_key"] == "chave-de-teste-1234"


def test_nao_grava_nada_no_laudo_a_geracao_e_so_texto_de_retorno(client, monkeypatch):
    headers = registrar_e_logar(client)
    _configurar_ia(client, headers)
    report_id = _criar_relatorio(client, headers)

    monkeypatch.setattr(
        reports_module,
        "generate_conclusion_and_interventions",
        lambda **kwargs: ConclusionAndInterventions(consideracoes_finais="X", sugestoes_intervencao="Y"),
    )

    client.post(f"/api/reports/{report_id}/generate-conclusion", headers=headers, json=_payload_conclusao())

    laudo = client.get(f"/api/reports/{report_id}", headers=headers).json()
    assert laudo["generated_text"] is None


def test_sem_configuracao_de_ia_retorna_500_com_mensagem_clara(client):
    headers = registrar_e_logar(client)
    report_id = _criar_relatorio(client, headers)

    response = client.post(f"/api/reports/{report_id}/generate-conclusion", headers=headers, json=_payload_conclusao())

    assert response.status_code == 500
    assert "Configurações" in response.json()["detail"]


def test_erro_do_provedor_de_ia_retorna_500_com_mensagem_clara(client, monkeypatch):
    headers = registrar_e_logar(client)
    _configurar_ia(client, headers)
    report_id = _criar_relatorio(client, headers)

    def fake(**kwargs):
        raise AIConfigurationError("Provedor de IA desconhecido: 'anthropic'.")

    monkeypatch.setattr(reports_module, "generate_conclusion_and_interventions", fake)

    response = client.post(f"/api/reports/{report_id}/generate-conclusion", headers=headers, json=_payload_conclusao())

    assert response.status_code == 500


def test_erro_generico_do_provedor_de_ia_retorna_502_com_mensagem_clara(client, monkeypatch):
    headers = registrar_e_logar(client)
    _configurar_ia(client, headers)
    report_id = _criar_relatorio(client, headers)

    def fake(**kwargs):
        raise RuntimeError("Error code: 401 - invalid x-api-key")

    monkeypatch.setattr(reports_module, "generate_conclusion_and_interventions", fake)

    response = client.post(f"/api/reports/{report_id}/generate-conclusion", headers=headers, json=_payload_conclusao())

    assert response.status_code == 502
    assert "Configurações" in response.json()["detail"]


def test_outro_psicologo_nao_gera_conclusao_de_laudo_alheio(client):
    headers_a = registrar_e_logar(client, email="a@example.com")
    headers_b = registrar_e_logar(client, email="b@example.com")
    report_id = _criar_relatorio(client, headers_a)

    response = client.post(
        f"/api/reports/{report_id}/generate-conclusion", headers=headers_b, json=_payload_conclusao()
    )

    assert response.status_code == 404
