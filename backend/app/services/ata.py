"""Pontuação da ATA calculada pelo sistema a partir das caixas marcadas.

A IA só transcreve o PDF (quantas caixas de cada item estão marcadas — ver
`RespostaExtraida.marcadas`); a regra da escala fica aqui, igual para todo
laudo:

- nota do item: nenhuma caixa = 0, uma = 1, duas ou mais = 2 (nunca 3);
- % do item (tabela do relatório): caixas marcadas ÷ caixas do item;
- % de características: pontos ÷ 44 (22 itens × 2 pontos).

Os campos devolvidos são os do formulário (`ata_item_N`, `ata_perc_N`,
`ata`, `ataPercentual`)."""

import re
import unicodedata

from app.services.ai.agentes.extracao import DocumentoExtraido, RespostaExtraida

# Caixas de cada item (I a XXII) no formulário da ATA usado pela clínica.
OPCOES_POR_ITEM = (7, 6, 4, 3, 4, 6, 4, 5, 8, 4, 4, 7, 5, 5, 5, 8, 4, 4, 2, 6, 8, 3)
NOTA_MAXIMA_DO_ITEM = 2
PONTOS_MAXIMOS = NOTA_MAXIMA_DO_ITEM * len(OPCOES_POR_ITEM)

# Trecho do título que identifica cada item (sem acento, minúsculo) — a IA
# às vezes tira o número romano da pergunta.
_TITULOS = (
    "interacao social",
    "manipulacao do ambiente",
    "utilizacao das pessoas",
    "resistencia a mudancas",
    "ordem rigida",
    "contato visual",
    "mimica",
    "sono",
    "alimentacao",
    "esfincteres",
    "exploracao dos objetos",
    "uso inapropriado",
    "falta de atencao",
    "aprendizagem",
    "iniciativa",
    "linguagem e comunicacao",
    "habilidades e conhecimentos",
    "frustracao",
    "responsabilidade",
    "hiperatividade",
    "estereotipad",
    "perigo",
)
_ROMANOS = {"I": 1, "V": 5, "X": 10, "L": 50}
_NUMERO_ROMANO = re.compile(r"^\s*([IVXL]+)\s*[.\-–)]")


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def _romano_para_int(romano: str) -> int:
    total = 0
    for atual, seguinte in zip(romano, romano[1:] + " "):
        valor = _ROMANOS[atual]
        total += -valor if seguinte in _ROMANOS and _ROMANOS[seguinte] > valor else valor
    return total


def indice_do_item(pergunta: str) -> int | None:
    """Posição (0 a 21) do item da ATA pela pergunta transcrita."""
    numero = _NUMERO_ROMANO.match(pergunta.upper())
    if numero:
        posicao = _romano_para_int(numero.group(1)) - 1
        if 0 <= posicao < len(OPCOES_POR_ITEM):
            return posicao
    texto = _sem_acento(pergunta)
    return next((i for i, titulo in enumerate(_TITULOS) if titulo in texto), None)


def caixas_marcadas(resposta: RespostaExtraida) -> int:
    if resposta.marcadas is not None:
        return resposta.marcadas
    # Extrações antigas (sem a contagem): uma opção por trecho separado.
    return len([parte for parte in re.split(r"\s*(?:;|\n|\|)\s*", resposta.resposta.strip()) if parte])


def nota_do_item(marcadas: int) -> int:
    return min(max(marcadas, 0), NOTA_MAXIMA_DO_ITEM)


def percentual_do_item(marcadas: int, opcoes: int) -> int:
    return min(100, round(100 * max(marcadas, 0) / opcoes)) if opcoes else 0


def percentual_total(pontos: int) -> int:
    return min(100, round(100 * pontos / PONTOS_MAXIMOS))


def pontuar_ata(documentos: list[DocumentoExtraido]) -> dict[str, str]:
    """Campos da ATA calculados a partir dos PDFs da escala (vazio se não houver)."""
    marcadas_por_item: dict[int, int] = {}
    for documento in documentos:
        if documento.tipo != "ata":
            continue
        for resposta in documento.respostas:
            indice = indice_do_item(resposta.pergunta)
            if indice is not None and indice not in marcadas_por_item:
                marcadas_por_item[indice] = caixas_marcadas(resposta)
    if not marcadas_por_item:
        return {}

    answers: dict[str, str] = {}
    for indice, marcadas in marcadas_por_item.items():
        answers[f"ata_item_{indice}"] = str(nota_do_item(marcadas))
        answers[f"ata_perc_{indice}"] = str(percentual_do_item(marcadas, OPCOES_POR_ITEM[indice]))
    if len(marcadas_por_item) == len(OPCOES_POR_ITEM):
        pontos = sum(nota_do_item(m) for m in marcadas_por_item.values())
        answers["ata"] = str(pontos)
        answers["ataPercentual"] = str(percentual_total(pontos))
    return answers
