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


def test_exclusao_confirmada_remove_historico_fotos_e_dependentes(client, tmp_path, monkeypatch):
    from uuid import UUID
    from datetime import date
    from app.models.patient import Patient
    from app.models.report import Report
    from app.models.patient_photo import PatientPhoto
    from app.models.report_change_log import ReportChangeLog
    from app.models.patient_attachment import PatientAttachment
    from app.models.guardian_form_submission import GuardianFormSubmission
    from app.models.consolidated_report import ConsolidatedReport
    import app.services.storage as storage

    monkeypatch.setattr(storage, "_LOCAL_STORAGE_ROOT", tmp_path / "arquivos")
    headers = registrar_e_logar(client)
    pid = client.post("/api/patients", json={"name": "Paciente", "birth_date": "2020-01-01"}, headers=headers).json()[
        "id"
    ]
    tid = client.post("/api/templates", json=TEMPLATE_VALIDO, headers=headers).json()["id"]
    rid = client.post(
        f"/api/patients/{pid}/reports",
        json={"template_id": tid, "answers": {"comunicacao": {"iniciativa_social": 2}}},
        headers=headers,
    ).json()["id"]
    with client.db_session_factory() as db:
        p = db.get(Patient, UUID(pid))
        r = db.get(Report, UUID(rid))
        r.computed_json = {"arquivos": [{"chave": f"{pid}/origem.pdf"}]}
        r.pdf_path = f"{pid}/relatorio.pdf"
        db.add(
            ReportChangeLog(
                report_id=r.id,
                psychologist_id=p.owner_id,
                field="generated_text",
                old_value="Antes",
                new_value="Depois",
            )
        )
        db.add(PatientPhoto(patient_id=p.id, file_path=f"{pid}/foto.png"))
        db.add(
            PatientAttachment(
                patient_id=p.id,
                report_id=r.id,
                created_by_id=p.owner_id,
                nome="Anexo",
                mime="image/png",
                file_path=f"{pid}/anexo.png",
            )
        )
        db.add(
            GuardianFormSubmission(
                patient_id=p.id,
                kind="Anamnese",
                respondent_name="Mãe",
                filled_at=date(2026, 10, 15),
                created_by_id=p.owner_id,
                file_path=f"{pid}/familia.pdf",
            )
        )
        db.add(
            ConsolidatedReport(
                patient_id=p.id,
                owner_id=p.owner_id,
                report_ids=[rid],
                generated_text="Texto",
                pdf_path=f"{pid}/consolidado.pdf",
            )
        )
        db.commit()
    arquivos = [
        (storage.get_photos_storage(), "foto.png"),
        (storage.get_attachments_storage(), "anexo.png"),
        (storage.get_guardian_forms_storage(), "familia.pdf"),
        (storage.get_form_pdfs_storage(), "origem.pdf"),
        (storage.get_reports_storage(), "relatorio.pdf"),
        (storage.get_reports_storage(), "consolidado.pdf"),
    ]
    for store, nome in arquivos:
        store.save(f"{pid}/{nome}", b"teste")
    outra = registrar_e_logar(client, email="outra@example.com")
    assert client.delete(f"/api/patients/{pid}?confirmar_historico=true", headers=outra).status_code == 404
    resposta = client.delete(f"/api/patients/{pid}?confirmar_historico=true", headers=headers)
    assert resposta.status_code == 204, resposta.text
    assert client.get(f"/api/patients/{pid}", headers=headers).status_code == 404
    assert client.get(f"/api/reports/{rid}", headers=headers).status_code == 404
    for store, nome in arquivos:
        assert not store.exists(f"{pid}/{nome}")
    with client.db_session_factory() as db:
        for model in (
            Patient,
            Report,
            PatientPhoto,
            PatientAttachment,
            GuardianFormSubmission,
            ConsolidatedReport,
            ReportChangeLog,
        ):
            assert db.query(model).count() == 0
