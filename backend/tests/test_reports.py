from tests.helpers import registrar_e_logar
from tests.test_templates import TEMPLATE_VALIDO


def _criar_paciente(client, headers, name="Safira Kerolainy"):
    response = client.post(
        "/api/patients", json={"name": name, "birth_date": "2020-05-10"}, headers=headers
    )
    return response.json()["id"]


def _criar_template(client, headers):
    response = client.post("/api/templates", json=TEMPLATE_VALIDO, headers=headers)
    return response.json()["id"]


RESPOSTAS_VALIDAS = {"comunicacao": {"iniciativa_social": 3}}


def test_gera_laudo_calculando_o_resultado_do_motor_de_regras(client):
    headers = registrar_e_logar(client)
    patient_id = _criar_paciente(client, headers)
    template_id = _criar_template(client, headers)

    response = client.post(
        f"/api/patients/{patient_id}/reports",
        json={"template_id": template_id, "answers": RESPOSTAS_VALIDAS},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["patient_id"] == patient_id
    assert body["template_id"] == template_id
    assert body["answers_json"] == RESPOSTAS_VALIDAS
    assert body["computed_json"]["scores"] == {"comunicacao": 3.0}
    assert body["computed_json"]["total"] == 3.0
    assert body["generated_text"] is None
    assert body["pdf_path"] is None


def test_respostas_invalidas_retornam_400(client):
    headers = registrar_e_logar(client)
    patient_id = _criar_paciente(client, headers)
    template_id = _criar_template(client, headers)

    response = client.post(
        f"/api/patients/{patient_id}/reports",
        json={"template_id": template_id, "answers": {"comunicacao": {"iniciativa_social": "muito"}}},
        headers=headers,
    )

    assert response.status_code == 400


def test_nao_gera_laudo_para_paciente_de_outro_psicologo(client):
    headers_a = registrar_e_logar(client, email="a@example.com")
    headers_b = registrar_e_logar(client, email="b@example.com")
    patient_id = _criar_paciente(client, headers_a)
    template_id_b = _criar_template(client, headers_b)

    response = client.post(
        f"/api/patients/{patient_id}/reports",
        json={"template_id": template_id_b, "answers": RESPOSTAS_VALIDAS},
        headers=headers_b,
    )

    assert response.status_code == 404


def test_nao_gera_laudo_com_template_de_outro_psicologo(client):
    headers_a = registrar_e_logar(client, email="a@example.com")
    headers_b = registrar_e_logar(client, email="b@example.com")
    patient_id_a = _criar_paciente(client, headers_a)
    template_id_b = _criar_template(client, headers_b)

    response = client.post(
        f"/api/patients/{patient_id_a}/reports",
        json={"template_id": template_id_b, "answers": RESPOSTAS_VALIDAS},
        headers=headers_a,
    )

    assert response.status_code == 404


def test_lista_historico_de_laudos_do_paciente(client):
    headers = registrar_e_logar(client)
    patient_id = _criar_paciente(client, headers)
    template_id = _criar_template(client, headers)
    client.post(
        f"/api/patients/{patient_id}/reports",
        json={"template_id": template_id, "answers": RESPOSTAS_VALIDAS},
        headers=headers,
    )

    response = client.get(f"/api/patients/{patient_id}/reports", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_busca_laudo_por_id(client):
    headers = registrar_e_logar(client)
    patient_id = _criar_paciente(client, headers)
    template_id = _criar_template(client, headers)
    created = client.post(
        f"/api/patients/{patient_id}/reports",
        json={"template_id": template_id, "answers": RESPOSTAS_VALIDAS},
        headers=headers,
    )
    report_id = created.json()["id"]

    response = client.get(f"/api/reports/{report_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == report_id


def test_outro_psicologo_nao_acessa_laudo_alheio(client):
    headers_a = registrar_e_logar(client, email="a@example.com")
    headers_b = registrar_e_logar(client, email="b@example.com")
    patient_id = _criar_paciente(client, headers_a)
    template_id = _criar_template(client, headers_a)
    created = client.post(
        f"/api/patients/{patient_id}/reports",
        json={"template_id": template_id, "answers": RESPOSTAS_VALIDAS},
        headers=headers_a,
    )
    report_id = created.json()["id"]

    response = client.get(f"/api/reports/{report_id}", headers=headers_b)

    assert response.status_code == 404
