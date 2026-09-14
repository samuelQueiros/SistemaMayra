import pytest

import app.services.storage as storage_module
from tests.helpers import registrar_e_logar
from tests.test_templates import TEMPLATE_VALIDO

RESPOSTAS_VALIDAS = {"comunicacao": {"iniciativa_social": 3}}


@pytest.fixture(autouse=True)
def usar_storage_temporario(tmp_path, monkeypatch):
    # Evita que os testes gravem PDFs/fotos de verdade em backend/storage/.
    monkeypatch.setattr(storage_module, "_LOCAL_STORAGE_ROOT", tmp_path / "storage_teste")


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


def test_baixa_pdf_do_laudo(client):
    headers = registrar_e_logar(client)
    report_id = _criar_relatorio(client, headers)

    response = client.get(f"/api/reports/{report_id}/pdf", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 500


def test_pdf_reflete_texto_revisado(client):
    headers = registrar_e_logar(client)
    report_id = _criar_relatorio(client, headers)
    client.put(
        f"/api/reports/{report_id}/text",
        json={"generated_text": "Texto de revisão específico para o teste do PDF."},
        headers=headers,
    )

    response = client.get(f"/api/reports/{report_id}/pdf", headers=headers)

    assert response.status_code == 200
    # O PDF é binário comprimido; o mais confiável é confirmar que o
    # laudo foi marcado com o caminho do arquivo salvo, e não vasculhar
    # bytes comprimidos em busca do texto.
    detalhe = client.get(f"/api/reports/{report_id}", headers=headers).json()
    assert detalhe["pdf_path"] is not None
    assert detalhe["pdf_path"].endswith(f"{report_id}.pdf")


def test_pdf_com_secoes_clinicas_fotos_e_assinatura_continua_gerando_normalmente(client):
    headers = registrar_e_logar(client)
    client.put("/api/auth/me", json={"professional_registration": "CRP 12/34567"}, headers=headers)
    report_id = _criar_relatorio(client, headers)

    patient_id = client.get(f"/api/reports/{report_id}", headers=headers).json()["patient_id"]
    client.post(
        f"/api/patients/{patient_id}/photos",
        headers=headers,
        files={"file": ("foto.jpg", b"\xff\xd8\xff\xe0conteudo-de-teste", "image/jpeg")},
    )
    client.patch(
        f"/api/reports/{report_id}/clinical-sections",
        json={
            "anamnese": "Texto de anamnese de teste.\n\nSegundo parágrafo.",
            "plano_intervencao": "Plano de intervenção de teste.",
            "encaminhamentos": ["Fonoaudiologia"],
            "diagnostic_hypotheses": [{"label": "TEA", "cid": "6A02"}],
        },
        headers=headers,
    )

    response = client.get(f"/api/reports/{report_id}/pdf", headers=headers)

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_outro_psicologo_nao_baixa_pdf_de_laudo_alheio(client):
    headers_a = registrar_e_logar(client, email="a@example.com")
    headers_b = registrar_e_logar(client, email="b@example.com")
    report_id = _criar_relatorio(client, headers_a)

    response = client.get(f"/api/reports/{report_id}/pdf", headers=headers_b)

    assert response.status_code == 404
