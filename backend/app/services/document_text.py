import io

from fastapi import UploadFile


class DocumentTextError(Exception):
    """Formato de arquivo não suportado ou falha ao extrair texto do
    documento enviado (usado na importação de modelos de laudo via IA)."""


def extract_text(upload: UploadFile) -> str:
    """Extrai o texto bruto de um documento enviado pela psicóloga
    descrevendo uma escala/instrumento (PDF, DOCX ou TXT), para servir de
    entrada à extração por IA do `schema_json` (ver services/ai/chains.py::
    extract_template_from_document)."""

    nome = (upload.filename or "").lower()
    conteudo = upload.file.read()

    if nome.endswith(".pdf"):
        return _extrair_pdf(conteudo)
    if nome.endswith(".docx"):
        return _extrair_docx(conteudo)
    if nome.endswith(".txt"):
        return conteudo.decode("utf-8", errors="ignore")

    raise DocumentTextError(
        f"Formato de arquivo não suportado: '{upload.filename}'. Envie um PDF, DOCX ou TXT."
    )


def _extrair_pdf(conteudo: bytes) -> str:
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
