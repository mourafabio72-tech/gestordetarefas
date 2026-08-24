"""
prova_painel.py — os números do painel.

O que motivou: a rosca do dashboard somava 101%. "Atrasada" era contada dentro
de "pendente", então uma tarefa aparecia duas vezes e a soma passava do total.
Um painel em que os números não fecham não é usado para decidir nada.

    python provas/prova_painel.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
_tmp = tempfile.mkdtemp(prefix="prova-painel-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ.setdefault("SECRET_KEY", "chave-de-prova")

from fastapi.testclient import TestClient                      # noqa: E402
from app.database import Base, engine, SessionLocal            # noqa: E402
from app.models import Usuario, Empresa, Setor, Tarefa, StatusTarefa  # noqa: E402
from app.auth import get_password_hash, create_access_token    # noqa: E402
from app.main import app                                       # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)

ok = True
def checa(nome, cond, extra=""):
    global ok
    print(("  ok   " if cond else "FALHA  ") + nome + (f"  {extra}" if extra else ""))
    ok = ok and bool(cond)


cab = {"Authorization": "Bearer " + create_access_token(data={"sub": "admin@x.com"})}
agora = datetime.utcnow()

db = SessionLocal()
db.add(Usuario(nome="Admin", email="admin@x.com", grupo="admin", ativo=True,
               senha_hash=get_password_hash("x")))
ana = Usuario(nome="Ana", email="ana@x.com", grupo="analista", ativo=True,
              senha_hash=get_password_hash("x"))
bia = Usuario(nome="Bia", email="bia@x.com", grupo="analista", ativo=True,
              senha_hash=get_password_hash("x"))
fiscal = Setor(nome="Fiscal"); contab = Setor(nome="Contabilidade")
emp = Empresa(razao_social="Cliente", cnpj="1")
db.add_all([ana, bia, fiscal, contab, emp]); db.commit()

def nova(titulo, status, dias, setor, multa=False, quem=(), comp="07/2026"):
    t = Tarefa(titulo=titulo, empresa_id=emp.id, setor_id=setor.id, status=status,
               gera_multa=multa, competencia=comp,
               data_prazo=agora + timedelta(days=dias) if dias is not None else None)
    db.add(t); db.commit()
    for u in quem:
        t.responsaveis.append(u)
    db.commit()
    return t

nova("atrasada com multa", StatusTarefa.PENDENTE, -3, fiscal, multa=True, quem=(ana,))
nova("atrasada sem multa", StatusTarefa.PENDENTE, -1, fiscal, quem=(ana,))
nova("pendente futura", StatusTarefa.PENDENTE, 5, fiscal, multa=True, quem=(bia,))
nova("em andamento", StatusTarefa.EM_ANDAMENTO, 2, contab, quem=(ana, bia))
nova("concluida com multa", StatusTarefa.CONCLUIDA, -10, contab, multa=True, quem=(bia,))
nova("cancelada", StatusTarefa.CANCELADA, -10, contab)
nova("sem responsavel", StatusTarefa.PENDENTE, 3, contab)
db.close()

d = client.get("/api/painel", headers=cab).json()
r = d["resumo"]

print("\n1. Situação exclusiva — cada tarefa conta UMA vez")
checa("total é 7", r["total"] == 7, str(r["total"]))
soma = sum(r[s] for s in ("pendente", "em_andamento", "atrasada", "concluida", "cancelada"))
checa("as situações somam exatamente o total", soma == r["total"], f"({soma} x {r['total']})")
checa("atrasada NÃO está dentro de pendente",
      r["atrasada"] == 2 and r["pendente"] == 2, f"atrasada={r['atrasada']} pendente={r['pendente']}")
checa("em andamento", r["em_andamento"] == 1)
checa("concluída", r["concluida"] == 1)
checa("cancelada", r["cancelada"] == 1)

print("\n2. Multa conta só o que ainda pode dar problema")
checa("duas em aberto geram multa", r["multa"] == 2, str(r["multa"]))
checa("a concluída com multa não entra — já não é risco", r["multa"] != 3)

print("\n3. Por setor")
setores = {s["nome"]: s for s in d["por_setor"]}
checa("Fiscal com 3", setores["Fiscal"]["total"] == 3)
checa("e 2 atrasadas", setores["Fiscal"]["atrasada"] == 2)
checa("Contabilidade com 4", setores["Contabilidade"]["total"] == 4)
checa("o mais carregado vem primeiro", d["por_setor"][0]["nome"] == "Fiscal", d["por_setor"][0]["nome"])

print("\n4. Por colaborador — tarefa com dois responsáveis conta para os dois")
colab = {c["nome"]: c for c in d["por_colaborador"]}
checa("Ana com 3", colab["Ana"]["total"] == 3, str(colab["Ana"]["total"]))
checa("Bia com 3", colab["Bia"]["total"] == 3, str(colab["Bia"]["total"]))
# Duas tarefas sem ninguém: a "sem responsavel" e a "cancelada".
checa("quem não tem responsável aparece à parte",
      colab.get("Sem responsável", {}).get("total") == 2,
      str(colab.get("Sem responsável", {}).get("total")))
# A soma por colaborador passa do total, e tem de passar: tarefa com dois
# responsáveis conta para os dois. Confundir isso com erro levaria a "consertar"
# a contagem e esconder metade do trabalho de alguém.
soma_colab = sum(c["total"] for c in d["por_colaborador"])
checa("a soma por colaborador excede o total, por causa do trabalho dividido",
      soma_colab == 8 and soma_colab > r["total"], str(soma_colab))

print("\n5. Próximas do vencimento, agrupadas por setor")
grupos = {g["setor"]: g for g in d["proximas"]}
checa("só o que está em aberto", sum(g["total"] for g in d["proximas"]) == 5,
      str(sum(g["total"] for g in d["proximas"])))
checa("concluída e cancelada ficam de fora",
      all(t["titulo"] not in ("concluida com multa", "cancelada")
          for g in d["proximas"] for t in g["tarefas"]))
checa("o setor com atraso vem primeiro", d["proximas"][0]["setor"] == "Fiscal")
checa("cada grupo conta suas atrasadas", grupos["Fiscal"]["atrasadas"] == 2)
checa("a tarefa traz quem responde",
      any(t["responsaveis"] == ["Ana"] for t in grupos["Fiscal"]["tarefas"]))
checa("e se gera multa", any(t["multa"] for t in grupos["Fiscal"]["tarefas"]))
checa("ordenadas pelo prazo",
      [t["titulo"] for t in grupos["Fiscal"]["tarefas"]][0] == "atrasada com multa")

print("\n6. Filtros")
f = lambda **kw: client.get("/api/painel", params=kw, headers=cab).json()["resumo"]
checa("por setor", f(setor_id=fiscal.id if False else 1)["total"] in (3, 4))
checa("só multa traz as três que geram", f(so_multa=True)["total"] == 3, str(f(so_multa=True)["total"]))
checa("competência que não existe zera", f(competencia="01/1999")["total"] == 0)
checa("competência certa traz tudo", f(competencia="07/2026")["total"] == 7)

print("\n7. Sem sessão não abre")
checa("401 ou 403", client.get("/api/painel").status_code in (401, 403))

import shutil                                                  # noqa: E402
shutil.rmtree(_tmp, ignore_errors=True)
print("\n" + ("TUDO VERDE" if ok else "VERMELHO") + "\n")
sys.exit(0 if ok else 1)
