import json

import pytest
from weasyprint import HTML

import app.api.laudo_ia as modulo
import app.services.storage as storage_module
from app.services.ai.schemas import ProtocoloPorIA
from app.services.ai.agentes import DocumentoExtraido
from app.services.laudo_ia import CatalogoDoProtocolo, ResultadoDaIA, formatar_catalogo, respostas_para_answers
from tests.helpers import registrar_e_logar


@pytest.fixture(autouse=True)
def usar_storage_temporario(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_module, "_LOCAL_STORAGE_ROOT", tmp_path / "storage_teste")


CATALOGO = {
    "campos": [
        {"id": "parto", "secao": "2. Anamnese Inicial", "rotulo": "Parto", "tipo": "opcao",
         "opcoes": [{"valor": "Normal", "rotulo": "Normal"}, {"valor": "Cesáreo", "rotulo": "Cesáreo"}]},
        {"id": "complicacaoParto", "secao": "2. Anamnese Inicial", "rotulo": "Houve Complicação No Parto?", "tipo": "opcao",
         "opcoes": [{"valor": "Sim", "rotulo": "Sim"}, {"valor": "Não", "rotulo": "Não"}]},
        {"id": "cars_0", "secao": "11. Pontuações ATA E CARS", "grupo": "CARS", "rotulo": "Relacionamento", "tipo": "opcao",
         "opcoes": [{"valor": "1", "rotulo": "Normal"}, {"valor": "2", "rotulo": "Leve"}]},
        {"id": "dom_atencao", "secao": "17. Domínios", "rotulo": "Atenção (%)", "tipo": "numero", "min": 0, "max": 100},
        {"id": "hip_tdah", "secao": "9. Hipóteses", "rotulo": "TDAH", "tipo": "marcar"},
        {"id": "queixaFamiliar", "secao": "4. Queixas", "rotulo": "Queixas Familiares", "tipo": "texto"},
    ],
    "contexto": "Habilidades por ano: 2º Ano: Leitura, Escrita",
}

PROTOCOLO = ProtocoloPorIA(
    estudo_de_caso="Criança de 7 anos encaminhada pela escola por desatenção.",
    campos=[
        {"id": "parto", "valor": "Cesáreo"},
        {"id": "complicacaoParto", "valor": "Talvez"},  # fora das opções -> descartado
        {"id": "cars_0", "valor": "Leve"},  # rótulo -> vira o valor "2"
        {"id": "dom_atencao", "valor": "35%"},
        {"id": "hip_tdah", "valor": "sim"},
        {"id": "queixaFamiliar", "valor": "Esquece tarefas."},
        {"id": "campo_inventado", "valor": "x"},  # fora do catálogo -> descartado
    ],
    lacunas=["Sem dados do Portage."],
)


def test_respostas_validadas_contra_o_catalogo():
    answers, descartados = respostas_para_answers(PROTOCOLO, CatalogoDoProtocolo.model_validate(CATALOGO))
    assert answers == {
        "parto": "Cesáreo",
        "cars_0": "2",
        "dom_atencao": "35",
        "hip_tdah": True,
        "queixaFamiliar": "Esquece tarefas.",
        "estudoCaso": "Criança de 7 anos encaminhada pela escola por desatenção.",
    }
    assert set(descartados) == {"complicacaoParto", "campo_inventado"}


def test_catalogo_formatado_para_o_prompt():
    texto = formatar_catalogo(CatalogoDoProtocolo.model_validate(CATALOGO))
    assert "## 2. Anamnese Inicial" in texto
    assert "- [cars_0] Relacionamento · opções: 1=Normal | 2=Leve" in texto
    assert "- [dom_atencao] Atenção (%) · número (0 a 100)" in texto
    assert "Habilidades por ano" in texto


@pytest.fixture
def ia_falsa(monkeypatch):
    chamadas = []

    def fake(**kwargs):
        chamadas.append(kwargs)
        documento = DocumentoExtraido(tipo="formulario", titulo="Anamnese", arquivo="anamnese.pdf", respostas=[])
        return ResultadoDaIA(protocolo=PROTOCOLO, documentos=[documento], tempos={"extracao_s": 1.0, "especialistas_s": 2.0})

    monkeypatch.setattr(modulo, "preencher_protocolo", fake)
    return chamadas


def _pdf(titulo: str) -> bytes:
    return HTML(string=f"<h1>{titulo}</h1><p>Parto: (x) Cesáreo ( ) Normal</p>").write_pdf()


def _preparar(client):
    headers = registrar_e_logar(client)
    client.put(
        "/api/settings/ai",
        json={"provider": "anthropic", "model": "claude-sonnet-5", "api_key": "chave-de-teste-1234"},
        headers=headers,
    )
    pid = client.post("/api/patients", json={"name": "Criança Teste", "birth_date": "2019-02-10", "sex": "Masculino"}, headers=headers).json()["id"]
    return headers, pid


def _enviar(client, headers, pid, catalogo=None, arquivos=None):
    return client.post(
        f"/api/patients/{pid}/laudo-ia",
        headers=headers,
        files=[("arquivos", (n, c, "application/pdf")) for n, c in (arquivos or [("anamnese.pdf", _pdf("Anamnese")), ("cars.pdf", _pdf("CARS"))])],
        data={"catalogo": catalogo if catalogo is not None else json.dumps(CATALOGO), "observacoes": "Foco em atenção"},
    )


