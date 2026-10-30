"""Exportação do laudo do formulário fixo (`formulario-novo-paciente.html`)
para PDF e DOCX.

O HTML do laudo é montado inteiro no navegador (`gerarDocumentoLaudoHTML()`
no formulário), seguindo o modelo oficial da psicóloga (relatório
"Parecer Neuropsicopedagógico / Análise Comportamental"). Este módulo só
converte esse HTML:

- PDF: WeasyPrint, com o CSS de página (A4, moldura, logo e rodapé em
  todas as páginas, exceto na capa) que já vem embutido no próprio HTML;
- DOCX: python-docx, percorrendo o vocabulário fechado de blocos que o
  formulário gera (classes CSS abaixo) e reproduzindo a mesma estrutura em
  Word — capa de página inteira numa seção própria, moldura da página,
  cabeçalho com logo, rodapé com contatos, tabelas, gráficos e destaques
  —, para a psicóloga poder editar o laudo no Word mantendo o layout.

Imagens só são aceitas como `data:` URI (o formulário embute tudo em
base64): nenhuma URL externa é buscada, nem pelo WeasyPrint.
"""

import base64
import io
import re

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor
from lxml import html as lxml_html
from weasyprint import HTML
from weasyprint.urls import URLFetcher

FONTE_PADRAO = "Arial"
TAMANHO_PADRAO = 10
RECUO_PRIMEIRA_LINHA_MM = 12.5
# A capa já vem composta pelo formulário (arte + nome) numa imagem A4. No
# Word ela fica um pouco menor que a página para a linha da imagem nunca
# transbordar e criar uma página em branco.
LARGURA_CAPA_DOCX_MM = 208

_DESTAQUES = {"amarelo": WD_COLOR_INDEX.YELLOW}
# Cores do modelo do relatório (CSS_LAUDO do formulário): os antigos fundos
# cinza viraram azul-claro. O Word não tem azul-claro entre as cores de
# realce, então o destaque "cinza" vira sombreamento do trecho.
COR_DESTAQUE = "DBE5F1"
COR_FAIXA = "C6D9F1"
COR_FAIXA_TOPICO = "B8CCE4"
COR_CAIXA = "C6D9F1"
COR_CAIXA_CLARA = "DBE5F1"
_ALINHAMENTOS = {
    "centro": WD_ALIGN_PARAGRAPH.CENTER,
    "direita": WD_ALIGN_PARAGRAPH.RIGHT,
    "esquerda": WD_ALIGN_PARAGRAPH.LEFT,
}


class DocumentoInvalidoError(ValueError):
    """O HTML recebido não é um laudo do formulário (falta o bloco `.documento`)."""

    pass


# ---------------------------------------------------------------- PDF


def _buscador_somente_data_uri() -> URLFetcher:
    return URLFetcher(allowed_protocols={"data"})


# Laudos gerados antes dos ajustes de 2026-10-18 guardam o HTML do modelo
# antigo. Na exportação (PDF e Word) eles saem no modelo atual naquilo que é
# só texto ou estilo; o resto (fotos na galeria, quadros por área, destaques
# da ATA) exige gerar o documento de novo ("Atualizar Relatório").
_BLOCOS_REMOVIDOS = (
    # "Observação sobre a faixa etária do Portage"
    re.compile(
        r'<div class="caixa-cinza clara"><p><strong>Observação sobre a faixa etária do Portage:</strong>.*?</p></div>',
        re.S,
    ),
    # "Encaminhei também o paciente para avaliação complementar…"
    re.compile(r'<div class="caixa-cinza clara"><p[^>]*>Encaminhei também .*?</div>', re.S),
    # "Estudo De Caso E Observações Clínicas" (já resumido nas seções acima),
    # até o próximo título.
    re.compile(r'<h3><mark class="cinza">Estudo De Caso E Observações Clínicas</mark></h3>.*?(?=<h3)', re.S),
)
_NOTA_SOBRE_OS_RESULTADOS = re.compile(
    r'<div class="(?:caixa-cinza clara|fechamento-texto)"><p><strong>NOTA SOBRE OS RESULTADOS:</strong>.*?</p></div>',
    re.S,
)
_BLOCO_ASSINATURA = '<div class="bloco-assinatura">'
_ATENCIOSAMENTE = '<p class="direita" style="margin-top:6mm"><strong>Atenciosamente,</strong></p>'
_IDADE_COGNITIVA_ANTIGA = re.compile(
    r"Repertório de referência pelo Portage: (.*?) \(fora da faixa etária do instrumento — não é comparação normativa\)"
)
_TROCAS = (
    ("PARECER NEUROPSICOPEDAGÓGICO<br>ANÁLISE COMPORTAMENTAL", "PARECER NEUROPSICOPEDAGÓGICO ANÁLISE COMPORTAMENTAL"),
    ("<strong>PROTOCOLO UTILIZADO</strong>", "<strong>METODOLOGIA E PROTOCOLOS UTILIZADOS</strong>"),
    # Credencial da assinatura
    (
        ">com formação especializada em Análise do Comportamento Aplicada (ABA)</span>",
        ">Especialista em Análise do Comportamento Aplicada - ABA</span>",
    ),
    (">Analista Comportamental - ABA</span>", ">Especialista em Análise do Comportamento Aplicada - ABA</span>"),
    # Fundos cinza -> azul-claro (CSS do documento)
    ("mark.cinza{background:#d9d9d9}", "mark.cinza{background:#dbe5f1}"),
    (".faixa{background:#bfbfbf;", ".faixa{background:#c6d9f1;"),
    (".faixa-topico{background:#a6a6a6;", ".faixa-topico{background:#b8cce4;"),
    (".caixa-cinza{background:#a6a6a6;", ".caixa-cinza{background:#c6d9f1;"),
    (".caixa-cinza.clara{background:#bfbfbf}", ".caixa-cinza.clara{background:#dbe5f1}"),
    ("background:#ede9fa", "background:#dbe5f1"),
    # Rodapé do tamanho e na altura do relatório-modelo de referência (~87 mm de conteúdo, ~7 mm da borda)
    (".rodape-pagina img{width:78mm}", ".rodape-pagina img{width:99mm}"),
    (
        "@bottom-center{content:element(rodapePagina);vertical-align:top;padding-top:1mm}",
        "@bottom-center{content:element(rodapePagina);vertical-align:top;padding-top:2mm}",
    ),
)


