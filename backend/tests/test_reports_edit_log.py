from tests.helpers import registrar_e_logar
from tests.test_templates import TEMPLATE_VALIDO

RESPOSTAS_VALIDAS = {"comunicacao": {"iniciativa_social": 3}}


def _criar_relatorio(client, headers):
    patient = client.post(
        "/api/patients", json={"name": "Safira Kerolainy", "birth_date": "2020-05-10"}, headers=headers
    ).json()
    template = client.post("/api/templates", json=TEMPLATE_VALIDO, headers=headers).json()
    report = client.post(
        f"/api/patients/{patient['id']}/reports",
        json={"template_id": template["id"], "answers": RESPOSTAS_VALIDAS},
        headers=headers,
    ).json()
    return report["id"]


def test_edita_nome_do_modelo_e_classificacao(client):
    headers = registrar_e_logar(client)
    report_id = _criar_relatorio(client, headers)

    response = client.patch(
        f"/api/reports/{report_id}",
        json={"template_name_override": "CARS (Revisado)", "classification_override": "Grave (revisado)"},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["template_name_override"] == "CARS (Revisado)"
    assert body["classification_override"] == "Grave (revisado)"


def test_editar_apenas_um_campo_nao_apaga_o_outro(client):
    headers = registrar_e_logar(client)
    report_id = _criar_relatorio(client, headers)
    client.patch(
        f"/api/reports/{report_id}",
        json={"template_name_override": "Nome Corrigido"},
        headers=headers,
    )

    response = client.patch(
        f"/api/reports/{report_id}",
        json={"classification_override": "Classificação Corrigida"},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["template_name_override"] == "Nome Corrigido"
    assert body["classification_override"] == "Classificação Corrigida"


def test_cada_edicao_gera_uma_entrada_de_log(client):
    headers = registrar_e_logar(client)
    report_id = _criar_relatorio(client, headers)

    client.patch(
        f"/api/reports/{report_id}",
        json={"classification_override": "Primeira Correção"},
        headers=headers,
    )
    client.patch(
        f"/api/reports/{report_id}",
        json={"classification_override": "Segunda Correção"},
        headers=headers,
    )

    response = client.get(f"/api/reports/{report_id}/logs", headers=headers)

    assert response.status_code == 200
    logs = response.json()
    assert len(logs) == 2
    assert logs[0]["new_value"] == "Segunda Correção"  # mais recente primeiro
    assert logs[0]["old_value"] == "Primeira Correção"
    assert logs[1]["new_value"] == "Primeira Correção"
    assert logs[1]["old_value"] is None
    assert all(log["field"] == "classification_override" for log in logs)
    assert all(log["psychologist_name"] == "Mayra" for log in logs)


def test_editar_com_o_mesmo_valor_nao_gera_log(client):
    headers = registrar_e_logar(client)
    report_id = _criar_relatorio(client, headers)
    client.patch(
        f"/api/reports/{report_id}",
        json={"classification_override": "Valor Único"},
        headers=headers,
    )

    client.patch(
        f"/api/reports/{report_id}",
        json={"classification_override": "Valor Único"},
        headers=headers,
    )

    logs = client.get(f"/api/reports/{report_id}/logs", headers=headers).json()
    assert len(logs) == 1


def test_outro_psicologo_nao_edita_nem_ve_logs_de_laudo_alheio(client):
    headers_a = registrar_e_logar(client, email="a@example.com")
    headers_b = registrar_e_logar(client, email="b@example.com")
    report_id = _criar_relatorio(client, headers_a)

    edit_response = client.patch(
        f"/api/reports/{report_id}",
        json={"classification_override": "Tentativa Indevida"},
        headers=headers_b,
    )
    logs_response = client.get(f"/api/reports/{report_id}/logs", headers=headers_b)

    assert edit_response.status_code == 404
    assert logs_response.status_code == 404
