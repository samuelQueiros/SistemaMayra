"""Lista fixa de hipóteses diagnósticas comuns nos laudos da clínica, com o
código CID-11 correspondente (ver referencia_cliente/RELATORIO_FINAL_
ARTHUR_DANIEL__assinado.pdf). Não é uma tabela oficial completa do CID-11 —
é só um atalho para as hipóteses mais frequentes; a psicóloga pode
descrever qualquer outra hipótese como texto livre na seção de hipóteses
diagnósticas do laudo."""

CID_CODES: list[dict[str, str]] = [
    {"label": "Transtorno do Espectro Autista (TEA)", "cid": "6A02"},
    {"label": "Transtorno de Déficit de Atenção e Hiperatividade (TDAH)", "cid": "6A05"},
    {"label": "Deficiência Intelectual (DI)", "cid": "6A00"},
    {"label": "Transtorno Opositor Desafiador (TOD)", "cid": "6C90.1"},
    {"label": "Transtorno Específico de Aprendizagem", "cid": "6A03"},
    {"label": "Transtorno de Processamento Auditivo Central (TPAC)", "cid": "N/A"},
]
