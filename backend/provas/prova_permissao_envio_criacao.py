"""Prova da Fase 50: rotas que so pediam login.

Levantado em 2026-09-23, respondendo "quem pode incluir, alterar ou excluir":

(a) anexar a guia (POST /tarefas/{id}/saida) e enviar ao cliente
    (POST /tarefas/{id}/enviar-cliente) dependiam so de login + escopo. O grupo
    Consulta, que e "so visualiza", tem escopo `todas`: trocava a guia de
    qualquer tarefa e mandava ao cliente. Decisao do usuario: as duas exigem
    editar em tarefas.
(b) criar tarefa (POST /tarefas) exigia editar em tarefas, mas nao conferia o
    escopo: analista, com escopo `proprias`, criava tarefa para qualquer
    responsavel. Decisao: responsavel fora do alcance da 403; sem responsavel,
    a tarefa fica com quem criou.
(c) usuario do tipo CLIENTE entra no grupo Consulta (escopo `todas`) e nada no
    backend o prendia a propria empresa: via as tarefas, os documentos, as
    empresas e os usuarios de TODOS os clientes. Decisao: o cliente ve so a
    propria empresa, so leitura, e sem empresa nao ve nada.
(d) irmaos achados no mesmo levantamento: POST /auth/register criava conta
    com senha escolhida por qualquer logado (a conta nasce no grupo legado, que
    ve tudo); POST /alertas/enviar/{id} disparava WhatsApp de qualquer logado,
    quando o irmao /alertas/verificar ja exige admin.

    cd backend && ./venv/bin/python provas/prova_permissao_envio_criacao.py
"""

from __future__ import annotations  # producao e 3.12, a maquina local e 3.9

import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_perm_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["SECRET_KEY"] = "chave-de-prova-nao-usar-em-producao"
os.environ["ZOARIA_SSO_SECRET"] = ""

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient                  # noqa: E402
from app.database import Base, engine, SessionLocal        # noqa: E402
from app.models import (Usuario, Empresa, Tarefa,          # noqa: E402
                        TarefaEnvio, StatusTarefa)
from app.auth import get_password_hash, create_access_token  # noqa: E402
from app.services import whatsapp as zap                   # noqa: E402
from app.services import email as mail                     # noqa: E402
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


# -- dubles: nada sai para a rede ---------------------------------------------
enviados = []


async def zap_falso(phone, mensagem, cfg, user_id=None):
    enviados.append(("whatsapp", phone))
    return {"success": True, "error": None}


def mail_falso(to, subject, body, cfg, anexos=None, html=None, imagens=None):
    enviados.append(("email", to))
    return {"success": True, "error": None}


async def zap_vazio(cfg):
    return {"linha": "", "numero": {}, "user_id": {}}

zap.send_whatsapp_message = zap_falso
mail.send_email = mail_falso
zap.carregar_zap = zap_vazio

# -- cenario -------------------------------------------------------------------
db = SessionLocal()
h = get_password_hash("x")
emp_a = Empresa(razao_social="Cliente A Ltda", cnpj="11111111000111", email="fin@a.com")
emp_b = Empresa(razao_social="Cliente B Ltda", cnpj="22222222000122", email="fin@b.com")
db.add_all([emp_a, emp_b])
db.commit()
admin = Usuario(nome="Admin", email="admin@x.com", grupo="admin", senha_hash=h, ativo=True)
consulta = Usuario(nome="Consulta", email="consulta@x.com", grupo="consulta", senha_hash=h, ativo=True)
analista = Usuario(nome="Analista", email="analista@x.com", grupo="analista", senha_hash=h, ativo=True)
outro = Usuario(nome="Outro", email="outro@x.com", grupo="analista", senha_hash=h, ativo=True)
cli_a = Usuario(nome="Socio A", email="socio@a.com", grupo="consulta", tipo="cliente",
                empresa_id=emp_a.id, senha_hash=h, ativo=True)
