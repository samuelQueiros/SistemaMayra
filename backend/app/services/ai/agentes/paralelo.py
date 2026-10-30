"""Execução em paralelo das chamadas ao provedor de IA."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

T = TypeVar("T")

# Chamadas simultâneas ao provedor por pedido (limites de taxa dos provedores).
MAXIMO_EM_PARALELO = 6


def em_paralelo(tarefas: list[Callable[[], T]], maximo: int = MAXIMO_EM_PARALELO) -> list[T]:
    """Executa as tarefas em paralelo (chamadas de rede ao provedor de IA) e
    devolve os resultados na mesma ordem. Um erro em qualquer tarefa é
    repassado depois que as demais terminam."""
    if len(tarefas) <= 1:
        return [tarefa() for tarefa in tarefas]
    with ThreadPoolExecutor(max_workers=min(maximo, len(tarefas))) as executor:
        futuros = [executor.submit(tarefa) for tarefa in tarefas]
        return [futuro.result() for futuro in futuros]
