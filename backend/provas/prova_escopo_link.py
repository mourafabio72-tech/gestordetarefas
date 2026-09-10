"""Prova da Fase 26: as duas rotas que nao aplicavam escopo.

`GET /api/tarefas/{id}/link-envio` dependia so de `get_current_user`: qualquer
usuario autenticado pedia o link publico de QUALQUER tarefa, inclusive de
empresa que ele nao atende. E o link publico e o endereco por onde o cliente
manda comprovante SEM LOGIN.

E ela e pior do que uma leitura indevida, porque nao e so leitura: o
`link_publico` chama `get_or_create_token`, entao o GET CRIA o token quando
ainda nao existe. Um GET que muta, e a mutacao e justamente abrir uma porta
sem senha.

`POST /{id}/transferir` tem o mesmo buraco, com alcance menor: exige admin ou
gestor, e esses ja tem escopo `todas` por padrao. So morde quando existe um
gestor de escopo reduzido, que o app permite criar.

    cd backend && ./venv/bin/python provas/prova_escopo_link.py

Isto NAO e fase de logging: e autorizacao. O evento de IDOR sai de brinde,
porque o helper que aplica o escopo ja registra.
"""

from __future__ import annotations  # producao e 3.12, a maquina local e 3.9

import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_escopo_")
_banco = os.path.join(_tmp, "prova.db")

os.environ["DATABASE_URL"] = f"sqlite:///{_banco}"
os.environ["SECRET_KEY"] = "chave-jwt-de-teste"
os.environ["ZOARIA_SSO_SECRET"] = ""

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient                      # noqa: E402

from app.auth import get_password_hash                         # noqa: E402
from app.database import Base, engine, SessionLocal            # noqa: E402
from app.models import Empresa, Setor, Tarefa, Usuario         # noqa: E402
from app.main import app                                       # noqa: E402

Base.metadata.create_all(bind=engine)

SENHA = "senha-boa-123"
EMAIL_ADMIN = "chefe@bps4.com.br"
EMAIL_FORA = "curioso@bps4.com.br"

cliente = TestClient(app)
ids = {}


def semear():
    db = SessionLocal()
    try:
        admin = Usuario(nome="Chefe", email=EMAIL_ADMIN, grupo="admin",
                        senha_hash=get_password_hash(SENHA), ativo=True)
        # `analista` e o papel com `escopo_tarefas: proprias`.
        fora = Usuario(nome="Fora do Escopo", email=EMAIL_FORA,
                       grupo="analista",
                       senha_hash=get_password_hash(SENHA), ativo=True)
        empresa = Empresa(razao_social="Cliente Alheio", cnpj="00000000000191")
        setor = Setor(nome="Fiscal")
        db.add_all([admin, fora, empresa, setor])
        db.commit()
        tarefa = Tarefa(titulo="Tarefa do chefe", empresa_id=empresa.id,
                        setor_id=setor.id, responsavel_id=admin.id)
        db.add(tarefa)
        db.commit()
        ids.update(admin=admin.id, fora=fora.id, tarefa=tarefa.id)
    finally:
        db.close()


def entrar(email):
    r = cliente.post("/api/auth/login", json={"email": email, "senha": SENHA})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def capturar(funcao):
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        retorno = funcao()
    linhas = []
    for bruta in buffer.getvalue().splitlines():
        bruta = bruta.strip()
        if not bruta.startswith("{"):
            continue
        try:
            linhas.append(json.loads(bruta))
        except json.JSONDecodeError:
            continue
    return retorno, linhas


def evento(linhas, nome):
    for linha in linhas:
        if linha.get("event") == nome:
            return linha
    return None


def token_no_banco():
    db = SessionLocal()
    try:
        t = db.query(Tarefa).filter(Tarefa.id == ids["tarefa"]).first()
        return t.upload_token
    finally:
        db.close()


semear()
falhou = []


def checa(n, descricao, condicao):
    if condicao:
        print(f"  ok  {n:>3}. {descricao}")
    else:
        print(f"FALHA  {n:>3}. {descricao}")
        falhou.append(n)


admin = entrar(EMAIL_ADMIN)
fora = entrar(EMAIL_FORA)


# ------------------------------------------------------------ (a) link-envio
# O estado ANTES importa: o teste seguinte so prova alguma coisa se a tarefa
# comeca sem token, porque o que se mede e a criacao dele.
checa(1, "a tarefa comeca sem token de upload, senao o item 3 nao mede nada",
      token_no_banco() is None)

