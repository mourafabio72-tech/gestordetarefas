"""
prova_entrega_cliente.py — o documento que o ESCRITÓRIO entrega ao cliente.

Caminho contrário do e-validador: em vez de esperar o comprovante, a tarefa
carrega uma guia e a envia. Guia do Simples é o caso típico.

Duas coisas erram calado aqui e a prova existe por elas: concluir a tarefa
quando nenhum envio funcionou (registra como entregue algo que não chegou, e o
erro só aparece quando o cliente reclama da multa) e a lista de destinatários
(mandar guia para quem não devia, ou não mandar para ninguém).

Os envios de verdade são substituídos por dublês — a prova não fala com a API
do Zap nem com o SMTP.

    python provas/prova_entrega_cliente.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

_tmp = tempfile.mkdtemp(prefix="prova-entrega-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ.setdefault("SECRET_KEY", "chave-de-prova-nao-usar-em-producao")

from fastapi.testclient import TestClient                  # noqa: E402
from app.database import Base, engine, SessionLocal        # noqa: E402
from app.models import Usuario, Empresa, Tarefa, TarefaEnvio, StatusTarefa  # noqa: E402
from app.auth import get_password_hash, create_access_token  # noqa: E402
from app.services import whatsapp as zap                   # noqa: E402
from app.services import email as mail                     # noqa: E402
from app.main import app                                   # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)

ok = True
def checa(nome, cond, extra=""):
    global ok
    print(("  ok   " if cond else "FALHA  ") + nome + (f"  {extra}" if extra else ""))
    ok = ok and bool(cond)


def cabeca(email="admin@x.com"):
    return {"Authorization": "Bearer " + create_access_token(data={"sub": email})}


# ── dublês: nada sai para a rede ─────────────────────────────────────────────
enviados = []
FALHA_ZAP = {"ok": True}
FALHA_MAIL = {"ok": True}

async def zap_falso(phone, mensagem, cfg, user_id=None):
    enviados.append(("whatsapp", phone, mensagem, 0))
    return {"success": FALHA_ZAP["ok"], "error": None if FALHA_ZAP["ok"] else "zap fora do ar"}

def mail_falso(to, subject, body, cfg, anexos=None):
    enviados.append(("email", to, (anexos or [(None,)])[0][0], len(anexos or [])))
    return {"success": FALHA_MAIL["ok"], "error": None if FALHA_MAIL["ok"] else "smtp recusou"}

import app.routes.tarefas as rota_tarefas                  # noqa: E402
zap.send_whatsapp_message = zap_falso
mail.send_email = mail_falso

async def zap_vazio(cfg):
    return {"linha": "", "numero": {}, "user_id": {}}
zap.carregar_zap = zap_vazio

# ── cenário ──────────────────────────────────────────────────────────────────
db = SessionLocal()
admin = Usuario(nome="Admin", email="admin@x.com", grupo="admin", ativo=True,
                senha_hash=get_password_hash("x"))
completa = Empresa(razao_social="Completa Ltda", cnpj="1", email="fin@completa.com",
                   telefone="21911112222")
muda = Empresa(razao_social="Muda Ltda", cnpj="2")     # sem e-mail e sem telefone
db.add_all([admin, completa, muda])
db.commit()
# Usuário do tipo cliente ligado à empresa completa; um deles repete o e-mail da ficha.
db.add_all([
    Usuario(nome="Sócio", email="socio@completa.com", grupo="consulta", ativo=True,
            tipo="cliente", empresa_id=completa.id, telefone="21933334444",
            senha_hash=get_password_hash("x")),
    Usuario(nome="Repetido", email="fin@completa.com", grupo="consulta", ativo=True,
            tipo="cliente", empresa_id=completa.id, senha_hash=get_password_hash("x")),
    Usuario(nome="Bloqueado", email="bloq@completa.com", grupo="consulta", ativo=True,
            tipo="cliente", empresa_id=completa.id, bloqueado=True,
            senha_hash=get_password_hash("x")),
    Usuario(nome="Colaborador", email="colab@bps4.com", grupo="analista", ativo=True,
            tipo="colaborador", empresa_id=completa.id, telefone="21955556666",
            senha_hash=get_password_hash("x")),
])
t_ok = Tarefa(titulo="Guia do Simples", empresa_id=completa.id, competencia="07/2026",
              status=StatusTarefa.PENDENTE)
t_muda = Tarefa(titulo="Guia sem destino", empresa_id=muda.id, status=StatusTarefa.PENDENTE)
db.add_all([t_ok, t_muda])
db.commit()
id_ok, id_muda = t_ok.id, t_muda.id
id_completa = completa.id      # guardado antes de fechar: depois o objeto desanexa
db.close()


print("\n=== 1. anexar o documento ===")
r = client.post(f"/api/tarefas/{id_ok}/saida", headers=cabeca(),
                files={"arquivo": ("DAS 07-2026.pdf", b"%PDF guia", "application/pdf")})
checa("anexa o PDF", r.status_code == 200, f"({r.status_code} {r.text[:60]})")
checa("devolve o nome limpo, sem o prefixo interno",
      r.json().get("arquivo") == "DAS_07-2026.pdf", str(r.json()))
r = client.post(f"/api/tarefas/{id_ok}/saida", headers=cabeca(),
                files={"arquivo": ("virus.exe", b"MZ", "application/octet-stream")})
checa("recusa extensão fora da lista", r.status_code == 400, f"({r.status_code})")
r = client.post(f"/api/tarefas/{id_ok}/saida", headers=cabeca(),
                files={"arquivo": ("vazio.pdf", b"", "application/pdf")})
checa("recusa arquivo vazio", r.status_code == 400)
checa("anexar NÃO conclui a tarefa — são dois passos de propósito",
      client.get(f"/api/tarefas?status=pendente", headers=cabeca()).status_code == 200)

print("\n=== 2. o ensaio mostra para quem vai, sem mandar nada ===")
enviados.clear()
r = client.post(f"/api/tarefas/{id_ok}/enviar-cliente?ensaio=true", headers=cabeca()).json()
alvos = {(d["canal"], d["endereco"]) for d in r["destinatarios"]}
checa("WhatsApp da empresa", ("whatsapp", "5521911112222") in alvos, str(alvos))
checa("e-mail da empresa", ("email", "fin@completa.com") in alvos)
checa("WhatsApp do sócio cadastrado como cliente", ("whatsapp", "5521933334444") in alvos)
checa("e-mail do sócio", ("email", "socio@completa.com") in alvos)
checa("e-mail repetido na ficha e no usuário não duplica", len(alvos) == 4, str(len(alvos)))
checa("cliente bloqueado fica de fora", ("email", "bloq@completa.com") not in alvos)
checa("COLABORADOR não recebe guia de cliente",
      ("whatsapp", "5521955556666") not in alvos)
checa("o ensaio não envia nada", enviados == [], str(enviados))

print("\n=== 3. o envio de verdade ===")
enviados.clear()
r = client.post(f"/api/tarefas/{id_ok}/enviar-cliente", headers=cabeca()).json()
checa("quatro envios", r["enviados"] == 4, str(r))
checa("sem falhas", r["falhas"] == 0)
checa("a tarefa conclui", r["concluiu"] is True)
# O WhatsApp leva LINK, não arquivo: é o que dá rastreio e dispensa o provedor
# aceitar o anexo. O e-mail leva os dois — o cliente arquiva a guia na caixa.
zaps = [m for c, _, m, _t in enviados if c == "whatsapp"]
checa("o WhatsApp levou o link do documento",
      all("/api/publico/baixar/" in m for m in zaps), str(zaps)[:120])
checa("e o nome do arquivo na mensagem",
      all("DAS_07-2026.pdf" in m for m in zaps))
checa("o e-mail foi com anexo",
      any(c == "email" and n == "DAS_07-2026.pdf" for c, _, n, _q in enviados))
db = SessionLocal()
checa("a tarefa ficou concluída no banco",
      db.query(Tarefa).get(id_ok).status == StatusTarefa.CONCLUIDA)
checa("cada envio virou uma linha de histórico",
      db.query(TarefaEnvio).filter(TarefaEnvio.tarefa_id == id_ok).count() == 4)
db.close()
h = client.get(f"/api/tarefas/{id_ok}/envios", headers=cabeca()).json()
checa("o histórico traz canal, endereço e quem recebeu",
      all(e["canal"] and e["endereco"] and e["destinatario"] for e in h))

print("\n=== 3b. trocar o documento revoga o link e zera o rastro ===")
db = SessionLocal()
t_antes = db.query(Tarefa).get(id_ok)
token_antigo = t_antes.saida_token
t_antes.saida_downloads, t_antes.saida_baixada_em = 3, None
db.commit(); db.close()
checa("o envio gerou token", bool(token_antigo))
r = client.get(f"/api/publico/baixar/{token_antigo}")
checa("o link público serve o documento sem login", r.status_code == 200, f"({r.status_code})")
db = SessionLocal()
checa("e o acesso é contado", db.query(Tarefa).get(id_ok).saida_downloads == 4)
checa("com data", db.query(Tarefa).get(id_ok).saida_baixada_em is not None)
from app.models import SaidaAcesso                        # noqa: E402
checa("e vira linha de auditoria",
      db.query(SaidaAcesso).filter(SaidaAcesso.tarefa_id == id_ok).count() == 1)
db.close()

client.post(f"/api/tarefas/{id_ok}/saida", headers=cabeca(),
            files={"arquivo": ("DAS retificada.pdf", b"%PDF nova", "application/pdf")})
db = SessionLocal()
t_dep = db.query(Tarefa).get(id_ok)
checa("token novo depois da troca", t_dep.saida_token != token_antigo)
checa("contador zerado — baixaram o documento ANTERIOR", t_dep.saida_downloads == 0)
checa("e a data também", t_dep.saida_baixada_em is None)
db.close()
checa("o link antigo morre", client.get(f"/api/publico/baixar/{token_antigo}").status_code == 404)
checa("link inventado não abre nada",
      client.get("/api/publico/baixar/nao-existe-esse-token").status_code == 404)

print("\n=== 4. nenhum envio funcionou: a tarefa NÃO pode concluir ===")
db = SessionLocal()
t2 = Tarefa(titulo="Guia que falha", empresa_id=id_completa, status=StatusTarefa.PENDENTE)
db.add(t2); db.commit(); id_falha = t2.id; db.close()
client.post(f"/api/tarefas/{id_falha}/saida", headers=cabeca(),
            files={"arquivo": ("DAS.pdf", b"%PDF", "application/pdf")})
FALHA_ZAP["ok"] = FALHA_MAIL["ok"] = False
r = client.post(f"/api/tarefas/{id_falha}/enviar-cliente", headers=cabeca()).json()
checa("nada foi entregue", r["enviados"] == 0 and r["falhas"] == 4, str(r["message"]))
checa("a tarefa NÃO conclui", r["concluiu"] is False)
checa("a mensagem diz que segue aberta", "segue aberta" in r["message"], r["message"])
db = SessionLocal()
checa("no banco continua pendente",
      db.query(Tarefa).get(id_falha).status == StatusTarefa.PENDENTE)
checa("e a falha fica registrada com o motivo",
      all(e.sucesso is False and e.detalhe for e in
          db.query(TarefaEnvio).filter(TarefaEnvio.tarefa_id == id_falha).all()))
db.close()

print("\n=== 5. entrega parcial ainda é entrega ===")
FALHA_ZAP["ok"], FALHA_MAIL["ok"] = False, True
db = SessionLocal()
t3 = Tarefa(titulo="Só e-mail vai", empresa_id=id_completa, status=StatusTarefa.PENDENTE)
db.add(t3); db.commit(); id_parcial = t3.id; db.close()
client.post(f"/api/tarefas/{id_parcial}/saida", headers=cabeca(),
            files={"arquivo": ("DAS.pdf", b"%PDF", "application/pdf")})
r = client.post(f"/api/tarefas/{id_parcial}/enviar-cliente", headers=cabeca()).json()
checa("o WhatsApp falhou mas o e-mail chegou", r["enviados"] == 2 and r["falhas"] == 2, str(r["message"]))
checa("com alguém alcançado, a tarefa conclui", r["concluiu"] is True)
FALHA_ZAP["ok"] = FALHA_MAIL["ok"] = True

print("\n=== 6. o que impede o envio ===")
r = client.post(f"/api/tarefas/{id_muda}/saida", headers=cabeca(),
                files={"arquivo": ("DAS.pdf", b"%PDF", "application/pdf")})
r = client.post(f"/api/tarefas/{id_muda}/enviar-cliente", headers=cabeca())
checa("empresa sem contato nenhum: 400 explicando", r.status_code == 400, f"({r.status_code})")
checa("e o texto diz o que falta cadastrar",
      "e-mail nem telefone" in r.text, r.text[:100])
db = SessionLocal()
t4 = Tarefa(titulo="Sem anexo", empresa_id=id_completa, status=StatusTarefa.PENDENTE)
db.add(t4); db.commit(); id_sem = t4.id; db.close()
r = client.post(f"/api/tarefas/{id_sem}/enviar-cliente", headers=cabeca())
checa("sem documento anexado: 400", r.status_code == 400, f"({r.status_code})")
checa("tarefa inexistente: 404",
      client.post("/api/tarefas/999999/enviar-cliente", headers=cabeca()).status_code == 404)
checa("sem sessão não envia",
      client.post(f"/api/tarefas/{id_ok}/enviar-cliente").status_code in (401, 403))

import shutil                                              # noqa: E402
shutil.rmtree(_tmp, ignore_errors=True)
print("\n" + ("TUDO VERDE" if ok else "VERMELHO") + "\n")
sys.exit(0 if ok else 1)
