"""Prova da rota de integração da equipe (2026-10-27, para o Workforce).

O que ela trava:
  - sem INTEGRACAO_EMPRESAS_TOKEN no servidor, a rota responde 404 (fechada);
  - sem token, com token errado ou com o JWT de um usuário: 401;
  - com o token certo: a equipe, inativos e bloqueados incluídos, com o estado e
    o nome do setor de cada um; o usuário-CLIENTE não sai;
  - só os campos combinados: nada de senha, grupo, permissões, telefone ou convite.

    cd backend && uv run --no-project --python 3.12 --with-requirements requirements.txt python provas/prova_integracao_usuarios.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_integ_usu_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["SECRET_KEY"] = "chave-de-prova-nao-usar-em-producao"
os.environ["ZOARIA_SSO_SECRET"] = ""
os.environ.pop("INTEGRACAO_EMPRESAS_TOKEN", None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient                  # noqa: E402
from app.database import Base, engine, SessionLocal        # noqa: E402
from app.models import Empresa, Setor, Usuario             # noqa: E402
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


db = SessionLocal()
fiscal = Setor(nome="Fiscal")
cliente_emp = Empresa(razao_social="Cliente Teste Ltda", cnpj="44.555.666/0001-77")
db.add_all([fiscal, cliente_emp])
db.flush()
senha = get_password_hash("x")
db.add_all([
    Usuario(nome="Ana Prova", email="ana-prova@x.com", senha_hash=senha, grupo="analista",
            tipo="colaborador", setor_id=fiscal.id, telefone="2199", cargo="Analista",
            permissoes='{"x": 1}', convite_token="abc", ativo=True),
    Usuario(nome="Bia Inativa", email="bia-prova@x.com", senha_hash=senha, ativo=False),
    Usuario(nome="Caio Bloqueado", email="caio-prova@x.com", senha_hash=senha, bloqueado=True),
    Usuario(nome="Cliente Externo", email="cliente-prova@x.com", senha_hash=senha,
            tipo="cliente", empresa_id=cliente_emp.id),
    Usuario(nome="Admin Prova", email="admin-prova@x.com", senha_hash=senha, grupo="admin"),
])
db.commit()
db.close()

URL = "/api/integracao/usuarios"

r = client.get(URL, headers={"Authorization": "Bearer qualquer"})
checa(1, "sem a variável no servidor: 404 (fechada)", r.status_code == 404, r.status_code)

os.environ["INTEGRACAO_EMPRESAS_TOKEN"] = "token-de-prova-123"
checa(2, "sem token: 401", client.get(URL).status_code == 401)
checa(3, "token errado: 401",
      client.get(URL, headers={"Authorization": "Bearer outro"}).status_code == 401)
jwt = create_access_token(data={"sub": "admin-prova@x.com"})
checa(4, "JWT de usuário (até admin) não serve: 401",
      client.get(URL, headers={"Authorization": "Bearer " + jwt}).status_code == 401)

r = client.get(URL, headers={"Authorization": "Bearer token-de-prova-123"})
checa(5, "token certo: 200", r.status_code == 200, r.status_code)
lista = r.json().get("usuarios", []) if r.status_code == 200 else []
por_email = {u["email"]: u for u in lista}
checa(6, "o cliente externo não sai", "cliente-prova@x.com" not in por_email, sorted(por_email))
checa(7, "a equipe sai inteira, inativo e bloqueado incluídos",
      {"ana-prova@x.com", "bia-prova@x.com", "caio-prova@x.com", "admin-prova@x.com"}
      <= set(por_email), sorted(por_email))
ana = por_email.get("ana-prova@x.com", {})
checa(8, "nome e setor saem", (ana.get("nome"), ana.get("setor")) == ("Ana Prova", "Fiscal"), ana)
checa(9, "o estado de cada um sai",
      (por_email.get("bia-prova@x.com", {}).get("ativo"),
       por_email.get("caio-prova@x.com", {}).get("bloqueado")) == (False, True))
campos = set().union(*[set(u) for u in lista]) if lista else set()
checa(10, "só os campos combinados (nada de senha, grupo, telefone, convite)",
      campos == {"id", "nome", "email", "setor", "ativo", "bloqueado"}, sorted(campos))
checa(11, "nem o hash da senha aparece no corpo", "$2b$" not in r.text)

print("\nFALHAS:", len(falhou))
sys.exit(1 if falhou else 0)
