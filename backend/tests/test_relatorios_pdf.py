import pytest
from weasyprint import HTML

import app.api.relatorios_pdf as modulo
import app.services.ai.chains as chains
import app.services.storage as storage_module
from app.services.ai.schemas import RelatorioPorPdfs
from tests.helpers import registrar_e_logar
from tests.test_documents_export import HTML_LAUDO


@pytest.fixture(autouse=True)
def usar_storage_temporario(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_module, "_LOCAL_STORAGE_ROOT", tmp_path / "storage_teste")


def _pdf(titulo: str) -> bytes:
    return HTML(string=f"<h1>{titulo}</h1><p>1. A criança se distrai? (x) Sempre ( ) Nunca</p>").write_pdf()


RELATORIO = RelatorioPorPdfs(
    formularios=[{"arquivo": "mae.pdf", "titulo": "Anamnese", "respondente": "Mãe", "data": "01/10/2026"}],
    metodologia="Foram analisados formulários respondidos pela família.",
    areas=[
        {
            "titulo": "Atenção",
            "texto": "Relatos de desatenção frequente.",
            "fontes": ["Anamnese"],
            "grafico": {"titulo": "SNAP", "rotulos": ["Desatenção"], "valores": [7], "maximo": 9, "regua": "itens marcados"},
        }
    ],
    consideracoes_finais="Síntese.",
    sugestoes_intervencao="• Rotina visual",
)


@pytest.fixture
def ia_falsa(monkeypatch):
    chamadas = []

    def fake(**kwargs):
        chamadas.append(kwargs)
        return RELATORIO

    monkeypatch.setattr(modulo, "generate_report_from_form_pdfs", fake)
    return chamadas


def _configurar_ia(client, headers):
    client.put(
        "/api/settings/ai",
        json={"provider": "anthropic", "model": "claude-sonnet-5", "api_key": "chave-de-teste-1234"},
        headers=headers,
    )


def _paciente(client, headers):
    return client.post("/api/patients", json={"name": "Criança Teste", "birth_date": "2018-02-10"}, headers=headers).json()["id"]


def _enviar(client, headers, patient_id, arquivos, observacoes=None):
    dados = {"observacoes": observacoes} if observacoes else None
    return client.post(
        f"/api/patients/{patient_id}/relatorios-pdf",
        headers=headers,
        files=[("arquivos", (nome, conteudo, "application/pdf")) for nome, conteudo in arquivos],
        data=dados,
    )


def test_gera_relatorio_a_partir_dos_pdfs(client, ia_falsa):
    headers = registrar_e_logar(client)
    _configurar_ia(client, headers)
    pid = _paciente(client, headers)

    resposta = _enviar(client, headers, pid, [("mae.pdf", _pdf("Anamnese")), ("escola.pdf", _pdf("Escola"))], "Foco em atenção")

    assert resposta.status_code == 201, resposta.text
    laudo = resposta.json()
    assert laudo["computed_json"]["relatorio"]["areas"][0]["titulo"] == "Atenção"
    assert [a["nome"] for a in laudo["answers_json"]["arquivos"]] == ["mae.pdf", "escola.pdf"]
    chamada = ia_falsa[0]
    assert [p["nome"] for p in chamada["pdfs"]] == ["mae.pdf", "escola.pdf"]
    assert "distrai" in chamada["pdfs"][0]["texto"]
    assert chamada["pdfs"][0]["conteudo"].startswith(b"%PDF")
    assert chamada["observacoes"] == "Foco em atenção"
    assert chamada["patient_name"] == "Criança Teste"

    original = client.get(f"/api/reports/{laudo['id']}/arquivos/1", headers=headers)
    assert original.status_code == 200
    assert original.content.startswith(b"%PDF")
    assert client.get(f"/api/reports/{laudo['id']}/arquivos/2", headers=headers).status_code == 404