# Cliente com grupo errado de proposito: a trava tem de ser o TIPO, e nao o
# grupo, senao um cadastro descuidado devolve o acesso total.
cli_admin = Usuario(nome="Socio Admin", email="socio2@a.com", grupo="admin", tipo="cliente",
                    empresa_id=emp_a.id, senha_hash=h, ativo=True)
cli_sem = Usuario(nome="Sem Empresa", email="sem@x.com", grupo="consulta", tipo="cliente",
                  empresa_id=None, senha_hash=h, ativo=True)
db.add_all([admin, consulta, analista, outro, cli_a, cli_admin, cli_sem])
db.commit()

t_a = Tarefa(titulo="Guia A", empresa_id=emp_a.id, competencia="08/2026",
             status=StatusTarefa.PENDENTE, anexo_nome="doc_a.pdf")
t_a.responsaveis = [analista]
t_a.responsavel_id = analista.id
t_b = Tarefa(titulo="Guia B", empresa_id=emp_b.id, competencia="08/2026",
             status=StatusTarefa.PENDENTE, anexo_nome="doc_b.pdf")
t_b.responsaveis = [outro]
t_b.responsavel_id = outro.id
db.add_all([t_a, t_b])
db.commit()
ids = dict(a=t_a.id, b=t_b.id, emp_a=emp_a.id, emp_b=emp_b.id, admin=admin.id,
           analista=analista.id, outro=outro.id, cli_a=cli_a.id)
db.close()

os.makedirs(os.environ["UPLOAD_DIR"], exist_ok=True)
for nome in ("doc_a.pdf", "doc_b.pdf"):
    Path(os.environ["UPLOAD_DIR"], nome).write_bytes(b"%PDF prova")


def tarefa(tid):
    s = SessionLocal()
    try:
        return s.query(Tarefa).filter(Tarefa.id == tid).first()
    finally:
        s.close()


def n_envios():
    s = SessionLocal()
    try:
        return s.query(TarefaEnvio).count()
    finally:
        s.close()


def n_tarefas():
    s = SessionLocal()
    try:
        return s.query(Tarefa).count()
    finally:
        s.close()


PDF = {"arquivo": ("DAS 08-2026.pdf", b"%PDF guia", "application/pdf")}

# ============================================================ (a) anexar e enviar
print("\n(a) anexar a guia e enviar ao cliente")
r = client.post(f"/api/tarefas/{ids['a']}/saida", headers=cab("consulta@x.com"), files=PDF)
checa(1, "Consulta NAO anexa guia (403)", r.status_code == 403, r.status_code)
checa(2, "e a tarefa continua sem guia", not tarefa(ids["a"]).saida_nome)

r = client.post(f"/api/tarefas/{ids['a']}/enviar-cliente?ensaio=true", headers=cab("consulta@x.com"))
checa(3, "Consulta NAO faz o ensaio de envio (403)", r.status_code == 403, r.status_code)

r = client.post(f"/api/tarefas/{ids['a']}/saida", headers=cab("analista@x.com"), files=PDF)
checa(4, "NAO-REGRESSAO: analista anexa a guia na propria tarefa", r.status_code == 200, r.text[:120])

envios_antes = n_envios()
r = client.post(f"/api/tarefas/{ids['a']}/enviar-cliente", headers=cab("consulta@x.com"))
checa(5, "com guia anexada, Consulta continua sem enviar (403) e nada sai",
      r.status_code == 403 and n_envios() == envios_antes and not enviados, r.status_code)

r = client.post(f"/api/tarefas/{ids['a']}/enviar-cliente?ensaio=true", headers=cab("analista@x.com"))
checa(6, "NAO-REGRESSAO: analista faz o ensaio na propria tarefa", r.status_code == 200, r.text[:120])

# ================================================================ (b) criar tarefa
print("\n(b) criar tarefa com escopo reduzido")
antes = n_tarefas()
r = client.post("/api/tarefas", headers=cab("analista@x.com"),
                json={"titulo": "Para o outro", "empresa_id": ids["emp_a"],
                      "responsavel_ids": [ids["outro"]]})
