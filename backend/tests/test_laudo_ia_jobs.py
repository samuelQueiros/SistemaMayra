"""Laudo Por IA em segundo plano: andamento, isolamento e geração parada."""

import json
from datetime import datetime, timedelta, timezone

import pytest

import app.api.laudo_ia as modulo
import app.services.laudo_ia_jobs as jobs
import app.services.storage as storage_module
from app.services.ai.agentes.extracao import ErroNaLeituraDosDocumentos
from tests.helpers import registrar_e_logar
from tests.test_laudo_ia import CATALOGO, _concluir, _enviar, _preparar


@pytest.fixture(autouse=True)
def usar_storage_temporario(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_module, "_LOCAL_STORAGE_ROOT", tmp_path / "storage_teste")


def test_rota_responde_na_hora_e_o_andamento_mostra_o_erro_do_documento(client, monkeypatch):
    headers, pid = _preparar(client)

    def falhar(**kwargs):
        kwargs["ao_progredir"]("lendo_documento", indice=1, total=2, nome="anamnese.pdf")
        raise ErroNaLeituraDosDocumentos([("cars.pdf", TimeoutError("Request timed out."))], lidos=1)

    monkeypatch.setattr(modulo, "preencher_protocolo", falhar)
    andamento = _concluir(client, headers, _enviar(client, headers, pid))

    assert andamento["status"] == "erro"
    assert "'cars.pdf' (o provedor de IA demorou demais para responder)" in andamento["erro"]
    assert "O outro documento já foi lido" in andamento["erro"]
    assert [d["nome"] for d in andamento["documentos"]] == ["anamnese.pdf", "cars.pdf"]
    assert "owner_id" not in andamento
    assert client.get(f"/api/patients/{pid}/reports", headers=headers).json() == []


def test_andamento_de_outra_psicologa_da_404(client, monkeypatch):
    headers, pid = _preparar(client)
    monkeypatch.setattr(modulo, "preencher_protocolo", lambda **kw: (_ for _ in ()).throw(RuntimeError("x")))
    job_id = _enviar(client, headers, pid).json()["job_id"]
    outra = registrar_e_logar(client, email="outra@exemplo.com")
    assert client.get(f"/api/laudo-ia/jobs/{job_id}", headers=outra).status_code == 404
    assert client.get("/api/laudo-ia/jobs/nao-e-uuid", headers=headers).status_code == 404


def test_geracao_sem_noticias_vira_interrompida():
    job = jobs.criar(owner_id="o", patient_id="p", nomes_dos_arquivos=["a.pdf"])
    chave = f"laudo_ia_jobs/{job['id']}.json"
    storage = storage_module.get_form_pdfs_storage()
    dados = json.loads(storage.read(chave))
    dados.update(status="processando", atualizado_em=(datetime.now(timezone.utc) - timedelta(minutes=6)).isoformat())
    storage.save(chave, json.dumps(dados).encode())

    lido = jobs.ler(job["id"])
    assert lido["status"] == "erro" and "interrompida" in lido["erro"]


def test_mensagens_de_andamento_por_etapa():
    job = jobs.criar(owner_id="o", patient_id="p", nomes_dos_arquivos=["a.pdf", "b.pdf", "c.pdf", "d.pdf"])
    andamento = jobs.Andamento(job)
    andamento("lendo_documento", indice=1, total=4, nome="a.pdf")
    andamento("documento_lido", indice=1, total=4, nome="a.pdf")
    assert jobs.ler(job["id"])["mensagem"] == "Lendo documento 2 de 4…"
    andamento("preenchendo", etapas=["anamnese", "escalas", "estudo_de_caso"])
    assert jobs.ler(job["id"])["mensagem"] == "Preenchendo o protocolo (anamnese e histórico, escalas) e redigindo o estudo de caso…"
    andamento("etapa_concluida", etapa="anamnese")
    andamento("etapa_concluida", etapa="escalas")
    assert jobs.ler(job["id"])["mensagem"] == "Redigindo o estudo de caso…"
    andamento.concluir("r1")
    final = jobs.ler(job["id"])
    assert final["status"] == "concluido" and final["report_id"] == "r1"


