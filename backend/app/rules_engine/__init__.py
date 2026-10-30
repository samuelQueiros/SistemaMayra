"""Motor de regras dos modelos configuráveis (legado): a pontuação vem de um `schema_json`. O protocolo
fixo e os modelos próprios não passam por aqui: o motor devolve `{}` para `custom_form` e `protocolo`, e a
pontuação sai do navegador."""

from app.rules_engine.engine import calculate_report
from app.rules_engine.exceptions import RulesEngineError

__all__ = ["calculate_report", "RulesEngineError"]
