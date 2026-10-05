import base64
import re
import time

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.services.ai.provedores import provedor
from app.services.ai.provider import get_structured_model
from app.services.document_text import paginas_em_png
from app.services.ai.schemas import ConclusionAndInterventions, ExtractedTemplateDraft, RelatorioPorPdfs, ReportSections

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

# Ponto 10 da revisão de relatórios: limites explícitos do que a IA pode e
# não pode fazer, compartilhados por todos os prompts deste módulo. A IA
# pode organizar, integrar e redigir os dados fornecidos — nunca criar
# achados clínicos que não estejam nos registros.
LIMITES_DA_IA = (
    "Use SOMENTE os dados fornecidos abaixo — nunca invente sintomas, "
    "comportamentos, diagnósticos, instrumentos/escalas ou qualquer outro "
    "dado que não esteja explicitamente informado. Não infira ou afirme um "
    "diagnóstico fechado: descreva os achados e deixe claro que a "
    "interpretação final e a conduta são de responsabilidade do "
    "profissional responsável pelo caso. Nunca cite um instrumento, "
    "protocolo ou escala que não apareça nos dados fornecidos. Os "
    "percentuais/percentuais que aparecerem nos dados são descritivos e "
    "clínico-observacionais, não percentis normativos — nunca use a "
    "palavra 'percentil' ao se referir a eles. Se um dado necessário para "
    "alguma parte do texto não estiver disponível, sinalize a lacuna "
    "explicitamente (ex.: 'não há registro suficiente sobre X') em vez de "
    "preenchê-la com suposições."
)