r_fora, l_fora = capturar(
    lambda: cliente.get(f"/api/tarefas/{ids['tarefa']}/link-envio",
                        headers=fora))

checa(2, "quem esta fora do escopo NAO recebe o link publico da tarefa alheia",
      r_fora.status_code == 404)
checa(3, "e o GET recusado NAO cria o token: a porta nao chega a ser aberta",
      token_no_banco() is None)
checa(4, "a recusa emite ACESSO_NEGADO_IDOR, porque a tarefa existe",
      evento(l_fora, "ACESSO_NEGADO_IDOR") is not None)

r_inexistente, l_inexistente = capturar(
    lambda: cliente.get("/api/tarefas/999999/link-envio", headers=fora))
checa(5, "id inexistente devolve o MESMO 404 e nao emite evento nenhum",
      r_inexistente.status_code == 404
      and r_inexistente.json() == r_fora.json()
      and evento(l_inexistente, "ACESSO_NEGADO_IDOR") is None)

# NAO-REGRESSAO: quem tem direito continua recebendo o link, e e aqui que o
# token nasce. Sem este item, uma rota que recusasse TODO MUNDO passaria nos
# tres primeiros e pareceria consertada.
r_dono, l_dono = capturar(
    lambda: cliente.get(f"/api/tarefas/{ids['tarefa']}/link-envio",
                        headers=admin))
checa(6, "NAO-REGRESSAO: o dono continua recebendo o link, e o token nasce ai",
      r_dono.status_code == 200
      and "/enviar/" in (r_dono.json().get("link") or "")
      and token_no_banco() is not None)
checa(7, "e o dono nao gera ACESSO_NEGADO_IDOR",
      evento(l_dono, "ACESSO_NEGADO_IDOR") is None)

# Com o token ja criado, a recusa continua sendo recusa: o buraco nao pode
# reabrir so porque a tarefa passou a ter token.
r_fora2, _ = capturar(
    lambda: cliente.get(f"/api/tarefas/{ids['tarefa']}/link-envio",
                        headers=fora))
checa(8, "com o token ja existente, quem esta fora do escopo continua barrado",
      r_fora2.status_code == 404)


# ------------------------------------------------------------- (b) transferir
# Este e o irmao menor, e o cenario tem de ser montado com cuidado: a rota
# exige admin ou gestor, e o preset de gestor tem escopo `todas`. So um gestor
# de escopo REDUZIDO alcanca o buraco, e o app permite criar um.
db = SessionLocal()
gestor = Usuario(nome="Gestor de Setor", email="gestor@bps4.com.br",
                 grupo="gestor",
                 permissoes=json.dumps({"escopo_tarefas": "proprias"}),
                 senha_hash=get_password_hash(SENHA), ativo=True)
db.add(gestor)
db.commit()
ids["gestor"] = gestor.id
db.close()

gestor_h = entrar("gestor@bps4.com.br")
r_transf, l_transf = capturar(
    lambda: cliente.post(f"/api/tarefas/{ids['tarefa']}/transferir",
                         json={"responsavel_id": ids["fora"]},
                         headers=gestor_h))
checa(9, "gestor de escopo reduzido nao transfere tarefa que nao enxerga",
      r_transf.status_code == 404)
checa(10, "e a recusa tambem emite IDOR",
      evento(l_transf, "ACESSO_NEGADO_IDOR") is not None)

db = SessionLocal()
resp_atual = (db.query(Tarefa).filter(Tarefa.id == ids["tarefa"])
              .first().responsavel_id)
db.close()
checa(11, "e a tarefa continua com o responsavel de antes",
      resp_atual == ids["admin"])

# NAO-REGRESSAO do outro lado: o admin, que enxerga tudo, continua transferindo.
r_admin_transf, _ = capturar(
    lambda: cliente.post(f"/api/tarefas/{ids['tarefa']}/transferir",
                         json={"responsavel_id": ids["fora"]},
                         headers=admin))
checa(12, "NAO-REGRESSAO: admin continua transferindo normalmente",
      r_admin_transf.status_code == 200)


print()
if falhou:
    print(f"PROVA FALHOU nos itens: {sorted(set(falhou))}")
    sys.exit(1)
print(f"PROVA OK: {12 - len(falhou)} checagens verdes")
