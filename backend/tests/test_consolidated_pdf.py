import pytest

import app.api.reports as reports_module
import app.services.storage as storage_module
from app.services.ai.schemas import ReportSections
from tests.helpers import registrar_e_logar
from tests.test_templates import TEMPLATE_VALIDO

RESPOSTAS_VALIDAS = {"comunicacao": {"iniciativa_social": 3}}


@pytest.fixture(autouse=True)
def usar_storage_temporario(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_module, "_LOCAL_STORAGE_ROOT", tmp_path / "storage_teste")


def _criar_paciente_e_laudos(client, headers, quantidade=2):
    patient = client.post(
        "/api/patients", json={"name": "Safira Kerolainy", "birth_date": "2020-05-10"}, headers=headers
    ).json()
    template = client.post("/api/templates", json=TEMPLATE_VALIDO, headers=headers).json()
    report_ids = []
    for _ in range(quantidade):
        report = client.post(
            f"/api/patients/{patient['id']}/reports",
            json={"template_id": template["id"], "answers": RESPOSTAS_VALIDAS},
            headers=headers,
        ).json()
        report_ids.append(report["id"])
    return patient["id"], report_ids


def _configurar_ia(client, headers):
    client.put(
        "/api/settings/ai",
        json={"provider": "anthropic", "model": "claude-sonnet-5", "api_key": "chave-de-teste-1234"},
        headers=headers,
    )


def _mockar_ia(monkeypatch):
    resposta_falsa = ReportSections(
        introducao="Introdução consolidada de teste.",
        analise_por_area="Síntese consolidada de teste.",
        conclusao="Conclusão consolidada de teste.",
    )
    chamada = {}

    def fake(**kwargs):
        chamada.update(kwargs)
        return resposta_falsa

    monkeypatch.setattr(reports_module, "generate_consolidated_report_text", fake)
    return chamada


def test_gera_pdf_consolidado_de_varios_laudos(client, monkeypatch):
    headers = registrar_e_logar(client)
    _configurar_ia(client, headers)
    patient_id, report_ids = _criar_paciente_e_laudos(client, headers, quantidade=2)
    chamada = _mockar_ia(monkeypatch)

    response = client.post(
        f"/api/patients/{patient_id}/consolidated-pdf",
        json={"report_ids": report_ids},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert len(chamada["reports"]) == 2
    assert chamada["patient_name"] == "Safira Kerolainy"


def test_exige_ao_menos_um_laudo(client):
    headers = registrar_e_logar(client)
    patient_id, _ = _criar_paciente_e_laudos(client, headers, quantidade=1)

    response = client.post(
        f"/api/patients/{patient_id}/consolidated-pdf",
        json={"report_ids": []},
        headers=headers,
    )

    assert response.status_code == 400


def test_rejeita_laudo_de_outro_paciente(client, monkeypatch):
    headers = registrar_e_logar(client)
    _mockar_ia(monkeypatch)
    patient_id_1, report_ids_1 = _criar_paciente_e_laudos(client, headers, quantidade=1)
    _, report_ids_2 = _criar_paciente_e_laudos(client, headers, quantidade=1)

    response = client.post(
        f"/api/patients/{patient_id_1}/consolidated-pdf",
        json={"report_ids": [report_ids_1[0], report_ids_2[0]]},
        headers=headers,
    )

    assert response.status_code == 400


def test_pdf_consolidado_fica_salvo_e_listado_no_historico(client, monkeypatch):
    headers = registrar_e_logar(client)
    _configurar_ia(client, headers)
    patient_id, report_ids = _criar_paciente_e_laudos(client, headers, quantidade=2)
    _mockar_ia(monkeypatch)

    gerado = client.post(
        f"/api/patients/{patient_id}/consolidated-pdf",
        json={"report_ids": report_ids},
        headers=headers,
    )
    assert gerado.status_code == 200

    listado = client.get(f"/api/patients/{patient_id}/consolidated-reports", headers=headers)
    assert listado.status_code == 200
    body = listado.json()
    assert len(body) == 1
    assert set(body[0]["report_ids"]) == set(report_ids)
    assert "Introdução consolidada de teste." in body[0]["generated_text"]


def test_redownload_do_consolidado_nao_chama_a_ia_de_novo(client, monkeypatch):
    headers = registrar_e_logar(client)
    _configurar_ia(client, headers)
    patient_id, report_ids = _criar_paciente_e_laudos(client, headers, quantidade=2)
    _mockar_ia(monkeypatch)

    client.post(
        f"/api/patients/{patient_id}/consolidated-pdf",
        json={"report_ids": report_ids},
        headers=headers,
    )
    consolidated_id = client.get(
        f"/api/patients/{patient_id}/consolidated-reports", headers=headers
    ).json()[0]["id"]

    def falha_se_chamado(**kwargs):
        raise AssertionError("Não deveria chamar a IA de novo para rebaixar um PDF já salvo.")

    monkeypatch.setattr(reports_module, "generate_consolidated_report_text", falha_se_chamado)

    resposta = client.get(f"/api/consolidated-reports/{consolidated_id}/pdf", headers=headers)

    assert resposta.status_code == 200
    assert resposta.content.startswith(b"%PDF")


def test_outro_psicologo_nao_ve_nem_rebaixa_consolidado_alheio(client, monkeypatch):
    headers_a = registrar_e_logar(client, email="a@example.com")
    headers_b = registrar_e_logar(client, email="b@example.com")
    _configurar_ia(client, headers_a)
    patient_id, report_ids = _criar_paciente_e_laudos(client, headers_a, quantidade=1)
    _mockar_ia(monkeypatch)

    client.post(
        f"/api/patients/{patient_id}/consolidated-pdf",
        json={"report_ids": report_ids},
        headers=headers_a,
    )
    consolidated_id = client.get(
        f"/api/patients/{patient_id}/consolidated-reports", headers=headers_a
    ).json()[0]["id"]

    # B nem enxerga que o paciente existe (mesmo padrão de get_patient_or_404
    # usado em todo o sistema — 404, não uma lista vazia revelando o paciente).
    assert client.get(f"/api/patients/{patient_id}/consolidated-reports", headers=headers_b).status_code == 404
    assert client.get(f"/api/consolidated-reports/{consolidated_id}/pdf", headers=headers_b).status_code == 404


def test_outro_psicologo_nao_consolida_laudos_alheios(client, monkeypatch):
    headers_a = registrar_e_logar(client, email="a@example.com")
    headers_b = registrar_e_logar(client, email="b@example.com")
    _mockar_ia(monkeypatch)
    patient_id, report_ids = _criar_paciente_e_laudos(client, headers_a, quantidade=1)

    response = client.post(
        f"/api/patients/{patient_id}/consolidated-pdf",
        json={"report_ids": report_ids},
        headers=headers_b,
    )

    assert response.status_code == 404
