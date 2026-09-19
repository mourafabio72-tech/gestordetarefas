"""
prova_chave_especifica.py: o e-validador escolhe a chave mais específica.

Em produção, os recibos de SPED Fiscal ensinaram à obrigação 169 a chave
"RECIBO DE ENTREGA DE ESCRITURAÇÃO FISCAL DIGITAL", e a 170 (SPED
Contribuições) tem "RECIBO DE ENTREGA DE ESCRITURAÇÃO FISCAL DIGITAL -
CONTRIBUIÇÕES". A primeira está dentro da segunda: todo recibo de
Contribuições casava com as duas e o e-validador respondia "ambíguo", sem
baixar nada. Decisão do usuário em 2026-09-19 (1a): quando a chave de uma
candidata está contida na chave de outra, vence a mais específica.

Os itens 3, 4 e 5 passam JÁ no RED, de propósito: o desempate não pode
inventar escolha entre chaves independentes nem entre chaves iguais, e o
recibo de SPED Fiscal tem de continuar achando a 169.

    python provas/prova_chave_especifica.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
_tmp = tempfile.mkdtemp(prefix="prova-chave-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = os.path.join(_tmp, "uploads")
os.environ.setdefault("SECRET_KEY", "chave-de-prova")

from app.database import Base, engine, SessionLocal                    # noqa: E402
from app.models import Obrigacao, Empresa, Tarefa, StatusTarefa        # noqa: E402
from app.services import validador                                     # noqa: E402

Base.metadata.create_all(bind=engine)
TOTAL = 6
falhou = []


def checa(n, descricao, condicao):
    if condicao:
        print(f"  ok  {n:>3}. {descricao}")
    else:
        print(f"FALHA  {n:>3}. {descricao}")
        falhou.append(n)


FISCAL = "RECIBO DE ENTREGA DE ESCRITURAÇÃO FISCAL DIGITAL"
CONTRIB = "RECIBO DE ENTREGA DE ESCRITURAÇÃO FISCAL DIGITAL - CONTRIBUIÇÕES"

db = SessionLocal()
o169 = Obrigacao(nome="entrega_sped_fiscal", sentido="transmitir", identificadores=FISCAL)
o170 = Obrigacao(nome="entrega_sped_contribuições", sentido="transmitir", identificadores=CONTRIB)
oa = Obrigacao(nome="guia_a", sentido="entregar", identificadores="GUIA ALFA")
ob = Obrigacao(nome="guia_b", sentido="entregar", identificadores="PAGAMENTO BETA")
oc = Obrigacao(nome="igual_1", sentido="entregar", identificadores="DOCUMENTO GAMA")
od = Obrigacao(nome="igual_2", sentido="entregar", identificadores="DOCUMENTO GAMA")
emp = Empresa(razao_social="Cliente Prova", cnpj="11.222.333/0001-81")
db.add_all([o169, o170, oa, ob, oc, od, emp])
db.commit()
db.add(Tarefa(titulo="SPED Contribuições", empresa_id=emp.id, obrigacao_id=o170.id,
              competencia="05/2026", status=StatusTarefa.PENDENTE))
db.commit()


def nomes(texto):
    return sorted(o.nome for o in validador.identificar_obrigacao(db, texto))


recibo_contrib = (f"{CONTRIB}\nVersão EFD-Contribuições: 6.1\nCNPJ 11.222.333/0001-81\n"
                  "Período 01/05/2026 a 31/05/2026")
recibo_fiscal = f"{FISCAL}\nVersão Sped Fiscal: 5.0\nEFD ICMS IPI\nPeríodo 01/05/2026 a 31/05/2026"

# 1. o recibo de Contribuições casa só com a 170
r = nomes(recibo_contrib)
checa(1, f"recibo de Contribuições casa só com a 170: {r}", r == ["entrega_sped_contribuições"])

# 2. e o processar baixa, em vez de responder ambíguo
validador.ler_arquivo = lambda nome, conteudo: recibo_contrib
res = validador.processar(db, "recibo.pdf", b"%PDF")
checa(2, f"processar baixa a tarefa da 170: {res.get('status')} {res.get('detalhe')}",
      res.get("status") == "baixada")

# 3. não-regressão: o recibo de SPED Fiscal continua achando a 169
r = nomes(recibo_fiscal)
checa(3, f"recibo de SPED Fiscal continua casando com a 169: {r}", r == ["entrega_sped_fiscal"])

# 4. chaves independentes que casam no mesmo texto continuam ambíguas
r = nomes("GUIA ALFA e PAGAMENTO BETA no mesmo papel")
checa(4, f"chaves independentes não são desempatadas: {r}", r == ["guia_a", "guia_b"])

# 5. chaves iguais em duas obrigações continuam ambíguas
r = nomes("DOCUMENTO GAMA")
checa(5, f"chaves iguais não são desempatadas: {r}", r == ["igual_1", "igual_2"])

# 6. a chave curta só perde para a longa se a longa também casou no texto
r = nomes(f"{FISCAL}\nsem a palavra do outro")
checa(6, f"texto só com a chave curta acha a 169 sozinha: {r}", r == ["entrega_sped_fiscal"])

db.close()
print()
if falhou:
    print(f"PROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print(f"PROVA OK: {TOTAL} checagens verdes")
