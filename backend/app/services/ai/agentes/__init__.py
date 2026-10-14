"""Agentes de IA com tarefas pequenas, rodando em paralelo.

1. Extração (`extracao.py`): cada PDF vira JSON (perguntas e respostas
   marcadas), um agente por PDF, com cache pelo conteúdo do arquivo.
2. Especialistas (`especialistas.py`): trabalham só sobre o JSON — nunca
   releem os PDFs — cada um com a sua parte do protocolo.

A orquestração do Laudo Por IA fica em `app/services/laudo_ia.py`."""

from app.services.ai.agentes.especialistas import (
    ANAMNESE,
    DESENVOLVIMENTO,
    ESCALAS,
    CamposDoEspecialista,
    Especialista,
    preencher_campos,
    redigir_estudo_de_caso,
)
from app.services.ai.agentes.extracao import DocumentoExtraido, documentos_em_texto, extrair_documentos
from app.services.ai.agentes.paralelo import em_paralelo

__all__ = [
    "ANAMNESE",
    "DESENVOLVIMENTO",
    "ESCALAS",
    "CamposDoEspecialista",
    "DocumentoExtraido",
    "Especialista",
    "documentos_em_texto",
    "em_paralelo",
    "extrair_documentos",
    "preencher_campos",
    "redigir_estudo_de_caso",
]
