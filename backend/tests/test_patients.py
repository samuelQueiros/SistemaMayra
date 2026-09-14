from tests.helpers import registrar_e_logar
from tests.test_templates import TEMPLATE_VALIDO


def test_exige_autenticacao_para_listar_pacientes(client):
    response = client.get("/api/patients")

    assert response.status_code == 401


def test_cria_e_lista_paciente_do_proprio_psicologo(client):
    headers = registrar_e_logar(client)

    created = client.post(
        "/api/patients",
        json={"name": "Safira Kerolainy", "birth_date": "2020-05-10"},
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["name"] == "Safira Kerolainy"

    listed = client.get("/api/patients", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["name"] == "Safira Kerolainy"


def test_psicologo_nao_ve_paciente_de_outro_psicologo(client):
    headers_a = registrar_e_logar(client, email="a@example.com")
    headers_b = registrar_e_logar(client, email="b@example.com")

    created = client.post(
        "/api/patients",
        json={"name": "Paciente da Psicóloga A", "birth_date": "2019-01-01"},
        headers=headers_a,
    )
    patient_id = created.json()["id"]

    # B não vê o paciente de A na listagem.
    listed_b = client.get("/api/patients", headers=headers_b)
    assert listed_b.json() == []

    # B não consegue acessar diretamente pelo id (404, não 403 — não revela
    # que o paciente existe).
    get_b = client.get(f"/api/patients/{patient_id}", headers=headers_b)
    assert get_b.status_code == 404

    update_b = client.put(
        f"/api/patients/{patient_id}",
        json={"name": "Tentativa De Alteração", "birth_date": "2019-01-01"},
        headers=headers_b,
    )
    assert update_b.status_code == 404

    delete_b = client.delete(f"/api/patients/{patient_id}", headers=headers_b)
    assert delete_b.status_code == 404

    # A continua enxergando o próprio paciente normalmente.
    get_a = client.get(f"/api/patients/{patient_id}", headers=headers_a)
    assert get_a.status_code == 200


def test_atualiza_e_remove_paciente(client):
    headers = registrar_e_logar(client)
    created = client.post(
        "/api/patients",
        json={"name": "Nome Original", "birth_date": "2020-05-10"},
        headers=headers,
    )
    patient_id = created.json()["id"]

    updated = client.put(
        f"/api/patients/{patient_id}",
        json={"name": "Nome Corrigido", "birth_date": "2020-05-10", "notes": "Observação"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Nome Corrigido"

    deleted = client.delete(f"/api/patients/{patient_id}", headers=headers)
    assert deleted.status_code == 204

    get_after_delete = client.get(f"/api/patients/{patient_id}", headers=headers)
    assert get_after_delete.status_code == 404


def test_nao_permite_excluir_paciente_com_laudos_no_historico(client):
    headers = registrar_e_logar(client)
    patient_id = client.post(
        "/api/patients",
        json={"name": "Safira Kerolainy", "birth_date": "2020-05-10"},
        headers=headers,
    ).json()["id"]
    template_id = client.post("/api/templates", json=TEMPLATE_VALIDO, headers=headers).json()["id"]
    client.post(
        f"/api/patients/{patient_id}/reports",
        json={"template_id": template_id, "answers": {"comunicacao": {"iniciativa_social": 2}}},
        headers=headers,
    )

    response = client.delete(f"/api/patients/{patient_id}", headers=headers)

    assert response.status_code == 409
    # o paciente continua existindo
    assert client.get(f"/api/patients/{patient_id}", headers=headers).status_code == 200
