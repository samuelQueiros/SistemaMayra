"""Fotos e documentos anexados, prontos para a IA: menores e sem metadados.

Foto de celular tem 3-5 MB e localização (EXIF/GPS) — mandar assim gasta
tokens e tempo à toa e expõe dados. Aqui cada imagem é girada conforme a
câmera, reduzida para no máximo 1600 px no maior lado e regravada em JPEG
qualidade 80, sem metadados. PDF: até 6 páginas, como imagens."""

import io

from PIL import Image, ImageOps

from app.services.document_text import paginas_em_png

LADO_MAXIMO_PX = 1600
QUALIDADE_JPEG = 80
MAXIMO_DE_PAGINAS = 6

TIPOS_ACEITOS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
}


class ArquivoInvalido(ValueError):
    """O arquivo enviado não é uma imagem que o sistema consiga abrir."""

    pass


def _comprimir(imagem: Image.Image) -> bytes:
    imagem = ImageOps.exif_transpose(imagem)
    if imagem.mode in ("RGBA", "LA", "P"):
        imagem = imagem.convert("RGBA")
        fundo = Image.new("RGB", imagem.size, "white")  # transparência vira branco
        fundo.paste(imagem, mask=imagem.getchannel("A"))
        imagem = fundo
    elif imagem.mode != "RGB":
        imagem = imagem.convert("RGB")
    imagem.thumbnail((LADO_MAXIMO_PX, LADO_MAXIMO_PX))
    saida = io.BytesIO()
    imagem.save(saida, format="JPEG", quality=QUALIDADE_JPEG, optimize=True)  # sem exif=: nenhum metadado
    return saida.getvalue()


def imagens_para_ia(conteudo: bytes, mime: str) -> list[bytes]:
    """JPEGs comprimidos do anexo (uma por imagem/página)."""
    try:
        if mime == "application/pdf":
            return [
                _comprimir(Image.open(io.BytesIO(png))) for png in paginas_em_png(conteudo, maximo=MAXIMO_DE_PAGINAS)
            ]
        return [_comprimir(Image.open(io.BytesIO(conteudo)))]
    except Exception as exc:  # noqa: BLE001 - arquivo corrompido ou formato disfarçado
        raise ArquivoInvalido("Não foi possível abrir o arquivo. Envie uma foto (JPG, PNG, WEBP) ou um PDF.") from exc


def tipo_do_arquivo(nome: str, conteudo: bytes) -> str:
    """MIME pela extensão, conferido pelo início do arquivo."""
    extensao = "." + nome.rsplit(".", 1)[-1].lower() if "." in nome else ""
    mime = TIPOS_ACEITOS.get(extensao)
    assinaturas = {
        "image/jpeg": (b"\xff\xd8\xff",),
        "image/png": (b"\x89PNG",),
        "image/webp": (b"RIFF",),
        "application/pdf": (b"%PDF",),
    }
    if mime is None or not conteudo.startswith(assinaturas[mime]):
        raise ArquivoInvalido(f"'{nome}' não é uma foto (JPG, PNG, WEBP) nem um PDF.")
    return mime
