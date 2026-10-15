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
    "das queixas, das hipóteses diagnósticas investigadas e dos encaminhamentos.",
)
ESCALAS = Especialista(
    "escalas",
    "Você transcreve as escalas pontuadas (CARS, ATA, SNAP-IV, TOD, M-CHAT) item a item para "
    "os campos do catálogo, usando a pontuação/opção registrada no documento da escala.",
)
DESENVOLVIMENTO = Especialista(
    "desenvolvimento",
    "Você cuida do Portage (itens da faixa etária do paciente), das habilidades acadêmicas do "
    "ano escolar, do perfil das funções executivas e da distribuição das dificuldades por domínio.",
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
        "'lacunas'. Hipóteses diagnósticas só podem ser marcadas quando os "
        "documentos as mencionarem — nunca conclua um diagnóstico. "
        "Para os encaminhamentos (campos enc_*), analise as necessidades sustentadas "
        "pelos documentos e selecione um ou mais encaminhamentos pertinentes dentre "
        "as opções do catálogo, marcando 'sim'. Eles são sugestões para revisão da "
        "profissional, não diagnósticos nem encaminhamentos já realizados. Não invente "
        "opções e não marque todos indiscriminadamente; se não houver evidência "
        "suficiente, informe a lacuna em vez de selecionar sem fundamento. "
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
