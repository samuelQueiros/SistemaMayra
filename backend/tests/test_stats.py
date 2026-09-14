from tests.helpers import registrar_e_logar
from tests.test_templates import TEMPLATE_VALIDO

RESPOSTAS_VALIDAS = {"comunicacao": {"iniciativa_social": 3}}


def _criar_paciente(client, headers, nome="Safira Kerolainy"):
    return client.post("/api/patients", json={"name": nome, "birth_date": "2020-05-10"}, headers=headers).json()


def _gerar_laudo(client, headers, patient_id, template_id):
    return client.post(
        f"/api/patients/{patient_id}/reports",
        json={"template_id": template_id, "answers": RESPOSTAS_VALIDAS},
        headers=headers,
    ).json()


def test_exige_autenticacao(client):
    response = client.get("/api/stats/summary")

    assert response.status_code == 401


def test_resumo_vazio_para_psicologa_sem_dados(client):
    headers = registrar_e_logar(client)

    response = client.get("/api/stats/summary", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "total_patients": 0,
        "total_reports": 0,
        "reports_last_30_days": 0,
        "reports_by_template": [],
    }


def test_conta_pacientes_laudos_e_laudos_por_modelo(client):
    headers = registrar_e_logar(client)
    template = client.post("/api/templates", json=TEMPLATE_VALIDO, headers=headers).json()
    paciente_1 = _criar_paciente(client, headers, "Paciente Um")
    paciente_2 = _criar_paciente(client, headers, "Paciente Dois")
    _gerar_laudo(client, headers, paciente_1["id"], template["id"])
    _gerar_laudo(client, headers, paciente_1["id"], template["id"])
    _gerar_laudo(client, headers, paciente_2["id"], template["id"])

    response = client.get("/api/stats/summary", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total_patients"] == 2
    assert body["total_reports"] == 3
    assert body["reports_last_30_days"] == 3
    assert body["reports_by_template"] == [{"template_name": TEMPLATE_VALIDO["name"], "count": 3}]


def test_estatisticas_sao_isoladas_por_psicologa(client):
    headers_a = registrar_e_logar(client, email="a@example.com")
    headers_b = registrar_e_logar(client, email="b@example.com")
    template_a = client.post("/api/templates", json=TEMPLATE_VALIDO, headers=headers_a).json()
    paciente_a = _criar_paciente(client, headers_a)
    _gerar_laudo(client, headers_a, paciente_a["id"], template_a["id"])

    response = client.get("/api/stats/summary", headers=headers_b)

    assert response.status_code == 200
    body = response.json()
    assert body["total_patients"] == 0
    assert body["total_reports"] == 0
    assert body["reports_by_template"] == []
