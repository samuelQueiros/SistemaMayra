"""Classificação de limites do provedor, inclusive erros encapsulados pelo SDK."""


def cota_diaria_esgotada(erro: Exception) -> bool:
    texto = str(erro).lower()
    limite = "429" in texto or "resource_exhausted" in texto
    diario = any(marca in texto for marca in ("perday", "per_day", "per day", "daily quota"))
    return limite and diario
