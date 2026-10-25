"""Prova da rota de integração das empresas (2026-10-25, para o Tracker).

O que ela trava:
  - sem INTEGRACAO_EMPRESAS_TOKEN no servidor, a rota responde 404 (fechada);
  - sem token, com token errado ou com o JWT de um usuário: 401;
  - com o token certo: a lista inteira, inativas e bloqueadas incluídas, com o
    estado de cada uma;
  - só os campos combinados saem: nada de e-mail, telefone, endereço ou responsável.

    cd backend && uv run --no-project --python 3.12 --with-requirements requirements.txt python provas/prova_integracao_empresas.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_integ_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["SECRET_KEY"] = "chave-de-prova-nao-usar-em-producao"
os.environ["ZOARIA_SSO_SECRET"] = ""
os.environ.pop("INTEGRACAO_EMPRESAS_TOKEN", None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient                  # noqa: E402
from app.database import Base, engine, SessionLocal        # noqa: E402
from app.models import Empresa, Usuario                    # noqa: E402
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
db.add_all([
    Empresa(razao_social="MARKBUILDING PARTICIPACOES LTDA", nome_fantasia="MKB",
            cnpj="11.222.333/0001-81", email="x@y.com", telefone="1199", endereco="Rua A",
            grupo="Markbuilding", ativo=True, bloqueado=False),
    Empresa(razao_social="EMPRESA INATIVA SA", cnpj="22.333.444/0001-55", ativo=False),
    Empresa(razao_social="EMPRESA BLOQUEADA ME", cnpj="33.444.555/0001-66", ativo=True,
            bloqueado=True),
])
if not db.query(Usuario).filter(Usuario.email == "prova-integ@x.com").first():
    db.add(Usuario(nome="Prova", email="prova-integ@x.com",
                   senha_hash=get_password_hash("x"), grupo="admin", ativo=True))
db.commit()
db.close()

URL = "/api/integracao/empresas"

r = client.get(URL, headers={"Authorization": "Bearer qualquer"})
checa(1, "sem a variável no servidor: 404 (fechada)", r.status_code == 404, r.status_code)

os.environ["INTEGRACAO_EMPRESAS_TOKEN"] = "token-de-prova-123"
checa(2, "sem token: 401", client.get(URL).status_code == 401)
checa(3, "token errado: 401",
      client.get(URL, headers={"Authorization": "Bearer outro"}).status_code == 401)
jwt = create_access_token(data={"sub": "prova-integ@x.com"})
checa(4, "JWT de usuário (até admin) não serve: 401",
      client.get(URL, headers={"Authorization": "Bearer " + jwt}).status_code == 401)
checa(5, "token sem o 'Bearer ': 401",
      client.get(URL, headers={"Authorization": "token-de-prova-123"}).status_code == 401)

r = client.get(URL, headers={"Authorization": "Bearer token-de-prova-123"})
checa(6, "token certo: 200", r.status_code == 200, r.status_code)
lista = r.json().get("empresas", []) if r.status_code == 200 else []
por_nome = {e["razao_social"]: e for e in lista}
checa(7, "as três empresas, inativa e bloqueada incluídas", len(lista) == 3, len(lista))
mkb = por_nome.get("MARKBUILDING PARTICIPACOES LTDA", {})
checa(8, "fantasia, CNPJ e grupo saem",
      (mkb.get("nome_fantasia"), mkb.get("cnpj"), mkb.get("grupo"))
      == ("MKB", "11.222.333/0001-81", "Markbuilding"), mkb)
checa(9, "o estado de cada uma sai",
      (por_nome.get("EMPRESA INATIVA SA", {}).get("ativo"),
       por_nome.get("EMPRESA BLOQUEADA ME", {}).get("bloqueado")) == (False, True))
campos = set().union(*[set(e) for e in lista]) if lista else set()
checa(10, "só os campos combinados",
      campos == {"id", "razao_social", "nome_fantasia", "cnpj", "grupo", "ativo", "bloqueado"},
      sorted(campos))

print("\nFALHAS:", len(falhou))
sys.exit(1 if falhou else 0)