def no_modelo_atual(html: str) -> str:
    """Adapta o HTML de laudos gerados antes das últimas mudanças ao modelo atual (blocos removidos, textos
    e cores trocados, nota perto da assinatura), para PDF e Word saírem iguais aos laudos novos."""
    for bloco in _BLOCOS_REMOVIDOS:
        html = bloco.sub("", html)
    html = _IDADE_COGNITIVA_ANTIGA.sub(r"\1", html)
    for antigo, novo in _TROCAS:
        html = html.replace(antigo, novo)
    # "Nota sobre os resultados": no fim, perto da assinatura.
    nota = _NOTA_SOBRE_OS_RESULTADOS.search(html)
    if nota and _ATENCIOSAMENTE in html:
        html = html[: nota.start()] + html[nota.end() :]
        # Antes do bloco da assinatura (que abre com "Desde já…") quando ele existe.
        ancora = _BLOCO_ASSINATURA if _BLOCO_ASSINATURA in html else _ATENCIOSAMENTE
        html = html.replace(ancora, nota.group(0) + ancora, 1)
    return html


def html_para_pdf(html: str) -> bytes:
    """PDF do laudo, gerado pelo WeasyPrint. Só aceita imagens `data:` (nenhuma URL externa é buscada)."""
    return HTML(string=no_modelo_atual(html), url_fetcher=_buscador_somente_data_uri()).write_pdf()


# ---------------------------------------------------------------- DOCX


def _classes(el) -> set[str]:
    return set((el.get("class") or "").split())


def _cor_hex(valor: str | None) -> RGBColor | None:
    if not valor:
        return None
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})", valor.strip())
    return RGBColor.from_string(m.group(1).upper()) if m else None


def _estilo_inline(el, propriedade: str) -> str | None:
    m = re.search(rf"(?:^|;)\s*{propriedade}\s*:\s*([^;]+)", el.get("style") or "")
    return m.group(1).strip() if m else None


def _imagem_bytes(src: str | None) -> io.BytesIO | None:
    if not src or not src.startswith("data:") or "," not in src:
        return None
    cabecalho, dados = src.split(",", 1)
    if ";base64" not in cabecalho:
        return None
    try:
        return io.BytesIO(base64.b64decode(dados))
    except (ValueError, TypeError):
        return None


def _adicionar_imagem(run, src: str | None, largura_mm: float) -> bool:
    """Insere a imagem no run; imagem corrompida ou em formato que o Word
    não aceita é ignorada em vez de impedir a geração do documento."""
    imagem = _imagem_bytes(src)
    if imagem is None:
        return False
    try:
        run.add_picture(imagem, width=Mm(largura_mm))
    except Exception:  # noqa: BLE001 — python-docx levanta vários tipos para imagem inválida
        return False
    return True


def _mm_do_elemento(el, padrao: float) -> float:
    try:
        return float(el.get("data-mm") or padrao)
    except ValueError:
        return padrao


def _sombrear(elemento_pr, cor: str) -> None:
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), cor.lstrip("#").upper())
    elemento_pr.append(shd)


