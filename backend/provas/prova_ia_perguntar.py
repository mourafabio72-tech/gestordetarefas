"""Prova do "Pergunte à IA" e das chaves de IA (pedido de 2026-10-05).

Itens 25 a 30 (2026-10-06): a NVIDIA tirou meta/llama-3.3-70b-instruct do
catálogo e passou a responder HTTP 410. Padrão novo, troca do nome antigo
guardado no banco, e 404/410 viram mensagem que manda trocar o modelo.

A IA só traduz a pergunta em filtro. Quem consulta o banco é o Tareffas, dentro
do escopo de quem perguntou. Para a IA vai a pergunta e a data de hoje, e nada
do banco: nome de cliente, CNPJ e título de tarefa não saem daqui.

Sem rede: o httpx.post do módulo de IA é trocado por um dublê que grava o que
recebeu e devolve a resposta combinada.

    cd backend && ./venv/bin/python provas/prova_ia_perguntar.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_ia_")
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
emp = Empresa(razao_social="Mark Building Ltda", nome_fantasia="MKB", cnpj="11222333000181")
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


tarefa("DCTFWeb MKB 09/2026", ana, fiscal, hoje)
tarefa("Reinf MKB 09/2026", ana, fiscal, hoje - timedelta(days=3))
tarefa("Conciliação MKB 09/2026", ana, contabil, hoje + timedelta(days=4))
tarefa("EFD MKB 09/2026", bruno, fiscal, hoje)
tarefa("Balancete MKB 08/2026", ana, contabil, hoje - timedelta(days=1), status=StatusTarefa.CONCLUIDA)
db.commit()
db.close()

CFG = "/api/configuracao/notificacoes"
PERG = "/api/ia/perguntar"

# 1. Sem chave nenhuma, a caixa diz que a IA não está configurada.
r = client.get("/api/ia/status", headers=cab("ana@x.com"))
checa(1, "status sem chave: indisponível", r.status_code == 200 and r.json().get("disponivel") is False,
      f"{r.status_code} {r.text[:120]}")

r = client.post(PERG, json={"pergunta": "o que vence hoje?"}, headers=cab("ana@x.com"))
checa(2, "perguntar sem chave: recusa clara, sem chamar rede",
      r.status_code == 409 and "configurad" in r.text.lower() and not chamadas,
      f"{r.status_code} {r.text[:120]}")

# 3. Só admin grava chave.
r = client.put(CFG, json={"nvidia_api_key": "nvapi-segredo-123"}, headers=cab("ana@x.com"))
checa(3, "analista não grava configuração", r.status_code == 403, f"{r.status_code}")

# 4. Admin grava chave da NVIDIA e escolhe o provedor; a chave não volta.
r = client.put(CFG, json={"nvidia_api_key": "nvapi-segredo-123", "ia_provedor": "nvidia",
                          "openai_api_key": "sk-segredo-456"}, headers=cab("admin@x.com"))
j = r.json() if r.status_code == 200 else {}
checa(4, "chaves gravadas e mascaradas na resposta",
      r.status_code == 200 and j.get("nvidia_api_key") == "" and j.get("nvidia_api_key_set") is True
      and j.get("openai_api_key") == "" and j.get("ia_provedor") == "nvidia"
      and "segredo" not in r.text, r.text[:200])

# 5. Salvar com a chave vazia mantém a guardada.
client.put(CFG, json={"nvidia_api_key": "", "nvidia_model": "nvidia/llama-3.1-nemotron-70b-instruct"},
           headers=cab("admin@x.com"))
r = client.get(CFG, headers=cab("admin@x.com"))
checa(5, "chave vazia no salvar mantém a guardada", r.json().get("nvidia_api_key_set") is True, r.text[:200])

# 6. Testar conexão da NVIDIA usa o endereço e a chave da NVIDIA, e não devolve a chave.
ia_devolve("OK")
chamadas.clear()
r = client.post("/api/configuracao/ia/testar", json={"provedor": "nvidia"}, headers=cab("admin@x.com"))
c = chamadas[-1] if chamadas else {}
checa(6, "testar NVIDIA: endereço e chave da NVIDIA",
      r.status_code == 200 and r.json().get("ok") is True
      and "integrate.api.nvidia.com" in c.get("url", "")
      and c.get("headers", {}).get("Authorization") == "Bearer nvapi-segredo-123"
      and "segredo" not in r.text, f"{r.status_code} {r.text[:160]} {c.get('url')}")

# 7. Testar OpenAI usa a chave da OpenAI.
chamadas.clear()
r = client.post("/api/configuracao/ia/testar", json={"provedor": "openai"}, headers=cab("admin@x.com"))
c = chamadas[-1] if chamadas else {}
checa(7, "testar OpenAI: chave da OpenAI",
      r.json().get("ok") is True and c.get("headers", {}).get("Authorization") == "Bearer sk-segredo-456",
      r.text[:160])

# 8. Provedor fora da lista é recusado.
r = client.post("/api/configuracao/ia/testar", json={"provedor": "outro"}, headers=cab("admin@x.com"))
checa(8, "provedor desconhecido: 422", r.status_code == 422, f"{r.status_code}")

# 9. Erro do provedor vira mensagem, não 500, e não ecoa a chave.
resposta_ia["status"] = 401
r = client.post("/api/configuracao/ia/testar", json={"provedor": "nvidia"}, headers=cab("admin@x.com"))
checa(9, "chave recusada pelo provedor: ok false com motivo",
      r.status_code == 200 and r.json().get("ok") is False and "401" in r.json().get("erro", "")
      and "segredo" not in r.text, r.text[:160])
resposta_ia["status"] = 200

# 10. Agora está disponível para colaborador.
r = client.get("/api/ia/status", headers=cab("ana@x.com"))
checa(10, "status com chave: disponível, provedor nvidia",
      r.json().get("disponivel") is True and r.json().get("provedor") == "nvidia", r.text[:120])

# 11. Cliente não usa.
r = client.post(PERG, json={"pergunta": "o que vence hoje?"}, headers=cab("cli@x.com"))
checa(11, "cliente: 403", r.status_code == 403, f"{r.status_code}")

# 12. "O que vence hoje": Ana vê só as dela (escopo próprias), e não a do Bruno.
ia_devolve({"situacao": "hoje"})
chamadas.clear()
r = client.post(PERG, json={"pergunta": "liste as tarefas que vencem hoje"}, headers=cab("ana@x.com"))
j = r.json() if r.status_code == 200 else {}
titulos = [t["titulo"] for t in j.get("tarefas", [])]
checa(12, "vence hoje no escopo da Ana: só a DCTFWeb dela",
      r.status_code == 200 and titulos == ["DCTFWeb MKB 09/2026"] and j.get("total") == 1,
      f"{r.status_code} {titulos} {r.text[:200]}")

# 13. Para a IA foi a pergunta e a data, e nada do banco.
enviado = json.dumps(chamadas[-1]["json"], ensure_ascii=False) if chamadas else ""
checa(13, "a IA não recebe nome de cliente, CNPJ nem título de tarefa",
      "vencem hoje" in enviado and agora.strftime("%Y-%m-%d") in enviado
      and not any(x in enviado for x in ("Mark Building", "MKB", "11222333000181", "DCTFWeb MKB", "Ana")),
      enviado[:300])

# 14. Admin (escopo todas) vê as duas que vencem hoje.
r = client.post(PERG, json={"pergunta": "o que vence hoje?"}, headers=cab("admin@x.com"))
checa(14, "admin vê as duas de hoje", r.json().get("total") == 2, r.text[:200])

# 15. Atrasadas do Fiscal: só a Reinf (a concluída de ontem não conta).
ia_devolve({"situacao": "atrasada", "setor": "fiscal"})
r = client.post(PERG, json={"pergunta": "o que está atrasado no fiscal"}, headers=cab("admin@x.com"))
titulos = [t["titulo"] for t in r.json().get("tarefas", [])]
checa(15, "atrasadas do Fiscal", titulos == ["Reinf MKB 09/2026"], f"{titulos}")

# 16. Contagem por obrigação: quantas DCTFWeb faltam.
ia_devolve({"obrigacao": "dctfweb", "situacao": "aberta", "contar": True})
r = client.post(PERG, json={"pergunta": "quantas DCTFWeb faltam?"}, headers=cab("admin@x.com"))
j = r.json()
checa(16, "contar DCTFWeb em aberto: 1", j.get("total") == 1 and j.get("contar") is True, r.text[:200])

# 17. A frase "entendi" sai do filtro validado, não do texto livre da IA.
checa(17, "entendi descreve o filtro", "dctfweb" in (j.get("entendi") or "").lower(), j.get("entendi"))

# 18. Campo inválido da IA é descartado, e o resto vale.
ia_devolve({"situacao": "xyz", "data_de": "ontem", "setor": "contábil", "prioridade": "maxima"})
r = client.post(PERG, json={"pergunta": "tarefas do contábil"}, headers=cab("admin@x.com"))
titulos = sorted(t["titulo"] for t in r.json().get("tarefas", []))
checa(18, "campos inválidos ignorados e só o setor vale (sem situação, a concluída entra)",
      r.status_code == 200 and titulos == ["Balancete MKB 08/2026", "Conciliação MKB 09/2026"]
      and set(r.json().get("ignorados", [])) >= {"situacao", "data_de", "prioridade"},
      f"{r.status_code} {titulos} {r.text[:200]}")

# 19. Resposta que não é JSON: mensagem, não 500.
ia_devolve("não sei responder isso")
r = client.post(PERG, json={"pergunta": "qual o sentido da vida"}, headers=cab("admin@x.com"))
checa(19, "IA sem JSON: 502 com mensagem", r.status_code == 502 and "detail" in r.json(), f"{r.status_code} {r.text[:120]}")

# 20. JSON cercado de texto (modelos da NVIDIA fazem isso) ainda é lido.
ia_devolve('Claro! Aqui está:\n```json\n{"situacao": "hoje"}\n```')
r = client.post(PERG, json={"pergunta": "vence hoje"}, headers=cab("admin@x.com"))
checa(20, "JSON dentro de cerca de código é lido", r.status_code == 200 and r.json().get("total") == 2,
      f"{r.status_code} {r.text[:160]}")

# 21. Filtro sem nenhum critério não despeja a base inteira sem aviso: devolve, com limite.
ia_devolve({"minhas": True})
r = client.post(PERG, json={"pergunta": "minhas tarefas"}, headers=cab("bruno@x.com"))
titulos = [t["titulo"] for t in r.json().get("tarefas", [])]
checa(21, "minhas tarefas do Bruno", titulos == ["EFD MKB 09/2026"], f"{titulos}")

# 22. Pergunta vazia ou longa demais: 422, sem gastar chamada.
chamadas.clear()
r1 = client.post(PERG, json={"pergunta": "  "}, headers=cab("ana@x.com"))
r2 = client.post(PERG, json={"pergunta": "x" * 301}, headers=cab("ana@x.com"))
checa(22, "pergunta vazia ou com mais de 300 caracteres: 422",
      r1.status_code == 422 and r2.status_code == 422 and not chamadas, f"{r1.status_code} {r2.status_code}")

# 23. Limite por pessoa: passou do teto na janela, 429.
ia_rota._uso.clear()
ia_devolve({"situacao": "hoje"})
codigos = [client.post(PERG, json={"pergunta": "vence hoje"}, headers=cab("ana@x.com")).status_code
           for _ in range(ia_rota.LIMITE + 1)]
checa(23, f"limite de {ia_rota.LIMITE} perguntas por janela: a seguinte é 429",
      codigos[:-1] == [200] * ia_rota.LIMITE and codigos[-1] == 429, f"{codigos}")

# 24. O limite é por pessoa: o Bruno continua perguntando.
r = client.post(PERG, json={"pergunta": "vence hoje"}, headers=cab("bruno@x.com"))
checa(24, "limite da Ana não trava o Bruno", r.status_code == 200, f"{r.status_code}")

# ---------- modelo retirado do catálogo (2026-10-06) ----------
from app.services import config as cfgmod                 # noqa: E402

ANTIGO = "meta/llama-3.3-70b-instruct"
NOVO = "nvidia/llama-3.1-nemotron-70b-instruct"

# 25. O padrão da NVIDIA é o modelo que está no catálogo.
checa(25, "padrão da NVIDIA é o nemotron, no código e na configuração",
      ia_mod.PROVEDORES["nvidia"][4] == NOVO
      and (os.getenv("NVIDIA_MODEL") or cfgmod.DEFAULTS["nvidia_model"] == NOVO),
      f"{ia_mod.PROVEDORES['nvidia'][4]} {cfgmod.DEFAULTS['nvidia_model']}")

# 26. Nome antigo guardado no banco é lido como o substituto, na tela e na chamada.
client.put(CFG, json={"nvidia_model": ANTIGO}, headers=cab("admin@x.com"))
r = client.get(CFG, headers=cab("admin@x.com"))
ia_devolve("OK")
chamadas.clear()
client.post("/api/configuracao/ia/testar", json={"provedor": "nvidia"}, headers=cab("admin@x.com"))
enviado = chamadas[-1]["json"].get("model") if chamadas else None
checa(26, "modelo retirado guardado no banco vira o substituto (tela e chamada)",
      r.json().get("nvidia_model") == NOVO and enviado == NOVO, f"{r.json().get('nvidia_model')} {enviado}")

# 27. Modelo que não é da lista de retirados passa intacto.
client.put(CFG, json={"nvidia_model": "meta/llama-3.1-8b-instruct"}, headers=cab("admin@x.com"))
r = client.get(CFG, headers=cab("admin@x.com"))
checa(27, "modelo fora da lista de retirados não é trocado",
      r.json().get("nvidia_model") == "meta/llama-3.1-8b-instruct", r.text[:160])

# 28. Testar com 410: manda trocar o modelo, sem corpo da resposta e sem chave.
resposta_ia["status"] = 410
r = client.post("/api/configuracao/ia/testar", json={"provedor": "nvidia"}, headers=cab("admin@x.com"))
erro = r.json().get("erro", "")
checa(28, "testar com HTTP 410: manda trocar o modelo, sem corpo nem chave",
      r.json().get("ok") is False and "410" in erro and "modelo" in erro.lower()
      and "configura" in erro.lower() and "erro do provedor" not in r.text and "segredo" not in r.text,
      r.text[:200])

# 29. Perguntar com 410: 502 com a mesma orientação, sem corpo nem chave.
ia_rota._uso.clear()
r = client.post(PERG, json={"pergunta": "vence hoje"}, headers=cab("admin@x.com"))
det = r.json().get("detail", "") if r.status_code == 502 else ""
checa(29, "perguntar com HTTP 410: 502 que manda trocar o modelo",
      "410" in det and "modelo" in det.lower() and "configura" in det.lower()
      and "erro do provedor" not in r.text and "segredo" not in r.text, f"{r.status_code} {r.text[:200]}")

# 30. 404 tem o mesmo tratamento.
resposta_ia["status"] = 404
r = client.post("/api/configuracao/ia/testar", json={"provedor": "nvidia"}, headers=cab("admin@x.com"))
erro = r.json().get("erro", "")
checa(30, "testar com HTTP 404: mesma orientação, sem corpo",
      "404" in erro and "modelo" in erro.lower() and "erro do provedor" not in r.text, r.text[:200])
resposta_ia["status"] = 200

print()
if falhou:
    print(f"FALHOU: {falhou}")
    sys.exit(1)
print("PROVA OK: 30 de 30")
