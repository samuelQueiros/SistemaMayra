"""Agentes de IA: extração PDF → JSON (um por PDF, com cache), divisão do
catálogo entre especialistas e orquestração em paralelo."""

import base64
import json
import threading
from pathlib import Path

import pytest
from weasyprint import HTML

import app.services.ai.agentes.extracao as extracao
import app.services.ai.chains as chains
import app.services.laudo_ia as laudo_ia
import app.services.storage as storage_module
from app.services.ai.agentes import CamposDoEspecialista, DocumentoExtraido
from app.services.ai.schemas import RelatorioPorPdfs
from app.services.laudo_ia import CAMPOS_DA_PROFISSIONAL, CatalogoDoProtocolo, dividir_catalogo, preencher_protocolo


@pytest.fixture(autouse=True)
def usar_storage_temporario(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_module, "_LOCAL_STORAGE_ROOT", tmp_path / "storage_teste")
    monkeypatch.setattr(chains.time, "sleep", lambda *_: None)


def _pdf(titulo: str) -> bytes:
    return HTML(string=f"<h1>{titulo}</h1><p>1. Distrai-se? (x) Sempre ( ) Nunca</p>").write_pdf()


DOCUMENTO = DocumentoExtraido(
    tipo="formulario",
    titulo="Anamnese",
    respondente="Mãe",
    respostas=[{"pergunta": "Distrai-se?", "resposta": "Sempre"}],
)


class ModeloFalso:
    def __init__(self, resposta=DOCUMENTO, falhar_com_imagens=False):
        self.chamadas = []
        self.resposta = resposta
        self.falhar_com_imagens = falhar_com_imagens

    def invoke(self, messages):
        self.chamadas.append(messages)
        conteudo = messages[1].content
        if self.falhar_com_imagens and isinstance(conteudo, list) and any(b["type"] == "image" for b in conteudo):
            raise RuntimeError("this model does not support images")
        return self.resposta


def _extrair(monkeypatch, provider, modelo, conteudo=None):
    monkeypatch.setattr(extracao, "get_structured_model", lambda *a: modelo)
    pdf = {"nome": "mae.pdf", "conteudo": conteudo or _pdf("Anamnese"), "texto": "Pergunta 1"}
    return extracao.extrair_documento(provider=provider, model="m", api_key="k", pdf=pdf)


# --- extração: como o PDF chega a cada provedor -----------------------------


def test_extracao_envia_o_pdf_inteiro_e_devolve_json(monkeypatch):
    modelo = ModeloFalso()
    documento = _extrair(monkeypatch, "anthropic", modelo)
    assert documento.arquivo == "mae.pdf" and documento.respostas[0].resposta == "Sempre"
    sistema, humano = modelo.chamadas[0]
    assert "TRANSCREVER" in sistema.content and "opção escolhida" in sistema.content
    arquivo = next(b for b in humano.content if b["type"] == "file")
    assert arquivo["filename"] == "mae.pdf" and base64.b64decode(arquivo["base64"]).startswith(b"%PDF")
    assert "Pergunta 1" in " ".join(b["text"] for b in humano.content if b["type"] == "text")


def test_extracao_manda_paginas_como_png_para_quem_le_imagem(monkeypatch):
    modelo = ModeloFalso()
    _extrair(monkeypatch, "xai", modelo)
    blocos = modelo.chamadas[0][1].content
    assert any(b["type"] == "image" and b["mime_type"] == "image/png" for b in blocos)
    assert not any(b["type"] == "file" for b in blocos)


def test_extracao_cai_para_texto_quando_o_modelo_nao_tem_visao(monkeypatch):
    modelo = ModeloFalso(falhar_com_imagens=True)
    _extrair(monkeypatch, "groq", modelo)
    assert len(modelo.chamadas) == 2
    assert all(b["type"] == "text" for b in modelo.chamadas[-1][1].content)


def test_extracao_so_texto_pede_para_nao_supor(monkeypatch):
    modelo = ModeloFalso()
    _extrair(monkeypatch, "deepseek", modelo)
    assert "deixe a resposta vazia" in modelo.chamadas[0][1].content[0]["text"]


def test_mesmo_pdf_usa_o_cache_e_nao_chama_a_ia_de_novo(monkeypatch):
    modelo = ModeloFalso()
    conteudo = _pdf("Anamnese")
    _extrair(monkeypatch, "anthropic", modelo, conteudo)
    segundo = _extrair(monkeypatch, "anthropic", modelo, conteudo)
    assert len(modelo.chamadas) == 1
    assert segundo.titulo == "Anamnese"
    _extrair(monkeypatch, "anthropic", modelo, _pdf("Outro"))  # outro conteúdo: chama de novo
    assert len(modelo.chamadas) == 2