checa(7, "analista NAO cria tarefa para responsavel fora do alcance (403)",
      r.status_code == 403 and n_tarefas() == antes, r.status_code)

r = client.post("/api/tarefas", headers=cab("analista@x.com"),
                json={"titulo": "Mista", "empresa_id": ids["emp_a"],
                      "responsavel_ids": [ids["analista"], ids["outro"]]})
checa(8, "nem misturando ele com alguem de fora (403)",
      r.status_code == 403 and n_tarefas() == antes, r.status_code)

r = client.post("/api/tarefas", headers=cab("analista@x.com"),
                json={"titulo": "Sem ninguem", "empresa_id": ids["emp_a"]})
ok9 = r.status_code == 201 and [u["id"] for u in r.json().get("responsaveis", [])] == [ids["analista"]]
checa(9, "sem responsavel, a tarefa fica com quem criou", ok9, r.text[:160])

r = client.post("/api/tarefas", headers=cab("analista@x.com"),
                json={"titulo": "Minha", "empresa_id": ids["emp_a"],
                      "responsavel_ids": [ids["analista"]]})
checa(10, "NAO-REGRESSAO: analista cria para si mesmo", r.status_code == 201, r.text[:120])

r = client.post("/api/tarefas", headers=cab("admin@x.com"),
                json={"titulo": "Do admin", "empresa_id": ids["emp_b"],
                      "responsavel_ids": [ids["outro"]]})
checa(11, "NAO-REGRESSAO: admin cria para qualquer responsavel", r.status_code == 201, r.text[:120])

# ================================================================= (c) cliente
print("\n(c) usuario do tipo cliente preso a propria empresa")
r = client.get("/api/tarefas", headers=cab("socio@a.com"))
emps = {t["empresa_id"] for t in r.json()} if r.status_code == 200 else None
checa(12, "cliente lista so tarefas da propria empresa",
      r.status_code == 200 and emps == {ids["emp_a"]}, emps)

r = client.get(f"/api/tarefas/{ids['b']}", headers=cab("socio@a.com"))
checa(13, "tarefa de outra empresa pelo id: 404", r.status_code == 404, r.status_code)

r = client.get(f"/api/tarefas/{ids['b']}/anexo", headers=cab("socio@a.com"))
checa(14, "comprovante de outra empresa: 404", r.status_code == 404, r.status_code)

r = client.get(f"/api/tarefas/{ids['a']}/anexo", headers=cab("socio@a.com"))
checa(15, "comprovante da propria empresa: 200", r.status_code == 200, r.status_code)

r = client.get("/api/documentos", headers=cab("socio@a.com"))
corpo = r.json() if r.status_code == 200 else {}
docs = corpo if isinstance(corpo, list) else (corpo.get("documentos") or corpo.get("itens") or [])
checa(16, "acervo de documentos so com a propria empresa",
      r.status_code == 200 and docs and {d.get("empresa_id") for d in docs} == {ids["emp_a"]},
      [d.get("empresa_id") for d in docs])

r = client.get("/api/empresas", headers=cab("socio@a.com"))
checa(17, "lista de empresas so com a dele",
      r.status_code == 200 and [e["id"] for e in r.json()] == [ids["emp_a"]],
      r.text[:120])

r = client.get(f"/api/empresas/{ids['emp_b']}", headers=cab("socio@a.com"))
checa(18, "empresa alheia pelo id: 404", r.status_code == 404, r.status_code)

r = client.get("/api/usuarios", headers=cab("socio@a.com"))
checa(19, "lista de usuarios so com ele mesmo",
      r.status_code == 200 and [u["id"] for u in r.json()] == [ids["cli_a"]],
      [u.get("id") for u in r.json()] if r.status_code == 200 else r.status_code)

