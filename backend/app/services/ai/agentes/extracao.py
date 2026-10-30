"""Agente de extração: PDF → JSON. Um agente por PDF, em paralelo.

É a única etapa que lê os PDFs (a parte cara: arquivo inteiro, imagens das
páginas). O resultado fica em cache pelo conteúdo do arquivo, então reenviar
o mesmo PDF (outro laudo, importar escalas de novo) não chama a IA."""

import hashlib
import json
import re
from collections.abc import Callable
from functools import partial
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.services.ai.agentes import limites
from app.services.ai.agentes.paralelo import em_paralelo
from app.services.ai.chains import (
    PERSONA,
    _blocos_dos_pdfs,
    _invocar_com_retentativas,
    status_http_do_erro,
    tempo_esgotado,
)
from app.services.ai.provedores import provedor
from app.services.ai.erros import cota_diaria_esgotada
from app.services.ai.provider import get_structured_model
from app.services.storage import get_form_pdfs_storage

# Mudou o prompt ou o formato? Suba a versão para não reaproveitar cache antigo.
VERSAO_DA_EXTRACAO = 2

# PDFs lidos ao mesmo tempo. Cada um passa de 10 mil tokens: com todos de uma
# vez, 3 ou mais PDFs estouravam o limite de tokens por minuto da conta do
# provedor (erro 429) e a geração falhava.
MAXIMO_DE_LEITURAS_SIMULTANEAS = 3

# Avisos de andamento para a tela: ao_progredir(evento, **dados).
AoProgredir = Callable[..., None]


def sem_aviso(*_args, **_kwargs) -> None:
    """Aviso de andamento que não faz nada (usado quando ninguém acompanha a geração)."""
    pass


class ErroNaEtapaDaIA(Exception):
    """Falha de uma etapa do Laudo Por IA com mensagem pronta para a tela."""


def motivo_do_erro(exc: Exception) -> str:
    """Motivo curto, em português, de uma falha do provedor de IA."""
    status_http = status_http_do_erro(exc)
    if tempo_esgotado(exc):
        return "o provedor de IA demorou demais para responder"
    if status_http == 429:
        return "limite de uso por minuto do provedor de IA atingido"
    if status_http in (400, 413):
        return "o documento é grande demais ou não é aceito pelo modelo configurado"
    if status_http in (401, 403):
        return "a chave de API foi recusada pelo provedor"
    if status_http == 404:
        return "o modelo configurado não foi encontrado no provedor"
    if status_http is not None and status_http >= 500:
        return "o provedor de IA está instável no momento"
    if "connection" in type(exc).__name__.lower():
        return "não foi possível conectar ao provedor de IA"
    return "erro inesperado do provedor de IA"


class ErroNaLeituraDosDocumentos(ErroNaEtapaDaIA):
    """Um ou mais PDFs não puderam ser lidos; guarda cada falha com o nome do arquivo."""

    def __init__(self, falhas: list[tuple[str, Exception]], lidos: int):
        self.falhas = falhas
        self.lidos = lidos
        nomes = "; ".join(f"'{nome}' ({motivo_do_erro(erro)})" for nome, erro in falhas)
        mensagem = f"Não foi possível ler {nomes}."
        if lidos == 1:
            mensagem += " O outro documento já foi lido e não será lido de novo ao tentar outra vez."
        elif lidos > 1:
            mensagem += f" Os outros {lidos} documentos já foram lidos e não serão lidos de novo ao tentar outra vez."
        super().__init__(mensagem)


# Uma pergunta do PDF com a resposta marcada ou escrita (vazia se não respondida).
class RespostaExtraida(BaseModel):
    pergunta: str = Field(description="Pergunta ou item, como está no PDF (sem o número, se houver).")
    resposta: str = Field(
        description=(
            "O que foi MARCADO ou escrito: a(s) opção(ões) escolhida(s), a pontuação ou o texto. "
            "Vazio quando a pergunta ficou sem resposta."
        )
    )
    # Perguntas de caixas de seleção ("marque todas que se aplicam", como os
    # itens da ATA): a pontuação é calculada pelo sistema a partir da contagem.
    marcadas: int | None = Field(
        default=None,
        ge=0,
        le=60,
        description="Caixas de seleção: quantas caixas estão marcadas. Vazio nas demais perguntas.",
    )
    opcoes: int | None = Field(
        default=None,
        ge=0,
        le=60,
        description="Caixas de seleção: quantas caixas existem na pergunta. Vazio nas demais perguntas.",
    )


