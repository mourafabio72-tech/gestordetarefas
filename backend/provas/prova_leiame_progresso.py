"""Prova do registro do Leia-me (pedido de 2026-10-05).

O manual interativo (/leia-me/) tem um fluxo guiado de 7 etapas. Cada pessoa
logada grava o proprio progresso; admin e gestor veem todos os colaboradores
ativos, inclusive quem nao comecou.

    cd backend && ./venv/bin/python provas/prova_leiame_progresso.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_leiame_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["SECRET_KEY"] = "chave-de-prova-nao-usar-em-producao"
os.environ["ZOARIA_SSO_SECRET"] = ""

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient                  # noqa: E402
from app.database import Base, engine, SessionLocal        # noqa: E402
from app.models import Usuario                             # noqa: E402
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
db.add_all([
    Usuario(nome="Gestora", email="gestora@x.com", grupo="gestor", senha_hash=h, ativo=True),
    Usuario(nome="Ana", email="ana@x.com", grupo="analista", senha_hash=h, ativo=True),
    Usuario(nome="Bruno", email="bruno@x.com", grupo="analista", senha_hash=h, ativo=True),
    Usuario(nome="Inativo", email="inativo@x.com", grupo="analista", senha_hash=h, ativo=False),
    Usuario(nome="Socio Cliente", email="cli@x.com", grupo="consulta", tipo="cliente", senha_hash=h, ativo=True),
])
db.commit(); db.close()

ESTADO_7 = [{"acao": True, "resp": True, "erros": 0}] * 7
ESTADO_3 = [{"acao": True, "resp": True, "erros": 1}] * 3 + [{"acao": False, "resp": False, "erros": 0}] * 4
URL = "/api/leiame/progresso"

# 1. Sem login nada entra.
r = client.put(URL, json={"estado": ESTADO_3, "liberada": 3})
checa(1, "sem login: 401", r.status_code == 401, f"{r.status_code}")

# 2. Quem nunca abriu o fluxo le um progresso vazio, sem erro.
r = client.get(URL, headers=cab("ana@x.com"))
checa(2, "progresso de quem nao comecou vem vazio", r.status_code == 200 and r.json().get("etapas") == 0,
      f"{r.status_code} {r.text[:120]}")

# 3. Grava o proprio progresso; etapas e erros saem do estado, nao do que o navegador diz.
r = client.put(URL, json={"estado": ESTADO_3, "liberada": 3, "etapas": 7, "concluido": True},
               headers=cab("ana@x.com"))
j = r.json() if r.status_code == 200 else {}
checa(3, "PUT grava e o servidor conta as etapas (3, nao os 7 que o corpo mandou)",
      r.status_code == 200 and j.get("etapas") == 3 and j.get("concluido") is False and j.get("erros") == 3,
      f"{r.status_code} {r.text[:160]}")

# 4. Le de volta o mesmo estado (para continuar em outro computador).
r = client.get(URL, headers=cab("ana@x.com"))
j = r.json()
checa(4, "GET devolve o estado gravado", j.get("liberada") == 3 and len(j.get("estado", [])) == 7, r.text[:160])

# 5. Concluir marca a data uma vez so; refazer depois nao apaga a conclusao.
r = client.put(URL, json={"estado": ESTADO_7, "liberada": 6}, headers=cab("ana@x.com"))
quando = r.json().get("concluido_em")
r2 = client.put(URL, json={"estado": ESTADO_3, "liberada": 3}, headers=cab("ana@x.com"))
checa(5, "conclusao fica registrada e nao some ao refazer",
      bool(quando) and r2.json().get("concluido") is True and r2.json().get("concluido_em") == quando,
      f"{quando} -> {r2.text[:160]}")

# 6. Lixo no corpo da 422 e nao grava.
ruins = [{"estado": [{"acao": True}] * 3, "liberada": 1},
         {"estado": ESTADO_3, "liberada": 99},
         {"estado": "abc", "liberada": 1},
         {"estado": [{"acao": "x", "resp": True, "erros": 0}] * 7, "liberada": 1},
         {"estado": [{"acao": True, "resp": True, "erros": -5}] * 7, "liberada": 1}]
cods = [client.put(URL, json=b, headers=cab("bruno@x.com")).status_code for b in ruins]
r = client.get(URL, headers=cab("bruno@x.com"))
checa(6, "corpo invalido da 422 e nada e gravado", cods == [422] * 5 and r.json().get("etapas") == 0, f"{cods}")

# 7. Analista nao ve o quadro de todos.
r = client.get("/api/leiame/conclusoes", headers=cab("bruno@x.com"))
checa(7, "analista: quadro de todos da 403", r.status_code == 403, f"{r.status_code}")

# 8. Gestor ve todos os colaboradores ativos, inclusive quem nao comecou; sem inativo e sem cliente.
r = client.get("/api/leiame/conclusoes", headers=cab("gestora@x.com"))
lista = r.json() if r.status_code == 200 else []
nomes = {x["nome"]: x for x in lista} if isinstance(lista, list) else {}
checa(8, "gestor ve Ana (concluiu), Bruno e a propria gestora (nao comecaram)",
      r.status_code == 200 and nomes.get("Ana", {}).get("concluido") is True
      and nomes.get("Bruno", {}).get("etapas") == 0 and "Gestora" in nomes,
      f"{r.status_code} {r.text[:200]}")
checa(9, "fora do quadro: inativo e usuario cliente",
      "Inativo" not in nomes and "Socio Cliente" not in nomes, f"{list(nomes)}")

# 10. O quadro nao expoe e-mail nem o estado detalhado de cada um.
checa(10, "quadro sem e-mail e sem estado detalhado",
      all("email" not in x and "estado" not in x for x in lista), f"{lista[:1]}")

print()
if falhou:
    print(f"PROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print("PROVA OK: 10 checagens verdes")