def test_um_template_interno_por_psicologa(client, ia_falsa):
    headers = registrar_e_logar(client)
    _configurar_ia(client, headers)
    pid = _paciente(client, headers)
    a = _enviar(client, headers, pid, [("a.pdf", _pdf("A"))]).json()
    b = _enviar(client, headers, pid, [("b.pdf", _pdf("B"))]).json()
    assert a["template_id"] == b["template_id"]
    assert len(client.get(f"/api/patients/{pid}/reports", headers=headers).json()) == 2


def test_limite_de_seis_pdfs(client, ia_falsa):
    headers = registrar_e_logar(client)
    _configurar_ia(client, headers)
    pid = _paciente(client, headers)
    resposta = _enviar(client, headers, pid, [(f"{i}.pdf", _pdf(str(i))) for i in range(7)])
    assert resposta.status_code == 400
    assert "no máximo 6" in resposta.json()["detail"]
    assert ia_falsa == []


def test_rejeita_arquivo_que_nao_e_pdf(client, ia_falsa):
    headers = registrar_e_logar(client)
    _configurar_ia(client, headers)
    pid = _paciente(client, headers)
    resposta = _enviar(client, headers, pid, [("foto.png", b"\x89PNG...")])
    assert resposta.status_code == 400
    assert "não é um PDF" in resposta.json()["detail"]


def test_sem_ia_configurada_da_erro_amigavel(client, monkeypatch):
    monkeypatch.setattr(modulo, "resolve_ai_credentials", lambda _s: (_ for _ in ()).throw(modulo.AIConfigurationError("Configure a IA.")))
    headers = registrar_e_logar(client)
    pid = _paciente(client, headers)
    resposta = _enviar(client, headers, pid, [("a.pdf", _pdf("A"))])
    assert resposta.status_code == 500
    assert resposta.json()["detail"] == "Configure a IA."


def test_falha_do_provedor_vira_502_explicando(client, monkeypatch):
    def quebra(**_):
        raise RuntimeError("modelo não aceita PDF")

    monkeypatch.setattr(modulo, "generate_report_from_form_pdfs", quebra)
    headers = registrar_e_logar(client)
    _configurar_ia(client, headers)
    pid = _paciente(client, headers)
    resposta = _enviar(client, headers, pid, [("a.pdf", _pdf("A"))])
    assert resposta.status_code == 502
    assert "aceitar PDFs" in resposta.json()["detail"]


def test_paciente_de_outra_psicologa_da_404(client, ia_falsa):
    headers_a = registrar_e_logar(client, email="a@example.com")
    headers_b = registrar_e_logar(client, email="b@example.com")
    _configurar_ia(client, headers_a)
    _configurar_ia(client, headers_b)
    pid = _paciente(client, headers_a)
    assert _enviar(client, headers_b, pid, [("a.pdf", _pdf("A"))]).status_code == 404

    laudo = _enviar(client, headers_a, pid, [("a.pdf", _pdf("A"))]).json()
    assert client.get(f"/api/reports/{laudo['id']}/arquivos/0", headers=headers_b).status_code == 404
    edicao = {"relatorio": RELATORIO.model_dump()}
    assert client.put(f"/api/reports/{laudo['id']}/relatorio-ia", json=edicao, headers=headers_b).status_code == 404


