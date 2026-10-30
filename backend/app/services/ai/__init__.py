"""Camada de IA: chamadas ao provedor configurado (via LangChain), agentes do Laudo por IA e escolha da
chave. Nenhuma chamada de IA parte do navegador; a chave nunca sai do servidor."""

from app.services.ai.chains import (
    extract_template_from_document,
    generate_conclusion_and_interventions,
    generate_report_from_form_pdfs,
    generate_report_text,
)
from app.services.ai.exceptions import AIConfigurationError
from app.services.ai.resolver import resolve_ai_credentials

__all__ = [
    "generate_report_text",
    "generate_conclusion_and_interventions",
    "generate_report_from_form_pdfs",
    "extract_template_from_document",
    "AIConfigurationError",
    "resolve_ai_credentials",
]