SYSTEM_PROMPT = (
    f"{PERSONA} {LIMITES_DA_IA} Escreva em português do Brasil, em tom "
    f"clínico, objetivo e respeitoso. {ESTILO_DE_ESCRITA}"
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
    chat_model = get_structured_model(provider, model, api_key, ReportSections)
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


# Pontos 2 e 3 da revisão de relatórios: considerações finais e sugestões
# de intervenção deixam de ser texto-padrão fixo (potencialmente vinculado
# só à hipótese diagnóstica) e passam a ser compostas pela IA a partir do
# conjunto de dados individuais do paciente — usado pelo formulário
# standalone (formulario-novo-paciente.html) ao gerar o laudo.
CONCLUSION_SYSTEM_PROMPT = (
    f"{PERSONA} Sua tarefa agora é escrever DUAS seções de fechamento de um "
    "parecer neuropsicopedagógico — as \"Considerações Finais\" e as "
    "\"Sugestões De Intervenção\" — construídas a partir do conjunto de "
    "dados específicos deste paciente (estudo de caso, observações "
    f"clínicas, habilidades avaliadas, protocolos utilizados e a hipótese "
    "diagnóstica selecionada). As sugestões de intervenção devem decorrer "
    "das necessidades, dificuldades e potencialidades registradas para "
    "este paciente — nunca ser uma lista fixa que você associa apenas por "
    f"causa da hipótese diagnóstica informada. {LIMITES_DA_IA} Escreva em "
    f"português do Brasil, em tom clínico, objetivo e respeitoso. {ESTILO_DE_ESCRITA}"
)

CONCLUSION_HUMAN_TEMPLATE = """Paciente: {patient_name}

Dados registrados para este paciente (fonte única de verdade — não use \
nada além disso):
{resumo}

Escreva as "Considerações Finais" (síntese clínica de fechamento que \
integra o estudo de caso, as observações, as habilidades avaliadas, os \
protocolos utilizados e a hipótese selecionada) e as "Sugestões De \
Intervenção" (recomendações que decorrem diretamente das necessidades, \
dificuldades e potencialidades descritas acima para este paciente)."""

_conclusion_prompt = ChatPromptTemplate.from_messages(
    [("system", CONCLUSION_SYSTEM_PROMPT), ("human", CONCLUSION_HUMAN_TEMPLATE)]
)


def generate_conclusion_and_interventions(
    *,
    provider: str,
    model: str,
    api_key: str,
    patient_name: str,
    estudo_de_caso: str | None,
    observacoes_clinicas: str | None,
    habilidades_avaliadas: str | None,
    protocolos_utilizados: str | None,
    hipotese_selecionada: str | None,
) -> ConclusionAndInterventions:
    partes = []
    if estudo_de_caso:
        partes.append(f"Estudo de caso:\n{estudo_de_caso}")
    if observacoes_clinicas:
        partes.append(f"Observações clínicas:\n{observacoes_clinicas}")
    if habilidades_avaliadas:
        partes.append(f"Habilidades avaliadas:\n{habilidades_avaliadas}")
    if protocolos_utilizados:
        partes.append(f"Protocolos efetivamente utilizados e resultados:\n{protocolos_utilizados}")
    if hipotese_selecionada:
        partes.append(f"Hipótese diagnóstica selecionada para este paciente:\n{hipotese_selecionada}")
    resumo = "\n\n".join(partes) if partes else "(nenhum dado adicional registrado até o momento)"

    chat_model = get_structured_model(provider, model, api_key, ConclusionAndInterventions)
    messages = _conclusion_prompt.format_messages(patient_name=patient_name, resumo=resumo)
    return _invocar_com_retentativas(chat_model, messages)


_TAG_HTML = re.compile(r"<[^>]+>")
_ESPACOS_REPETIDOS = re.compile(r"[ \t]+")
_LINHAS_EM_BRANCO_REPETIDAS = re.compile(r"\n{3,}")


def _remover_html(texto: str) -> str:
    """O texto de laudos criados pelo formulário standalone
    (`gerarDocumentoLaudoHTML()`) é o HTML inteiro do laudo, não texto
    corrido — mandar isso direto pra IA (ponto 10 da revisão) arrisca
    truncar no meio de uma tag e passar markup quebrado como se fosse
    conteúdo clínico. Extrai só o texto visível antes de truncar/enviar."""
    sem_tags = _TAG_HTML.sub(" ", texto)
    sem_espacos = _ESPACOS_REPETIDOS.sub(" ", sem_tags)
    return _LINHAS_EM_BRANCO_REPETIDAS.sub("\n\n", sem_espacos).strip()


def _truncar(texto: str, limite: int = _TAMANHO_MAXIMO_TEXTO_POR_LAUDO) -> str:
    texto = _remover_html(texto)
    if len(texto) <= limite:
        return texto
    return texto[:limite].rstrip() + "…"


FORM_PDFS_SYSTEM_PROMPT = (
    f"{PERSONA} Você vai receber de 1 a 6 PDFs com as RESPOSTAS de "
    "formulários (geralmente exportados do Google Forms) preenchidos por "
    "familiares, cuidadores, professores ou pelo próprio paciente. Leia com "
    "atenção cada pergunta e a opção efetivamente MARCADA — no PDF do Google "
    "Forms a opção escolhida aparece como círculo/caixa preenchida ou "
    "destacada; as demais opções listadas NÃO foram escolhidas. Organize o "
    "relatório por ÁREA/TEMA clínico, cruzando o que os formulários dizem "
    "sobre cada área e indicando as fontes. Gráficos só com valores "
    "efetivamente contados ou somados a partir das respostas marcadas, "
    "dizendo a régua usada; sem dados em escala, não há gráfico. "
    f"{LIMITES_DA_IA} Escreva em português do Brasil, em tom clínico, "
    f"objetivo e respeitoso. {ESTILO_DE_ESCRITA}"
)

# Texto extraído de cada PDF vai junto como apoio (ajuda em PDFs digitais),
# limitado para não estourar o prompt com 6 arquivos.
_TAMANHO_MAXIMO_TEXTO_POR_PDF = 12000


def generate_report_from_form_pdfs(
    *,
    provider: str,
    model: str,
    api_key: str,
    patient_name: str,
    idade: str | None,
    pdfs: list[dict],
    observacoes: str | None = None,
) -> RelatorioPorPdfs:
    """Gera o relatório por área/tema a partir dos PDFs de respostas. Cada
    item de `pdfs` tem `nome`, `conteudo` (bytes) e `texto` (extraído). A
    forma de entregar os PDFs depende do provedor (`provedores.py`): inteiros
    (bloco `file`), como imagens das páginas, ou só o texto — porque a opção
    marcada no Google Forms costuma ser só um desenho, que o texto extraído
    não mostra. Se o modelo recusar as imagens (modelo sem visão), tenta de
    novo só com o texto."""

    info = provedor(provider)
    leitura = info.leitura_pdf if info else "nativa"
    messages = _mensagens_dos_pdfs(patient_name, idade, pdfs, observacoes, leitura)
    chat_model = get_structured_model(provider, model, api_key, RelatorioPorPdfs)
    if leitura != "imagens":
        return _invocar_com_retentativas(chat_model, messages)
    try:
        return _invocar_com_retentativas(chat_model, messages, tentativas=1)
    except Exception:  # noqa: BLE001 - modelo sem visão: cai para só texto
        texto = _mensagens_dos_pdfs(patient_name, idade, pdfs, observacoes, "texto")
        return _invocar_com_retentativas(chat_model, texto)


def _mensagens_dos_pdfs(patient_name, idade, pdfs, observacoes, leitura) -> list:
    instrucoes = (
        f"Paciente: {patient_name}" + (f" ({idade})" if idade else "") + "\n"
        f"Formulários anexados ({len(pdfs)}): " + ", ".join(p["nome"] for p in pdfs) + "\n"
    )
    if observacoes and observacoes.strip():
        instrucoes += f"Observações da profissional para esta análise: {observacoes.strip()}\n"
    instrucoes += (
        "\nLeia os PDFs a seguir (fonte única de verdade) e produza o relatório "
        "estruturado: formulários lidos, metodologia, análise por área/tema com "
        "fontes e gráficos quando houver dados em escala, considerações finais e "
        "sugestões de intervenção."
    )
    if leitura == "imagens":
        instrucoes += " Cada página dos PDFs vem como imagem: veja nela qual opção está marcada."
    if leitura == "texto":
        instrucoes += (
            " Os PDFs chegam só como texto extraído: se não for possível saber qual "
            "opção foi marcada numa pergunta, diga isso no relatório em vez de supor."
        )
    conteudo: list[dict] = [{"type": "text", "text": instrucoes}]
    for pdf in pdfs:
        conteudo.append({"type": "text", "text": f"=== Arquivo: {pdf['nome']} ==="})
        if leitura == "nativa":
            conteudo.append(
                {
                    "type": "file",
                    "base64": base64.b64encode(pdf["conteudo"]).decode("ascii"),
                    "mime_type": "application/pdf",
                    "filename": pdf["nome"],
                }
            )
        elif leitura == "imagens":
            for numero, png in enumerate(paginas_em_png(pdf["conteudo"]), start=1):
                conteudo.append({"type": "text", "text": f"Página {numero}:"})
                conteudo.append({"type": "image", "base64": base64.b64encode(png).decode("ascii"), "mime_type": "image/png"})
        if pdf.get("texto", "").strip():
            rotulo = (
                "Texto extraído deste PDF:\n"
                if leitura == "texto"
                else "Texto extraído deste PDF (apoio — a opção marcada pode não aparecer aqui):\n"
            )
            conteudo.append({"type": "text", "text": rotulo + _truncar(pdf["texto"], _TAMANHO_MAXIMO_TEXTO_POR_PDF)})
    return [SystemMessage(content=FORM_PDFS_SYSTEM_PROMPT), HumanMessage(content=conteudo)]


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
    chat_model = get_structured_model(provider, model, api_key, ExtractedTemplateDraft)
    messages = _template_extraction_prompt.format_messages(document_text=document_text)
    return _invocar_com_retentativas(chat_model, messages)
