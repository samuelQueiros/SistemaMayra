"""Laudo Por IA: catálogo do protocolo fixo e validação da resposta da IA.

O catálogo vem do próprio formulário (`catalogoParaIA()` em
frontend/public/formulario-novo-paciente.html): a lista de campos que a IA
pode preencher, com tipo e opções. Assim o formulário continua sendo a única
fonte da verdade (itens da CARS, ATA, SNAP-IV, Portage da faixa etária...).
Aqui o catálogo vira texto para o prompt e serve de régua para descartar
qualquer campo ou valor que a IA invente."""

import time
from dataclasses import dataclass, field
from functools import partial
from typing import Literal

from pydantic import BaseModel, Field

from app.services.ai.agentes import (
    ANAMNESE,
    DESENVOLVIMENTO,
    ESCALAS,
    DocumentoExtraido,
    Especialista,
    documentos_em_texto,
    em_paralelo,
    extrair_documentos,
    preencher_campos,
    redigir_estudo_de_caso,
)
from app.services.ai.schemas import ProtocoloPorIA

MAXIMO_DE_CAMPOS = 3000
TAMANHO_MAXIMO_TEXTO = 8000


class OpcaoDoCatalogo(BaseModel):
    valor: str = Field(max_length=200)
    rotulo: str = Field(default="", max_length=1500)  # opções da CARS trazem a descrição clínica do grau


class CampoDoCatalogo(BaseModel):
    id: str = Field(max_length=120, pattern=r"^[A-Za-z0-9_\-]+$")
    secao: str = Field(default="", max_length=200)
    grupo: str = Field(default="", max_length=200)
    rotulo: str = Field(default="", max_length=1500)
    tipo: Literal["texto", "numero", "opcao", "marcar"]
    opcoes: list[OpcaoDoCatalogo] = Field(default_factory=list, max_length=60)
    min: float | None = None
    max: float | None = None


class CatalogoDoProtocolo(BaseModel):
    campos: list[CampoDoCatalogo] = Field(max_length=MAXIMO_DE_CAMPOS)
    # Orientações extras do formulário (ex.: lista de habilidades por ano escolar).
    contexto: str = Field(default="", max_length=20000)


def formatar_catalogo(catalogo: CatalogoDoProtocolo) -> str:
    """Catálogo em texto compacto, agrupado por seção e grupo."""
    linhas: list[str] = []
    secao_atual = grupo_atual = None
    for campo in catalogo.campos:
        if campo.secao != secao_atual:
            secao_atual, grupo_atual = campo.secao, None
            linhas.append(f"\n## {campo.secao or 'Outros'}")
        if campo.grupo and campo.grupo != grupo_atual:
            grupo_atual = campo.grupo
            linhas.append(f"### {campo.grupo}")
        if campo.tipo == "opcao":
            opcoes = " | ".join(
                o.valor if not o.rotulo or o.rotulo == o.valor else f"{o.valor}={o.rotulo}" for o in campo.opcoes
            )
            descricao = f"opções: {opcoes}"
        elif campo.tipo == "numero":
            faixa = f" ({campo.min:g} a {campo.max:g})" if campo.min is not None and campo.max is not None else ""
            descricao = f"número{faixa}"
        elif campo.tipo == "marcar":
            descricao = "marcar: sim/não"
        else:
            descricao = "texto livre"
        linhas.append(f"- [{campo.id}] {campo.rotulo} · {descricao}")
    if catalogo.contexto.strip():
        linhas.append("\n## Orientações do protocolo\n" + catalogo.contexto.strip())
    return "\n".join(linhas).strip()


def _numero(valor: str) -> float | None:
    try:
        return float(valor.strip().replace("%", "").replace(",", "."))
    except ValueError:
        return None


def _normalizar(texto: str) -> str:
    return " ".join(texto.lower().split())


