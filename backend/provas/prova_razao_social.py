"""
prova_razao_social.py — a razão social escrita igual nos dois lados.

O mesmo algoritmo existe no backend (mensagem ao cliente) e no frontend (telas).
Esta prova roda os dois nos MESMOS casos e compara: sem isso, uma correção num
lado passaria despercebida no outro, e o cliente veria o nome de um jeito na
tela e de outro no WhatsApp.

    python provas/prova_razao_social.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.services.razao_social import formatar   # noqa: E402

ok = True
def checa(nome, cond, extra=""):
    global ok
    print(("  ok   " if cond else "FALHA  ") + nome + (f"  {extra}" if extra else ""))
    ok = ok and bool(cond)


CASOS = [
    ("Mark Building Gerenc. Predial Ltda.", "Mark Building Gerenc. Predial Ltda."),
    ("RIO BRAVO COM. DE ARMAS MUNIÇÕES E ACESS. LTDA", "Rio Bravo Com. de Armas Munições e Acess. Ltda"),
    ("TROPS CENTRO DE ESP. E LAZER LTDA-ME", "Trops Centro de Esp. e Lazer Ltda-ME"),
    ("MKB PARTICIPACOES LTDA", "MKB Participacoes Ltda"),
    ("IWC COMERCIO LTDA", "IWC Comercio Ltda"),
    ("RIO NEGRO TRANSPORTES", "Rio Negro Transportes"),
    ("CW ADMINISTRA LTDA", "CW Administra Ltda"),
    ("BPS4 OUTSOURCING LTDA", "BPS4 Outsourcing Ltda"),
    ("DE PAULA E FILHOS LTDA", "De Paula e Filhos Ltda"),
    ("CASA DAS TINTAS DO NORTE", "Casa das Tintas do Norte"),
    ("COMERCIAL XPTO S/A", "Comercial Xpto S.A."),
    ("PADARIA CENTRAL EIRELI", "Padaria Central Eireli"),
    ("GRAFICA SOL LTDA-EPP", "Grafica Sol Ltda-EPP"),
    ("IND. E COM. DE PECAS", "Ind. e Com. de Pecas"),
    ("  Alpha   Serviços Ltda  ", "Alpha Serviços Ltda"),
    ("", ""),
]

print("\n1. O backend escreve como se espera")
for entrada, esperado in CASOS:
    checa(f"{entrada!r} -> {esperado!r}", formatar(entrada) == esperado,
          "" if formatar(entrada) == esperado else f"(deu {formatar(entrada)!r})")
checa("nulo não quebra", formatar(None) == "")

print("\n2. E escreve IGUAL ao frontend")
node = shutil.which("node")
if not node:
    print("  --   node não encontrado; comparação entre os lados pulada")
else:
    # Caminho RELATIVO ao .mjs: import ESM com caminho absoluto exigiria
    # `file://`, e o erro que ele dá não diz isso.
    script = (
        "import {formatarRazaoSocial as f} from "
        "'../../frontend/src/pages/razaoSocial.js';\n"
        "const casos=JSON.parse(process.argv[2]);\n"
        "console.log(JSON.stringify(casos.map(c=>f(c))));\n"
    )
    entradas = [c[0] for c in CASOS]
    arq = RAIZ / "provas" / "_cmp_razao.mjs"
    arq.write_text(script, encoding="utf-8")
    try:
        saida = subprocess.run([node, str(arq), json.dumps(entradas)],
                               capture_output=True, text=True, timeout=30)
        if saida.returncode != 0:
            checa("o frontend rodou", False, saida.stderr.strip()[:120])
        else:
            do_front = json.loads(saida.stdout)
            do_back = [formatar(e) for e in entradas]
            divergentes = [(e, b, f) for e, b, f in zip(entradas, do_back, do_front) if b != f]
            checa("os dois lados escrevem igual em todos os casos",
                  not divergentes,
                  "" if not divergentes else "; ".join(
                      f"{e!r}: back={b!r} front={f!r}" for e, b, f in divergentes[:3]))
    finally:
        arq.unlink(missing_ok=True)

print("\n" + ("TUDO VERDE" if ok else "VERMELHO") + "\n")
sys.exit(0 if ok else 1)