def test_salva_edicoes_e_exporta_pdf_e_word_do_historico(client, ia_falsa):
    headers = registrar_e_logar(client)
    _configurar_ia(client, headers)
    pid = _paciente(client, headers)
    laudo_id = _enviar(client, headers, pid, [("a.pdf", _pdf("A"))]).json()["id"]

    editado = RELATORIO.model_dump()
    editado["areas"][0]["texto"] = "Texto revisado pela psicóloga."
    resposta = client.put(
        f"/api/reports/{laudo_id}/relatorio-ia", json={"relatorio": editado, "extras": {"cidade": "Gama"}}, headers=headers
    )
    assert resposta.status_code == 200
    assert resposta.json()["computed_json"]["relatorio"]["areas"][0]["texto"] == "Texto revisado pela psicóloga."
    assert resposta.json()["answers_json"]["extras"] == {"cidade": "Gama"}
    assert resposta.json()["answers_json"]["arquivos"][0]["nome"] == "a.pdf"

    client.put(f"/api/reports/{laudo_id}/text", json={"generated_text": HTML_LAUDO}, headers=headers)
    assert client.get(f"/api/reports/{laudo_id}/pdf", headers=headers).content.startswith(b"%PDF")
    assert client.get(f"/api/reports/{laudo_id}/docx", headers=headers).content.startswith(b"PK")


def test_rota_do_consolidado_antigo_nao_existe_mais(client):
    headers = registrar_e_logar(client)
    pid = _paciente(client, headers)
    assert client.post(f"/api/patients/{pid}/consolidated-pdf", json={"report_ids": []}, headers=headers).status_code in (404, 405)


class ModeloFalso:
    def __init__(self, falhar_com_imagens=False):
        self.chamadas = []
        self.falhar_com_imagens = falhar_com_imagens

    def invoke(self, messages):
        self.chamadas.append(messages)
        if self.falhar_com_imagens and any(b["type"] == "image" for b in messages[1].content):
            raise RuntimeError("this model does not support images")
        return RELATORIO


def _gerar(monkeypatch, provider, modelo):
    monkeypatch.setattr(chains, "get_structured_model", lambda *a: modelo)
    chains.generate_report_from_form_pdfs(
        provider=provider,
        model="m",
        api_key="k",
        patient_name="Criança",
        idade="8 anos e 7 meses",
        pdfs=[{"nome": "mae.pdf", "conteudo": _pdf("Anamnese"), "texto": "Pergunta 1"}],
        observacoes="olhar atenção",
    )
    return [b for b in modelo.chamadas[-1][1].content]


def test_chain_envia_os_pdfs_inteiros_ao_modelo(monkeypatch):
    modelo = ModeloFalso()
    blocos = _gerar(monkeypatch, "anthropic", modelo)
    sistema = modelo.chamadas[0][0]
    assert "opção efetivamente MARCADA" in sistema.content
    arquivo = next(b for b in blocos if b["type"] == "file")
    assert arquivo["mime_type"] == "application/pdf"
    assert arquivo["filename"] == "mae.pdf"
    import base64

    assert base64.b64decode(arquivo["base64"]).startswith(b"%PDF")
    textos = " ".join(b["text"] for b in blocos if b["type"] == "text")
    assert "Criança (8 anos e 7 meses)" in textos
    assert "olhar atenção" in textos
    assert "Pergunta 1" in textos


def test_provedor_que_le_imagem_recebe_as_paginas_como_png(monkeypatch):
    blocos = _gerar(monkeypatch, "xai", ModeloFalso())
    imagens = [b for b in blocos if b["type"] == "image"]
    assert imagens and all(b["mime_type"] == "image/png" for b in imagens)
    assert not any(b["type"] == "file" for b in blocos)
    assert "Página 1:" in " ".join(b["text"] for b in blocos if b["type"] == "text")


def test_modelo_sem_visao_cai_para_so_texto(monkeypatch):
    modelo = ModeloFalso(falhar_com_imagens=True)
    blocos = _gerar(monkeypatch, "groq", modelo)
    assert len(modelo.chamadas) == 2
    assert all(b["type"] == "text" for b in blocos)
    assert "Pergunta 1" in " ".join(b["text"] for b in blocos)


def test_provedor_so_texto_avisa_a_ia_para_nao_supor(monkeypatch):
    blocos = _gerar(monkeypatch, "deepseek", ModeloFalso())
    assert all(b["type"] == "text" for b in blocos)
    assert "em vez de supor" in blocos[0]["text"]