r = client.get(f"/api/usuarios/{ids['admin']}", headers=cab("socio@a.com"))
checa(20, "usuario alheio pelo id: 404", r.status_code == 404, r.status_code)

s = SessionLocal()
n_da_a = s.query(Tarefa).filter(Tarefa.empresa_id == ids["emp_a"]).count()
s.close()
r = client.get("/api/tarefas/dashboard/stats", headers=cab("socio@a.com"))
checa(21, "painel de numeros conta so a propria empresa",
      r.status_code == 200 and r.json().get("total_tarefas") == n_da_a, (n_da_a, r.text[:80]))

r = client.put(f"/api/tarefas/{ids['a']}", headers=cab("socio@a.com"), json={"titulo": "mexi"})
checa(22, "cliente NAO altera tarefa, nem da propria empresa (403)",
      r.status_code == 403 and tarefa(ids["a"]).titulo == "Guia A", r.status_code)

r = client.get("/api/obrigacoes", headers=cab("socio2@a.com"))
checa(23, "cliente com grupo admin por engano: obrigacoes 403", r.status_code == 403, r.status_code)

r = client.get("/api/tarefas", headers=cab("socio2@a.com"))
emps = {t["empresa_id"] for t in r.json()} if r.status_code == 200 else None
checa(24, "e continua vendo so a propria empresa", emps == {ids["emp_a"]}, emps)

r = client.get("/api/grupos", headers=cab("socio2@a.com"))
checa(25, "e rota de admin/gestor por grupo tambem recusa (403)", r.status_code == 403, r.status_code)

r = client.get("/api/tarefas", headers=cab("sem@x.com"))
checa(26, "cliente sem empresa nao ve tarefa nenhuma (falha fechado)",
      r.status_code == 200 and r.json() == [], r.text[:120])

r = client.get("/api/auth/me", headers=cab("socio@a.com"))
perm = r.json().get("permissoes_efetivas", {}) if r.status_code == 200 else {}
checa(27, "/auth/me mostra ao front a permissao real do cliente (tarefas: ver)",
      perm.get("tarefas") == "ver" and perm.get("obrigacoes") == "nenhum", perm)

r = client.get("/api/tarefas", headers=cab("admin@x.com"))
emps = {t["empresa_id"] for t in r.json()} if r.status_code == 200 else None
checa(28, "NAO-REGRESSAO: admin continua vendo as duas empresas",
      emps == {ids["emp_a"], ids["emp_b"]}, emps)

# ================================================================= (d) irmaos
print("\n(d) criar conta e disparar alerta")
r = client.post("/api/auth/register", headers=cab("socio@a.com"),
                json={"nome": "Intruso", "email": "intruso@x.com", "senha": "senha-boa-123"})
s = SessionLocal()
criado = s.query(Usuario).filter(Usuario.email == "intruso@x.com").first()
s.close()
checa(29, "cliente NAO cria conta pelo /auth/register (403)",
      r.status_code == 403 and criado is None, r.status_code)

r = client.post("/api/auth/register", headers=cab("analista@x.com"),
                json={"nome": "Intruso", "email": "intruso2@x.com", "senha": "senha-boa-123"})
checa(30, "analista tambem nao (403)", r.status_code == 403, r.status_code)

r = client.post("/api/auth/register", headers=cab("admin@x.com"),
                json={"nome": "Novo", "email": "novo@x.com", "senha": "senha-boa-123"})
checa(31, "NAO-REGRESSAO: admin cria", r.status_code == 201, r.text[:120])

r = client.post(f"/api/alertas/enviar/{ids['outro']}", headers=cab("analista@x.com"))
checa(32, "analista NAO dispara alerta de WhatsApp para outro (403)",
      r.status_code == 403 and not enviados, r.status_code)

print()
if falhou:
    print(f"PROVA FALHOU nos itens: {sorted(set(falhou))}")
    sys.exit(1)
print("PROVA OK: 32 checagens verdes")