def respostas_para_answers(protocolo: ProtocoloPorIA, catalogo: CatalogoDoProtocolo) -> tuple[dict, list[str]]:
    """Converte a resposta da IA no `answers_json` do formulário (chaves =
    ids dos campos, mesmo formato de `coletarDados()`). Campos fora do
    catálogo ou com valor inválido são descartados e devolvidos à parte."""
    por_id = {c.id: c for c in catalogo.campos}
    answers: dict = {}
    descartados: list[str] = []

    for item in protocolo.campos:
        campo = por_id.get(item.id)
        valor = (item.valor or "").strip()
        if campo is None or not valor:
            descartados.append(item.id)
            continue
        if campo.tipo == "opcao":
            escolhida = next((o.valor for o in campo.opcoes if o.valor == valor), None)
            if escolhida is None:  # a IA às vezes devolve o rótulo da opção
                escolhida = next((o.valor for o in campo.opcoes if _normalizar(o.rotulo) == _normalizar(valor)), None)
            if escolhida is None:
                descartados.append(item.id)
                continue
            answers[campo.id] = escolhida
        elif campo.tipo == "numero":
            numero = _numero(valor)
            if numero is None or (campo.min is not None and numero < campo.min) or (campo.max is not None and numero > campo.max):
                descartados.append(item.id)
                continue
            answers[campo.id] = f"{numero:g}"
        elif campo.tipo == "marcar":
            answers[campo.id] = _normalizar(valor) in {"sim", "s", "true", "x", "marcado", "verdadeiro"}
        else:
            answers[campo.id] = valor[:TAMANHO_MAXIMO_TEXTO]

    if protocolo.estudo_de_caso.strip():
        answers["estudoCaso"] = protocolo.estudo_de_caso.strip()[: TAMANHO_MAXIMO_TEXTO * 2]
    return answers, descartados


# Qual especialista cuida de cada seção do formulário (pelo título da seção;
# o resto fica com a anamnese).
SECOES_POR_ESPECIALISTA: dict[str, tuple[str, ...]] = {
    ESCALAS.nome: ("ATA E CARS", "Protocolo TOD", "SNAP-IV", "M-CHAT"),
    DESENVOLVIMENTO.nome: ("Portage", "Habilidades Acadêmicas", "Funções Executivas", "Por Domínio"),
}
ESPECIALISTAS: tuple[Especialista, ...] = (ANAMNESE, ESCALAS, DESENVOLVIMENTO)


def dividir_catalogo(catalogo: CatalogoDoProtocolo) -> dict[str, CatalogoDoProtocolo]:
    """Parte do catálogo de cada especialista (só os que têm campos)."""
    partes: dict[str, list[CampoDoCatalogo]] = {e.nome: [] for e in ESPECIALISTAS}
    for campo in catalogo.campos:
        dono = next(
            (nome for nome, secoes in SECOES_POR_ESPECIALISTA.items() if any(s.lower() in campo.secao.lower() for s in secoes)),
            ANAMNESE.nome,
        )
        partes[dono].append(campo)
    return {nome: CatalogoDoProtocolo(campos=campos, contexto=catalogo.contexto) for nome, campos in partes.items() if campos}


@dataclass
class ResultadoDaIA:
    protocolo: ProtocoloPorIA
    documentos: list[DocumentoExtraido]
    tempos: dict[str, float] = field(default_factory=dict)


def preencher_protocolo(
    *,
    provider: str,
    model: str,
    api_key: str,
    paciente: str,
    pdfs: list[dict],
    catalogo: CatalogoDoProtocolo,
    observacoes: str | None = None,
    com_estudo_de_caso: bool = True,
) -> ResultadoDaIA:
    """Laudo Por IA em duas etapas paralelas:
    1. um agente por PDF transcreve o arquivo em JSON (com cache);
    2. sobre esse JSON, ao mesmo tempo, o redator escreve o estudo de caso e
       cada especialista preenche a sua parte do catálogo."""
    credenciais = {"provider": provider, "model": model, "api_key": api_key}
    inicio = time.monotonic()
    documentos = extrair_documentos(pdfs=pdfs, **credenciais)
    fim_da_extracao = time.monotonic()

    texto = documentos_em_texto(documentos)
    partes = dividir_catalogo(catalogo)
    especialistas = [e for e in ESPECIALISTAS if e.nome in partes]
    tarefas = [
        partial(
            preencher_campos,
            especialista=e,
            paciente=paciente,
            documentos_texto=texto,
            catalogo_texto=formatar_catalogo(partes[e.nome]),
            observacoes=observacoes,
            **credenciais,
        )
        for e in especialistas
    ]
    if com_estudo_de_caso:
        tarefas.append(partial(redigir_estudo_de_caso, paciente=paciente, documentos_texto=texto, observacoes=observacoes, **credenciais))
    resultados = em_paralelo(tarefas)

    estudo = resultados.pop() if com_estudo_de_caso else ""
    campos = [c for r in resultados for c in r.campos]
    lacunas = [lacuna for r in resultados for lacuna in r.lacunas]
    return ResultadoDaIA(
        protocolo=ProtocoloPorIA(estudo_de_caso=estudo, campos=campos, lacunas=lacunas),
        documentos=documentos,
        tempos={
            "extracao_s": round(fim_da_extracao - inicio, 1),
            "especialistas_s": round(time.monotonic() - fim_da_extracao, 1),
        },
    )
