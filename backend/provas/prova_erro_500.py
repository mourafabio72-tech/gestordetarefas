"""Prova da Fase 20: a resposta de erro para de sair pelada.

Quando a rota levanta excecao sem tratamento, a resposta 500 sai por fora dos
middlewares deste app: o `ServerErrorMiddleware` do Starlette e o mais externo
de todos. Resultado medido pelo verificador funcional da Fase 18: a tela de erro
volta SEM `X-Request-ID` e SEM os cabecalhos de seguranca, que e justo o caso em
que o id mais serviria.

Esta prova mede a resposta que o cliente recebe, a linha que o servidor escreve,
e o traceback no stderr de um uvicorn de verdade. Nao mede o que o codigo parece
fazer.

    cd backend && ./venv/bin/python provas/prova_erro_500.py

Notas que regem: `CSRF_Cookies_Headers` (secao "Headers de seguranca (em toda
resposta)"), `Padrao_Logging_Estruturado`, `Revisao_Vulnerabilidades` item 9,
`Mapa_de_Conceitos_de_Seguranca` Familia 6 ("o cliente recebe pouca informacao,
o log do servidor recebe muita").
"""

from __future__ import annotations  # producao e 3.12, a maquina local e 3.9

import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_erro_500_")
_banco = os.path.join(_tmp, "prova.db")

# Precisam existir ANTES de importar o app: `database.py` le a URL no import.
os.environ["DATABASE_URL"] = f"sqlite:///{_banco}"
os.environ["SECRET_KEY"] = "chave-jwt-de-teste"
os.environ["ZOARIA_SSO_SECRET"] = ""

_BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND))

from fastapi.testclient import TestClient                      # noqa: E402

from app.database import Base, engine                          # noqa: E402
from app.seguranca import HEADERS_SEGURANCA, log_event         # noqa: E402
from app.main import app                                       # noqa: E402

Base.metadata.create_all(bind=engine)

CAMPOS = ["timestamp", "level", "event", "user_id", "ip", "request_id",
          "path", "method"]

PROIBIDAS = ["senha", "password", "token", "authorization", "cookie", "csrf",
             "cpf", "cartao", "secret"]

# A mensagem carrega de proposito as tres coisas que a Familia 6 manda nao
# mostrar ao cliente: SQL, caminho de arquivo e detalhe interno. Se qualquer
# pedaco dela chegar ao corpo da resposta, a fase falhou.
SEGREDO = "SELECT senha_hash FROM usuarios WHERE email='chefe@bps4.com.br'"


@app.get("/api/_prova_estoura")
def _prova_estoura():
    """Emite uma linha e ENTAO quebra: e o par que prova a correlacao."""
    log_event("PROVA_ANTES_DE_ESTOURAR")
    raise ValueError(SEGREDO)


# `raise_server_exceptions=False` porque o padrao do TestClient re-levanta a
# excecao dentro do teste em vez de devolver a resposta que o cliente veria.
cliente = TestClient(app, raise_server_exceptions=False)
cliente_estrito = TestClient(app)

falhou = []


def checa(n, descricao, condicao):
    if condicao:
        print(f"  ok  {n:>3}. {descricao}")
    else:
        print(f"FALHA  {n:>3}. {descricao}")
        falhou.append(n)


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


resp, linhas = capturar(lambda: cliente.get(
    "/api/_prova_estoura", headers={"X-Forwarded-For": "200.1.2.3"}))

antes = next((l for l in linhas if l.get("event") == "PROVA_ANTES_DE_ESTOURAR"), {})
erro = next((l for l in linhas if l.get("event") == "ERRO_NAO_TRATADO"), {})
corpo = resp.text or ""

# -------------------------------------------------------------------- (a) 500

checa(1, "excecao nao tratada devolve 500, e nao derruba a conexao",
      resp.status_code == 500)

# ------------------------------------------------------------ (b) X-Request-ID

checa(2, "a resposta de erro traz X-Request-ID",
      bool(resp.headers.get("X-Request-ID")))

# ------------------------------------------------------------ (c) correlacao

checa(3, "o X-Request-ID do erro e o mesmo id da linha de log daquele request",
      bool(antes.get("request_id"))
      and resp.headers.get("X-Request-ID") == antes.get("request_id"))

# ------------------------------------------------------ (d) headers da nota

faltando = [nome for nome in HEADERS_SEGURANCA
            if nome not in resp.headers]

