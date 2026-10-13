"""Prova da janela do mascote em texto (2026-10-14, o modelo do FinControl).

O que ela trava:
  - nome de empresa atendida e de pessoa não saem: viram X01 e P01, com prefixos
    distintos, e voltam como nome na resposta;
  - o título da tarefa sai com o nome da empresa trocado pelo código;
  - CNPJ não sai;
  - o escopo é o da tela de Tarefas (Bruno não vê as tarefas da Ana);
  - modelo gpt-4.1-mini na OpenAI, temperatura 0, histórico de 4;
  - cliente (usuário do tipo cliente) não conversa; sem chave, 409.

Sem rede: o httpx.post do módulo de IA é trocado por um dublê.

    cd backend && uv run --no-project --python 3.12 --with-requirements requirements.txt python provas/prova_ia_conversa.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_conv_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["SECRET_KEY"] = "chave-de-prova-nao-usar-em-producao"
os.environ["ZOARIA_SSO_SECRET"] = ""
os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("NVIDIA_API_KEY", None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient                  # noqa: E402
from app.database import Base, engine, SessionLocal        # noqa: E402
from app.models import Usuario, Empresa, Setor, Tarefa, StatusTarefa  # noqa: E402
from app.auth import get_password_hash, create_access_token  # noqa: E402
from app.main import app                                   # noqa: E402
from app.services import ia as ia_mod                      # noqa: E402
from app.routes import ia as ia_rota                       # noqa: E402
from app.services import ia_conversa as C                 # noqa: E402

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


# ---------- dublê da rede ----------
class Resp:
    def __init__(self, status, corpo):
        self.status_code = status
        self._corpo = corpo
        self.text = corpo if isinstance(corpo, str) else json.dumps(corpo)

    def json(self):
        return self._corpo if not isinstance(self._corpo, str) else json.loads(self._corpo)


chamadas = []
resposta_ia = {"conteudo": "{}", "status": 200}


def falso_post(url, headers=None, json=None, timeout=None):
    chamadas.append({"url": url, "headers": headers or {}, "json": json})
    if resposta_ia["status"] != 200:
        return Resp(resposta_ia["status"], "erro do provedor")
    return Resp(200, {"choices": [{"message": {"content": resposta_ia["conteudo"]}}]})


ia_mod.httpx.post = falso_post


def ia_devolve(d):
    resposta_ia["conteudo"] = d if isinstance(d, str) else json_dumps(d)
    resposta_ia["status"] = 200


json_dumps = json.dumps

# ---------- dados ----------
db = SessionLocal()
h = get_password_hash("x")
admin = Usuario(nome="Admin", email="admin@x.com", grupo="admin", senha_hash=h, ativo=True)
ana = Usuario(nome="Ana", email="ana@x.com", grupo="analista", senha_hash=h, ativo=True)
bruno = Usuario(nome="Bruno", email="bruno@x.com", grupo="analista", senha_hash=h, ativo=True)
db.add_all([admin, ana, bruno])
fiscal = Setor(nome="Fiscal")
contabil = Setor(nome="Contábil")
db.add_all([fiscal, contabil])
db.flush()
emp = Empresa(razao_social="Smart Luz Energia Ltda", nome_fantasia="Smartluz", cnpj="11222333000181")
db.add(emp)
db.flush()
cli = Usuario(nome="Socio Cliente", email="cli@x.com", grupo="consulta", tipo="cliente",
              empresa_id=emp.id, senha_hash=h, ativo=True)
db.add(cli)

agora = datetime.now()
hoje = agora.replace(hour=12, minute=0, second=0, microsecond=0)


def tarefa(titulo, resp, setor, prazo, status=StatusTarefa.PENDENTE, venc=None):
    t = Tarefa(titulo=titulo, empresa_id=emp.id, setor_id=setor.id, responsavel_id=resp.id,
               status=status, data_prazo=prazo, data_vencimento=venc or prazo)
    t.responsaveis = [resp]
    db.add(t)
    return t


tarefa("DCTFWeb Smartluz 09/2026", ana, fiscal, hoje)
tarefa("Reinf MKB 09/2026", ana, fiscal, hoje - timedelta(days=3))
tarefa("Conciliação MKB 09/2026", ana, contabil, hoje + timedelta(days=4))
tarefa("EFD MKB 09/2026", bruno, fiscal, hoje)
tarefa("Balancete MKB 08/2026", ana, contabil, hoje - timedelta(days=1), status=StatusTarefa.CONCLUIDA)
db.commit()
db.close()


CFG = "/api/configuracao/notificacoes"
CONV = "/api/ia/conversar"

r = client.post(CONV, json={"pergunta": "o que vence hoje?"}, headers=cab("ana@x.com"))
checa(1, "sem chave: 409, sem chamar rede", r.status_code == 409 and not chamadas, f"{r.status_code} {r.text[:120]}")

client.put(CFG, json={"openai_api_key": "sk-segredo-456", "ia_provedor": "openai"}, headers=cab("admin@x.com"))


def responde_com_codigo(url, headers=None, json=None, timeout=None):
    import re
    chamadas.append({"url": url, "headers": headers or {}, "json": json})
    perg = json["messages"][-1]["content"]
    x = re.search(r"X\d{2}", perg)
    p = re.search(r"P\d{2}", perg)
    texto = f"{x.group(0) if x else 'X01'} tem DCTFWeb hoje, com {p.group(0) if p else 'P01'}."
    return Resp(200, {"choices": [{"message": {"content": texto}}]})


ia_mod.httpx.post = responde_com_codigo
r = client.post(CONV, json={"pergunta": "o que a SMARTLUZ tem hoje com a Ana?",
                            "historico": [{"papel": "assistente", "texto": "Smart Luz Energia tem Reinf."}] * 6},
                headers=cab("ana@x.com"))
checa(2, "conversa responde 200", r.status_code == 200, f"{r.status_code} {r.text[:200]}")
corpo = chamadas[-1]["json"]
saiu = json_dumps(corpo, ensure_ascii=False).lower()
checa(3, "a pergunta saiu com X e P no lugar dos nomes",
      "smartluz" not in corpo["messages"][-1]["content"].lower() and "ana" not in corpo["messages"][-1]["content"].lower()
      and "X0" in corpo["messages"][-1]["content"] and "P0" in corpo["messages"][-1]["content"], corpo["messages"][-1]["content"])
resposta = r.json().get("resposta", "")
checa(4, "a resposta voltou com o nome da empresa e da pessoa",
      "Smart Luz Energia" in resposta and "Ana" in resposta, resposta)
for i, termo in enumerate(("smart luz", "smartluz", "11222333000181", "bruno", '"ana"'), 5):
    checa(i, f"nada de {termo} no que sairia", termo not in saiu)
dados = json.loads(corpo["messages"][1]["content"].split("DADOS:\n", 1)[1])
titulos = [t["obrigacao"] for t in dados["vencem_hoje"]]
checa(10, "o título sai com o código no lugar da empresa", titulos and all("smartluz" not in t.lower() for t in titulos)
      and any("X0" in t for t in titulos), str(titulos))
checa(11, "empresa e pessoa com prefixos distintos",
      all(t["empresa"].startswith("X") for t in dados["vencem_hoje"])
      and all(c.startswith("P") for t in dados["vencem_hoje"] for c in (t["responsaveis"] or [])))
checa(12, "modelo gpt-4.1-mini e temperatura 0", corpo["model"] == "gpt-4.1-mini" and corpo["temperature"] == 0,
      f"{corpo['model']} {corpo['temperature']}")
checa(13, "histórico de no máximo 4", len(corpo["messages"]) <= 2 + 4 + 1, str(len(corpo["messages"])))
checa(14, "as instruções separam empresa de pessoa", "Nunca troque um pelo outro" in C.INSTRUCOES)

# Escopo: o Bruno (analista) só vê as dele, como na tela de Tarefas.
r = client.post(CONV, json={"pergunta": "quantas tarefas abertas?"}, headers=cab("bruno@x.com"))
dados_b = json.loads(chamadas[-1]["json"]["messages"][1]["content"].split("DADOS:\n", 1)[1])
db2 = SessionLocal()
from app.models import Tarefa as T                          # noqa: E402
from app.routes.tarefas import _aplicar_escopo              # noqa: E402
bruno_u = db2.query(Usuario).filter(Usuario.email == "bruno@x.com").one()
esperado = _aplicar_escopo(db2.query(T), db2, bruno_u).filter(T.status != StatusTarefa.CANCELADA).count()
db2.close()
checa(15, "o escopo é o da tela de Tarefas",
      dados_b["resumo"]["abertas"] + dados_b["resumo"]["concluidas_no_mes"] <= esperado, f"{dados_b['resumo']} x {esperado}")

r = client.post(CONV, json={"pergunta": "o que vence hoje?"}, headers=cab("cli@x.com"))
checa(16, "usuário cliente não conversa", r.status_code == 403, f"{r.status_code}")
r = client.post(CONV, json={"pergunta": "   "}, headers=cab("ana@x.com"))
checa(17, "pergunta vazia é recusada", r.status_code == 422, f"{r.status_code}")

print(f"\nPROVA OK: 17 de 17" if not falhou else f"\nPROVA FALHOU: {falhou}")
sys.exit(1 if falhou else 0)
