"""Agente que lê uma foto/documento anexado (ficha preenchida à mão,
caderneta, relatório escolar, laudo anterior) e sugere valores só para os
campos que ainda faltam no laudo. As sugestões são validadas contra o
catálogo e só entram no laudo depois da psicóloga confirmar."""

import base64

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.services.ai.agentes import limites
from app.services.ai.agentes.extracao import ErroNaEtapaDaIA
from app.services.ai.chains import LIMITES_DA_IA, PERSONA, _invocar_com_retentativas
from app.services.ai.provedores import provedor
from app.services.ai.provider import get_structured_model


# Valor que a IA leu num anexo para um campo do catálogo, com o trecho que o justifica.
class CampoSugerido(BaseModel):
    id: str = Field(description="Id exato do campo no catálogo.")
    valor: str = Field(description="Valor lido no documento (em campos com opções, um dos valores listados).")
    trecho: str = Field(default="", description="O que está escrito no documento que sustenta o valor (curto).")


# Saída do agente que lê um anexo (foto ou documento) e sugere valores para campos pendentes.
class LeituraDoAnexo(BaseModel):
    campos: list[CampoSugerido] = Field(
        description="Só os campos do catálogo que o documento responde com clareza. Omita o resto."
    )


ANEXO_SYSTEM_PROMPT = (
    f"{PERSONA} Você recebe a foto ou o PDF de um documento do caso (ficha "
    "preenchida à mão, caderneta de saúde, relatório escolar, laudo anterior) e "
    "a lista dos campos do protocolo que ainda estão sem resposta. Leia o "
    "documento e preencha somente os campos que ele responde com clareza, usando "
    "o id exato de cada campo e, em campos com opções, somente os valores "
    "listados. Em 'trecho', copie em poucas palavras o que está escrito e "
    f"sustenta o valor. Letra ilegível ou dúvida: não preencha. {LIMITES_DA_IA}"
)


def ler_anexo(
    *, provider: str, model: str, api_key: str, imagens: list[bytes], nome: str, catalogo_texto: str
) -> LeituraDoAnexo:
    """Lê um anexo e sugere valores só para os campos pendentes informados. Nada vai para o laudo sem a
    psicóloga confirmar."""
    info = provedor(provider)
    if info is not None and info.leitura_pdf == "texto":
        raise ErroNaEtapaDaIA(
            "O modelo de IA configurado não lê imagens. Escolha um modelo com visão em "
            "Configurações → Inteligência Artificial ou preencha os campos digitando."
        )
    conteudo: list[dict] = [
        {
            "type": "text",
            "text": f"Documento: {nome}\n\nCAMPOS SEM RESPOSTA (id · rótulo · tipo/opções):\n{catalogo_texto}",
        }
    ]
    for numero, imagem in enumerate(imagens, start=1):
        if len(imagens) > 1:
            conteudo.append({"type": "text", "text": f"Página {numero}:"})
        conteudo.append(
            {"type": "image", "base64": base64.b64encode(imagem).decode("ascii"), "mime_type": "image/jpeg"}
        )
    chat_model = get_structured_model(provider, model, api_key, LeituraDoAnexo, limites.ANEXO)
    return _invocar_com_retentativas(
        chat_model, [SystemMessage(content=ANEXO_SYSTEM_PROMPT), HumanMessage(content=conteudo)]
    )
