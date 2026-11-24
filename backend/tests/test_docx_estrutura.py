"""Estrutura do Word gerado: cabeçalho do paciente e ordem dos elementos do XML.

Retorno da cliente: no Word dela o cabeçalho (foto + identificação) saía com bordas em todas as células e o
texto sem negrito, todo num parágrafo só. A causa era o conversor genérico de tabelas ser usado no lugar do
conversor do cabeçalho; e o XML tinha elementos fora da ordem do schema, que o Word do Windows perdoa mas outros
programas (Word para Mac, Pages, Google Docs) não.
"""

import io
import zipfile

from docx import Document
from docx.oxml.ns import qn
from lxml import etree

from app.services.laudo_documento import _ORDEM_XML, html_para_docx
from tests.test_documents_export import HTML_LAUDO, PNG_1X1

QUADRO = f"""<div class="faixa centro">HIPÓTESE DE TRANSTORNO DO PROCESSAMENTO AUDITIVO CENTRAL – TPAC</div>
<h3 class="area">ÁREA DO DESENVOLVIMENTO: Comunicação</h3>
<table class="tabela simples centro quadro" data-larguras="34,58,40,38" data-fonte="9"><thead><tr><th>Comportamento Observado</th><th>Descrição Detalhada</th><th>Possíveis Características</th><th>Associação aos Critérios</th></tr></thead>
<tr><td><strong>Facilidade em se distrair</strong></td><td>Desvio de atenção</td><td>Pode ocorrer</td><td>Não descrito</td></tr></table>
<div class="grafico"><img src="{PNG_1X1}" data-mm="120"></div>"""

HTML = HTML_LAUDO.replace('<div class="faixa-topico">', QUADRO + '<div class="faixa-topico">', 1)


def _docx(html: str = HTML) -> Document:
    return Document(io.BytesIO(html_para_docx(html)))


def test_cabecalho_do_paciente_usa_o_conversor_proprio():
    tabela = _docx().tables[0]
    colunas = [int(c.get(qn("w:w"))) for c in tabela._tbl.tblGrid.findall(qn("w:gridCol"))]
    # 44 | 10 | 112 mm (e não as 3 colunas iguais do conversor genérico)
    assert colunas[0] < colunas[2] and colunas[1] < colunas[0]

    foto, espaco, caixa = tabela.rows[0].cells
    # só a caixa de identificação tem borda
    assert foto._tc.tcPr.find(qn("w:tcBorders")) is None
    assert espaco._tc.tcPr.find(qn("w:tcBorders")) is None
    assert caixa._tc.tcPr.find(qn("w:tcBorders")) is not None

    # um parágrafo por linha, em negrito e centralizado
    assert [p.text for p in caixa.paragraphs] == ["Paciente: Criança Teste", "D/N: 10 / 02 / 2018"]
    for p in caixa.paragraphs:
        assert p.alignment is not None and p.alignment == 1
        assert all(run.bold for run in p.runs)


def _problemas_de_schema(raiz) -> list[str]:
    problemas = []
    for el in raiz.iter():
        if not isinstance(el.tag, str):
            continue
        pai = etree.QName(el).localname
        if pai not in _ORDEM_XML:
            continue
        ordem = _ORDEM_XML[pai]
        vistos, ultimo = set(), -1
        for filho in el:
            nome = etree.QName(filho).localname
            if nome not in ordem:
                continue
            if nome in vistos:
                problemas.append(f"{pai}: {nome} repetido")
            vistos.add(nome)
            if ordem.index(nome) < ultimo:
                problemas.append(f"{pai}: {nome} fora de ordem")
            ultimo = max(ultimo, ordem.index(nome))
    return problemas


def test_xml_do_word_segue_a_ordem_do_schema():
    with zipfile.ZipFile(io.BytesIO(html_para_docx(HTML))) as z:
        raiz = etree.fromstring(z.read("word/document.xml"))
    assert _problemas_de_schema(raiz) == []


def test_titulo_e_cabecalho_das_colunas_ficam_presos_a_tabela():
    documento = _docx()
    quadro = next(t for t in documento.tables if "ÁREA DO DESENVOLVIMENTO" in t.rows[0].cells[0].text)
    titulo, cabecalho, dados = quadro.rows[0], quadro.rows[1], quadro.rows[2]
    assert titulo.cells[0].paragraphs[0].paragraph_format.keep_with_next is True
    assert all(c.paragraphs[0].paragraph_format.keep_with_next is True for c in cabecalho.cells)
    # a linha de dados não prende a tabela inteira à próxima página
    assert not dados.cells[0].paragraphs[0].paragraph_format.keep_with_next
