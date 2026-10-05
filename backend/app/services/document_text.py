import io

from fastapi import UploadFile

from app.core.uploads import ler_upload


class DocumentTextError(Exception):
    """Formato de arquivo não suportado ou falha ao extrair texto do
    documento enviado (usado na importação de modelos de laudo via IA)."""


def extract_text(upload: UploadFile) -> str:
    """Extrai o texto bruto de um documento enviado pela psicóloga
    descrevendo uma escala/instrumento (PDF, DOCX ou TXT), para servir de
    entrada à extração por IA do `schema_json` (ver services/ai/chains.py::
    extract_template_from_document)."""

    nome = (upload.filename or "").lower()
    conteudo = ler_upload(upload)

    if nome.endswith(".pdf"):
        return extrair_texto_pdf(conteudo)
    if nome.endswith(".docx"):
        return _extrair_docx(conteudo)
    if nome.endswith(".txt"):
        return conteudo.decode("utf-8", errors="ignore")

    raise DocumentTextError(
        f"Formato de arquivo não suportado: '{upload.filename}'. Envie um PDF, DOCX ou TXT."
    )


def extrair_texto_pdf(conteudo: bytes) -> str:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        leitor = PdfReader(io.BytesIO(conteudo))
        return "\n".join(pagina.extract_text() or "" for pagina in leitor.pages)
    except PdfReadError as exc:
        raise DocumentTextError(f"Não foi possível ler o PDF enviado: {exc}") from exc


def _extrair_docx(conteudo: bytes) -> str:
    import zipfile

    from docx import Document
    from docx.opc.exceptions import PackageNotFoundError

    try:
        documento = Document(io.BytesIO(conteudo))
    except (PackageNotFoundError, zipfile.BadZipFile) as exc:
        raise DocumentTextError(f"Não foi possível ler o DOCX enviado: {exc}") from exc

    linhas = [paragrafo.text for paragrafo in documento.paragraphs]
    for tabela in documento.tables:
        for linha_tabela in tabela.rows:
            linhas.append(" | ".join(celula.text for celula in linha_tabela.cells))
    return "\n".join(linhas)


# Limites para mandar páginas como imagem à IA (6 PDFs × 10 páginas no máximo).
_MAXIMO_DE_PAGINAS_POR_PDF = 10
_ESCALA_DAS_PAGINAS = 1.4  # ~100 dpi: legível para a IA, sem pesar demais


def paginas_em_png(conteudo: bytes, maximo: int = _MAXIMO_DE_PAGINAS_POR_PDF) -> list[bytes]:
    """Páginas do PDF como imagens PNG, para IAs que enxergam imagem mas não
    aceitam PDF (ver services/ai/provedores.py, leitura "imagens")."""
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(conteudo)
    try:
        imagens = []
        for indice in range(min(len(pdf), maximo)):
            pagina = pdf[indice]
            imagem = pagina.render(scale=_ESCALA_DAS_PAGINAS).to_pil()
            saida = io.BytesIO()
            imagem.save(saida, format="PNG", optimize=True)
            imagens.append(saida.getvalue())
            pagina.close()
        return imagens
    finally:
        pdf.close()