checa(4, f"a resposta de erro traz os cabecalhos de seguranca (faltando: {faltando})",
      not faltando)

# ------------------------------------------------------------- (e) corpo mudo

vazamentos = [pedaco for pedaco in
              (SEGREDO, "Traceback", "ValueError", ".py", "seguranca", "app/")
              if pedaco in corpo]

checa(5, f"o corpo nao carrega traceback, excecao, caminho nem SQL (achados: {vazamentos})",
      not vazamentos)

checa(6, "o corpo e JSON generico, e nao pagina de texto do Starlette",
      resp.headers.get("content-type", "").startswith("application/json")
      and isinstance(resp.json(), dict))

# ------------------------------------------------ (f) a linha ERRO_NAO_TRATADO

checa(7, "o servidor escreve ERRO_NAO_TRATADO em nivel ERROR",
      erro.get("event") == "ERRO_NAO_TRATADO" and erro.get("level") == "ERROR")

checa(8, "a linha ERRO_NAO_TRATADO tem os oito campos da nota",
      all(campo in erro for campo in CAMPOS))

checa(9, "a linha do erro liga com a resposta: mesmo request_id, path e method",
      erro.get("request_id") == resp.headers.get("X-Request-ID")
      and erro.get("path") == "/api/_prova_estoura"
      and erro.get("method") == "GET"
      and erro.get("ip") == "200.1.2.3")

suspeitas = sorted({chave for l in linhas for chave in l
                    if any(p in chave.lower() for p in PROIBIDAS)})

checa(10, f"nenhuma chave da lista proibida aparece nas linhas (achadas: {suspeitas})",
      not suspeitas)

# -------------------------------------- o caminho feliz nao muda de comportamento

ok_resp = cliente.get("/api/health")

checa(11, "o caminho feliz segue 200 e com X-Request-ID",
      ok_resp.status_code == 200 and bool(ok_resp.headers.get("X-Request-ID")))

# ------------------- o modo de falha do servidor nao pode ser TROCADO pelo handler

relevantou = False
try:
    cliente_estrito.get("/api/_prova_estoura")
except ValueError:
    relevantou = True
except Exception:
    relevantou = False

checa(12, "o ServerErrorMiddleware continua re-levantando a excecao, que e o que "
          "faz o servidor logar o traceback",
      relevantou)

# ----------------- e a prova de campo: uvicorn de verdade, traceback no stderr

def porta_livre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


PORTA = porta_livre()
_servidor_py = os.path.join(_tmp, "servidor.py")
Path(_servidor_py).write_text(
    "import os, sys\n"
    f"os.environ['DATABASE_URL'] = 'sqlite:///{_banco}'\n"
    "os.environ['SECRET_KEY'] = 'chave-jwt-de-teste'\n"
    "os.environ['ZOARIA_SSO_SECRET'] = ''\n"
    f"sys.path.insert(0, {str(_BACKEND)!r})\n"
    "from app.main import app\n"
    "@app.get('/api/_prova_estoura_servidor')\n"
    "def _e():\n"
    "    raise ValueError('estouro proposital da prova')\n"
    "import uvicorn\n"
    f"uvicorn.run(app, host='127.0.0.1', port={PORTA}, log_level='error')\n",
    encoding="utf-8")

processo = subprocess.Popen(
    [sys.executable, _servidor_py],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

subiu = False
for _ in range(100):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORTA}/api/health", timeout=1)
        subiu = True
        break
    except Exception:
        time.sleep(0.2)

if subiu:
    try:
        urllib.request.urlopen(
            f"http://127.0.0.1:{PORTA}/api/_prova_estoura_servidor", timeout=5)
    except urllib.error.HTTPError:
        pass
    except Exception:
        pass
    time.sleep(0.5)

processo.terminate()
try:
    saida_servidor = processo.communicate(timeout=10)[0] or ""
except subprocess.TimeoutExpired:
    processo.kill()
    saida_servidor = processo.communicate()[0] or ""

checa(13, "o servidor de verdade subiu para a prova de campo", subiu)

checa(14, "o traceback CONTINUA saindo no log do servidor depois do handler",
      "Traceback" in saida_servidor and "ValueError" in saida_servidor)

for arquivo in Path(_tmp).glob("*"):
    arquivo.unlink()
os.rmdir(_tmp)

if falhou:
    print(f"\nPROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print("\nPROVA OK: 14 checagens verdes")
