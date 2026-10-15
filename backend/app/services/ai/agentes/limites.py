"""Tempo e tamanho máximos de cada chamada dos agentes do Laudo Por IA.

Calibrados pelo tamanho das respostas: a extração de um formulário longo
(~80 perguntas) devolve poucos milhares de tokens; os especialistas, até
algumas centenas de campos. Os tetos ficam bem acima disso — servem para a
chamada nunca ficar presa, não para cortar respostas normais (nos modelos
de raciocínio, o teto inclui os tokens de raciocínio)."""

from app.services.ai.provider import LimitesDaChamada

# Transcrever não exige raciocínio longo: com GPT-5/o3 fica bem mais rápido.
EXTRACAO = LimitesDaChamada(timeout_s=240, max_tokens=24_000, raciocinio_leve=True)
ESPECIALISTA = LimitesDaChamada(timeout_s=240, max_tokens=32_000)
ESTUDO_DE_CASO = LimitesDaChamada(timeout_s=240, max_tokens=16_000)
