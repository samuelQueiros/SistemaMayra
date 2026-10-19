"""Agentes especialistas: cada um preenche uma parte do protocolo a partir
do JSON dos documentos (saída da extração), sem reler os PDFs — chamadas
só de texto, menores e em paralelo."""

from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.services.ai.agentes import limites
from app.services.ai.chains import ESTILO_DE_ESCRITA, LIMITES_DA_IA, PERSONA, _invocar_com_retentativas
from app.services.ai.provider import get_structured_model
from app.services.ai.schemas import CampoPreenchido


@dataclass(frozen=True)
class Especialista:
    nome: str
    papel: str


ANAMNESE = Especialista(
    "anamnese",
    "Você cuida da identificação complementar (responsável, escola, rotina), da anamnese "
    "(gestação, parto, complicações), do histórico de desenvolvimento, do encaminhamento e "
    "das queixas. Marcos do desenvolvimento (andou, falou, desfralde): quando o documento "
    "informar a idade, preencha o campo de anos (…Ano) e o de meses (…Mes) separadamente, "
    "com os valores das opções (ex.: '2 anos e 6 meses' → '2 anos' e '6 meses'; só '3 anos' → "
    "'3 anos' e '0 meses'; '18 meses' → '1 ano' e '6 meses'). Desfralde: preencha também a "
    "situação ('desfralde': Controle Total, Controle Diurno, Em Processo ou Escapes) sempre que "
    "o documento disser se a criança usa ou não fralda, de dia ou à noite.",
)
ESCALAS = Especialista(
    "escalas",
    "Você transcreve as escalas pontuadas (CARS, ATA, SNAP-IV, TOD, M-CHAT) item a item para "
    "os campos do catálogo, usando a pontuação/opção registrada no documento da escala. "
    "ATA: cada item (I a XXII) vale pela quantidade de caixas marcadas — nenhuma = 0, "
    "uma = 1, duas ou mais = 2 (nunca 3); o percentual do item é marcadas ÷ caixas do item.",
)
DESENVOLVIMENTO = Especialista(
    "desenvolvimento",
    "Você cuida do Portage, do perfil das funções "
    "executivas, da distribuição das dificuldades por domínio e das habilidades acadêmicas e "
    "cognitivas. Quando houver um documento do Portage, preencha TODOS os itens do catálogo que "
    "ele responde (inclusive os que não foram atingidos), sem deixar para a profissional o que o "
    "documento já traz. "
    "FUNÇÕES EXECUTIVAS (fe_perc_N e fe_manif_N, N de 0 a 5): o indicador de dificuldade é uma "
    "estimativa clínico-observacional que VOCÊ calcula — nenhum documento traz esse número pronto. "
    "Para cada uma das seis funções, avalie os comportamentos relatados nos documentos (por pais, "
    "escola e escalas) que se relacionam com ela e preencha fe_perc_N com um número inteiro de 0 a "
    "100 (0 = sem dificuldade; ~25 = leve; ~50 = moderada; ~75 = acentuada; 100 = comprometimento "
    "máximo), e fe_manif_N com 2 a 4 frases descrevendo como a dificuldade se manifesta, coerentes "
    "com o percentual e baseadas só no que os documentos relatam. Deixe em branco apenas a função "
    "sobre a qual os documentos não dizem nada. "
    "HABILIDADES ACADÊMICAS: escolha o ano escolar [anoEscolar] pelo que os documentos informam "
    "(série/ano da criança); depois, para cada habilidade da lista desse ano (veja as orientações do "
    "protocolo), preencha hab_status_N com o desempenho relatado e hab_obs_N com uma observação curta. "
    "Sem informação sobre uma habilidade, deixe-a em branco.",
)


class CamposDoEspecialista(BaseModel):
    campos: list[CampoPreenchido] = Field(
        description="Campos do catálogo que os documentos permitem preencher. Omita o que os documentos não informam."
    )
    lacunas: list[str] = Field(
        default_factory=list, description="Informações da sua parte que os documentos não trazem (para a psicóloga completar)."
    )


class EstudoDeCaso(BaseModel):
    estudo_de_caso: str = Field(description="Estudo de caso do paciente em prosa clínica.")


def _system_especialista(especialista: Especialista) -> str:
    return (
        f"{PERSONA} {especialista.papel} Você recebe os documentos do caso já "
        "transcritos em JSON (perguntas e respostas marcadas) e o CATÁLOGO dos "
        "campos da sua parte do protocolo. Preencha usando somente o id exato de "
        "cada campo e, em campos com opções, somente os valores de opção listados. "
        "Preencha apenas o que os documentos sustentam; o que faltar vai para "
        "'lacunas'. Nunca conclua um diagnóstico: hipóteses diagnósticas e "
        "encaminhamentos são escolhidos pela profissional. "
        f"{LIMITES_DA_IA}"
    )