def test_extracao_roda_um_agente_por_pdf_em_paralelo(monkeypatch):
    # As 3 extrações só passam da barreira se estiverem rodando ao mesmo tempo.
    barreira = threading.Barrier(3, timeout=5)

    class Simultaneo(ModeloFalso):
        def invoke(self, messages):
            barreira.wait()
            return DOCUMENTO

    monkeypatch.setattr(extracao, "get_structured_model", lambda *a: Simultaneo())
    pdfs = [{"nome": f"f{i}.pdf", "conteudo": _pdf(f"F{i}"), "texto": ""} for i in range(3)]
    documentos = extracao.extrair_documentos(provider="anthropic", model="m", api_key="k", pdfs=pdfs)
    assert [d.arquivo for d in documentos] == ["f0.pdf", "f1.pdf", "f2.pdf"]


# --- Relatório Por IA (fluxo antigo) agora lê o JSON ------------------------


def test_relatorio_por_ia_escreve_a_partir_do_json_sem_reenviar_pdfs(monkeypatch):
    relatorio = RelatorioPorPdfs(
        formularios=[], metodologia="m", areas=[], consideracoes_finais="c", sugestoes_intervencao="s"
    )
    modelo_relatorio = ModeloFalso(resposta=relatorio)
    monkeypatch.setattr(extracao, "get_structured_model", lambda *a: ModeloFalso())
    monkeypatch.setattr(chains, "get_structured_model", lambda *a: modelo_relatorio)
    chains.generate_report_from_form_pdfs(
        provider="anthropic",
        model="m",
        api_key="k",
        patient_name="Criança",
        idade="8 anos e 7 meses",
        pdfs=[{"nome": "mae.pdf", "conteudo": _pdf("Anamnese"), "texto": ""}],
        observacoes="olhar atenção",
    )
    sistema, humano = modelo_relatorio.chamadas[0]
    assert "transcritas em JSON" in sistema.content
    assert isinstance(humano.content, str)  # só texto: nenhum PDF reenviado
    assert "Criança (8 anos e 7 meses)" in humano.content and "olhar atenção" in humano.content
    assert '"resposta":"Sempre"' in humano.content


# --- especialistas -------------------------------------------------------------


def _catalogo_real() -> CatalogoDoProtocolo:
    dados = json.loads((Path(__file__).parent / "fixtures_catalogo_protocolo.json").read_text(encoding="utf-8"))
    return CatalogoDoProtocolo.model_validate(dados)


def test_catalogo_dividido_entre_os_especialistas():
    partes = dividir_catalogo(_catalogo_real())
    ids = {nome: {c.id for c in parte.campos} for nome, parte in partes.items()}
    assert {"parto", "complicacaoParto", "queixaFamiliar", "andouAno", "falouMes"} <= ids["anamnese"]
    assert {"cars_0", "ata_item_0", "snap_0"} <= ids["escalas"]
    assert any(i.startswith("portage_") for i in ids["desenvolvimento"])
    assert any(i.startswith("dom_") for i in ids["desenvolvimento"])
    # A IA escreve a observação de cada habilidade e estima as funções executivas.
    assert {"hab_obs_0", "fe_perc_0", "fe_manif_0"} <= ids["desenvolvimento"]
    # Hipóteses, encaminhamentos, desfralde, ano escolar e desempenho nas
    # habilidades ficam com a profissional.
    da_profissional = {c.id for c in _catalogo_real().campos if CAMPOS_DA_PROFISSIONAL.match(c.id)}
    assert {
        "hip_tdah",
        "enc_fonoaudiologia",
        "anoEscolar",
        "desfralde",
        "desfraldeAno",
        "desfraldeMes",
        "hab_status_0",
    } <= da_profissional
    assert "hab_obs_0" not in da_profissional
    # Cada campo com um único dono.
    todos = [i for parte in ids.values() for i in parte]
    assert not da_profissional & set(todos)
    assert len(todos) == len(set(todos)) == len(_catalogo_real().campos) - len(da_profissional)


def test_orquestracao_extrai_e_roda_especialistas_e_redator_em_paralelo(monkeypatch):
    chamadas = []
    monkeypatch.setattr(laudo_ia, "extrair_documentos", lambda **kw: [DOCUMENTO])

    def especialista(**kw):
        chamadas.append(("especialista", kw["especialista"].nome, kw["catalogo_texto"], kw["documentos_texto"]))
        primeiro_id = kw["catalogo_texto"].split("[", 1)[1].split("]", 1)[0]
        return CamposDoEspecialista(
            campos=[{"id": primeiro_id, "valor": "x"}], lacunas=[f"lacuna {kw['especialista'].nome}"]
        )

    def redator(**kw):
        chamadas.append(("redator", kw["paciente"]))
        return "Estudo de caso."

    monkeypatch.setattr(laudo_ia, "preencher_campos", especialista)
    monkeypatch.setattr(laudo_ia, "redigir_estudo_de_caso", redator)

    resultado = preencher_protocolo(
        provider="anthropic", model="m", api_key="k", paciente="Criança (7 anos)", pdfs=[], catalogo=_catalogo_real()
    )
    nomes = sorted(c[1] for c in chamadas if c[0] == "especialista")
    assert nomes == ["anamnese", "desenvolvimento", "escalas"]
    escalas = next(c for c in chamadas if c[1] == "escalas")
    assert "[cars_0]" in escalas[2] and "[parto]" not in escalas[2]
    assert '"titulo":"Anamnese"' in escalas[3]
    assert resultado.protocolo.estudo_de_caso == "Estudo de caso."
    assert len(resultado.protocolo.campos) == 3
    assert sorted(resultado.protocolo.lacunas) == ["lacuna anamnese", "lacuna desenvolvimento", "lacuna escalas"]
    assert set(resultado.tempos) == {"extracao_s", "especialistas_s"}

    chamadas.clear()
    preencher_protocolo(
        provider="anthropic",
        model="m",
        api_key="k",
        paciente="Criança",
        pdfs=[],
        catalogo=_catalogo_real(),
        com_estudo_de_caso=False,
    )
    assert not any(c[0] == "redator" for c in chamadas)


