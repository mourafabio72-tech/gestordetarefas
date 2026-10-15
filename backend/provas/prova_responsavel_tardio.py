"""Prova: tarefa que nasceu sem dono recebe o responsável cadastrado depois.

Caso de 2026-10-15, empresa Bergamo: as tarefas foram geradas antes de a
matriz (empresa x setor) ser preenchida e ficaram com Analista vazio. O
gerador copia os responsáveis SÓ quando cria a tarefa, e salvar a matriz só
cancelava setor desmarcado. Decisões do usuário:

  (a) salvar a matriz preenche as tarefas EM ABERTO da empresa, geradas por
      obrigação, que estão SEM DONO. Quem já tem dono não é mexido;
  (b) uma rota de admin faz o mesmo em todas as empresas, com ensaio (lista
      sem mudar) antes do valer.

    cd backend && ./venv/bin/python provas/prova_responsavel_tardio.py
"""

from __future__ import annotations  # producao e 3.12, a maquina local e 3.9

import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_responsavel_tardio_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["SECRET_KEY"] = "chave-de-prova-nao-usar-em-producao"
os.environ["ZOARIA_SSO_SECRET"] = ""

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient                          # noqa: E402
from app.auth import get_password_hash, create_access_token        # noqa: E402
from app.database import Base, engine, SessionLocal                # noqa: E402
from app.models import (Empresa, EmpresaSetorResponsavel, Obrigacao,  # noqa: E402
                        Setor, StatusTarefa, Tarefa, Usuario)
from app.services import resp_setor                                # noqa: E402
from app.main import app                                           # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
MESES = "1,2,3,4,5,6,7,8,9,10,11,12"
falhou = []
ids = {}


