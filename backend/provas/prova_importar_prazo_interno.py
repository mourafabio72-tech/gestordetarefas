"""Prova: o importador de obrigações entende "Dia N", prazo interno, sentido e comentário.

Pedido de 2026-10-26: subir o fluxo mensal da folha do DP (planilha
Tarefas_DP.xlsx). Os prazos dela são "Dia 12", "Dia 15": o importador só lia
dia útil e trocava, calado, qualquer outra coisa por "último dia útil". E não
gravava o prazo interno da BPS4, o sentido nem o roteiro.

  (a) "Dia 12", "Até dia 15" e o número 12 viram dia fixo; "5º dia útil" segue
      dia útil;
  (b) colunas novas: Prazo interno (vira regra própria), Sentido, Comentário;
  (c) a planilha antiga, sem as colunas novas, importa como antes;
  (d) o que vem do navegador é validado: tipo, dia e sentido fora da lista
      não entram.

    cd backend && ./venv/bin/python provas/prova_importar_prazo_interno.py
"""

from __future__ import annotations  # producao e 3.12, a maquina local e 3.9

import io
import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_importar_prazo_interno_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["SECRET_KEY"] = "chave-de-prova-nao-usar-em-producao"
os.environ["ZOARIA_SSO_SECRET"] = ""

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import openpyxl                                                    # noqa: E402
from fastapi.testclient import TestClient                          # noqa: E402
from app.auth import get_password_hash, create_access_token        # noqa: E402
from app.database import Base, engine, SessionLocal                # noqa: E402
from app.models import Obrigacao, Setor, Usuario                   # noqa: E402
from app.main import app                                           # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
falhou = []


