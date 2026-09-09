"""Prova das Fases 18 e 19: os campos obrigatorios entram sozinhos no log.

A `Padrao_Logging_Estruturado` da vault manda oito campos em TODA linha de log:
`timestamp`, `level`, `event`, `user_id`, `ip`, `request_id`, `path` e `method`.
O `log_event` deste projeto garantia tres, e os outros cinco dependiam de o
chamador lembrar. Esta prova mede o que sai no stdout de verdade, e nao o que o
codigo parece fazer.

    cd backend && ./venv/bin/python provas/prova_logging.py

Roda contra as rotas reais, num SQLite temporario, e nao deixa arquivo para tras.
As rotas `_prova_*` sao criadas aqui, nesta prova, e nao existem em producao:
servem para emitir duas linhas dentro do MESMO request, que e a unica forma de
provar que o `request_id` correlaciona.
"""

from __future__ import annotations  # producao e 3.12, a maquina local e 3.9

import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_logging_")
_banco = os.path.join(_tmp, "prova.db")

# Precisam existir ANTES de importar o app: `database.py` le a URL no import.
os.environ["DATABASE_URL"] = f"sqlite:///{_banco}"
os.environ["SECRET_KEY"] = "chave-jwt-de-teste"
os.environ["ZOARIA_SSO_SECRET"] = ""

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import Depends                                    # noqa: E402
from fastapi.testclient import TestClient                      # noqa: E402

from app.auth import get_current_user, get_password_hash       # noqa: E402
from app.database import Base, engine, SessionLocal            # noqa: E402
from app.models import Usuario                                 # noqa: E402
from app.seguranca import log_event                            # noqa: E402
from app.main import app                                       # noqa: E402

Base.metadata.create_all(bind=engine)

SENHA = "senha-boa-123"
EMAIL = "logueiro@bps4.com.br"

# A ordem da tabela da nota, verbatim. Linha de log e coisa que ferramenta le, e
# ordem estavel de campo e o que deixa um `grep` de olho humano funcionar.
CAMPOS = ["timestamp", "level", "event", "user_id", "ip", "request_id",
          "path", "method"]

# Lista absoluta da nota, na forma de pedaco de nome de chave. Nenhuma linha de
# log pode carregar chave que case com um destes.
PROIBIDAS = ["senha", "password", "token", "authorization", "cookie", "csrf",
             "cpf", "cartao", "secret"]


@app.get("/api/_prova_duas_linhas")
def _prova_duas_linhas():
    """Duas linhas no mesmo request: e o que prova a correlacao."""
    log_event("PROVA_PRIMEIRA")
    log_event("PROVA_SEGUNDA", user_id=4242, ip="9.9.9.9")
    return {"ok": True}


@app.get("/api/_prova_autenticada")
def _prova_autenticada(current_user: Usuario = Depends(get_current_user)):
    """Rota autenticada: o `user_id` tem que vir sozinho, sem a rota passar."""
    log_event("PROVA_AUTENTICADA")
    return {"id": current_user.id}


cliente = TestClient(app)


def semear():
    db = SessionLocal()
    try:
        if not db.query(Usuario).filter(Usuario.email == EMAIL).first():
            db.add(Usuario(nome="Pessoa do Log", email=EMAIL, grupo="admin",
                           senha_hash=get_password_hash(SENHA), ativo=True))
            db.commit()
    finally:
        db.close()


def capturar(funcao):
    """Roda `funcao` com o stdout desviado e devolve (retorno, linhas JSON)."""
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


semear()
falhou = []


def checa(n, descricao, condicao):
    if condicao:
        print(f"  ok  {n:>3}. {descricao}")
    else:
        print(f"FALHA  {n:>3}. {descricao}")
        falhou.append(n)


# ---------------------------------------------------------------- (a) e ordem

resp, linhas = capturar(lambda: cliente.get(
    "/api/_prova_duas_linhas", headers={"X-Forwarded-For": "200.1.2.3"}))

primeira = linhas[0] if linhas else {}

checa(1, "linha emitida dentro de request tem os oito campos da nota",
      all(campo in primeira for campo in CAMPOS))

checa(2, "os oito campos saem na ordem da tabela da nota",
      list(primeira.keys())[:8] == CAMPOS)

checa(3, "path e method vem do request, sem a rota passar",
      primeira.get("path") == "/api/_prova_duas_linhas"
      and primeira.get("method") == "GET")

checa(4, "o ip vem do X-Forwarded-For pelo ip_cliente que ja existia",
      primeira.get("ip") == "200.1.2.3")

# ------------------------------------------------------------------------ (c)

checa(5, "duas linhas do MESMO request tem o mesmo request_id",
      len(linhas) >= 2
      and linhas[0].get("request_id")
      and linhas[0]["request_id"] == linhas[1]["request_id"])

