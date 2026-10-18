import base64
import io

import pytest
from docx import Document
from docx.oxml.ns import qn

import app.services.storage as storage_module
from app.services.laudo_documento import _buscador_somente_data_uri, html_para_docx
from tests.helpers import registrar_e_logar

# PNG 1x1 transparente — suficiente para testar imagens embutidas.
PNG_1X1 = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)

HTML_LAUDO = f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<style>@page{{size:A4;margin:30mm 20mm 27mm 20mm}}</style></head><body>
<div class="moldura"></div>
<div class="cabecalho-pagina"><img src="{PNG_1X1}" data-mm="19"></div>
<div class="rodape-pagina"><img src="{PNG_1X1}" data-mm="78"></div>
<main class="documento">
<table class="cab-paciente"><tr><td class="cab-foto"><img src="{PNG_1X1}" data-mm="42"></td><td class="cab-espaco"></td>
<td class="cab-info"><div class="cab-box"><p>Paciente: Criança Teste</p><p>D/N: 10 / 02 / 2018</p></div></td></tr></table>
<div class="faixa centro">PARECER NEUROPSICOPEDAGÓGICO<br>ANÁLISE COMPORTAMENTAL</div>
<p><strong>METODOLOGIA</strong>: Realizada análise dos comportamentos.</p>
<p class="recuo">Resultado de <mark class="cinza"><strong>Avaliação Neuropsicopedagógica</strong></mark> e texto.</p>
<ul class="checks"><li>Anamnese;</li><li>Provas projetivas;</li></ul>
<h3><mark class="cinza">ANAMNESE INICIAL</mark></h3>
<ul class="bullets"><li><strong>Parto:</strong> Normal</li></ul>
<div class="quebra"></div>
<h2>Quadro Comparativo – Análise dos Comportamentos</h2>
<table class="tabela dupla centro" data-larguras="38,46,43,43"><tr><th>A</th><th>B</th><th>C</th><th>D</th></tr>
<tr><td>1</td><td>2</td><td>3</td><td>4</td></tr></table>
<div class="grafico"><img src="{PNG_1X1}" data-mm="170"></div>
<div class="faixa-topico">Hiperatividade</div>
<div class="caixa-cinza clara"><p class="recuo">Encaminhei também o paciente.</p></div>
<p class="centro"><mark class="amarelo"><strong>destaque amarelo</strong></mark></p>
<div class="linha-assinatura"></div>
<p class="centro compacto assinatura-nome">Mayra Vanessa Andrade da Cunha</p>
</main></body></html>"""


@pytest.fixture(autouse=True)
def usar_storage_temporario(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_module, "_LOCAL_STORAGE_ROOT", tmp_path / "storage_teste")


def test_exportar_exige_autenticacao(client):
    assert client.post("/api/documents/pdf", json={"html": HTML_LAUDO}).status_code == 401
    assert client.post("/api/documents/docx", json={"html": HTML_LAUDO}).status_code == 401


def test_exporta_pdf_do_laudo(client):
    headers = registrar_e_logar(client)
    resposta = client.post(
        "/api/documents/pdf", json={"html": HTML_LAUDO, "file_name": "Relatório Criança"}, headers=headers
    )
    assert resposta.status_code == 200
    assert resposta.headers["content-type"] == "application/pdf"
    assert 'filename="Relatorio_Crianca.pdf"' in resposta.headers["content-disposition"]
    assert resposta.content.startswith(b"%PDF")


def test_exporta_docx_com_estrutura_do_modelo(client):
    headers = registrar_e_logar(client)
    resposta = client.post("/api/documents/docx", json={"html": HTML_LAUDO, "file_name": "laudo"}, headers=headers)
    assert resposta.status_code == 200
    assert resposta.content.startswith(b"PK")  # .docx é um zip

    doc = Document(io.BytesIO(resposta.content))
    texto = "\n".join(p.text for p in doc.paragraphs)
    assert "PARECER NEUROPSICOPEDAGÓGICO" in texto
    assert "✔\tAnamnese;" in texto
    assert "Hiperatividade" in texto
    # Cabeçalho da identificação, quadro comparativo e caixa cinza viram tabelas.
    assert len(doc.tables) >= 3
    identificacao = doc.tables[0].cell(0, 2).text
    assert "Paciente: Criança Teste" in identificacao

    secao = doc.sections[0]
    # Moldura da página e logo/rodapé repetidos em todas as páginas.
    assert secao._sectPr.find(qn("w:pgBorders")) is not None
    assert secao.header._element.xpath(".//pic:pic")
    assert secao.footer._element.xpath(".//pic:pic")
    # Quebra de página antes do quadro comparativo, como no modelo.
    titulo = next(p for p in doc.paragraphs if p.text.startswith("Quadro Comparativo"))
    assert titulo.paragraph_format.page_break_before


HTML_COM_CAPA = HTML_LAUDO.replace(
    "@page{{size:A4;margin:30mm 20mm 27mm 20mm}}".replace("{{", "{").replace("}}", "}"),
    "@page{size:A4;margin:30mm 20mm 27mm 20mm;@top-center{content:'CABECALHO'}}"
    "@page capa{margin:0;@top-center{content:none}}"
    ".moldura{position:fixed}.capa{page:capa;width:210mm;height:297mm;break-after:page}"
    ".capa img{width:210mm;height:297mm}",
).replace(
    '<div class="moldura"></div>',
    f'<div class="moldura"></div><div class="capa"><img src="{PNG_1X1}" data-mm="210"></div>',
)


def test_pdf_comeca_pela_capa_sem_cabecalho():
    from pypdf import PdfReader

    from app.services.laudo_documento import html_para_pdf

    leitor = PdfReader(io.BytesIO(html_para_pdf(HTML_COM_CAPA)))
    assert len(leitor.pages) == 2
    capa, segunda = leitor.pages[0].extract_text(), leitor.pages[1].extract_text()
    assert "CABECALHO" not in capa and "PARECER" not in capa
    assert "CABECALHO" in segunda and "PARECER NEUROPSICOPEDAG" in segunda


def test_docx_tem_capa_em_secao_propria():
    doc = Document(io.BytesIO(html_para_docx(HTML_COM_CAPA)))
    assert len(doc.sections) == 2
    capa, laudo = doc.sections
    # Capa: página inteira, sem margens, moldura, cabeçalho ou rodapé.
    assert capa.top_margin == 0 and capa.left_margin == 0
    assert capa._sectPr.find(qn("w:pgBorders")) is None
    assert not capa.header._element.xpath(".//pic:pic")
    primeiro = doc.paragraphs[0]
    assert primeiro._p.xpath(".//pic:pic") and not primeiro.text.strip()
    # A quebra de seção fica no próprio parágrafo da imagem (sem parágrafo
    # vazio extra que empurraria uma página em branco).
    assert primeiro._p.pPr.find(qn("w:sectPr")) is not None
    # Laudo: configuração de sempre a partir da 2ª página.
    assert laudo._sectPr.find(qn("w:pgBorders")) is not None
    assert not laudo.header.is_linked_to_previous
    assert laudo.header._element.xpath(".//pic:pic")
    assert laudo.footer._element.xpath(".//pic:pic")
    assert any("PARECER NEUROPSICOPEDAGÓGICO" in p.text for p in doc.paragraphs[1:])


def test_docx_preserva_destaques():
    doc = Document(io.BytesIO(html_para_docx(HTML_LAUDO)))
    runs = [r for p in doc.paragraphs for r in p.runs]
    # Os antigos destaques cinza viraram sombreamento azul-claro (modelo do relatório).
    destaque = next(r for r in runs if r.text == "Avaliação Neuropsicopedagógica")
    sombreamento = destaque._r.rPr.find(qn("w:shd"))
    assert destaque.bold and sombreamento is not None and sombreamento.get(qn("w:fill")) == "DBE5F1"
    amarelo = next(r for r in runs if r.text == "destaque amarelo")
    assert amarelo.font.highlight_color is not None
    assinatura = next(r for r in runs if r.text == "Mayra Vanessa Andrade da Cunha")
    assert assinatura.italic


def test_docx_rejeita_html_sem_documento(client):
    headers = registrar_e_logar(client)
    resposta = client.post("/api/documents/docx", json={"html": "<p>solto</p>"}, headers=headers)
    assert resposta.status_code == 400


def test_pdf_nao_busca_urls_externas():
    buscador = _buscador_somente_data_uri()
    with pytest.raises(ValueError):
        buscador.fetch("http://169.254.169.254/latest/meta-data")
    with pytest.raises(ValueError):
        buscador.fetch("file:///etc/passwd")
    assert buscador.fetch(PNG_1X1)  # data: URI continua funcionando


def _criar_laudo_do_formulario(client, headers, generated_text=None):
    patient = client.post(
        "/api/patients", json={"name": "Criança Teste", "birth_date": "2018-02-10"}, headers=headers
    ).json()
    template = client.post("/api/templates/custom-form-avaliacao", headers=headers).json()
    report = client.post(
        f"/api/patients/{patient['id']}/reports",
        json={"template_id": template["id"], "answers": {"nomePaciente": "Criança Teste"}},
        headers=headers,
    ).json()
    if generated_text is not None:
        client.put(f"/api/reports/{report['id']}/text", json={"generated_text": generated_text}, headers=headers)
    return report["id"]


def test_historico_baixa_word_e_pdf_do_laudo_do_formulario(client):
    headers = registrar_e_logar(client)
    report_id = _criar_laudo_do_formulario(client, headers, HTML_LAUDO)

    docx = client.get(f"/api/reports/{report_id}/docx", headers=headers)
    assert docx.status_code == 200
    assert docx.content.startswith(b"PK")
    assert 'filename="laudo_Crianca_Teste.docx"' in docx.headers["content-disposition"]

    pdf = client.get(f"/api/reports/{report_id}/pdf", headers=headers)
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")


def test_historico_word_sem_documento_gerado_da_400(client):
    headers = registrar_e_logar(client)
    report_id = _criar_laudo_do_formulario(client, headers)
    resposta = client.get(f"/api/reports/{report_id}/docx", headers=headers)
    assert resposta.status_code == 400


def test_word_de_laudo_de_outra_psicologa_da_404(client):
    headers = registrar_e_logar(client)
    report_id = _criar_laudo_do_formulario(client, headers, HTML_LAUDO)
    outra = registrar_e_logar(client, email="outra@example.com")
    assert client.get(f"/api/reports/{report_id}/docx", headers=outra).status_code == 404


def test_imagem_invalida_e_ignorada_sem_quebrar():
    html = HTML_LAUDO.replace(PNG_1X1, "data:image/png;base64," + base64.b64encode(b"nao e imagem").decode(), 1)
    # O logo inválido não deve impedir a geração do restante do documento.
    try:
        html_para_docx(html)
    except Exception as exc:  # pragma: no cover - diagnóstico
        pytest.fail(f"imagem inválida quebrou a conversão: {exc}")
