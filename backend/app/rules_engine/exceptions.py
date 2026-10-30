"""Erro do motor de regras."""


class RulesEngineError(Exception):
    """Erro de domínio do motor de regras (dados de entrada inválidos),
    distinto de um bug — deve virar um 400 na API, não um 500."""
