"""Leitura de arquivos enviados com limite de tamanho — sem isso um upload
gigante enche a memória/disco do servidor."""

from fastapi import HTTPException, UploadFile, status

MB = 1024 * 1024
TAMANHO_MAXIMO_PADRAO = 15 * MB


def ler_upload(arquivo: UploadFile, maximo: int = TAMANHO_MAXIMO_PADRAO) -> bytes:
    conteudo = arquivo.file.read(maximo + 1)
    if len(conteudo) > maximo:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"O arquivo '{arquivo.filename}' passa de {maximo // MB} MB. Envie um arquivo menor.",
        )
    return conteudo
