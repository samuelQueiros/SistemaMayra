import pytest

import app.services.storage as storage_module
from tests.helpers import registrar_e_logar


@pytest.fixture(autouse=True)
def usar_storage_temporario(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_module, "_LOCAL_STORAGE_ROOT", tmp_path / "storage_teste")


def _criar_paciente(client, headers):
    return client.post(
        "/api/patients", json={"name": "Paciente Teste", "birth_date": "2020-05-10"}, headers=headers
    ).json()["id"]


def _foto_jpeg_minima() -> bytes:
    # Não precisa ser uma imagem válida de verdade — o serviço só salva os
    # bytes em disco, a validação é só pela extensão do nome do arquivo.
    return b"\xff\xd8\xff\xe0conteudo-de-teste"


def test_upload_lista_e_baixa_foto_do_paciente(client):
    headers = registrar_e_logar(client)
    patient_id = _criar_paciente(client, headers)

    upload = client.post(
        f"/api/patients/{patient_id}/photos",
        headers=headers,
        files={"file": ("foto.jpg", _foto_jpeg_minima(), "image/jpeg")},
    )
    assert upload.status_code == 201
    photo_id = upload.json()["id"]

    listed = client.get(f"/api/patients/{patient_id}/photos", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == photo_id

    downloaded = client.get(f"/api/patients/{patient_id}/photos/{photo_id}/file", headers=headers)
    assert downloaded.status_code == 200
    assert downloaded.content == _foto_jpeg_minima()


def test_exclui_foto_do_paciente(client):
    headers = registrar_e_logar(client)
    patient_id = _criar_paciente(client, headers)
    photo_id = client.post(
        f"/api/patients/{patient_id}/photos",
        headers=headers,
        files={"file": ("foto.png", _foto_jpeg_minima(), "image/png")},
    ).json()["id"]

    response = client.delete(f"/api/patients/{patient_id}/photos/{photo_id}", headers=headers)

    assert response.status_code == 204
    assert client.get(f"/api/patients/{patient_id}/photos", headers=headers).json() == []


def test_formato_de_imagem_nao_suportado_retorna_400(client):
    headers = registrar_e_logar(client)
    patient_id = _criar_paciente(client, headers)

    response = client.post(
        f"/api/patients/{patient_id}/photos",
        headers=headers,
        files={"file": ("documento.pdf", b"nao e uma imagem", "application/pdf")},
    )

    assert response.status_code == 400


def test_outro_psicologo_nao_acessa_fotos_de_paciente_alheio(client):
    headers_a = registrar_e_logar(client, email="a@example.com")
    headers_b = registrar_e_logar(client, email="b@example.com")
    patient_id = _criar_paciente(client, headers_a)
    photo_id = client.post(
        f"/api/patients/{patient_id}/photos",
        headers=headers_a,
        files={"file": ("foto.jpg", _foto_jpeg_minima(), "image/jpeg")},
    ).json()["id"]

    assert client.get(f"/api/patients/{patient_id}/photos", headers=headers_b).status_code == 404
    assert client.get(f"/api/patients/{patient_id}/photos/{photo_id}/file", headers=headers_b).status_code == 404
    assert client.delete(f"/api/patients/{patient_id}/photos/{photo_id}", headers=headers_b).status_code == 404