def _bordas_celula(celula, cor: str = "000000", tipo: str = "single", tamanho: int = 4) -> None:
    tc_pr = celula._tc.get_or_add_tcPr()
    bordas = OxmlElement("w:tcBorders")
    for lado in ("top", "left", "bottom", "right"):
        b = OxmlElement(f"w:{lado}")
        b.set(qn("w:val"), tipo)
        b.set(qn("w:sz"), str(tamanho))
        b.set(qn("w:space"), "0")
        b.set(qn("w:color"), cor)
        bordas.append(b)
    tc_pr.append(bordas)


def _sem_bordas_tabela(tabela) -> None:
    tbl_pr = tabela._tbl.tblPr
    bordas = OxmlElement("w:tblBorders")
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = OxmlElement(f"w:{lado}")
        b.set(qn("w:val"), "nil")
        bordas.append(b)
    tbl_pr.append(bordas)


def _bordas_tabela(tabela, cor: str, tipo: str, tamanho: int) -> None:
    tbl_pr = tabela._tbl.tblPr
    bordas = OxmlElement("w:tblBorders")
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = OxmlElement(f"w:{lado}")
        b.set(qn("w:val"), tipo)
        b.set(qn("w:sz"), str(tamanho))
        b.set(qn("w:space"), "0")
        b.set(qn("w:color"), cor)
        bordas.append(b)
    tbl_pr.append(bordas)


def _largura_celula(celula, mm: float) -> None:
    celula.width = Mm(mm)
    tc_pr = celula._tc.get_or_add_tcPr()
    tc_w = tc_pr.find(qn("w:tcW"))
    if tc_w is None:
        tc_w = OxmlElement("w:tcW")
        tc_pr.append(tc_w)
    tc_w.set(qn("w:w"), str(int(mm * 56.7)))
    tc_w.set(qn("w:type"), "dxa")


def _fixar_colunas(tabela, larguras_mm: list[float]) -> None:
    """Grade fixa de colunas: sem isso Word/LibreOffice redistribuem as
    larguras e a tabela perde as proporções do modelo."""
    tabela.autofit = False
    tbl = tabela._tbl
    tbl_pr = tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tbl_pr.append(layout)
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(int(sum(larguras_mm) * 56.7)))
    tbl_w.set(qn("w:type"), "dxa")
    for col, largura in zip(tbl.tblGrid.findall(qn("w:gridCol")), larguras_mm):
        col.set(qn("w:w"), str(int(largura * 56.7)))
    for linha in tabela.rows:
        for celula, largura in zip(linha.cells, larguras_mm):
            _largura_celula(celula, largura)


def _repetir_cabecalho(linha) -> None:
    tr_pr = linha._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    tr_pr.append(el)


def _nao_quebrar_linha(linha) -> None:
    tr_pr = linha._tr.get_or_add_trPr()
    tr_pr.append(OxmlElement("w:cantSplit"))


def _moldura_da_pagina(secao) -> None:
    """Borda fina ao redor de toda a página, como no modelo."""
    sect_pr = secao._sectPr
    bordas = OxmlElement("w:pgBorders")
    bordas.set(qn("w:offsetFrom"), "page")
    for lado in ("top", "left", "bottom", "right"):
        b = OxmlElement(f"w:{lado}")
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), "6")
        b.set(qn("w:space"), "24")
        b.set(qn("w:color"), "000000")
        bordas.append(b)
    # A ordem dos filhos de sectPr importa para o Word: pgBorders vem logo
    # depois de pgMar.
    pg_mar = sect_pr.find(qn("w:pgMar"))
    if pg_mar is not None:
        pg_mar.addnext(bordas)
    else:
        sect_pr.append(bordas)


