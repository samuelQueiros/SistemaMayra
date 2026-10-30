"""Limite de tentativas de login (proteção básica contra força bruta).

Contador em memória do próprio processo — coerente com a decisão de
arquitetura do projeto ("um único serviço", ver docs/ARQUITETURA.md).
Limitação assumida conscientemente: reseta se o processo reiniciar, e não é
compartilhado entre processos — com WEB_CONCURRENCY=2 (padrão da imagem
Docker), cada processo conta à parte, então no pior caso o bloqueio vem
depois de até 2x MAX_TENTATIVAS falhas."""

from datetime import datetime, timedelta, timezone

MAX_TENTATIVAS = 5
# Por IP (várias contas tentadas do mesmo lugar): mais folga, mesmo período.
MAX_TENTATIVAS_POR_IP = 20
# Teto de chaves guardadas em memória (evita crescer sem limite).
_MAXIMO_DE_CHAVES = 10_000
JANELA = timedelta(minutes=15)

_tentativas_falhas: dict[str, list[datetime]] = {}


def _normalizar(identificador: str) -> str:
    return identificador.strip().lower()


def esta_bloqueado(identificador: str, maximo: int = MAX_TENTATIVAS) -> bool:
    """Verdadeiro se o identificador (e-mail ou IP) já falhou `maximo` vezes nos últimos 15 minutos."""
    chave = _normalizar(identificador)
    agora = datetime.now(timezone.utc)
    tentativas = [t for t in _tentativas_falhas.get(chave, []) if agora - t < JANELA]
    if tentativas:
        _tentativas_falhas[chave] = tentativas
    else:
        _tentativas_falhas.pop(chave, None)
    return len(tentativas) >= maximo


def registrar_falha(identificador: str) -> None:
    """Conta uma tentativa de login que falhou."""
    chave = _normalizar(identificador)
    agora = datetime.now(timezone.utc)
    tentativas = [t for t in _tentativas_falhas.get(chave, []) if agora - t < JANELA]
    tentativas.append(agora)
    if len(_tentativas_falhas) >= _MAXIMO_DE_CHAVES and chave not in _tentativas_falhas:
        _tentativas_falhas.pop(next(iter(_tentativas_falhas)))
    _tentativas_falhas[chave] = tentativas


def limpar_falhas(identificador: str) -> None:
    """Zera as falhas do identificador depois de um login correto."""
    _tentativas_falhas.pop(_normalizar(identificador), None)
