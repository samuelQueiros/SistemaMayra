import io

import pytest
from docx import Document
from fastapi import UploadFile
from pypdf import PdfWriter
from starlette.datastructures import Headers

from app.services.document_text import DocumentTextError, extract_text


def _upload(filename: str, content: bytes, content_type: str = "application/octet-stream") -> UploadFile:
    return UploadFile(
        filename=filename,
        file=io.BytesIO(content),
        headers=Headers({"content-type": content_type}),
    )


def test_extrai_texto_de_txt():
    upload = _upload("escala.txt", "Item 1: Comunicação\nItem 2: Socialização".encode("utf-8"), "text/plain")

    texto = extract_text(upload)

    assert "Comunicação" in texto
    assert "Socialização" in texto


def test_extrai_texto_de_docx():
    buffer = io.BytesIO()
    documento = Document()
    documento.add_paragraph("Escala de exemplo")
    documento.add_paragraph("Item 1: Iniciativa social")
    documento.save(buffer)

    upload = _upload("escala.docx", buffer.getvalue())

    texto = extract_text(upload)

    assert "Escala de exemplo" in texto
    assert "Iniciativa social" in texto


def test_extrai_texto_de_pdf_vazio_nao_gera_erro():
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)

    upload = _upload("escala.pdf", buffer.getvalue())

    texto = extract_text(upload)

    assert texto == ""


def test_formato_nao_suportado_gera_erro_claro():
    upload = _upload("foto.png", "não é um documento de texto".encode("utf-8"))

    with pytest.raises(DocumentTextError):
        extract_text(upload)


def test_pdf_corrompido_gera_erro_claro():
    upload = _upload("escala.pdf", b"isso nao e um pdf de verdade")

    with pytest.raises(DocumentTextError):
        extract_text(upload)


def test_docx_corrompido_gera_erro_claro():
    upload = _upload("escala.docx", b"isso nao e um docx de verdade")

    with pytest.raises(DocumentTextError):
        extract_text(upload)