def checa(n, descricao, cond, extra=""):
    print(("  ok  " if cond else "FALHA ") + f"{n:>3}. {descricao}"
          + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        falhou.append(n)


def planilha(linhas):
    wb = openpyxl.Workbook()
    for linha in linhas:
        wb.active.append(linha)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def obrig(nome):
    db = SessionLocal()
    try:
        return db.query(Obrigacao).filter(Obrigacao.nome == nome).first()
    finally:
        db.close()


db = SessionLocal()
db.add(Usuario(nome="Admin", email="admin@x.com", grupo="admin",
               senha_hash=get_password_hash("x"), ativo=True))
db.add(Setor(nome="DP", ativo=True))
db.commit()
db.close()
A = {"Authorization": "Bearer " + create_access_token(data={"sub": "admin@x.com"})}
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def analisar(conteudo):
    r = client.post("/api/cronograma/analisar", headers=A,
                    files={"arquivo": ("c.xlsx", conteudo, XLSX)})
    return {i["nome"]: i for i in r.json().get("itens", [])} if r.status_code == 200 else {}


# ------------------------------------------------------------ (a) e (b)
print("\n(a) e (b) dia fixo, prazo interno, sentido e comentario")
CAB = ["Descrição da tarefa", "Competência", "Vencimento", "Prazo interno", "Setor",
       "Sentido", "Gera multa", "Comentário"]
it = analisar(planilha([
    CAB,
    ["Folha: S-1200", "Mês anterior", "Dia 15", "Dia 12", "DP", "transmitir", "Sim",
     "Sistema: eSocial. Documento: recibo S-1200."],
    ["Folha: Solicitar movimentações", "Mesmo mês", "Até dia 23", 23, "DP", "interna", "Não", ""],
    ["Folha: Pagamento", "Mês anterior", "5º dia útil", "", "DP", "Entregar", "Não", ""],
    ["Folha: Sentido estranho", "Mês anterior", 12, "", "DP", "qualquer", "Não", ""],
]))
s1200 = it.get("Folha: S-1200", {})
checa(1, "'Dia 15' vira dia fixo 15",
      (s1200.get("regra_prazo_tipo"), s1200.get("regra_prazo_dia")) == ("dia_fixo", 15), s1200)
checa(2, "'Dia 12' no prazo interno vira regra dia fixo 12",
      (s1200.get("interno_regra_tipo"), s1200.get("interno_regra_dia")) == ("dia_fixo", 12), s1200)
checa(3, "sentido e comentario chegam no item",
      s1200.get("sentido") == "transmitir" and "eSocial" in (s1200.get("comentario") or ""), s1200)
sol = it.get("Folha: Solicitar movimentações", {})
checa(4, "'Até dia 23' e o numero 23 viram dia fixo 23, mesmo mes",
      (sol.get("regra_prazo_tipo"), sol.get("regra_prazo_dia"), sol.get("interno_regra_dia"),
       sol.get("competencia_ref")) == ("dia_fixo", 23, 23, "mesmo_mes"), sol)
pag = it.get("Folha: Pagamento", {})
checa(5, "'5º dia útil' continua dia util 5, sem prazo interno",
      (pag.get("regra_prazo_tipo"), pag.get("regra_prazo_dia"), pag.get("interno_regra_tipo"))
      == ("dia_util", 5, None), pag)
checa(6, "sentido com maiuscula e normalizado ('Entregar' -> entregar)", pag.get("sentido") == "entregar", pag)
est = it.get("Folha: Sentido estranho", {})
checa(7, "numero 12 na coluna Vencimento vira dia fixo 12",
      (est.get("regra_prazo_tipo"), est.get("regra_prazo_dia")) == ("dia_fixo", 12), est)
checa(8, "sentido fora da lista fica vazio", est.get("sentido") in (None, ""), est)

r = client.post("/api/cronograma/importar", headers=A,
                json={"grupo": "DP", "itens": list(it.values()), "para_todas": True})
checa(9, "importar responde 200 e cria 4", r.status_code == 200 and r.json().get("criadas") == 4, r.text[:200])
o = obrig("Folha: S-1200")
checa(10, "obrigacao gravada com dia fixo 15 e prazo interno regra dia 12",
      o and (o.regra_prazo_tipo, o.regra_prazo_dia, o.interno_modo, o.interno_regra_tipo,
             o.interno_regra_dia) == ("dia_fixo", 15, "regra", "dia_fixo", 12),
      o and (o.regra_prazo_tipo, o.regra_prazo_dia, o.interno_modo, o.interno_regra_tipo, o.interno_regra_dia))
checa(11, "sentido, multa e comentario gravados",
      o and o.sentido == "transmitir" and o.passivel_multa and "eSocial" in (o.comentario_padrao or ""),
      o and (o.sentido, o.passivel_multa, o.comentario_padrao))
o = obrig("Folha: Pagamento")
checa(12, "sem prazo interno, fica o modo de sempre (antes do vencimento)",
      o and (o.interno_modo or "antes_vencimento") == "antes_vencimento", o and o.interno_modo)
o = obrig("Folha: Sentido estranho")
checa(13, "sem sentido valido, fica o padrao do modelo (receber)", o and o.sentido == "receber",
      o and o.sentido)

# ------------------------------------------------------------ (c)
print("\n(c) planilha antiga, sem as colunas novas")
it = analisar(planilha([["Descrição da tarefa", "Competência", "Vencimento", "Setor"],
                        ["Apuracao antiga", "Mês anterior", "5º dia útil", "DP"]]))
velho = it.get("Apuracao antiga", {})
checa(14, "le como antes: dia util 5, sem interno, sem sentido",
      (velho.get("regra_prazo_tipo"), velho.get("regra_prazo_dia"), velho.get("interno_regra_tipo"),
       velho.get("sentido")) == ("dia_util", 5, None, None), velho)

# ------------------------------------------------------------ (d)
print("\n(d) o que vem do navegador e validado")
r = client.post("/api/cronograma/importar", headers=A, json={"grupo": "DP", "para_todas": True, "itens": [
    {"nome": "Folha: Forjada", "setor": "DP", "regra_prazo_tipo": "rm -rf", "regra_prazo_dia": 99,
     "interno_regra_tipo": "dia_fixo", "interno_regra_dia": 45, "sentido": "<script>",
     "comentario": "x" * 5000}]})
o = obrig("Folha: Forjada")
checa(15, "tipo fora da lista vira ultimo dia util e dia fora de 1..31 sai",
      r.status_code == 200 and o and o.regra_prazo_tipo == "ultimo_dia_util" and o.regra_prazo_dia is None,
      (r.status_code, o and (o.regra_prazo_tipo, o.regra_prazo_dia)))
checa(16, "prazo interno com dia invalido nao entra; sentido invalido nao entra",
      o and (o.interno_modo or "antes_vencimento") == "antes_vencimento" and o.sentido == "receber",
      o and (o.interno_modo, o.interno_regra_dia, o.sentido))
checa(17, "comentario cortado em 2000 caracteres", o and len(o.comentario_padrao or "") <= 2000,
      o and len(o.comentario_padrao or ""))

if falhou:
    print(f"\nPROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print("\nPROVA OK: 17 checagens verdes")
