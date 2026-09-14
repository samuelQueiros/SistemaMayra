import time

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.services.ai.provider import get_chat_model
from app.services.ai.schemas import ExtractedTemplateDraft, ReportSections

# Tamanho máximo do texto já redigido de cada laudo de origem, ao montar o
# resumo para o parecer consolidado. Sem isso, selecionar vários laudos com
# textos longos pode gerar um prompt grande demais e o provedor de IA falhar
# de forma intermitente (o sintoma relatado: "às vezes dá erro ao selecionar
# mais de um documento").
_TAMANHO_MAXIMO_TEXTO_POR_LAUDO = 2000

# Provedores de IA falham ocasionalmente por motivos transitórios (limite de
# taxa, instabilidade de rede, uma resposta que não bateu com o formato
# estruturado pedido) — tentar de novo antes de desistir evita boa parte dos
# erros intermitentes relatados pelo usuário, sem esconder uma falha real
# (chave inválida, provedor mal configurado) que continua sendo levantada
# normalmente após as tentativas.
_TENTATIVAS_PADRAO = 3
_ESPERA_ENTRE_TENTATIVAS_SEGUNDOS = 1.5


def _invocar_com_retentativas(chat_model: Runnable, messages: list, tentativas: int = _TENTATIVAS_PADRAO):
    ultimo_erro: Exception | None = None
    for tentativa in range(tentativas):
        try:
            return chat_model.invoke(messages)
        except Exception as exc:  # noqa: BLE001 - repassado após esgotar tentativas
            ultimo_erro = exc
            if tentativa < tentativas - 1:
                time.sleep(_ESPERA_ENTRE_TENTATIVAS_SEGUNDOS)
    assert ultimo_erro is not None
    raise ultimo_erro

# Framing pedido explicitamente pelo usuário: a IA deve responder como uma
# assistente experiente em psicologia/neuropsicopedagogia, e não como um
# assistente genérico de texto.
PERSONA = (
    "Você é uma assistente de IA com formação e experiência sólida na área "
    "de psicologia e neuropsicopedagogia clínica, especializada em apoiar "
    "profissionais na redação de laudos e pareceres técnicos. Seu objetivo é "
    "produzir o melhor documento clínico possível a partir dos dados "
    "fornecidos — claro, tecnicamente preciso e no padrão esperado por "
    "profissionais da área."
)

# Pedido explícito do usuário: o texto precisa soar como a redação de um
# profissional — técnico e ao mesmo tempo humano — nunca como uma lista de
# números narrada por um sistema, e nunca deve se referir a si mesmo como
# gerado por IA (o parecer é assinado pela profissional responsável).
ESTILO_DE_ESCRITA = (
    "Escreva em prosa corrida, no estilo de um parecer clínico redigido à "
    "mão por um profissional experiente — nunca como uma lista ou tabela "
    "narrada. Integre os números (pontuações, contagens, percentuais) "
    "naturalmente dentro das frases, como apoio à argumentação clínica, em "
    "vez de apenas enumerar 'área X: valor Y' uma atrás da outra. Use "
    "linguagem técnica e precisa, mas também humana e acolhedora — o texto "
    "fala sobre uma criança/paciente real, não é um relatório de máquina. "
    "Nunca mencione que o texto foi gerado por inteligência artificial, "
    "por um sistema, ou peça para o leitor revisar o conteúdo — isso é "
    "tratado fora do texto, pela interface do sistema."
)

SYSTEM_PROMPT = (
    f"{PERSONA} Use SOMENTE as informações fornecidas abaixo (nome da "
    "escala, respostas marcadas, pontuações calculadas e classificação) — "
    "nunca invente sintomas, comportamentos, diagnósticos ou dados que não "
    "estejam explicitamente informados. Escreva em português do Brasil, em "
    "tom clínico, objetivo e respeitoso. Não afirme um diagnóstico fechado: "
    "descreva os achados calculados e deixe claro que a interpretação final "
    "e a conduta são de responsabilidade do profissional responsável pelo "
    f"caso. {ESTILO_DE_ESCRITA}"
)

HUMAN_TEMPLATE = """Escala/modelo utilizado: {template_name}
Paciente: {patient_name}

Resultados calculados (fonte única de verdade — não use nada além disso):
{resumo}

Escreva o texto descritivo do laudo com base exclusivamente nesses dados, \
dividido em: introdução (contextualiza a avaliação), análise por área \
(descreve os achados por área/domínio a partir das pontuações) e conclusão \
(fecha o parecer com recomendações gerais, sem diagnóstico fechado)."""

_prompt = ChatPromptTemplate.from_messages(
    [("system", SYSTEM_PROMPT), ("human", HUMAN_TEMPLATE)]
)


def generate_report_text(
    *,
    provider: str,
    model: str,
    api_key: str,
    template_name: str,
    patient_name: str,
    schema: dict,
    answers: dict,
    computed: dict,
) -> ReportSections:
    resumo = _montar_resumo(schema, answers, computed)
    chat_model = get_chat_model(provider, model, api_key).with_structured_output(ReportSections)
    messages = _prompt.format_messages(
        template_name=template_name, patient_name=patient_name, resumo=resumo
    )
    return _invocar_com_retentativas(chat_model, messages)