def _cabecalho(paciente: str, observacoes: str | None) -> str:
    texto = f"Paciente: {paciente}\n"
    if observacoes and observacoes.strip():
        texto += f"Observações da profissional: {observacoes.strip()}\n"
    return texto


def preencher_campos(
    *,
    especialista: Especialista,
    provider: str,
    model: str,
    api_key: str,
    paciente: str,
    documentos_texto: str,
    catalogo_texto: str,
    observacoes: str | None = None,
) -> CamposDoEspecialista:
    chat_model = get_structured_model(provider, model, api_key, CamposDoEspecialista, limites.ESPECIALISTA)
    conteudo = (
        _cabecalho(paciente, observacoes)
        + "\nCATÁLOGO DOS CAMPOS (id · rótulo · tipo/opções):\n"
        + catalogo_texto
        + "\n\nDOCUMENTOS DO CASO (JSON):\n"
        + documentos_texto
    )
    return _invocar_com_retentativas(
        chat_model, [SystemMessage(content=_system_especialista(especialista)), HumanMessage(content=conteudo)]
    )


ESTUDO_DE_CASO_SYSTEM_PROMPT = (
    f"{PERSONA} Você redige o ESTUDO DE CASO do paciente a partir dos documentos "
    "do caso já transcritos em JSON (formulários respondidos por familiares, "
    "escola e escalas): história, queixas, gestação e desenvolvimento, rotina, "
    "comportamento, escola e o que as escalas registram. "
    f"{LIMITES_DA_IA} Escreva em português do Brasil, em tom clínico, objetivo e "
    f"respeitoso. {ESTILO_DE_ESCRITA}"
)


def redigir_estudo_de_caso(
    *, provider: str, model: str, api_key: str, paciente: str, documentos_texto: str, observacoes: str | None = None
) -> str:
    chat_model = get_structured_model(provider, model, api_key, EstudoDeCaso, limites.ESTUDO_DE_CASO)
    conteudo = _cabecalho(paciente, observacoes) + "\nDOCUMENTOS DO CASO (JSON):\n" + documentos_texto
    resultado = _invocar_com_retentativas(
        chat_model, [SystemMessage(content=ESTUDO_DE_CASO_SYSTEM_PROMPT), HumanMessage(content=conteudo)]
    )
    return resultado.estudo_de_caso


INTEGRAR_AO_ESTUDO_SYSTEM_PROMPT = (
    f"{PERSONA} Você recebe o ESTUDO DE CASO já redigido para este paciente e "
    "DADOS NOVOS confirmados pela profissional depois que ele foi escrito. "
    "Devolva o estudo de caso completo, incorporando os dados novos de forma "
    "coerente com o texto existente: mantenha a estrutura, a ordem, o tom, a "
    "terminologia e todo o conteúdo que continua válido; insira cada informação "
    "nova no trecho a que ela pertence (gestação, desenvolvimento, rotina, "
    "escola…), integrada à prosa e não como lista anexada ao fim; ajuste apenas "
    "as frases que os dados novos completam, corrigem ou tornam desatualizadas "
    "(por exemplo, algo dado como não informado). Se um dado novo já constar no "
    "texto, não o repita. Quando divergir do texto, prevalece o dado confirmado "
    "pela profissional. Não remova informações que os dados novos não contradizem "
    "e não acrescente interpretações que eles não sustentem. "
    f"{LIMITES_DA_IA} Escreva em português do Brasil. {ESTILO_DE_ESCRITA}"
)


def integrar_dados_ao_estudo_de_caso(
    *, provider: str, model: str, api_key: str, paciente: str, estudo_atual: str, dados_novos: str, observacoes: str | None = None
) -> str:
    """Atualização incremental: só o texto atual + os dados novos (sem os
    documentos do caso) — mais barata e preserva o que a IA já escreveu."""
    chat_model = get_structured_model(provider, model, api_key, EstudoDeCaso, limites.ESTUDO_DE_CASO)
    conteudo = (
        _cabecalho(paciente, observacoes)
        + "\nESTUDO DE CASO ATUAL:\n"
        + estudo_atual
        + "\n\nDADOS NOVOS CONFIRMADOS PELA PROFISSIONAL (seção — campo: resposta):\n"
        + dados_novos
    )
    resultado = _invocar_com_retentativas(
        chat_model, [SystemMessage(content=INTEGRAR_AO_ESTUDO_SYSTEM_PROMPT), HumanMessage(content=conteudo)]
    )
    return resultado.estudo_de_caso
