"""Gráficos do relatório no Word e no PDF.

O HTML abaixo repete os blocos que o formulário (protocolo padrão e relatório
por IA) gera com gráfico — título → tabela → gráfico, texto → gráfico,
gráfico → tabela (ATA) e os dois do SNAP-IV lado a lado — com imagens de
verdade. Se a conversão perder, mover ou esvaziar um gráfico, o teste falha.
"""

import base64
import io
import shutil
import subprocess
import zipfile

import pytest
from docx import Document
from docx.oxml.ns import qn
from PIL import Image, ImageDraw
from pypdf import PdfReader

from app.services.laudo_documento import html_para_docx, html_para_pdf

CORES = ["#4472c4", "#ed7d31", "#a5a5a5", "#ffc000", "#5b9bd5", "#c00000", "#70ad47", "#7030a0"]


def _grafico_png(indice: int, largura: int = 1000, altura: int = 480) -> str:
    """Gráfico de barras simples (fundo branco, barras coloridas), como os do Chart.js."""
    img = Image.new("RGB", (largura, altura), "white")
    desenho = ImageDraw.Draw(img)
    for barra in range(5):
        x = 80 + barra * 170
        desenho.rectangle([x, altura - 60 - (barra + 1) * 60, x + 110, altura - 60], fill=CORES[(indice + barra) % len(CORES)])
    saida = io.BytesIO()
    img.save(saida, format="PNG")
    return "data:image/png;base64," + base64.b64encode(saida.getvalue()).decode()


GRAFICOS = {nome: _grafico_png(i) for i, nome in enumerate(
    ["dominios", "habilidades", "funcoes", "portage", "cars", "ata", "snap_pontos", "snap_perc"]
)}


def _tabela(titulo: str) -> str:
    return (
        '<table class="tabela dupla compacta" data-larguras="85,85"><thead><tr><th>Item</th><th>Resultado</th></tr></thead>'
        f"<tr><td>{titulo} 1</td><td>Sim</td></tr><tr><td>{titulo} 2</td><td>Não</td></tr></table>"
    )


def _grafico(nome: str, mm: int = 160) -> str:
    return f'<div class="grafico"><img src="{GRAFICOS[nome]}" data-mm="{mm}" style="width:{mm}mm"></div>'


HTML_COM_GRAFICOS = f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<style>@page{{size:A4;margin:30mm 20mm 27mm 20mm}}.grafico{{text-align:center;break-inside:avoid}}</style></head><body>
<main class="documento">
<p>Texto inicial do relatório.</p>
{_grafico("dominios", 118)}
<h2 class="marcado"><mark class="cinza">HABILIDADES ACADÊMICAS – 1º ANO</mark></h2>
{_tabela("Habilidade")}
{_grafico("habilidades", 150)}
<p class="recuo">Interpretação das habilidades.</p>
<h3 class="area">Quadro – Aplicação das Funções Executivas do paciente</h3>
{_tabela("Função")}
{_grafico("funcoes")}
<p class="compacto">Legenda:</p>
<p class="recuo">Com base no resultado do protocolo <strong>PORTAGE</strong>.</p>
{_grafico("portage", 165)}
<p class="recuo">Escala CARS com resultado de 32 pontos.</p>
{_grafico("cars", 170)}
<p class="centro">Classificação.</p>
<p class="recuo">23 pontos na análise da escala ATA.</p>
{_grafico("ata", 165)}
{_tabela("ATA")}
<p class="recuo">Análise do SNAP-IV.</p>
<div class="graficos-lado"><img src="{GRAFICOS["snap_pontos"]}" data-mm="80"><img src="{GRAFICOS["snap_perc"]}" data-mm="80"></div>
<p class="recuo">Conclusão.</p>
</main></body></html>"""

TOTAL = len(GRAFICOS)


def _pixels_coloridos(img: Image.Image) -> int:
    img = img.convert("RGB")
    img.thumbnail((300, 300))
    return sum(1 for p in img.getdata() if min(p) < 235)


def _tem_conteudo(el) -> bool:
    return bool(el.findall(".//" + qn("w:drawing"))) or any((t.text or "").strip() for t in el.iter(qn("w:t")))


def test_word_tem_todos_os_graficos_com_conteudo():
    docx = html_para_docx(HTML_COM_GRAFICOS)
    with zipfile.ZipFile(io.BytesIO(docx)) as z:
        midias = [n for n in z.namelist() if n.startswith("word/media/")]
        assert len(midias) == TOTAL
        for nome in midias:
            assert _pixels_coloridos(Image.open(io.BytesIO(z.read(nome)))) > 500, nome
    corpo = Document(io.BytesIO(docx)).element.body
    assert len(corpo.findall(".//" + qn("w:drawing"))) == TOTAL


def test_word_grafico_vem_logo_depois_da_tabela_do_bloco():
    corpo = list(Document(io.BytesIO(html_para_docx(HTML_COM_GRAFICOS))).element.body)

    def tabela_com(texto: str) -> int:
        return next(i for i, el in enumerate(corpo) if el.tag == qn("w:tbl") and texto in "".join(t.text or "" for t in el.iter(qn("w:t"))))

    for titulo in ("HABILIDADES ACADÊMICAS", "Aplicação das Funções Executivas"):
        i = tabela_com(titulo)
        # Primeiro elemento com conteúdo depois da tabela: o parágrafo do gráfico.
        seguinte = next(el for el in corpo[i + 1:] if _tem_conteudo(el))
        assert seguinte.tag == qn("w:p") and seguinte.findall(".//" + qn("w:drawing")), titulo

    # ATA: o gráfico vem antes da tabela de percentuais e fica preso a ela
    # (vira a linha mesclada do topo da tabela).
    tabela_ata = corpo[tabela_com("ATA 1")]
    assert tabela_ata.findall(".//" + qn("w:tr"))[0].findall(".//" + qn("w:drawing"))


def test_pdf_tem_todos_os_graficos_e_nenhum_em_branco(tmp_path):
    pdf = html_para_pdf(HTML_COM_GRAFICOS)
    # O WeasyPrint compartilha os recursos entre as páginas: a mesma imagem
    # aparece na lista de cada página, por isso a contagem é por conteúdo.
    imagens = {img.data: img for pagina in PdfReader(io.BytesIO(pdf)).pages for img in pagina.images}.values()
    assert len(imagens) == TOTAL
    for img in imagens:
        assert _pixels_coloridos(img.image) > 500, img.name

    if shutil.which("pdfimages") is None:
        pytest.skip("pdfimages (Poppler) não instalado; contagem acima já feita com pypdf")
    caminho = tmp_path / "relatorio.pdf"
    caminho.write_bytes(pdf)
    lista = subprocess.run(["pdfimages", "-list", str(caminho)], capture_output=True, text=True, check=True).stdout
    tipos = [linha.split()[2] for linha in lista.splitlines()[2:] if linha.strip()]
    assert tipos.count("image") == TOTAL
