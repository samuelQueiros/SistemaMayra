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


def test_lista_codigos_cid(client):
    assert client.get("/api/cid-codes").status_code == 401
    response = client.get("/api/cid-codes", headers=registrar_e_logar(client))

    assert response.status_code == 200
    body = response.json()
    assert any(item["cid"] == "6A02" for item in body)


def test_salva_secoes_clinicas_do_laudo(client):
    headers = registrar_e_logar(client)
    report_id = _criar_relatorio(client, headers)

    payload = {
        "anamnese": "Texto de anamnese de teste.",
        "plano_intervencao": "Plano de intervenção de teste.",
        "encaminhamentos": ["Fonoaudiologia", "Terapia Ocupacional"],
        "diagnostic_hypotheses": [{"label": "Transtorno do Espectro Autista (TEA)", "cid": "6A02"}],
    }

    response = client.patch(f"/api/reports/{report_id}/clinical-sections", json=payload, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["clinical_sections_json"]["anamnese"] == "Texto de anamnese de teste."
    assert body["clinical_sections_json"]["encaminhamentos"] == ["Fonoaudiologia", "Terapia Ocupacional"]
    assert body["clinical_sections_json"]["diagnostic_hypotheses"][0]["cid"] == "6A02"

    detalhe = client.get(f"/api/reports/{report_id}", headers=headers).json()
    assert detalhe["clinical_sections_json"]["anamnese"] == "Texto de anamnese de teste."


def test_secoes_clinicas_omitidas_nao_aparecem_salvas(client):
    headers = registrar_e_logar(client)
    report_id = _criar_relatorio(client, headers)

    response = client.patch(
        f"/api/reports/{report_id}/clinical-sections",
        json={"anamnese": "Só anamnese preenchida."},
        headers=headers,
    )

    assert response.status_code == 200
    assert "plano_intervencao" not in response.json()["clinical_sections_json"]


def test_outro_psicologo_nao_edita_secoes_clinicas_de_laudo_alheio(client):
    headers_a = registrar_e_logar(client, email="a@example.com")
    headers_b = registrar_e_logar(client, email="b@example.com")
    report_id = _criar_relatorio(client, headers_a)

    response = client.patch(
        f"/api/reports/{report_id}/clinical-sections",
        json={"anamnese": "Tentativa indevida."},
        headers=headers_b,
    )

    assert response.status_code == 404


def test_atualiza_registro_profissional_do_psicologo(client):
    headers = registrar_e_logar(client)

    response = client.put(
        "/api/auth/me", json={"professional_registration": "CRP 12/34567"}, headers=headers
    )

    assert response.status_code == 200
    assert response.json()["professional_registration"] == "CRP 12/34567"
    assert client.get("/api/auth/me", headers=headers).json()["professional_registration"] == "CRP 12/34567"