# PDF transcrito: tipo (formulário ou escala), quem respondeu e todas as perguntas com respostas.
class DocumentoExtraido(BaseModel):
    arquivo: str = Field(default="", description="Deixe vazio (preenchido pelo sistema).")
    tipo: Literal["formulario", "cars", "ata", "snap_iv", "tod", "portage", "m_chat", "relatorio_escolar", "outro"] = (
        Field(
            description="Tipo do documento: formulário de respostas (ex.: Google Forms), escala pontuada ou relatório."
        )
    )
    titulo: str = Field(description="Título do formulário/escala.")
    respondente: str = Field(default="", description="Quem respondeu (ex.: mãe, professora), se o PDF disser.")
    data: str = Field(default="", description="Data do preenchimento, se houver.")
    respostas: list[RespostaExtraida] = Field(description="Todas as perguntas/itens, na ordem do PDF.")
    observacoes: str = Field(
        default="", description="Texto livre do PDF que não é pergunta/resposta (ex.: comentários)."
    )


EXTRACAO_SYSTEM_PROMPT = (
    f"{PERSONA} Sua tarefa agora é só TRANSCREVER um PDF para dados "
    "estruturados — sem interpretar, resumir ou concluir nada. O PDF é um "
    "formulário respondido (geralmente Google Forms), uma escala já "
    "pontuada (CARS, ATA, SNAP-IV, TOD, Portage, M-CHAT) ou um relatório. "
    "No Google Forms a opção escolhida aparece como círculo/caixa preenchida "
    "ou destacada; as demais opções NÃO foram escolhidas e não entram na "
    "resposta. Transcreva todas as perguntas/itens, na ordem, com o que foi "
    "marcado ou escrito; pergunta sem resposta fica com resposta vazia. "
    "Em perguntas de caixas de seleção (várias opções podem ser marcadas, como "
    "os itens I a XXII da ATA), cada item é UMA pergunta: na pergunta, o título "
    "do item com o número romano (ex.: 'I. DIFICULDADE NA INTERAÇÃO SOCIAL'); na "
    "resposta, as opções marcadas separadas por ';'; em 'marcadas', quantas caixas "
    "estão marcadas (0 se nenhuma); em 'opcoes', quantas caixas existem. "
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
    """Transcreve um PDF para `DocumentoExtraido`, sem interpretar. Usa o resultado em cache quando o mesmo
    arquivo já foi lido (`VERSAO_DA_EXTRACAO` invalida o cache)."""
    info = provedor(provider)
    leitura = info.leitura_pdf if info else "nativa"
    storage = get_form_pdfs_storage()
    chave = _chave_do_cache(pdf, provider, model, leitura)
    if storage.exists(chave):
        try:
            return DocumentoExtraido.model_validate_json(storage.read(chave)).model_copy(
                update={"arquivo": pdf["nome"]}
            )
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


def extrair_documentos(
    *, provider: str, model: str, api_key: str, pdfs: list[dict], ao_progredir: AoProgredir | None = None
) -> list[DocumentoExtraido]:
    """Um agente por PDF, até MAXIMO_DE_LEITURAS_SIMULTANEAS ao mesmo tempo.
    Cada PDF é independente: os que deram certo ficam no cache e a mensagem
    de erro diz quais falharam."""
    avisar = ao_progredir or sem_aviso
    total = len(pdfs)

    def ler(indice: int, pdf: dict) -> DocumentoExtraido | Exception:
        avisar("lendo_documento", indice=indice, total=total, nome=pdf["nome"])
        try:
            documento = extrair_documento(provider=provider, model=model, api_key=api_key, pdf=pdf)
        except Exception as exc:  # noqa: BLE001 - reunido abaixo, com o nome do arquivo
            avisar("documento_com_erro", indice=indice, total=total, nome=pdf["nome"], motivo=motivo_do_erro(exc))
            return exc
        avisar("documento_lido", indice=indice, total=total, nome=pdf["nome"])
        return documento

    resultados = em_paralelo(
        [partial(ler, indice, pdf) for indice, pdf in enumerate(pdfs, start=1)], maximo=MAXIMO_DE_LEITURAS_SIMULTANEAS
    )
    falhas = [(pdf["nome"], r) for pdf, r in zip(pdfs, resultados) if isinstance(r, Exception)]
    for _, erro in falhas:
        if cota_diaria_esgotada(erro):
            raise erro  # mensagem própria de cota na rota
    if falhas:
        raise ErroNaLeituraDosDocumentos(falhas, lidos=total - len(falhas))
    return resultados


def documentos_em_texto(documentos: list[DocumentoExtraido]) -> str:
    """JSON compacto dos documentos — é o que os agentes seguintes leem."""
    dados = [d.model_dump() for d in documentos]
    for d in dados:
        d["respostas"] = [r for r in d["respostas"] if r["pergunta"] or r["resposta"]]
    return json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
