import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_psychologist
from app.models.psychologist import Psychologist
from app.services.laudo_documento import DocumentoInvalidoError, html_para_docx, html_para_pdf

router = APIRouter(tags=["documents"])

MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# O HTML do laudo carrega fotos e gráficos em base64: pode passar de alguns
# MB, mas não precisa de mais que isso.
_TAMANHO_MAXIMO_HTML = 40_000_000


class DocumentExportRequest(BaseModel):
    html: str = Field(min_length=1, max_length=_TAMANHO_MAXIMO_HTML)
    file_name: str | None = Field(default=None, max_length=200)


def nome_de_arquivo_seguro(nome: str | None, extensao: str) -> str:
    base = unicodedata.normalize("NFKD", nome or "laudo").encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^A-Za-z0-9_-]+", "_", base).strip("_") or "laudo"
    base = re.sub(r"\.(pdf|docx)$", "", base, flags=re.IGNORECASE)
    return f"{base}.{extensao}"


def resposta_de_arquivo(conteudo: bytes, media_type: str, nome_arquivo: str) -> Response:
    return Response(
        content=conteudo,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )


@router.post("/api/documents/pdf")
def export_pdf(
    data: DocumentExportRequest,
    current: Psychologist = Depends(get_current_psychologist),
) -> Response:
    """Converte em PDF o laudo montado pelo formulário (mesmo HTML que é
    salvo no laudo e usado pelo Histórico)."""
    try:
        pdf = html_para_pdf(data.html)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return resposta_de_arquivo(pdf, "application/pdf", nome_de_arquivo_seguro(data.file_name, "pdf"))


@router.post("/api/documents/docx")
def export_docx(
    data: DocumentExportRequest,
    current: Psychologist = Depends(get_current_psychologist),
) -> Response:
    """Converte em Word (.docx) editável o laudo montado pelo formulário."""
    try:
        docx = html_para_docx(data.html)
    except DocumentoInvalidoError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return resposta_de_arquivo(docx, MIME_DOCX, nome_de_arquivo_seguro(data.file_name, "docx"))
