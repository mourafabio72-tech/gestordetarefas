"""
prova_tipo_documento.py — guia a pagar x comprovante de pagamento.

O par que mais erra, e erra em silêncio: um DARF em branco é GUIA — documento a
pagar, que o escritório entrega ao cliente. O MESMO DARF com autenticação
bancária é COMPROVANTE — prova de que foi pago, que o cliente devolve. São
papéis opostos no fluxo, e a versão anterior chamava os dois de comprovante só
porque a palavra "DARF" aparecia no texto.

    python provas/prova_tipo_documento.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.services.validador import classificar_tipo   # noqa: E402

ok = True
def checa(nome, cond, extra=""):
    global ok
    print(("  ok   " if cond else "FALHA  ") + nome + (f"  {extra}" if extra else ""))
    ok = ok and bool(cond)


def tipo(t):
    return classificar_tipo(t)


print("\n1. O mesmo DARF, dois papéis — é a marca de PAGAMENTO que separa")
darf = "DARF Documento de Arrecadacao de Receitas Federais Codigo da Receita 0220"
checa("DARF em branco é guia", tipo(darf) == "guia", tipo(darf))
checa("DARF com autenticação bancária é comprovante",
      tipo(darf + " Autenticacao Bancaria 0123456789") == "comprovante_pagamento")
checa("e com data de pagamento também",
      tipo(darf + " Data do Pagamento 20/08/2026") == "comprovante_pagamento")
checa("o texto 'comprovante de pagamento' decide sozinho",
      tipo("Comprovante de Pagamento") == "comprovante_pagamento")

print("\n2. As guias que o escritório manda")
for t, nome in [("DAS Simples Nacional linha digitavel", "DAS"),
                ("DARJ Documento de Arrecadacao do Rio de Janeiro", "DARJ"),
                ("GPS Guia da Previdencia Social", "GPS"),
                ("GNRE Guia Nacional de Recolhimento", "GNRE"),
                ("DAE Documento de Arrecadacao Estadual", "DAE"),
                ("Guia de Recolhimento do FGTS", "guia de recolhimento"),
                ("Boleto bancario codigo de barras", "boleto")]:
    checa(f"{nome} é guia", tipo(t) == "guia", tipo(t))

print("\n3. 'das' é preposição — a armadilha do português")
# Foi esta prova que pegou: com \bdas\b na lista de siglas, "apuração das
# contas" virava guia. Todo relatório contábil tem "das" no meio.
checa("'das' no meio de frase não vira guia",
      tipo("relatorio de apuracao das contas do mes") == "relatorio",
      tipo("relatorio de apuracao das contas do mes"))
checa("nem em 'demonstrativo das receitas'",
      tipo("demonstrativo das receitas e das despesas") == "relatorio")
checa("mas DAS perto de Simples é a guia mesmo",
      tipo("DAS Simples Nacional vencimento 20/09") == "guia")
checa("na ordem inversa também",
      tipo("Simples Nacional - DAS - codigo 1234") == "guia")
checa("'dae' dentro de outra palavra idem",
      tipo("memoria de calculo cidadae") != "guia")

print("\n4. Os outros tipos continuam de pé")
checa("recibo de entrega", tipo("Recibo de Entrega da EFD-Contribuicoes") == "recibo_entrega")
checa("recibo de transmissão idem", tipo("Recibo de Transmissao do arquivo") == "recibo_entrega")
checa("relatório", tipo("Balancete Analitico") == "relatorio")
checa("memória de cálculo é relatório",
      tipo("MEMORIA DE CALCULO Apuracao do IRPJ e CSLL") == "relatorio")
checa("o que não se reconhece fica em 'outro'", tipo("bla bla bla") == "outro")
checa("texto vazio não quebra", tipo("") == "outro" and tipo(None) == "outro")

print("\n5. Acento e caixa não mudam a resposta")
checa("com acento e maiúscula",
      tipo("DOCUMENTO DE ARRECADAÇÃO — GUIA DE RECOLHIMENTO") == "guia")

print("\n" + ("TUDO VERDE" if ok else "VERMELHO") + "\n")
sys.exit(0 if ok else 1)
