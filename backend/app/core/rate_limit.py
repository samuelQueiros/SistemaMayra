"""Limite de tentativas de login (proteção básica contra força bruta).

Contador em memória do próprio processo — coerente com a decisão de
arquitetura do projeto ("um único serviço", ver CLAUDE.md seção 2).
Limitação assumida conscientemente: reseta se o processo reiniciar, e não
seria compartilhado entre múltiplas instâncias caso o serviço um dia deixe
de ser único (fora do cenário atual, mas vale documentar)."""

from datetime import datetime, timedelta, timezone

MAX_TENTATIVAS = 5
JANELA = timedelta(minutes=15)

_tentativas_falhas: dict[str, list[datetime]] = {}


def _normalizar(identificador: str) -> str:
    return identificador.strip().lower()


def esta_bloqueado(identificador: str) -> bool:
    chave = _normalizar(identificador)
    agora = datetime.now(timezone.utc)
    tentativas = [t for t in _tentativas_falhas.get(chave, []) if agora - t < JANELA]
    _tentativas_falhas[chave] = tentativas
    return len(tentativas) >= MAX_TENTATIVAS


def registrar_falha(identificador: str) -> None:
    chave = _normalizar(identificador)
    agora = datetime.now(timezone.utc)
    tentativas = [t for t in _tentativas_falhas.get(chave, []) if agora - t < JANELA]
    tentativas.append(agora)
    _tentativas_falhas[chave] = tentativas


def limpar_falhas(identificador: str) -> None:
    _tentativas_falhas.pop(_normalizar(identificador), None)
