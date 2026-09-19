"""
prova_competencia_darf.py: o e-validador lê a competência da DARF.

O e-validador só lia competência de período "01/05/2026 a 31/05/2026", que é o
que o RECIBO traz. A DARF traz "Período de Apuração 31/03/2026", uma data só,
e ela é o ÚLTIMO dia do período. Em produção, todos os modelos de guia estavam
com a competência em branco (LOG de 2026-09-19). Decisão (a) do usuário: sem
período de/a, a competência é o mês da data de apuração.

Os itens 4 e 5 são não-regressão e passam JÁ no RED: recibo com de/a continua
lendo o início, mesmo que traga também uma data de apuração.

    python provas/prova_competencia_darf.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.services.validador import extrair_dados        # noqa: E402

TOTAL = 6
falhou = []


def checa(n, descricao, condicao):
    if condicao:
        print(f"  ok  {n:>3}. {descricao}")
    else:
        print(f"FALHA  {n:>3}. {descricao}")
        falhou.append(n)


def comp(texto):
    return extrair_dados(texto)["competencia"]


# 1. DARF com rótulo e data na mesma linha
c = comp("Documento de Arrecadação de Receitas Federais\nPeríodo de Apuração 31/03/2026\nCódigo 2089")
checa(1, f"'Período de Apuração 31/03/2026' dá 03/2026: {c}", c == "03/2026")

# 2. rótulo numa linha e a data na seguinte, com dois-pontos, sem acento
c = comp("PERIODO DE APURACAO:\n31/05/2026\nVALOR 1.234,56")
checa(2, f"rótulo e data em linhas separadas dá 05/2026: {c}", c == "05/2026")

# 3. DARF de dezembro não vira o ano seguinte
c = comp("Período de apuração 31/12/2025")
checa(3, f"31/12/2025 dá 12/2025: {c}", c == "12/2025")

# 4. não-regressão: recibo com período de/a continua lendo o início
c = comp("RECIBO\nPeríodo 01/01/2025 a 31/12/2025")
checa(4, f"recibo de/a continua dando 01/2025: {c}", c == "01/2025")

# 5. não-regressão: com os dois no texto, o de/a vence
c = comp("Período de apuração 31/03/2026\nescrituração de 01/01/2026 a 31/03/2026")
checa(5, f"com de/a e data de apuração, o de/a vence: {c}", c == "01/2026")

# 6. data solta que NÃO é de apuração não vira competência (vencimento, emissão)
c = comp("Data de vencimento 30/04/2026\nEmitido em 15/04/2026")
checa(6, f"vencimento e emissão não viram competência: {c}", c is None)

print()
if falhou:
    print(f"PROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print(f"PROVA OK: {TOTAL} checagens verdes")
