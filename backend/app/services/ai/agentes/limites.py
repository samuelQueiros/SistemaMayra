"""Tempo e tamanho máximos de cada chamada dos agentes do Laudo Por IA.

Calibrados pelo tamanho das respostas: a extração de um formulário longo
(~80 perguntas) devolve poucos milhares de tokens; os especialistas, até
algumas centenas de campos. Os tetos ficam bem acima disso — servem para a
chamada nunca ficar presa, não para cortar respostas normais (nos modelos
de raciocínio, o teto inclui os tokens de raciocínio)."""

from app.services.ai.provider import LimitesDaChamada

# Raciocínio leve em todos os agentes: transcrever, mapear respostas para o
# catálogo e redigir a partir de dados já estruturados não exige raciocínio
# longo. Com o padrão dos modelos que "pensam" (Gemini 3 no nível "high",
# GPT-5 no "medium"), cada agente levava minutos.
EXTRACAO = LimitesDaChamada(timeout_s=240, max_tokens=24_000, raciocinio_leve=True)
ESPECIALISTA = LimitesDaChamada(timeout_s=240, max_tokens=32_000, raciocinio_leve=True)
ESTUDO_DE_CASO = LimitesDaChamada(timeout_s=240, max_tokens=16_000, raciocinio_leve=True)
# Leitura de uma foto/documento anexado: só os campos que faltam.
ANEXO = LimitesDaChamada(timeout_s=180, max_tokens=8_000, raciocinio_leve=True)
