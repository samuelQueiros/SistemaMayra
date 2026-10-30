from app.services.ai.agentes import DocumentoExtraido
from app.services.ai.agentes.extracao import RespostaExtraida
from app.services.ata import (
    OPCOES_POR_ITEM,
    indice_do_item,
    nota_do_item,
    percentual_do_item,
    percentual_total,
    pontuar_ata,
)

TITULOS = [
    "I. DIFICULDADE NA INTERAÇÃO SOCIAL",
    "II. MANIPULAÇÃO DO AMBIENTE",
    "III. UTILIZAÇÃO DAS PESSOAS A SEU REDOR",
    "IV. RESISTÊNCIA A MUDANÇAS",
    "V. BUSCA DE UMA ORDEM RÍGIDA",
    "VI. FALTA DE CONTATO VISUAL. OLHAR INDEFINIDO",
    "VII. MÍMICA INEXPRESSIVA",
    "VIII. DISTÚRBIOS DE SONO",
    "IX. ALTERAÇÃO NA ALIMENTAÇÃO",
    "X. DIFICULDADE NO CONTROLE DOS ESFÍNCTERES",
    "XI. EXPLORAÇÃO DOS OBJETOS (APALPAR, CHUPAR)",
    "XII. USO INAPROPRIADO DOS OBJETOS.",
    "XIII. FALTA DE ATENÇÃO",
    "XIV. AUSÊNCIA DE INTERESSE PELA APRENDIZAGEM",
    "XV. FALTA DE INICIATIVA",
    "XVI. ALTERAÇÃO DE LINGUAGEM E COMUNICAÇÃO",
    "XVII. NÃO MANIFESTA HABILIDADES E CONHECIMENTOS",
    "XVIII. REAÇÕES INAPROPRIADAS ANTE A FRUSTRAÇÃO",
    "XIX. NÃO ASSUME RESPONSABILIDADES",
    "XX. HIPERATIVIDADE/ HIPOATIVIDADE",
    "XXI. MOVIMENTOS ESTEREOTIPADOS E REPETITIVOS",
    "XXII. IGNORA O PERIGO",
]
# Marcações de um formulário real (anonimizado): uma caixa por item, duas no XVIII.
MARCADAS = [1] * 22
MARCADAS[17] = 2


def _documento(titulos=TITULOS, marcadas=MARCADAS, tipo="ata") -> DocumentoExtraido:
    respostas = [RespostaExtraida(pergunta="Nome da Criança", resposta="Criança Teste")]
    respostas += [
        RespostaExtraida(pergunta=t, resposta="; ".join(["opção"] * m), marcadas=m, opcoes=OPCOES_POR_ITEM[i])
        for i, (t, m) in enumerate(zip(titulos, marcadas))
    ]
    return DocumentoExtraido(tipo=tipo, titulo="ATA", respostas=respostas)


def test_regra_de_pontuacao_do_item():
    assert [nota_do_item(n) for n in range(6)] == [0, 1, 2, 2, 2, 2]  # nunca 3
    assert percentual_do_item(1, 7) == 14
    assert percentual_do_item(2, 4) == 50
    assert percentual_do_item(9, 4) == 100
    assert percentual_total(23) == 52
    assert percentual_total(44) == 100


def test_identifica_o_item_pelo_numero_romano_ou_pelo_titulo():
    assert [indice_do_item(t) for t in TITULOS] == list(range(22))
    # A IA às vezes tira o número romano.
    assert indice_do_item("Ausência de interesse pela aprendizagem") == 13
    assert indice_do_item("XIX NÃO ASSUME RESPONSABILIDADES") == 18
    assert indice_do_item("Nome da Mãe") is None
    assert indice_do_item("Isolamento intenso.") is None


def test_pontua_o_formulario_da_ata():
    answers = pontuar_ata([_documento()])
    assert answers["ata"] == "23"
    assert answers["ataPercentual"] == "52"
    assert answers["ata_item_0"] == "1" and answers["ata_perc_0"] == "14"  # 1 de 7
    assert answers["ata_item_17"] == "2" and answers["ata_perc_17"] == "50"  # 2 de 4
    assert answers["ata_perc_18"] == "50"  # 1 de 2
    assert all(answers[f"ata_item_{i}"] in {"0", "1", "2"} for i in range(22))


def test_tres_ou_mais_caixas_valem_dois():
    marcadas = [0] * 22
    marcadas[0] = 5
    answers = pontuar_ata([_documento(marcadas=marcadas)])
    assert answers["ata_item_0"] == "2" and answers["ata_perc_0"] == "71"
    assert answers["ata_item_1"] == "0" and answers["ata_perc_1"] == "0"
    assert answers["ata"] == "2"


def test_sem_contagem_conta_as_opcoes_da_resposta():
    """Extrações antigas (sem 'marcadas'): conta as opções separadas por ';'."""
    documento = DocumentoExtraido(
        tipo="ata",
        titulo="ATA",
        respostas=[
            RespostaExtraida(pergunta="XVIII. REAÇÕES ANTE A FRUSTRAÇÃO", resposta="c. Desgostoso; d. Reações de birra")
        ],
    )
    answers = pontuar_ata([documento])
    assert answers == {"ata_item_17": "2", "ata_perc_17": "50"}  # sem os 22 itens, sem total


def test_ignora_documentos_que_nao_sao_da_ata():
    assert pontuar_ata([_documento(tipo="formulario")]) == {}