def checa(n, descricao, cond, extra=""):
    print(("  ok  " if cond else "FALHA ") + f"{n:>3}. {descricao}"
          + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        falhou.append(n)


def cab(email):
    return {"Authorization": "Bearer " + create_access_token(data={"sub": email})}


def dono(tid):
    """(principal, lista de responsáveis em ordem de id, supervisor)."""
    db = SessionLocal()
    try:
        t = db.query(Tarefa).filter(Tarefa.id == tid).first()
        return (t.responsavel_id, sorted(u.id for u in t.responsaveis), t.supervisor_id)
    finally:
        db.close()


def nova_tarefa(empresa, obrigacao, setor, status=StatusTarefa.PENDENTE,
                resp=None, sup=None, titulo="t"):
    db = SessionLocal()
    t = Tarefa(titulo=titulo, empresa_id=ids[empresa], setor_id=ids[setor],
               obrigacao_id=ids[obrigacao] if obrigacao else None,
               competencia="10/2026", status=status,
               responsavel_id=ids[resp] if resp else None,
               supervisor_id=ids[sup] if sup else None)
    if resp:
        t.responsaveis = [db.get(Usuario, ids[resp])]
    db.add(t)
    db.commit()
    tid = t.id
    db.close()
    return tid


# ------------------------------------------------------------------ cenário
db = SessionLocal()
h = get_password_hash("x")
pessoas = {k: Usuario(nome=k.title(), email=f"{k}@x.com", grupo=g, senha_hash=h, ativo=True)
           for k, g in (("admin", "admin"), ("gil", "gestor"), ("ana", "analista"),
                        ("bia", "analista"), ("caio", "analista"), ("duda", "analista"))}
db.add_all(pessoas.values())
db.flush()
pessoas["ana"].gestor_id = pessoas["gil"].id
fiscal = Setor(nome="Fiscal", ativo=True)
cliente = Setor(nome="Cliente", ativo=True)
db.add_all([fiscal, cliente])
db.flush()
emps = {k: Empresa(razao_social=f"Empresa {k}", cnpj=f"{n:02d}111111000111", ativo=True)
        for n, k in enumerate(("A", "B", "C"), start=1)}
db.add_all(emps.values())
db.flush()
o_fis = Obrigacao(nome="darf_inss_retido", setor_id=fiscal.id, meses_ativos=MESES, ativa=True,
                  supervisor_id=pessoas["duda"].id)
o_cli = Obrigacao(nome="calculo_cmv", setor_id=cliente.id, meses_ativos=MESES, ativa=True)
db.add_all([o_fis, o_cli])
db.flush()
# B foi preenchida direto no banco (Fiscal: Ana), como o que já está gravado
# em produção; C marcou o Fiscal sem escolher ninguém.
vb = EmpresaSetorResponsavel(empresa_id=emps["B"].id, setor_id=fiscal.id)
vc = EmpresaSetorResponsavel(empresa_id=emps["C"].id, setor_id=fiscal.id)
db.add_all([vb, vc])
resp_setor.gravar(db, vb, [pessoas["ana"].id])
resp_setor.gravar(db, vc, [])
db.commit()
ids.update({"fiscal": fiscal.id, "cliente": cliente.id, "o_fis": o_fis.id, "o_cli": o_cli.id,
            **{k: u.id for k, u in pessoas.items()}, **{k: e.id for k, e in emps.items()}})
db.close()

t_pend = nova_tarefa("A", "o_fis", "fiscal", sup="duda")
t_atras = nova_tarefa("A", "o_fis", "fiscal", StatusTarefa.ATRASADA)
t_concl = nova_tarefa("A", "o_fis", "fiscal", StatusTarefa.CONCLUIDA)
t_com_dono = nova_tarefa("A", "o_fis", "fiscal", resp="duda")
t_avulsa = nova_tarefa("A", None, "fiscal", titulo="avulsa")
t_cli = nova_tarefa("A", "o_cli", "cliente")
t_b = nova_tarefa("B", "o_fis", "fiscal")
t_c = nova_tarefa("C", "o_fis", "fiscal")

A = cab("admin@x.com")

# ------------------------------------------------- (a) salvar a matriz
print("\n(a) salvar a matriz preenche as tarefas abertas sem dono")
r = client.put(f"/api/empresas/{ids['A']}/responsaveis-setor", headers=A, json={"itens": [
    {"setor_id": ids["fiscal"], "responsavel_ids": [ids["ana"], ids["bia"]]},
    {"setor_id": ids["cliente"], "responsavel_ids": [ids["caio"]]}]})
checa(1, "PUT da matriz responde 200", r.status_code == 200, r.text)
d = dono(t_pend)
checa(2, "pendente sem dono recebe Ana (principal) e Bia",
      d[0] == ids["ana"] and d[1] == sorted([ids["ana"], ids["bia"]]), d)
checa(3, "supervisor vira o gestor da principal (Gil)", d[2] == ids["gil"], d)
checa(4, "atrasada sem dono tambem recebe", dono(t_atras)[0] == ids["ana"], dono(t_atras))
checa(5, "concluida nao muda", dono(t_concl)[0] is None, dono(t_concl))
checa(6, "tarefa que ja tinha dono (Duda) nao muda",
      dono(t_com_dono)[:2] == (ids["duda"], [ids["duda"]]), dono(t_com_dono))
checa(7, "avulsa (sem obrigacao) nao muda", dono(t_avulsa)[0] is None, dono(t_avulsa))
d = dono(t_cli)
checa(8, "setor Cliente recebe Caio; sem gestor, supervisor fica o que era",
      d[0] == ids["caio"] and d[1] == [ids["caio"]] and d[2] is None, d)
checa(9, "resposta conta as atribuidas",
      r.status_code == 200 and r.json().get("tarefas_atribuidas") == 3, r.text)
checa(10, "outra empresa nao muda ao salvar a matriz da A", dono(t_b)[0] is None, dono(t_b))

# ------------------------------------------------- (b) ajuste do que ja nasceu
print("\n(b) aplicar os responsaveis atuais ao que ja foi gerado")
rota = "/api/empresas/aplicar-responsaveis"
r = client.post(rota, headers=cab("ana@x.com"), json={"ensaio": True})
checa(11, "analista recebe 403", r.status_code == 403, r.status_code)
r = client.post(rota, headers=A, json={"ensaio": True})
corpo = r.json() if r.status_code == 200 else {}
achadas = [x.get("tarefa_id") for x in corpo.get("tarefas", [])]
checa(12, "ensaio lista so a tarefa da B (C marcou o setor sem ninguem)",
      r.status_code == 200 and achadas == [t_b], (r.status_code, r.text[:200]))
checa(13, "ensaio mostra quem vai receber",
      corpo.get("tarefas", [{}])[0].get("responsaveis") == ["Ana"], corpo)
checa(14, "ensaio nao muda nada", dono(t_b)[0] is None, dono(t_b))
checa(15, "sem corpo, a rota fica no ensaio",
      client.post(rota, headers=A).status_code == 200 and dono(t_b)[0] is None, dono(t_b))
r = client.post(rota, headers=A, json={"ensaio": False})
checa(16, "valendo, a tarefa da B recebe Ana e responde 1",
      r.status_code == 200 and r.json().get("tarefas_atribuidas") == 1
      and dono(t_b)[0] == ids["ana"], (r.text[:200], dono(t_b)))
checa(17, "a da C continua sem dono", dono(t_c)[0] is None, dono(t_c))
r = client.post(rota, headers=A, json={"ensaio": False})
checa(18, "segunda rodada nao acha nada (idempotente)",
      r.status_code == 200 and r.json().get("tarefas_atribuidas") == 0, r.text[:200])

# ------------------------------------------------- (c) pela planilha
print("\n(c) a planilha tem o mesmo efeito da tela")
import io, openpyxl
db = SessionLocal()
emp_p = Empresa(razao_social="Empresa P", cnpj="09111111000111", ativo=True)
db.add(emp_p)
db.commit()
ids["P"] = emp_p.id
db.close()
t_p = nova_tarefa("P", "o_fis", "fiscal")
wb = openpyxl.Workbook()
wb.active.append(["CNPJ", "Fiscal"])
wb.active.append(["09111111000111", "Bia"])
buf = io.BytesIO()
wb.save(buf)
r = client.post("/api/empresas/importar-responsaveis", headers=A,
                files={"arquivo": ("m.xlsx", buf.getvalue(),
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
checa(19, "planilha com Bia no Fiscal da P preenche a tarefa sem dono",
      r.status_code == 200 and dono(t_p)[0] == ids["bia"]
      and r.json()["resumo"].get("tarefas_atribuidas") == 1, (r.text[:300], dono(t_p)))

if falhou:
    print(f"\nPROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print("\nPROVA OK: 19 checagens verdes")
