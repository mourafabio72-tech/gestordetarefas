"""Validações de integridade reutilizáveis."""
import re


def cnpj_valido(cnpj: str) -> bool:
    """Valida CNPJ pelos dígitos verificadores (aceita com ou sem máscara)."""
    c = re.sub(r"\D", "", cnpj or "")
    if len(c) != 14 or len(set(c)) == 1:
        return False

    def _dv(base: str, pesos: list) -> str:
        s = sum(int(d) * p for d, p in zip(base, pesos))
        r = s % 11
        return "0" if r < 2 else str(11 - r)

    p1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    p2 = [6] + p1
    d1 = _dv(c[:12], p1)
    d2 = _dv(c[:12] + d1, p2)
    return c[12] == d1 and c[13] == d2
