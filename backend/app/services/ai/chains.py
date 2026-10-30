"""Prompts e chamadas de IA. `PERSONA`, `LIMITES_DA_IA` e `ESTILO_DE_ESCRITA` são compartilhados por todos os
prompts: a IA escreve como profissional da área, usa só os dados fornecidos, não fecha diagnóstico, não usa
a palavra "percentil" e nunca diz que o texto foi gerado por IA. Repetições só acontecem para erros passageiros
(limite de taxa, instabilidade); chave inválida ou documento grande demais falham na hora."""

import base64
import re
import time

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.services.ai.provider import get_structured_model
from app.services.ai.erros import cota_diaria_esgotada
from app.services.document_text import paginas_em_png
from app.services.ai.schemas import (
    ConclusionAndInterventions,
    ExtractedTemplateDraft,
    RelatorioPorPdfs,
    ReportSections,
)

# Tamanho máximo do texto já redigido de cada laudo de origem, ao montar o
# resumo para o parecer consolidado. Sem isso, selecionar vários laudos com
# textos longos pode gerar um prompt grande demais e o provedor de IA falhar
# de forma intermitente (o sintoma relatado: "às vezes dá erro ao selecionar
# mais de um documento").
_TAMANHO_MAXIMO_TEXTO_POR_LAUDO = 2000

# Provedores de IA falham ocasionalmente por motivos transitórios (limite de
# taxa, instabilidade de rede, uma resposta que não bateu com o formato
# estruturado pedido) — tentar de novo resolve boa parte deles. Erros que não
# se resolvem tentando de novo (chave inválida, modelo inexistente, documento
# grande demais para o modelo) falham na hora, sem fazer a psicóloga esperar.
_TENTATIVAS_PADRAO = 3
_ESPERA_ENTRE_TENTATIVAS_SEGUNDOS = 2.0
# Limite de tokens por minuto: o provedor diz quanto esperar ("try again in
# 8s" / retry-after); antes esperávamos 1,5 s e batíamos no limite de novo.
_ESPERA_MAXIMA_LIMITE_DE_TAXA_SEGUNDOS = 60.0
# Uma chamada que estourou o tempo-limite provavelmente estoura de novo:
# só mais uma tentativa.
_MAXIMO_DE_TEMPOS_ESGOTADOS = 2
_STATUS_DEFINITIVOS = {400, 401, 403, 404, 413, 422}


def status_http_do_erro(exc: Exception) -> int | None:
    """Status HTTP do erro do provedor (atributo do SDK ou texto da mensagem)."""
    for atributo in ("status_code", "code"):
        valor = getattr(exc, atributo, None)
        if isinstance(valor, int) and 100 <= valor < 600:
            return valor
    valor = getattr(getattr(exc, "response", None), "status_code", None)
    if isinstance(valor, int):
        return valor
    achado = re.search(r"(?:error code|status code|status)[:= ]*(\d{3})\b|^(\d{3}) [A-Z_]{4,}", str(exc), re.IGNORECASE)
    return int(achado.group(1) or achado.group(2)) if achado else None


def tempo_esgotado(exc: Exception) -> bool:
    """Verdadeiro se o erro é de tempo esgotado na chamada ao provedor."""
    nomes = " ".join(type(e).__name__.lower() for e in (exc, exc.__cause__) if e is not None)
    return "timeout" in nomes or "timed out" in str(exc).lower() or status_http_do_erro(exc) in (408, 504)


def _espera_pedida(exc: Exception) -> float | None:
    cabecalhos = getattr(getattr(exc, "response", None), "headers", None) or {}
    try:
        if cabecalhos.get("retry-after"):
            return float(cabecalhos["retry-after"])
    except (TypeError, ValueError):
        pass
    achado = re.search(r"(?:try again|retry) in ([\d.]+)\s*(ms|s)", str(exc), re.IGNORECASE)
    if achado:
        valor = float(achado.group(1))
        return valor / 1000 if achado.group(2).lower() == "ms" else valor
    return None


def _invocar_com_retentativas(chat_model: Runnable, messages: list, tentativas: int = _TENTATIVAS_PADRAO):
    tempos_esgotados = 0
    for tentativa in range(tentativas):
        try:
            return chat_model.invoke(messages)
        except Exception as exc:  # noqa: BLE001 - repassado quando não vale tentar de novo
            if cota_diaria_esgotada(exc):
                raise  # A cota diária não se recupera esperando alguns segundos.
            status_http = status_http_do_erro(exc)
            if status_http in _STATUS_DEFINITIVOS:
                raise
            if tempo_esgotado(exc):
                tempos_esgotados += 1
                if tempos_esgotados >= _MAXIMO_DE_TEMPOS_ESGOTADOS:
                    raise
            if tentativa == tentativas - 1:
                raise
            espera = _ESPERA_ENTRE_TENTATIVAS_SEGUNDOS * (2**tentativa)
            if status_http == 429:
                espera = min(max(_espera_pedida(exc) or espera, 1.0) + 1.0, _ESPERA_MAXIMA_LIMITE_DE_TAXA_SEGUNDOS)
            time.sleep(espera)


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

# Prompt legado do texto do parecer (modelos do motor de regras). Limites: só os dados fornecidos, sem
# diagnóstico fechado, sem "percentil", sem citar escala que não esteja nos dados.
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

_prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("human", HUMAN_TEMPLATE)])


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
    """Legado: texto do parecer a partir da pontuação do motor de regras."""
    resumo = _montar_resumo(schema, answers, computed)
    chat_model = get_structured_model(provider, model, api_key, ReportSections)
    messages = _prompt.format_messages(template_name=template_name, patient_name=patient_name, resumo=resumo)
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
# Considerações Finais e Sugestões de Intervenção. Objetivo: sugestões que decorrem do que foi registrado
# para este paciente, nunca uma lista fixa associada só à hipótese. Mesmos limites de LIMITES_DA_IA.
CONCLUSION_SYSTEM_PROMPT = (
    f"{PERSONA} Sua tarefa agora é escrever DUAS seções de fechamento de um "
    'parecer neuropsicopedagógico — as "Considerações Finais" e as '
    '"Sugestões De Intervenção" — construídas a partir do conjunto de '
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
    """Escreve Considerações Finais e Sugestões de Intervenção a partir dos dados do paciente."""
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


# Relatório por IA a partir de PDFs (fluxo anterior ao Laudo por IA). Objetivo: organizar por área clínica,
# citando as fontes. Limite: gráficos só com valores contados ou somados das respostas marcadas, dizendo a
# régua usada; sem dados em escala, não há gráfico.
FORM_PDFS_SYSTEM_PROMPT = (
    f"{PERSONA} Você vai receber as RESPOSTAS de 1 a 6 formulários "
    "(geralmente Google Forms) preenchidos por familiares, cuidadores, "
    "professores ou pelo próprio paciente, já transcritas em JSON a partir "
    "dos PDFs: cada pergunta com a opção efetivamente marcada ou o texto "
    "escrito (resposta vazia = não respondida). Organize o relatório por "
    "ÁREA/TEMA clínico, cruzando o que os formulários dizem sobre cada área "
    "e indicando as fontes. Gráficos só com valores efetivamente contados ou "
    "somados a partir das respostas marcadas, dizendo a régua usada; sem "
    "dados em escala, não há gráfico. "
    f"{LIMITES_DA_IA} Escreva em português do Brasil, em tom clínico, "
    f"objetivo e respeitoso. {ESTILO_DE_ESCRITA}"
)

# Texto extraído de cada PDF vai junto como apoio na extração (ajuda em PDFs
# digitais), limitado para não estourar o prompt.
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
    item de `pdfs` tem `nome`, `conteudo` (bytes) e `texto` (extraído).
    Primeiro um agente por PDF transcreve o arquivo em JSON (em paralelo e
    com cache — `agentes/extracao.py`); depois o relatório é escrito só a
    partir desse JSON, sem reenviar os PDFs."""
    # Import local: o pacote de agentes reaproveita funções deste módulo.
    from app.services.ai.agentes.extracao import documentos_em_texto, extrair_documentos

    documentos = extrair_documentos(provider=provider, model=model, api_key=api_key, pdfs=pdfs)
    chat_model = get_structured_model(provider, model, api_key, RelatorioPorPdfs)
    return _invocar_com_retentativas(
        chat_model, _mensagens_dos_formularios(patient_name, idade, pdfs, documentos_em_texto(documentos), observacoes)
    )


def _mensagens_dos_formularios(patient_name, idade, pdfs, documentos_texto, observacoes) -> list:
    instrucoes = (
        f"Paciente: {patient_name}" + (f" ({idade})" if idade else "") + "\n"
        f"Formulários anexados ({len(pdfs)}): " + ", ".join(p["nome"] for p in pdfs) + "\n"
    )
    if observacoes and observacoes.strip():
        instrucoes += f"Observações da profissional para esta análise: {observacoes.strip()}\n"
    instrucoes += (
        "\nCom base nos formulários abaixo (fonte única de verdade), produza o "
        "relatório estruturado: formulários lidos, metodologia, análise por "
        "área/tema com fontes e gráficos quando houver dados em escala, "
        "considerações finais e sugestões de intervenção.\n\nFORMULÁRIOS (JSON):\n" + documentos_texto
    )
    return [SystemMessage(content=FORM_PDFS_SYSTEM_PROMPT), HumanMessage(content=instrucoes)]


def _blocos_dos_pdfs(pdfs: list[dict], leitura: str) -> list[dict]:
    """Conteúdo multimodal com os PDFs, no formato que o provedor aceita
    (`leitura`: nativa, imagens ou texto), mais o texto extraído de apoio."""
    conteudo: list[dict] = []
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
                conteudo.append(
                    {"type": "image", "base64": base64.b64encode(png).decode("ascii"), "mime_type": "image/png"}
                )
        if pdf.get("texto", "").strip():
            rotulo = (
                "Texto extraído deste PDF:\n"
                if leitura == "texto"
                else "Texto extraído deste PDF (apoio — a opção marcada pode não aparecer aqui):\n"
            )
            conteudo.append({"type": "text", "text": rotulo + _truncar(pdf["texto"], _TAMANHO_MAXIMO_TEXTO_POR_PDF)})
    return conteudo


# Importação de modelo: lê o texto de um documento que descreve uma escala e propõe o `schema_json`.
# É só um rascunho, a psicóloga revisa antes de salvar.
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
    """Extrai um rascunho de modelo (`schema_json`) de um documento que descreve uma escala."""
    chat_model = get_structured_model(provider, model, api_key, ExtractedTemplateDraft)
    messages = _template_extraction_prompt.format_messages(document_text=document_text)
    return _invocar_com_retentativas(chat_model, messages)
