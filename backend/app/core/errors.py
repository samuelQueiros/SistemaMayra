"""Mensagens de erro em português claro para quem usa o sistema.

A validação automática do FastAPI/Pydantic responde 422 com uma lista
técnica em inglês (`[{"type": "missing", "loc": [...]}]`), que as telas
acabavam mostrando crua. Aqui ela vira uma frase única, dizendo o campo e
como corrigir — e erros inesperados viram um 500 com mensagem amigável (o
detalhe técnico fica só no log do servidor, sem dados do paciente).
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

_NOMES_DE_CAMPOS = {
    "email": "E-mail",
    "password": "Senha",
    "name": "Nome",
    "birth_date": "Data de nascimento",
    "sex": "Sexo",
    "school_info": "Escola",
    "template_id": "Modelo do protocolo",
    "answers": "Respostas do protocolo",
    "generated_text": "Texto do relatório",
    "html": "Conteúdo do relatório",
    "file_name": "Nome do arquivo",
    "report_ids": "Protocolos selecionados",
    "api_key": "Chave de acesso",
    "provider": "Provedor",
    "caption": "Legenda",
}


def _nome_do_campo(loc: tuple | list) -> str:
    partes = [str(p) for p in loc if p not in ("body", "query", "path") and not isinstance(p, int)]
    if not partes:
        return "Dados enviados"
    campo = partes[-1]
    return _NOMES_DE_CAMPOS.get(campo, campo.replace("_", " ").capitalize())


def mensagem_de_validacao(erro: dict) -> str:
    """Frase em português para um erro de validação do Pydantic."""
    campo = _nome_do_campo(erro.get("loc", ()))
    tipo = erro.get("type", "")
    contexto = erro.get("ctx") or {}

    if tipo == "missing":
        return f'Preencha o campo "{campo}".'
    if tipo == "string_too_short":
        minimo = contexto.get("min_length")
        return f'"{campo}" precisa ter pelo menos {minimo} caracteres.' if minimo else f'"{campo}" está curto demais.'
    if tipo == "string_too_long":
        maximo = contexto.get("max_length")
        return f'"{campo}" pode ter no máximo {maximo} caracteres.' if maximo else f'"{campo}" está longo demais.'
    if tipo in ("date_parsing", "date_from_datetime_parsing", "date_type", "datetime_parsing"):
        return f'"{campo}" não é uma data válida. Use o formato dd/mm/aaaa.'
    if tipo == "uuid_parsing":
        return "O registro solicitado não existe ou o endereço está incorreto."
    if tipo in ("greater_than", "greater_than_equal", "less_than", "less_than_equal"):
        return f'"{campo}" está fora do intervalo permitido.'
    if tipo in ("int_parsing", "float_parsing", "int_type", "float_type"):
        return f'"{campo}" precisa ser um número.'
    if tipo == "value_error" and "email" in str(erro.get("msg", "")).lower():
        return "Informe um e-mail válido (ex.: nome@exemplo.com)."
    if tipo == "json_invalid":
        return "Os dados enviados estão corrompidos. Recarregue a página e tente novamente."
    return f'O campo "{campo}" tem um valor inválido. Confira e tente novamente.'


def registrar_tratadores_de_erro(app: FastAPI) -> None:
    """Liga as respostas de erro amigáveis: o 422 de validação vira uma frase em português e o erro
    inesperado vira 500 com mensagem genérica (o detalhe fica só no log, sem dados de paciente)."""

    @app.exception_handler(RequestValidationError)
    async def _validacao(request: Request, exc: RequestValidationError) -> JSONResponse:
        mensagens = list(dict.fromkeys(mensagem_de_validacao(e) for e in exc.errors()))
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": " ".join(mensagens[:3])},
        )

    @app.exception_handler(Exception)
    async def _inesperado(request: Request, exc: Exception) -> JSONResponse:
        # Só o tipo/rota e o traceback vão para o log — nunca o corpo da
        # requisição (dados de pacientes, ver docs/ARQUITETURA.md).
        logger.exception("Erro inesperado em %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "O sistema encontrou um erro inesperado. Tente novamente em alguns instantes; "
                "se continuar, avise o suporte técnico."
            },
        )
