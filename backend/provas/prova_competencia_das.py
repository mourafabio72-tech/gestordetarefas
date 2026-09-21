"""
prova_competencia_das.py: o e-validador lê a competência do DAS.

O DAS do Simples escreve o período de apuração só com mês e ano: "Período de
Apuração: Agosto/2026" ou "PA 08/2026". A leitura da DARF (data completa,
prova_competencia_darf.py) não pega isso, e os dois DAS subidos em Modelos
ficaram com a competência em branco (produção, 2026-09-19). Mesma decisão (a)
do usuário: sem período de/a, a competência vem do período de apuração.

Os itens 5 a 7 são não-regressão e passam JÁ no RED.

    python provas/prova_competencia_das.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.services.validador import extrair_dados        # noqa: E402

TOTAL = 10
falhou = []


def checa(n, descricao, condicao):
    if condicao:
        print(f"  ok  {n:>3}. {descricao}")
    else:
        print(f"FALHA  {n:>3}. {descricao}")
        falhou.append(n)


def comp(texto):
    return extrair_dados(texto)["competencia"]


c = comp("Documento de Arrecadação do Simples Nacional\nPeríodo de Apuração\nAgosto/2026\nVencimento 20/09/2026")
checa(1, f"'Período de Apuração Agosto/2026' dá 08/2026: {c}", c == "08/2026")
c = comp("Período de Apuração: MARÇO/2026")
checa(2, f"mês em caixa alta e com acento dá 03/2026: {c}", c == "03/2026")
c = comp("PERIODO DE APURACAO: 08/2026")
checa(3, f"'08/2026' depois do rótulo dá 08/2026: {c}", c == "08/2026")
c = comp("Período de apuração dezembro de 2025")
checa(4, f"'dezembro de 2025' dá 12/2025: {c}", c == "12/2025")
c = comp("Período de Apuração 31/03/2026")
checa(5, f"não-regressão, DARF com data completa continua 03/2026: {c}", c == "03/2026")
c = comp("RECIBO 01/01/2025 a 31/12/2025\nPeríodo de apuração: Agosto/2026")
checa(6, f"não-regressão, de/a continua vencendo: {c}", c == "01/2025")
c = comp("Vencimento 20/09/2026\nAgosto/2026 foi um mês difícil")
checa(7, f"mês/ano solto, sem o rótulo, não vira competência: {c}", c is None)

# 8 e 9. Layout REAL do DAS gerado pelo PGDAS-D (conferido em 2026-09-21 no PDF
# da Trops, aqui com CNPJ, número e valores fictícios): "Período de Apuração" é
# cabeçalho de tabela, e o valor "agosto/2026" vem linhas depois, depois do
# vencimento e do número do documento. Datas dd/mm/aaaa no caminho não contam.
DAS_REAL = (
    "Documento de Arrecadação\ndo Simples Nacional\n \n11.222.333/0001-81 EMPRESA FICTICIA LTDA\n"
    "Período de Apuração Data de Vencimento Número do Documento\n"
    "07.20.00000.0000000-0 Pagar este documento até\n21/09/2026Observações\n"
    "Valor Total do Documento\n1.000,00\nCNPJ Razão Social\nagosto/2026 21/09/2026\n"
    "Código PrincipalDenominação TotalMulta Juros\n1001 IRPJ - SIMPLES NACIONAL 100,00 100,00\n08/2026\n")
c = comp(DAS_REAL)
checa(8, f"layout real do DAS dá 08/2026, e não o vencimento 09/2026: {c}", c == "08/2026")
c = comp(DAS_REAL.replace("agosto/2026", "dezembro/2025"))
checa(9, f"o mesmo layout em dezembro dá 12/2025: {c}", c == "12/2025")

# 10. A DARF nova da Receita tem o MESMO layout (conferido em 2026-09-21 em
# DARFs reais de CSLL 2372 trimestral e IPI 5123): a trimestral diz "Março/2026",
# o ÚLTIMO mês, e é isso que a regra trimestral de guia espera (decisão b).
DARF_TRI = DAS_REAL.replace("do Simples Nacional", "de Receitas Federais").replace(
    "agosto/2026", "Março/2026") + "2372 CSLL - DEMAIS\nPA:1º Trimestre/2026\n"
c = comp(DARF_TRI)
checa(10, f"DARF trimestral no layout de tabela dá 03/2026: {c}", c == "03/2026")

print()
if falhou:
    print(f"PROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print(f"PROVA OK: {TOTAL} checagens verdes")
