from tests.helpers import registrar_e_logar
from tests.test_templates import TEMPLATE_VALIDO


def _criar_paciente(client, headers, name="Paciente Teste"):
    response = client.post("/api/patients", json={"name": name, "birth_date": "2020-05-10"}, headers=headers)
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


def test_lista_de_laudos_e_autosave_sao_leves(client):
    """Lista e autosave não devolvem respostas (fotos em base64) nem o HTML
    final; o autosave sem fotos mantém as fotos já salvas."""
    headers = registrar_e_logar(client)
    template = client.post("/api/templates/custom-form-avaliacao", headers=headers).json()
    pid = client.post("/api/patients", json={"name": "Criança", "birth_date": "2019-01-01"}, headers=headers).json()[
        "id"
    ]
    fotos = [{"nome": "f.jpg", "src": "data:image/jpeg;base64," + "A" * 5000}]
    laudo = client.post(
        f"/api/patients/{pid}/reports",
        json={"template_id": template["id"], "answers": {"nomePaciente": "Criança", "__fotosPacienteDados": fotos}},
        headers=headers,
    ).json()
    client.put(
        f"/api/reports/{laudo['id']}/text", json={"generated_text": "<html>" + "x" * 5000 + "</html>"}, headers=headers
    )

    resposta = client.put(
        f"/api/reports/{laudo['id']}/answers", json={"answers": {"nomePaciente": "Criança Atualizada"}}, headers=headers
    )
    assert resposta.status_code == 200
    assert "answers_json" not in resposta.json() and "generated_text" not in resposta.json()

    lista = client.get(f"/api/patients/{pid}/reports", headers=headers).json()
    assert lista[0]["id"] == laudo["id"]
    assert "answers_json" not in lista[0] and "generated_text" not in lista[0]

    completo = client.get(f"/api/reports/{laudo['id']}", headers=headers).json()
    assert completo["answers_json"]["nomePaciente"] == "Criança Atualizada"
    assert completo["answers_json"]["__fotosPacienteDados"] == fotos
    assert completo["generated_text"].startswith("<html>")

    # Enviar a chave (ex.: lista vazia) substitui as fotos.
    client.put(f"/api/reports/{laudo['id']}/answers", json={"answers": {"__fotosPacienteDados": []}}, headers=headers)
    assert (
        client.get(f"/api/reports/{laudo['id']}", headers=headers).json()["answers_json"]["__fotosPacienteDados"] == []
    )


def test_resumo_individual_nao_transfere_documento_e_exige_proprietario(client):
    from uuid import UUID
    from app.models.report import Report

    headers = registrar_e_logar(client)
    pid = _criar_paciente(client, headers)
    tid = _criar_template(client, headers)
    rid = client.post(
        f"/api/patients/{pid}/reports", json={"template_id": tid, "answers": RESPOSTAS_VALIDAS}, headers=headers
    ).json()["id"]
    with client.db_session_factory() as db:
        report = db.get(Report, UUID(rid))
        report.answers_json = {"__fotosPacienteDados": ["foto-pesada"]}
        report.generated_text = "<html>documento-com-imagens</html>"
        report.computed_json = {"origem": "ia_pdf", "catalogo": {"campos": ["campo"]}}
        db.commit()
    resposta = client.get(f"/api/reports/{rid}/resumo", headers=headers)
    assert resposta.status_code == 200
    assert resposta.json()["id"] == rid
    assert resposta.json()["computed_json"] == {"origem": "ia_pdf"}
    assert "answers_json" not in resposta.json()
    assert "generated_text" not in resposta.json()
    completo = client.get(f"/api/reports/{rid}", headers=headers).json()
    assert completo["generated_text"] == "<html>documento-com-imagens</html>"
    outra = registrar_e_logar(client, email="outra@example.com")
    assert client.get(f"/api/reports/{rid}/resumo", headers=outra).status_code == 404
    assert client.get(f"/api/reports/{rid}/resumo").status_code == 401
