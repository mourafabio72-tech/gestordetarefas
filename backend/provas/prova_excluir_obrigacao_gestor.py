"""Prova da Fase 52: excluir obrigacao so admin e gestor.

Medido em producao em 2026-09-23: o grupo Analista foi editado na tela de
Grupos para `obrigacoes: editar`, e 31 pessoas estao nele. A exclusao
(DELETE /obrigacoes/{id}, e o lote que a tela usa no "Excluir N" e no
"Limpar todas") pedia so `obrigacoes: editar`. Excluir de vez apaga tambem as
tarefas ja geradas, entao qualquer analista podia apagar todo o cadastro e o
historico de tarefas num clique. Decisao do usuario: "exclusao so admin e
gestor". Inativar e editar continuam com quem edita obrigacoes.

    cd backend && ./venv/bin/python provas/prova_excluir_obrigacao_gestor.py
"""

from __future__ import annotations  # producao e 3.12, a maquina local e 3.9

import json
import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_excl_obr_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["SECRET_KEY"] = "chave-de-prova-nao-usar-em-producao"
os.environ["ZOARIA_SSO_SECRET"] = ""

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient                  # noqa: E402
from app.database import Base, engine, SessionLocal        # noqa: E402
from app.models import Usuario, Empresa, Tarefa, Obrigacao  # noqa: E402
from app.auth import get_password_hash, create_access_token  # noqa: E402
from app.main import app                                   # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
falhou = []


def checa(n, descricao, cond, extra=""):
    print(("  ok  " if cond else "FALHA ") + f"{n:>3}. {descricao}"
          + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        falhou.append(n)


def cab(email):
    return {"Authorization": "Bearer " + create_access_token(data={"sub": email})}


db = SessionLocal()
h = get_password_hash("x")
emp = Empresa(razao_social="Cliente Ltda", cnpj="11111111000111")
# O analista reproduz a producao: grupo analista com obrigacoes editar.
analista = Usuario(nome="Analista", email="analista@x.com", grupo="analista", senha_hash=h,
                   ativo=True, permissoes=json.dumps({"obrigacoes": "editar"}))
gestor = Usuario(nome="Gestor", email="gestor@x.com", grupo="gestor", senha_hash=h, ativo=True)
admin = Usuario(nome="Admin", email="admin@x.com", grupo="admin", senha_hash=h, ativo=True)
db.add_all([emp, analista, gestor, admin])
db.commit()
obr = [Obrigacao(nome=f"obrigacao_{i}", ativa=True) for i in range(5)]
db.add_all(obr)
db.commit()
tarefas = [Tarefa(titulo=f"tarefa da {o.nome}", empresa_id=emp.id, obrigacao_id=o.id) for o in obr]
db.add_all(tarefas)
db.commit()
ids = [o.id for o in obr]
db.close()


def existe(oid):
    s = SessionLocal()
    try:
        o = s.query(Obrigacao).filter(Obrigacao.id == oid).first()
        t = s.query(Tarefa).filter(Tarefa.obrigacao_id == oid).count()
        return (o is not None, o.ativa if o else None, t)
    finally:
        s.close()


print("\nanalista com obrigacoes editar (como em producao)")
r = client.delete(f"/api/obrigacoes/{ids[0]}?definitivo=true", headers=cab("analista@x.com"))
checa(1, "NAO exclui de vez (403), e obrigacao e tarefa continuam",
      r.status_code == 403 and existe(ids[0]) == (True, True, 1), (r.status_code, existe(ids[0])))

r = client.delete(f"/api/obrigacoes/{ids[0]}", headers=cab("analista@x.com"))
checa(2, "NAO usa a lixeira sem o definitivo (403)",
      r.status_code == 403 and existe(ids[0]) == (True, True, 1), (r.status_code, existe(ids[0])))

r = client.post("/api/obrigacoes/excluir-lote", headers=cab("analista@x.com"),
                json={"ids": ids, "definitivo": True})
checa(3, "NAO exclui em lote, que e o 'Limpar todas' (403), e nada some",
      r.status_code == 403 and all(existe(i)[0] and existe(i)[2] == 1 for i in ids), r.status_code)

r = client.post("/api/obrigacoes/excluir-lote", headers=cab("analista@x.com"),
                json={"ids": ids, "definitivo": False})
checa(4, "NAO inativa em lote pela rota de exclusao (403)",
      r.status_code == 403 and all(existe(i)[1] for i in ids), r.status_code)

r = client.put(f"/api/obrigacoes/{ids[1]}", headers=cab("analista@x.com"), json={"nome": "renomeada"})
checa(5, "NAO-REGRESSAO: continua editando", r.status_code == 200, r.text[:120])

r = client.post(f"/api/obrigacoes/{ids[1]}/status", headers=cab("analista@x.com"), json={"ativa": False})
checa(6, "NAO-REGRESSAO: continua inativando pelo botao de status",
      r.status_code == 200 and existe(ids[1])[1] is False, r.text[:120])

print("\ngestor e admin")
r = client.delete(f"/api/obrigacoes/{ids[2]}?definitivo=true", headers=cab("gestor@x.com"))
checa(7, "gestor exclui de vez, com as tarefas", r.status_code == 200 and existe(ids[2]) == (False, None, 0),
      (r.status_code, existe(ids[2])))

r = client.post("/api/obrigacoes/excluir-lote", headers=cab("admin@x.com"),
                json={"ids": [ids[3], ids[4]], "definitivo": True})
checa(8, "admin exclui em lote",
      r.status_code == 200 and not existe(ids[3])[0] and not existe(ids[4])[0], r.text[:120])

print()
if falhou:
    print(f"PROVA FALHOU nos itens: {sorted(set(falhou))}")
    sys.exit(1)
print("PROVA OK: 8 checagens verdes")