def _montar_resumo(schema: dict, answers: dict, computed: dict) -> str:
    scores = computed.get("scores", {})
    classification = computed.get("classification")
    classifications = computed.get("classifications")

    linhas = []
    for area in schema.get("areas", []):
        area_key = area["key"]
        label = area["label"]
        score = scores.get(area_key)
        respostas_area = answers.get(area_key, {})
        respostas_texto = ", ".join(f"{k}={v}" for k, v in respostas_area.items())

        linha = f"- {label}: pontuação/contagem = {score}"
        if classifications and area_key in classifications:
            linha += f", classificação da área = {classifications[area_key]}"
        if respostas_texto:
            linha += f" (respostas: {respostas_texto})"
        linhas.append(linha)

    if classification is not None:
        linhas.append(f"\nClassificação geral: {classification}")
    total = computed.get("total")
    if total is not None:
        linhas.append(f"Pontuação total: {total}")

    return "\n".join(linhas)


CONSOLIDATED_SYSTEM_PROMPT = (
    f"{PERSONA} Você vai ler os resultados de VÁRIAS avaliações já "
    "realizadas com o mesmo paciente (escalas/modelos diferentes ou a "
    "mesma escala em datas diferentes) e produzir um ÚNICO parecer "
    "consolidado, integrando os achados de todas elas numa visão clínica "
    "coerente — apontando convergências, divergências e evolução ao longo "
    "do tempo quando houver mais de uma data. Use SOMENTE as informações "
    "fornecidas abaixo; nunca invente sintomas, comportamentos, "
    "diagnósticos ou dados que não estejam explicitamente informados. "
    "Escreva em português do Brasil, em tom clínico, objetivo e "
    "respeitoso. Não afirme um diagnóstico fechado: descreva os achados e "
    "deixe claro que a interpretação final e a conduta são de "
    f"responsabilidade do profissional responsável pelo caso. {ESTILO_DE_ESCRITA}"
)

CONSOLIDATED_HUMAN_TEMPLATE = """Paciente: {patient_name}

Avaliações consideradas nesta síntese (fonte única de verdade — não use \
nada além disso):
{resumo}

Escreva um parecer consolidado único com base exclusivamente nesses dados, \
dividido em: introdução (contextualiza que se trata de uma síntese de \
múltiplas avaliações), análise por área (integra os achados de todas as \
avaliações, destacando convergências, divergências e evolução ao longo do \
tempo quando aplicável) e conclusão (fecha o parecer com recomendações \
gerais, sem diagnóstico fechado)."""

_consolidated_prompt = ChatPromptTemplate.from_messages(
    [("system", CONSOLIDATED_SYSTEM_PROMPT), ("human", CONSOLIDATED_HUMAN_TEMPLATE)]
)


def generate_consolidated_report_text(
    *,
    provider: str,
    model: str,
    api_key: str,
    patient_name: str,
    reports: list[dict],
) -> ReportSections:
    resumo = "\n\n".join(
        f"=== Avaliação de {r['created_at'].strftime('%d/%m/%Y')} — "
        f"{r['template_name']} ===\n"
        f"{_montar_resumo(r['schema'], r['answers'], r['computed'])}"
        + (
            f"\n\nTexto já redigido para esta avaliação: {_truncar(r['generated_text'])}"
            if r.get("generated_text")
            else ""
        )
        for r in reports
    )
    chat_model = get_chat_model(provider, model, api_key).with_structured_output(ReportSections)
    messages = _consolidated_prompt.format_messages(patient_name=patient_name, resumo=resumo)
    return _invocar_com_retentativas(chat_model, messages)


def _truncar(texto: str, limite: int = _TAMANHO_MAXIMO_TEXTO_POR_LAUDO) -> str:
    if len(texto) <= limite:
        return texto
    return texto[:limite].rstrip() + "…"


TEMPLATE_EXTRACTION_SYSTEM_PROMPT = (
    f"{PERSONA} Agora sua tarefa é diferente: ler o texto de um documento "
    "que descreve uma escala/instrumento de avaliação psicológica (extraído "
    "de um PDF/DOCX enviado pela psicóloga) e estruturar essas informações "
    "no formato de cadastro de modelo de laudo do sistema. Extraia apenas o "
    "que estiver de fato no texto — nunca invente áreas, itens, pesos ou "
    "faixas de classificação que não estejam explícitos ou claramente "
    "dedutíveis do documento. Se uma informação não estiver clara, deixe o "
    "campo correspondente vazio/no valor padrão em vez de adivinhar; a "
    "psicóloga revisa e completa o resultado antes de salvar."
)

TEMPLATE_EXTRACTION_HUMAN_TEMPLATE = """Texto extraído do documento da escala:
---
{document_text}
---

Estruture esse conteúdo no formato de modelo de laudo do sistema: nome da \
escala, o tipo de regra de pontuação mais adequado (sum_threshold para \
somar pontos e comparar com faixas de classificação; count_threshold para \
contar quantos itens bateram em valores específicos, como "bastante" ou \
"demais"; age_equivalent_percentage para escalas que comparam habilidades \
atingidas com a idade cronológica), as áreas/domínios com seus campos/itens \
(tipo de resposta, mínimo/máximo ou opções, peso), e as faixas de \
classificação encontradas no documento."""

_template_extraction_prompt = ChatPromptTemplate.from_messages(
    [("system", TEMPLATE_EXTRACTION_SYSTEM_PROMPT), ("human", TEMPLATE_EXTRACTION_HUMAN_TEMPLATE)]
)


def extract_template_from_document(
    *, provider: str, model: str, api_key: str, document_text: str
) -> ExtractedTemplateDraft:
    chat_model = get_chat_model(provider, model, api_key).with_structured_output(ExtractedTemplateDraft)
    messages = _template_extraction_prompt.format_messages(document_text=document_text)
    return _invocar_com_retentativas(chat_model, messages)
