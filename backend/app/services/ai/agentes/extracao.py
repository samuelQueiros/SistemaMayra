"""Agente de extração: PDF → JSON. Um agente por PDF, em paralelo.

É a única etapa que lê os PDFs (a parte cara: arquivo inteiro, imagens das
páginas). O resultado fica em cache pelo conteúdo do arquivo, então reenviar
o mesmo PDF (outro laudo, importar escalas de novo) não chama a IA."""

import hashlib
import json
import re
from functools import partial
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.services.ai.agentes import limites
from app.services.ai.agentes.paralelo import em_paralelo
from app.services.ai.chains import PERSONA, _blocos_dos_pdfs, _invocar_com_retentativas
from app.services.ai.provedores import provedor
from app.services.ai.erros import cota_diaria_esgotada
from app.services.ai.provider import get_structured_model
from app.services.storage import get_form_pdfs_storage

# Mudou o prompt ou o formato? Suba a versão para não reaproveitar cache antigo.
VERSAO_DA_EXTRACAO = 1


class RespostaExtraida(BaseModel):
    pergunta: str = Field(description="Pergunta ou item, como está no PDF (sem o número, se houver).")
    resposta: str = Field(
        description=(
            "O que foi MARCADO ou escrito: a(s) opção(ões) escolhida(s), a pontuação ou o texto. "
            "Vazio quando a pergunta ficou sem resposta."
        )
    )


class DocumentoExtraido(BaseModel):
    arquivo: str = Field(default="", description="Deixe vazio (preenchido pelo sistema).")
    tipo: Literal["formulario", "cars", "ata", "snap_iv", "tod", "portage", "m_chat", "relatorio_escolar", "outro"] = Field(
        description="Tipo do documento: formulário de respostas (ex.: Google Forms), escala pontuada ou relatório."
    )
    titulo: str = Field(description="Título do formulário/escala.")
    respondente: str = Field(default="", description="Quem respondeu (ex.: mãe, professora), se o PDF disser.")
    data: str = Field(default="", description="Data do preenchimento, se houver.")
    respostas: list[RespostaExtraida] = Field(description="Todas as perguntas/itens, na ordem do PDF.")
    observacoes: str = Field(default="", description="Texto livre do PDF que não é pergunta/resposta (ex.: comentários).")


EXTRACAO_SYSTEM_PROMPT = (
    f"{PERSONA} Sua tarefa agora é só TRANSCREVER um PDF para dados "
    "estruturados — sem interpretar, resumir ou concluir nada. O PDF é um "
    "formulário respondido (geralmente Google Forms), uma escala já "
    "pontuada (CARS, ATA, SNAP-IV, TOD, Portage, M-CHAT) ou um relatório. "
    "No Google Forms a opção escolhida aparece como círculo/caixa preenchida "
    "ou destacada; as demais opções NÃO foram escolhidas e não entram na "
    "resposta. Transcreva todas as perguntas/itens, na ordem, com o que foi "
    "marcado ou escrito; pergunta sem resposta fica com resposta vazia. "
    "Nunca invente respostas."
)


def _slug(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-")[:40]


def _chave_do_cache(pdf: dict, provider: str, model: str, leitura: str) -> str:
    conteudo = hashlib.sha256(pdf["conteudo"]).hexdigest()
    return f"extracoes/{conteudo}-{_slug(provider)}-{_slug(model)}-{leitura}-v{VERSAO_DA_EXTRACAO}.json"


def _mensagens(pdf: dict, modo: str) -> list:
    instrucoes = f"Arquivo: {pdf['nome']}\nTranscreva este PDF."
    if modo == "imagens":
        instrucoes += " Cada página vem como imagem: veja nela qual opção está marcada."
    if modo == "texto":
        instrucoes += (
            " O PDF chega só como texto extraído: quando não der para saber qual opção "
            "foi marcada, deixe a resposta vazia e explique em 'observacoes'."
        )
    conteudo = [{"type": "text", "text": instrucoes}, *_blocos_dos_pdfs([pdf], modo)]
    return [SystemMessage(content=EXTRACAO_SYSTEM_PROMPT), HumanMessage(content=conteudo)]


def extrair_documento(*, provider: str, model: str, api_key: str, pdf: dict) -> DocumentoExtraido:
    info = provedor(provider)
    leitura = info.leitura_pdf if info else "nativa"
    storage = get_form_pdfs_storage()
    chave = _chave_do_cache(pdf, provider, model, leitura)
    if storage.exists(chave):
        try:
            return DocumentoExtraido.model_validate_json(storage.read(chave)).model_copy(update={"arquivo": pdf["nome"]})
        except ValueError:
            pass  # cache corrompido: extrai de novo

    chat_model = get_structured_model(provider, model, api_key, DocumentoExtraido, limites.EXTRACAO)
    if leitura != "imagens":
        documento = _invocar_com_retentativas(chat_model, _mensagens(pdf, leitura))
    else:
        try:
            documento = _invocar_com_retentativas(chat_model, _mensagens(pdf, "imagens"), tentativas=1)
        except Exception as exc:  # noqa: BLE001 - modelo sem visão: cai para só texto
            if cota_diaria_esgotada(exc):
                raise
            documento = _invocar_com_retentativas(chat_model, _mensagens(pdf, "texto"))
    documento = documento.model_copy(update={"arquivo": pdf["nome"]})
    storage.save(chave, documento.model_dump_json().encode("utf-8"))
    return documento


def extrair_documentos(*, provider: str, model: str, api_key: str, pdfs: list[dict]) -> list[DocumentoExtraido]:
    """Um agente por PDF, todos ao mesmo tempo."""
    return em_paralelo([partial(extrair_documento, provider=provider, model=model, api_key=api_key, pdf=pdf) for pdf in pdfs])


def documentos_em_texto(documentos: list[DocumentoExtraido]) -> str:
    """JSON compacto dos documentos — é o que os agentes seguintes leem."""
    dados = [d.model_dump() for d in documentos]
    for d in dados:
        d["respostas"] = [r for r in d["respostas"] if r["pergunta"] or r["resposta"]]
    return json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