# --- extração resiliente ---------------------------------------------------------


def test_extracao_le_no_maximo_3_pdfs_ao_mesmo_tempo(monkeypatch):
    simultaneos, maximo = [0], [0]
    trava = threading.Lock()

    class Contador(ModeloFalso):
        def invoke(self, messages):
            with trava:
                simultaneos[0] += 1
                maximo[0] = max(maximo[0], simultaneos[0])
            threading.Event().wait(0.05)  # time.sleep está desligado neste arquivo
            with trava:
                simultaneos[0] -= 1
            return DOCUMENTO

    monkeypatch.setattr(extracao, "get_structured_model", lambda *a: Contador())
    pdfs = [{"nome": f"f{i}.pdf", "conteudo": _pdf(f"F{i}"), "texto": ""} for i in range(6)]
    assert len(extracao.extrair_documentos(provider="anthropic", model="m", api_key="k", pdfs=pdfs)) == 6
    assert maximo[0] == extracao.MAXIMO_DE_LEITURAS_SIMULTANEAS == 3


def test_pdf_com_erro_e_nomeado_e_os_lidos_ficam_guardados(monkeypatch):
    class Timeout(Exception):
        pass

    falhar = {"ligado": True}

    class FalhaNaEscola(ModeloFalso):
        def invoke(self, messages):
            self.chamadas.append(messages)
            arquivo = messages[1].content[0]["text"]
            if falhar["ligado"] and "escola.pdf" in arquivo:
                raise Timeout("Request timed out.")
            return DOCUMENTO

    modelo = FalhaNaEscola()
    monkeypatch.setattr(extracao, "get_structured_model", lambda *a: modelo)
    pdfs = [{"nome": n, "conteudo": _pdf(n), "texto": ""} for n in ("mae.pdf", "escola.pdf", "cars.pdf")]
    avisos = []

    with pytest.raises(extracao.ErroNaLeituraDosDocumentos) as erro:
        extracao.extrair_documentos(
            provider="anthropic",
            model="m",
            api_key="k",
            pdfs=pdfs,
            ao_progredir=lambda evento, **d: avisos.append((evento, d.get("nome"))),
        )
    mensagem = str(erro.value)
    assert "'escola.pdf' (o provedor de IA demorou demais para responder)" in mensagem
    assert "Os outros 2 documentos já foram lidos" in mensagem
    assert ("documento_com_erro", "escola.pdf") in avisos and ("documento_lido", "mae.pdf") in avisos

    # Tentar de novo: só o que falhou volta à IA.
    falhar["ligado"] = False
    modelo.chamadas.clear()
    documentos = extracao.extrair_documentos(provider="anthropic", model="m", api_key="k", pdfs=pdfs)
    assert [d.arquivo for d in documentos] == ["mae.pdf", "escola.pdf", "cars.pdf"]
    assert len(modelo.chamadas) == 1


def test_falha_de_um_especialista_diz_qual_parte(monkeypatch):
    from app.services.ai.agentes.extracao import ErroNaEtapaDaIA

    monkeypatch.setattr(laudo_ia, "extrair_documentos", lambda **kw: [DOCUMENTO])

    def especialista(**kw):
        if kw["especialista"].nome == "escalas":
            raise RuntimeError("Error code: 503 - overloaded")
        return CamposDoEspecialista(campos=[])

    monkeypatch.setattr(laudo_ia, "preencher_campos", especialista)
    monkeypatch.setattr(laudo_ia, "redigir_estudo_de_caso", lambda **kw: "Estudo.")
    with pytest.raises(ErroNaEtapaDaIA, match='parte "escalas" \\(o provedor de IA está instável no momento\\)'):
        preencher_protocolo(
            provider="anthropic", model="m", api_key="k", paciente="C", pdfs=[], catalogo=_catalogo_real()
        )


def test_motivo_do_erro_de_conexao():
    class APIConnectionError(Exception):
        pass

    assert (
        extracao.motivo_do_erro(APIConnectionError("Connection error."))
        == "não foi possível conectar ao provedor de IA"
    )