class _ConversorDocx:
    def __init__(self) -> None:
        self.doc = Document()
        self.quebra_pendente = False
        self._configurar_documento()

    # -- configuração geral -------------------------------------------

    def _configurar_documento(self) -> None:
        estilo = self.doc.styles["Normal"]
        estilo.font.name = FONTE_PADRAO
        estilo.font.size = Pt(TAMANHO_PADRAO)
        estilo.element.rPr.rFonts.set(qn("w:eastAsia"), FONTE_PADRAO)
        formato = estilo.paragraph_format
        formato.space_before = Pt(0)
        formato.space_after = Pt(6)
        formato.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        formato.line_spacing = 1.5

        secao = self.doc.sections[0]
        secao.page_width = Mm(210)
        secao.page_height = Mm(297)
        secao.top_margin = Mm(30)
        secao.bottom_margin = Mm(27)
        secao.left_margin = Mm(20)
        secao.right_margin = Mm(20)
        secao.header_distance = Mm(11)
        secao.footer_distance = Mm(10)
        _moldura_da_pagina(secao)

    def _capa(self, raiz) -> None:
        """Primeira seção do documento: só a imagem da capa, sem margens,
        moldura, cabeçalho nem rodapé. O laudo começa na seção seguinte."""
        achados = raiz.xpath('//*[contains(concat(" ", normalize-space(@class), " "), " capa ")]//img')
        if not achados or _imagem_bytes(achados[0].get("src")) is None:
            return
        paragrafo = self.doc.add_paragraph()
        paragrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        formato = paragrafo.paragraph_format
        formato.space_before = Pt(0)
        formato.space_after = Pt(0)
        formato.line_spacing = 1.0
        if not _adicionar_imagem(paragrafo.add_run(), achados[0].get("src"), LARGURA_CAPA_DOCX_MM):
            paragrafo._p.getparent().remove(paragrafo._p)
            return
        self.doc.add_section(WD_SECTION.NEW_PAGE)
        # add_section cria um parágrafo vazio só para guardar a quebra de
        # seção; ele não cabe na página da capa. A quebra passa para o
        # parágrafo da imagem e o vazio é removido.
        quebra = self.doc.paragraphs[-1]._p
        sect_pr_capa = quebra.pPr.find(qn("w:sectPr"))
        paragrafo._p.get_or_add_pPr().append(sect_pr_capa)
        quebra.getparent().remove(quebra)

        capa = self.doc.sections[0]
        for margem in (
            "top_margin",
            "bottom_margin",
            "left_margin",
            "right_margin",
            "header_distance",
            "footer_distance",
        ):
            setattr(capa, margem, Mm(0))
        bordas = capa._sectPr.find(qn("w:pgBorders"))
        if bordas is not None:
            capa._sectPr.remove(bordas)

    def _cabecalho_e_rodape(self, raiz) -> None:
        secao = self.doc.sections[-1]
        if len(self.doc.sections) > 1:
            # Depois da capa: cabeçalho/rodapé próprios, não herdados.
            secao.header.is_linked_to_previous = False
            secao.footer.is_linked_to_previous = False
        for classe, destino, largura in (
            ("cabecalho-pagina", secao.header, 19),
            ("rodape-pagina", secao.footer, 99),
        ):
            achados = raiz.xpath(f'//*[contains(concat(" ", normalize-space(@class), " "), " {classe} ")]//img')
            paragrafo = destino.paragraphs[0]
            paragrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragrafo.paragraph_format.space_after = Pt(0)
            paragrafo.paragraph_format.line_spacing = 1.0
            if achados:
                _adicionar_imagem(paragrafo.add_run(), achados[0].get("src"), _mm_do_elemento(achados[0], largura))

    # -- blocos ---------------------------------------------------------

    def _novo_paragrafo(self, container=None, *, recuo: bool = False, alinhamento=None):
        destino = container if container is not None else self.doc
        paragrafo = destino.add_paragraph()
        if recuo:
            paragrafo.paragraph_format.first_line_indent = Mm(RECUO_PRIMEIRA_LINHA_MM)
        paragrafo.alignment = alinhamento if alinhamento is not None else WD_ALIGN_PARAGRAPH.JUSTIFY
        if container is None and self.quebra_pendente:
            paragrafo.paragraph_format.page_break_before = True
            self.quebra_pendente = False
        return paragrafo

    def _antes_de_tabela(self) -> None:
        # Tabelas não aceitam "quebra de página antes" no Word: usa um
        # parágrafo mínimo com a quebra.
        if self.quebra_pendente:
            p = self.doc.add_paragraph()
            p.paragraph_format.page_break_before = True
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            run = p.add_run()
            run.font.size = Pt(2)
            self.quebra_pendente = False

    def _inline(self, paragrafo, el, formato: dict | None = None) -> None:
        """Adiciona ao parágrafo o texto de `el` (e filhos) como runs,
        preservando negrito, itálico, destaques, cor e tamanho."""
        formato = dict(formato or {})
        tag = el.tag if isinstance(el.tag, str) else ""
        classes = _classes(el)
        if tag in ("strong", "b"):
            formato["negrito"] = True
        elif tag in ("em", "i"):
            formato["italico"] = True
        elif tag == "u":
            formato["sublinhado"] = True
        elif tag == "mark":
            formato["destaque"] = "amarelo" if "amarelo" in classes else "cinza"
        cor = _estilo_inline(el, "color")
        if cor:
            formato["cor"] = cor
        tamanho = _estilo_inline(el, "font-size")
        if tamanho and tamanho.endswith("pt"):
            try:
                formato["tamanho"] = float(tamanho[:-2])
            except ValueError:
                pass
        if "negrito" in classes:
            formato["negrito"] = True

        if tag == "br":
            paragrafo.add_run().add_break()
        elif tag == "img":
            _adicionar_imagem(paragrafo.add_run(), el.get("src"), _mm_do_elemento(el, 40))
        else:
            self._run_texto(paragrafo, el.text, formato)
            for filho in el:
                self._inline(paragrafo, filho, formato)
                # O texto depois de um filho (tail) tem a formatação do pai.
                self._run_texto(paragrafo, filho.tail, formato)

    def _run_texto(self, paragrafo, texto: str | None, formato: dict) -> None:
        if not texto:
            return
        texto = re.sub(r"\s+", " ", texto)
        if not texto.strip() and not paragrafo.runs:
            return
        run = paragrafo.add_run(texto)
        run.bold = formato.get("negrito") or None
        run.italic = formato.get("italico") or None
        run.underline = formato.get("sublinhado") or None
        if formato.get("destaque") in _DESTAQUES:
            run.font.highlight_color = _DESTAQUES[formato["destaque"]]
        elif formato.get("destaque"):
            _sombrear(run._r.get_or_add_rPr(), COR_DESTAQUE)
        cor = _cor_hex(formato.get("cor"))
        if cor is not None:
            run.font.color.rgb = cor
        if formato.get("tamanho"):
            run.font.size = Pt(formato["tamanho"])
        if formato.get("fonte"):
            run.font.name = formato["fonte"]

    def _paragrafo_de(self, el, container=None, formato: dict | None = None):
        classes = _classes(el)
        alinhamento = next((_ALINHAMENTOS[c] for c in classes if c in _ALINHAMENTOS), None)
        recuo = "recuo" in classes
        paragrafo = self._novo_paragrafo(container, recuo=recuo, alinhamento=alinhamento)
        if "junto" in classes:
            paragrafo.paragraph_format.keep_with_next = True
        if "compacto" in classes:
            paragrafo.paragraph_format.space_after = Pt(0)
            paragrafo.paragraph_format.line_spacing = 1.15
        formato = dict(formato or {})
        if "assinatura-nome" in classes:
            # PDF usa "Dancing Script" (embutida em base64 no CSS_LAUDO); o Word
            # não embute fontes aqui, então usa "Segoe Script" (nativa do Windows)
            # para manter o nome em caligrafia também no .docx.
            formato.update(tamanho=18, fonte="Segoe Script")
        self._inline(paragrafo, el, formato)
        return paragrafo

    def _lista(self, el, container=None) -> None:
        marcador = "✔" if "checks" in _classes(el) else "•"
        for li in el.findall("li"):
            p = self._novo_paragrafo(container, alinhamento=WD_ALIGN_PARAGRAPH.LEFT)
            formato = p.paragraph_format
            formato.left_indent = Mm(6 if marcador == "✔" else 12)
            formato.first_line_indent = Mm(-6)
            formato.space_after = Pt(0)
            formato.tab_stops.add_tab_stop(formato.left_indent)
            p.add_run(marcador + "\t")
            self._inline(p, li)
        if container is None:
            espaco = self.doc.add_paragraph()
            espaco.paragraph_format.space_after = Pt(0)
            espaco.paragraph_format.line_spacing = 1.0

    def _titulo_marcado(self, el) -> None:
        p = self._novo_paragrafo(alinhamento=WD_ALIGN_PARAGRAPH.LEFT)
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.space_before = Pt(6)
        self._inline(p, el, {"negrito": True, "destaque": "cinza", "sublinhado": True})

    def _titulo_de_area(self, el) -> None:
        """ "ÁREA DO DESENVOLVIMENTO: …" acima de cada quadro, centralizado e sem fundo."""
        p = self._novo_paragrafo(alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(6)
        self._inline(p, el, {"negrito": True, "tamanho": 10.5})

    def _titulo(self, el) -> None:
        classes = _classes(el)
        p = self._novo_paragrafo(alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(10)
        formato = {"negrito": True, "tamanho": 12.5}
        if "roxo" in classes:
            formato["cor"] = "#5C4B92"
        if "marcado" in classes:
            formato.update(destaque="cinza", tamanho=10)
        self._inline(p, el, formato)

    def _faixa(self, el, cor: str) -> None:
        classes = _classes(el)
        alinhamento = WD_ALIGN_PARAGRAPH.CENTER if "centro" in classes else WD_ALIGN_PARAGRAPH.LEFT
        p = self._novo_paragrafo(alinhamento=alinhamento)
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(8)
        p.paragraph_format.line_spacing = 1.15
        _sombrear(p._p.get_or_add_pPr(), cor)
        self._inline(p, el, {"negrito": True})

    def _caixa(self, el, cor: str) -> None:
        self._antes_de_tabela()
        tabela = self.doc.add_table(rows=1, cols=1)
        tabela.alignment = WD_TABLE_ALIGNMENT.CENTER
        _sem_bordas_tabela(tabela)
        _fixar_colunas(tabela, [170])
        celula = tabela.cell(0, 0)
        _sombrear(celula._tc.get_or_add_tcPr(), cor)
        celula.paragraphs[0]._p.getparent().remove(celula.paragraphs[0]._p)
        for filho in el:
            if filho.tag == "p":
                p = self._paragrafo_de(filho, celula, {"negrito": "normal" not in _classes(el)})
                p.paragraph_format.space_after = Pt(6)
        if not celula.paragraphs:
            celula.add_paragraph()
        self.doc.add_paragraph().paragraph_format.space_after = Pt(0)

    def _imagem_centralizada(self, el, manter_com_proximo: bool = False) -> None:
        img = el if el.tag == "img" else next(iter(el.iter("img")), None)
        if img is None or _imagem_bytes(img.get("src")) is None:
            return
        p = self._novo_paragrafo(alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
        p.paragraph_format.keep_together = True
        if manter_com_proximo:
            p.paragraph_format.keep_with_next = True
        p.paragraph_format.line_spacing = 1.0
        _adicionar_imagem(p.add_run(), img.get("src"), _mm_do_elemento(img, 160))

    def _linha_de_imagens(self, el) -> None:
        imagens = [img for img in el.iter("img") if _imagem_bytes(img.get("src")) is not None]
        if not imagens:
            return
        self._antes_de_tabela()
        tabela = self.doc.add_table(rows=1, cols=len(imagens))
        tabela.alignment = WD_TABLE_ALIGNMENT.CENTER
        _sem_bordas_tabela(tabela)
        largura_coluna = 170 / len(imagens)
        _fixar_colunas(tabela, [largura_coluna] * len(imagens))
        for i, img in enumerate(imagens):
            celula = tabela.cell(0, i)
            _largura_celula(celula, largura_coluna)
            celula.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = celula.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.line_spacing = 1.0
            largura = min(_mm_do_elemento(img, largura_coluna - 4), largura_coluna - 2)
            _adicionar_imagem(p.add_run(), img.get("src"), largura)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(0)

    def _galeria(self, el) -> None:
        """Página final de fotos: duas por linha, mesmo tamanho."""
        imagens = [img for img in el.iter("img") if _imagem_bytes(img.get("src")) is not None]
        if not imagens:
            return
        self._antes_de_tabela()
        colunas = 2
        linhas = (len(imagens) + colunas - 1) // colunas
        tabela = self.doc.add_table(rows=linhas, cols=colunas)
        tabela.alignment = WD_TABLE_ALIGNMENT.CENTER
        _sem_bordas_tabela(tabela)
        largura_coluna = 85
        _fixar_colunas(tabela, [largura_coluna] * colunas)
        for i, img in enumerate(imagens):
            celula = tabela.cell(i // colunas, i % colunas)
            _largura_celula(celula, largura_coluna)
            p = celula.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(6)
            _adicionar_imagem(p.add_run(), img.get("src"), min(_mm_do_elemento(img, 78), largura_coluna - 4))
        for linha in tabela.rows:
            _nao_quebrar_linha(linha)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(0)

    def _cabecalho_paciente(self, el) -> None:
        """Bloco inicial: foto à esquerda e caixa com a identificação."""
        self._antes_de_tabela()
        foto = next(iter(el.xpath('.//*[contains(@class,"cab-foto")]//img')), None)
        caixa = next(iter(el.xpath('.//*[contains(@class,"cab-box")]')), None)
        tabela = self.doc.add_table(rows=1, cols=3)
        tabela.alignment = WD_TABLE_ALIGNMENT.CENTER
        _sem_bordas_tabela(tabela)
        _fixar_colunas(tabela, [44, 10, 112])
        c_foto, _, c_caixa = tabela.rows[0].cells
        if foto is not None:
            p = c_foto.paragraphs[0]
            p.paragraph_format.line_spacing = 1.0
            _adicionar_imagem(p.add_run(), foto.get("src"), _mm_do_elemento(foto, 42))
        c_caixa.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        _bordas_celula(c_caixa)
        c_caixa.paragraphs[0]._p.getparent().remove(c_caixa.paragraphs[0]._p)
        if caixa is not None:
            for filho in caixa.findall("p"):
                p = self._paragrafo_de(filho, c_caixa, {"negrito": True})
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(5)
                p.paragraph_format.space_after = Pt(5)
                p.paragraph_format.line_spacing = 1.0
        if not c_caixa.paragraphs:
            c_caixa.add_paragraph()
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def _linha_mesclada(self, linha, antes_el) -> None:
        """Primeira linha de uma tabela, mesclada e sem bordas: o título ou
        gráfico que precede a tabela no HTML vira parte da própria tabela em
        vez de um parágrafo solto antes dela — python-docx/Word não garante
        manter um parágrafo "preso" a uma tabela seguinte (keep_with_next
        entre parágrafo e tabela é frequentemente ignorado), mas uma linha
        marcada como cabeçalho (tblHeader) com cantSplit nunca se separa da
        tabela."""
        _nao_quebrar_linha(linha)
        celula = linha.cells[0]
        for outra in linha.cells[1:]:
            celula = celula.merge(outra)
        _bordas_celula(celula, tipo="nil")
        p = celula.paragraphs[0]
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        classes_el = _classes(antes_el)
        if "grafico" in classes_el:
            # Gráfico antes da tabela (ex.: ATA): não repete em cada página,
            # só precisa ficar preso à primeira linha de dados.
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.line_spacing = 1.0
            img = antes_el if antes_el.tag == "img" else next(iter(antes_el.iter("img")), None)
            if img is not None:
                _adicionar_imagem(p.add_run(), img.get("src"), _mm_do_elemento(img, 160))
            return
        _repetir_cabecalho(linha)
        if antes_el.tag in ("h1", "h2"):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            formato = {"negrito": True, "tamanho": 12.5}
            if "roxo" in classes_el:
                formato["cor"] = "#5C4B92"
            if "marcado" in classes_el:
                formato.update(destaque="cinza", tamanho=10)
            self._inline(p, antes_el, formato)
        elif "area" in classes_el:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            self._inline(p, antes_el, {"negrito": True, "tamanho": 10.5})
        else:
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            self._inline(p, antes_el, {"negrito": True, "destaque": "cinza", "sublinhado": True})

    def _tabela(self, el, antes_el=None):
        classes = _classes(el)
        linhas_html = el.xpath("./tr|./thead/tr|./tbody/tr")
        if not linhas_html:
            return None
        num_colunas = max(sum(int(c.get("colspan") or 1) for c in tr.xpath("./td|./th")) for tr in linhas_html)
        larguras = [float(x) for x in (el.get("data-larguras") or "").split(",") if x.strip()]
        if len(larguras) != num_colunas:
            larguras = [170 / num_colunas] * num_colunas
        tamanho_fonte = float(el.get("data-fonte") or 9)

        self._antes_de_tabela()
        offset = 1 if antes_el is not None else 0
        tabela = self.doc.add_table(rows=len(linhas_html) + offset, cols=num_colunas)
        tabela.alignment = WD_TABLE_ALIGNMENT.CENTER
        if "dupla" in classes:
            _bordas_tabela(tabela, "000000", "double", 4)
        elif "roxa" in classes:
            _bordas_tabela(tabela, "B3A5E2", "single", 6)
        else:
            _bordas_tabela(tabela, "000000", "single", 4)
        _fixar_colunas(tabela, larguras)

        if antes_el is not None:
            self._linha_mesclada(tabela.rows[0], antes_el)

        for i, tr in enumerate(linhas_html):
            linha = tabela.rows[i + offset]
            _nao_quebrar_linha(linha)
            celulas_html = tr.xpath("./td|./th")
            eh_cabecalho = bool(celulas_html) and all(c.tag == "th" for c in celulas_html)
            if eh_cabecalho:
                _repetir_cabecalho(linha)
            coluna = 0
            for celula_html in celulas_html:
                span = int(celula_html.get("colspan") or 1)
                celula = linha.cells[coluna]
                if span > 1:
                    celula = celula.merge(linha.cells[coluna + span - 1])
                _largura_celula(celula, sum(larguras[coluna : coluna + span]))
                celula.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                classes_celula = _classes(celula_html)
                fundo = _estilo_inline(celula_html, "background") or _estilo_inline(celula_html, "background-color")
                if fundo and _cor_hex(fundo) is not None:
                    _sombrear(celula._tc.get_or_add_tcPr(), fundo.lstrip("#"))
                formato = {"tamanho": tamanho_fonte}
                if celula_html.tag == "th":
                    formato["negrito"] = True
                cor_texto = _estilo_inline(celula_html, "color")
                if cor_texto:
                    formato["cor"] = cor_texto
                p = celula.paragraphs[0]
                if "centro" in classes_celula or celula_html.tag == "th" or "centro" in classes:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                else:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.0
                self._inline(p, celula_html, formato)
                coluna += span
        espaco = self.doc.add_paragraph()
        espaco.paragraph_format.space_after = Pt(4)
        return tabela

    def _prender_ao_proximo(self, tabela) -> None:
        """Marca o último parágrafo da última célula da tabela para ficar
        preso ao próximo bloco (ex.: tabela seguida do gráfico do mesmo
        protocolo) — ao contrário de parágrafo→tabela, o vínculo
        tabela→parágrafo seguinte via keep_with_next no fim da última célula
        é respeitado pelo Word."""
        ultima_linha = tabela.rows[-1]
        ultima_celula = ultima_linha.cells[-1]
        ultima_celula.paragraphs[-1].paragraph_format.keep_with_next = True

    def bloco(self, el) -> None:
        if not isinstance(el.tag, str):
            return
        tag = el.tag
        classes = _classes(el)

        if "quebra" in classes:
            self.quebra_pendente = True
        elif classes & {"cabecalho-pagina", "rodape-pagina", "moldura", "capa"}:
            return
        elif "cab-paciente" in classes:
            self._cabecalho_paciente(el)
        elif "faixa" in classes:
            self._faixa(el, COR_FAIXA)
        elif "faixa-topico" in classes:
            self._faixa(el, COR_FAIXA_TOPICO)
        elif "caixa-cinza" in classes:
            self._caixa(el, COR_CAIXA_CLARA if "clara" in classes else COR_CAIXA)
        elif "linha-assinatura" in classes:
            p = self._novo_paragrafo(alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
            p.paragraph_format.left_indent = Mm(38)
            p.paragraph_format.right_indent = Mm(38)
            p.paragraph_format.space_before = Pt(36)
            p.paragraph_format.space_after = Pt(0)
            p_bdr = OxmlElement("w:pBdr")
            base = OxmlElement("w:bottom")
            base.set(qn("w:val"), "single")
            base.set(qn("w:sz"), "6")
            base.set(qn("w:space"), "1")
            base.set(qn("w:color"), "000000")
            p_bdr.append(base)
            p._p.get_or_add_pPr().append(p_bdr)
        elif "grafico" in classes:
            self._imagem_centralizada(el)
        elif "galeria" in classes:
            self._galeria(el)
        elif "graficos-lado" in classes or "fotos" in classes:
            self._linha_de_imagens(el)
        elif tag == "table":
            self._tabela(el)
        elif tag == "ul":
            self._lista(el)
        elif tag in ("h1", "h2"):
            self._titulo(el)
        elif tag == "h3" and "area" in classes:
            self._titulo_de_area(el)
        elif tag == "h3":
            self._titulo_marcado(el)
        elif tag == "p":
            self._paragrafo_de(el)
        elif tag == "img":
            self._imagem_centralizada(el)
        elif tag in ("div", "section", "main", "article"):
            self._blocos(el)

    def _blocos(self, container) -> None:
        """Percorre os filhos olhando um à frente, para prender ao mesmo
        elemento tudo que o HTML sempre gera em sequência e que não pode se
        separar entre páginas no .docx: título (h1/h2/h3) logo antes de uma
        tabela, ou gráfico logo antes de uma tabela, viram a primeira linha
        dessa tabela; tabela logo antes de um gráfico/legenda, ou gráfico
        logo antes de uma legenda, ficam presos ao próximo parágrafo."""
        filhos = [f for f in container if isinstance(f.tag, str)]
        i = 0
        total = len(filhos)

        def prender_tabela_ao_que_vem_depois(tabela, depois) -> None:
            if tabela is not None and depois is not None and ("grafico" in _classes(depois) or depois.tag == "p"):
                self._prender_ao_proximo(tabela)

        while i < total:
            el = filhos[i]
            proximo = filhos[i + 1] if i + 1 < total else None
            classes = _classes(el)
            eh_titulo = el.tag in ("h1", "h2", "h3")
            eh_grafico = "grafico" in classes

            if (eh_titulo or eh_grafico) and proximo is not None and proximo.tag == "table":
                tabela = self._tabela(proximo, antes_el=el)
                if tabela is None:
                    # Tabela sem linhas (não deveria acontecer): não há onde
                    # mesclar o título/gráfico — renderiza-o normalmente.
                    self.bloco(el)
                    i += 1
                    continue
                depois = filhos[i + 2] if i + 2 < total else None
                prender_tabela_ao_que_vem_depois(tabela, depois)
                i += 2
                continue
            if el.tag == "table":
                tabela = self._tabela(el)
                prender_tabela_ao_que_vem_depois(tabela, proximo)
                i += 1
                continue
            if eh_grafico and proximo is not None and proximo.tag == "p":
                self._imagem_centralizada(el, manter_com_proximo=True)
                i += 1
                continue
            self.bloco(el)
            i += 1

    def converter(self, html: str) -> bytes:
        raiz = lxml_html.fromstring(html)
        corpo = raiz.xpath('//*[contains(concat(" ", normalize-space(@class), " "), " documento ")]')
        if not corpo:
            raise DocumentoInvalidoError("HTML do laudo não contém o bloco .documento.")
        self._capa(raiz)
        self._cabecalho_e_rodape(raiz)
        self._blocos(corpo[0])
        saida = io.BytesIO()
        self.doc.save(saida)
        return saida.getvalue()


def html_para_docx(html: str) -> bytes:
    """Word editável do laudo. Só entende o vocabulário de classes CSS que o formulário gera: se o
    gerador mudar, confira o conversor (`_ConversorDocx`)."""
    return _ConversorDocx().converter(no_modelo_atual(html))