def _concluir(client, headers, resposta) -> dict:
    """A geração roda em segundo plano: acompanha o andamento até o fim."""
    import time

    assert resposta.status_code == 202, resposta.text
    job_id = resposta.json()["job_id"]
    for _ in range(500):
        andamento = client.get(f"/api/laudo-ia/jobs/{job_id}", headers=headers).json()
        if andamento["status"] in ("concluido", "erro"):
            return andamento
        time.sleep(0.01)
    raise AssertionError("a geração não terminou")


def test_cota_diaria_retorna_orientacao_e_nao_cria_laudo(client, monkeypatch):
    headers, pid = _preparar(client)

    def falhar(**kwargs):
        raise RuntimeError(
            "429 RESOURCE_EXHAUSTED GenerateRequestsPerDayPerProjectPerModel-FreeTier "
            "quotaValue: 20 retryDelay: 77036s"
        )

    monkeypatch.setattr(modulo, "preencher_protocolo", falhar)
    andamento = _concluir(client, headers, _enviar(client, headers, pid))

    assert andamento["status"] == "erro"
    mensagem = andamento["erro"]
    assert "cota diária" in mensagem
    assert "Verifique a chave" not in mensagem
    assert "RESOURCE_EXHAUSTED" not in mensagem
    assert client.get(f"/api/patients/{pid}/reports", headers=headers).json() == []


def test_cria_laudo_do_protocolo_padrao(client, ia_falsa):
    headers, pid = _preparar(client)
    andamento = _concluir(client, headers, _enviar(client, headers, pid))
    assert andamento["status"] == "concluido", andamento
    laudo = client.get(f"/api/reports/{andamento['report_id']}", headers=headers).json()
    assert laudo["answers_json"]["parto"] == "Cesáreo"
    assert laudo["answers_json"]["estudoCaso"].startswith("Criança de 7 anos")
    assert laudo["computed_json"]["origem"] == "ia_pdf"
    assert laudo["computed_json"]["lacunas"] == ["Sem dados do Portage."]
    assert [a["nome"] for a in laudo["computed_json"]["arquivos"]] == ["anamnese.pdf", "cars.pdf"]

    # Mesmo template do protocolo padrão (fluxo manual).
    template = client.post("/api/templates/custom-form-avaliacao", headers=headers).json()
    assert laudo["template_id"] == template["id"]

    assert laudo["computed_json"]["documentos"][0]["titulo"] == "Anamnese"
    assert laudo["computed_json"]["tempos"] == {"extracao_s": 1.0, "especialistas_s": 2.0}

    chamada = ia_falsa[0]
    assert chamada["paciente"].startswith("Criança Teste (") and chamada["paciente"].endswith("sexo Masculino")
    assert {c.id for c in chamada["catalogo"].campos} >= {"parto", "cars_0"}
    assert len(chamada["pdfs"]) == 2 and chamada["com_estudo_de_caso"] is True


def test_catalogo_invalido(client, ia_falsa):
    headers, pid = _preparar(client)
    resposta = _enviar(client, headers, pid, catalogo="{nao e json")
    assert resposta.status_code == 400
    assert not ia_falsa


def test_rejeita_arquivo_que_nao_e_pdf(client, ia_falsa):
    headers, pid = _preparar(client)
    resposta = _enviar(client, headers, pid, arquivos=[("foto.png", b"\x89PNG")])
    assert resposta.status_code == 400
    assert not ia_falsa


def test_paciente_de_outra_psicologa(client, ia_falsa):
    _, pid = _preparar(client)
    outra = registrar_e_logar(client, email="outra@exemplo.com")
    resposta = _enviar(client, outra, pid)
    assert resposta.status_code == 404


# A leitura dos PDFs e os especialistas têm testes próprios: tests/test_ai_agentes.py.


def test_catalogo_real_do_formulario_e_aceito():
    """Catálogo gerado por catalogoParaIA() no formulário (paciente de 7 anos):
    as opções da CARS trazem a descrição clínica longa de cada grau."""
    from pathlib import Path

    dados = json.loads((Path(__file__).parent / "fixtures_catalogo_protocolo.json").read_text(encoding="utf-8"))
    catalogo = CatalogoDoProtocolo.model_validate(dados)
    ids = {c.id for c in catalogo.campos}
    assert {"parto", "complicacaoParto", "cars_0", "ata_item_0", "snap_0", "hip_tdah", "anoEscolar", "hab_status_0"} <= ids
    assert any(i.startswith("portage_") for i in ids)
    assert "estudoCaso" not in ids and "nomePaciente" not in ids
    texto = formatar_catalogo(catalogo)
    assert "Grau leve de anormalidade" in texto


def test_escalas_de_pdf_devolve_so_as_respostas(client, ia_falsa):
    headers, pid = _preparar(client)
    resposta = client.post(
        f"/api/patients/{pid}/escalas-de-pdf",
        headers=headers,
        files=[("arquivos", ("cars.pdf", _pdf("CARS"), "application/pdf"))],
        data={"catalogo": json.dumps(CATALOGO)},
    )
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["respostas"]["cars_0"] == "2"
    assert "estudoCaso" not in corpo["respostas"]
    assert corpo["lacunas"] == ["Sem dados do Portage."]
    assert ia_falsa[0]["com_estudo_de_caso"] is False
    # Nenhum laudo é criado.
    assert client.get(f"/api/patients/{pid}/reports", headers=headers).json() == []
