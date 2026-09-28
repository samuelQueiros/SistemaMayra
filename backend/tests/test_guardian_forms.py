import pytest

import app.services.storage as storage_module
from tests.helpers import registrar_e_logar


@pytest.fixture(autouse=True)
def usar_storage_temporario(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_module, "_LOCAL_STORAGE_ROOT", tmp_path / "storage_teste")


def _criar_paciente(client, headers):
    return client.post(
        "/api/patients", json={"name": "Fictício Teste Da Silva", "birth_date": "2019-03-01"}, headers=headers
    ).json()["id"]


def _dados_submissao(**extra):
    dados = {
        "kind": "SNAP-IV (Pais)",
        "respondent_name": "Responsável Fictício",
        "respondent_relation": "mãe",
        "filled_at": "2026-09-20",
        "notes": "Preenchido em papel na recepção.",
    }
    dados.update(extra)
    return dados


def test_registra_formulario_como_pendente_por_padrao(client):
    headers = registrar_e_logar(client)
    patient_id = _criar_paciente(client, headers)

    response = client.post(
        f"/api/patients/{patient_id}/guardian-forms", headers=headers, json=_dados_submissao()
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pendente"
    assert body["validated_by_id"] is None
    assert body["respondent_name"] == "Responsável Fictício"


def test_lista_formularios_do_paciente(client):
    headers = registrar_e_logar(client)
    patient_id = _criar_paciente(client, headers)
    client.post(f"/api/patients/{patient_id}/guardian-forms", headers=headers, json=_dados_submissao())

    response = client.get(f"/api/patients/{patient_id}/guardian-forms", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_valida_formulario_registra_quem_e_quando(client):
    headers = registrar_e_logar(client)
    patient_id = _criar_paciente(client, headers)
    submission_id = client.post(
        f"/api/patients/{patient_id}/guardian-forms", headers=headers, json=_dados_submissao()
    ).json()["id"]

    response = client.post(
        f"/api/patients/{patient_id}/guardian-forms/{submission_id}/validate", headers=headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "validado"
    assert body["validated_by_id"] is not None
    assert body["validated_at"] is not None


def test_rejeita_formulario(client):
    headers = registrar_e_logar(client)
    patient_id = _criar_paciente(client, headers)
    submission_id = client.post(
        f"/api/patients/{patient_id}/guardian-forms", headers=headers, json=_dados_submissao()
    ).json()["id"]

    response = client.post(
        f"/api/patients/{patient_id}/guardian-forms/{submission_id}/reject", headers=headers
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejeitado"


def test_upload_e_download_do_formulario_original_preserva_o_arquivo(client):
    headers = registrar_e_logar(client)
    patient_id = _criar_paciente(client, headers)
    submission_id = client.post(
        f"/api/patients/{patient_id}/guardian-forms", headers=headers, json=_dados_submissao()
    ).json()["id"]
    conteudo = b"conteudo-fake-do-formulario-escaneado"

    upload = client.post(
        f"/api/patients/{patient_id}/guardian-forms/{submission_id}/file",
        headers=headers,
        files={"file": ("formulario.pdf", conteudo, "application/pdf")},
    )
    assert upload.status_code == 200
    assert upload.json()["file_path"] is not None

    download = client.get(
        f"/api/patients/{patient_id}/guardian-forms/{submission_id}/file", headers=headers
    )
    assert download.status_code == 200
    assert download.content == conteudo


def test_formato_de_arquivo_nao_suportado_retorna_400(client):
    headers = registrar_e_logar(client)
    patient_id = _criar_paciente(client, headers)
    submission_id = client.post(
        f"/api/patients/{patient_id}/guardian-forms", headers=headers, json=_dados_submissao()
    ).json()["id"]

    response = client.post(
        f"/api/patients/{patient_id}/guardian-forms/{submission_id}/file",
        headers=headers,
        files={"file": ("dados.txt", b"texto qualquer", "text/plain")},
    )

    assert response.status_code == 400


def test_exclui_formulario(client):
    headers = registrar_e_logar(client)
    patient_id = _criar_paciente(client, headers)
    submission_id = client.post(
        f"/api/patients/{patient_id}/guardian-forms", headers=headers, json=_dados_submissao()
    ).json()["id"]

    response = client.delete(f"/api/patients/{patient_id}/guardian-forms/{submission_id}", headers=headers)

    assert response.status_code == 204
    assert client.get(f"/api/patients/{patient_id}/guardian-forms", headers=headers).json() == []


def test_outro_psicologo_nao_acessa_formularios_de_paciente_alheio(client):
    headers_a = registrar_e_logar(client, email="a@example.com")
    headers_b = registrar_e_logar(client, email="b@example.com")
    patient_id = _criar_paciente(client, headers_a)
    submission_id = client.post(
        f"/api/patients/{patient_id}/guardian-forms", headers=headers_a, json=_dados_submissao()
    ).json()["id"]

    assert client.get(f"/api/patients/{patient_id}/guardian-forms", headers=headers_b).status_code == 404
    assert (
        client.post(
            f"/api/patients/{patient_id}/guardian-forms/{submission_id}/validate", headers=headers_b
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/api/patients/{patient_id}/guardian-forms/{submission_id}", headers=headers_b
        ).status_code
        == 404
    )