# ------------------------------------------------------------------------ (e)

checa(6, "chamador que passa o campo a mao vence o default",
      len(linhas) >= 2
      and linhas[1].get("user_id") == 4242
      and linhas[1].get("ip") == "9.9.9.9")

# ------------------------------------------------------------------ X-Request-ID

checa(7, "X-Request-ID volta na resposta com o valor da linha de log",
      bool(resp.headers.get("X-Request-ID"))
      and resp.headers.get("X-Request-ID") == primeira.get("request_id"))

# ------------------------------------------------------------------------ (b)

_, linhas2 = capturar(lambda: cliente.get("/api/_prova_duas_linhas"))

checa(8, "dois requests distintos tem request_id diferente",
      linhas2 and linhas2[0].get("request_id") != primeira.get("request_id"))

checa(9, "o request_id tem os 16 hexadecimais que a nota usa",
      isinstance(primeira.get("request_id"), str)
      and len(primeira["request_id"]) == 16
      and all(c in "0123456789abcdef" for c in primeira["request_id"]))

# ------------------------------------------------------------------------ (d)

def _fora_de_request():
    log_event("PROVA_SCHEDULER")
    return True


try:
    _, linhas3 = capturar(_fora_de_request)
    quebrou = False
except Exception:
    linhas3, quebrou = [], True

checa(10, "log_event fora de request nao levanta excecao", not quebrou)

fora = linhas3[0] if linhas3 else {}
checa(11, "fora de request os cinco campos vem como null, e nao somem",
      all(campo in fora for campo in CAMPOS)
      and fora.get("request_id") is None
      and fora.get("path") is None
      and fora.get("method") is None
      and fora.get("user_id") is None
      and fora.get("ip") is None)

# ------------------------------------------------- user_id vem da autenticacao

token = cliente.post("/api/auth/login",
                     json={"email": EMAIL, "senha": SENHA}).json()["access_token"]

_, linhas4 = capturar(lambda: cliente.get(
    "/api/_prova_autenticada", headers={"Authorization": f"Bearer {token}"}))

db = SessionLocal()
try:
    id_esperado = db.query(Usuario).filter(Usuario.email == EMAIL).first().id
finally:
    db.close()

checa(12, "em request autenticado o user_id vem sozinho, da dependencia de auth",
      linhas4 and linhas4[0].get("user_id") == id_esperado)

checa(13, "em request anonimo o user_id e null, e nao o do ultimo que passou",
      bool(linhas2) and "user_id" in linhas2[0]
      and linhas2[0]["user_id"] is None)

# --------------------------------------------------- (f) e a grafia do campo

_, linhas5 = capturar(lambda: cliente.post(
    "/api/auth/login", json={"email": EMAIL, "senha": SENHA},
    headers={"X-Forwarded-For": "200.1.2.4"}))

login_ok = next((l for l in linhas5 if l.get("event") == "LOGIN_OK"), {})

checa(14, "a linha do LOGIN_OK traz user_id, a grafia da nota",
      login_ok.get("user_id") == id_esperado)

checa(15, "nenhuma linha carrega o campo legado usuario_id",
      all("usuario_id" not in l for l in linhas + linhas2 + linhas4 + linhas5))

todas = linhas + linhas2 + linhas3 + linhas4 + linhas5
suspeitas = sorted({chave for l in todas for chave in l
                    if any(p in chave.lower() for p in PROIBIDAS)})

checa(16, f"nenhuma chave da lista proibida aparece em linha nenhuma (achadas: {suspeitas})",
      not suspeitas)

# --------------------------------- 17. o codigo-fonte inteiro, e nao so o que
#     esta prova consegue exercitar. Um `grep -n "usuario_id="` nao enxerga
#     chamada quebrada em duas linhas, e foi assim que `tarefas.py:433` passou
#     batido na primeira medicao. Aqui a leitura e por AST, e cobre os 14
#     chamadores do log_event, inclusive os que nenhuma prova chama.
import ast                                                     # noqa: E402

_legado = []
for _arquivo in sorted(Path("app").rglob("*.py")):
    _arvore = ast.parse(_arquivo.read_text(encoding="utf-8"), filename=str(_arquivo))
    for _no in ast.walk(_arvore):
        if isinstance(_no, ast.Call) and getattr(_no.func, "id", None) == "log_event":
            for _kw in _no.keywords:
                if _kw.arg in ("usuario_id", "usuario", "userid"):
                    _legado.append(f"{_arquivo}:{_no.lineno} passa {_kw.arg}")

checa(17, f"nenhum chamador do log_event no codigo passa o campo legado (achados: {_legado})",
      not _legado)

for arquivo in Path(_tmp).glob("*"):
    arquivo.unlink()
os.rmdir(_tmp)

if falhou:
    print(f"\nPROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print("\nPROVA OK: 17 checagens verdes")
