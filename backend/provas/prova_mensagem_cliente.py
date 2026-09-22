"""
prova_mensagem_cliente.py: a mensagem que leva a guia ao cliente.

Decisões do usuário em 2026-09-21:
  - o e-mail vai SÓ com o link: o anexo sai do Google e o Tareffas não sabe se
    o cliente pegou a guia; o link é uma requisição aqui, e conta;
  - nome legível da guia pelo Mininome da obrigação, quando preenchido (1a);
  - texto aprovado: assunto "BPS4 | <nome>, <mês>/<ano>, <empresa>", saudação,
    competência por extenso, vencimento, botão "Baixar a guia" (2a);
  - o WhatsApp leva o mesmo texto, sem logo (3a);
  - o logo da BPS4 vai embutido (CID), porque Outlook bloqueia imagem externa.

WhatsApp e e-mail são dublês, e o item 10 troca o SMTP por um falso: nada sai.
O item 9 é não-regressão e passa JÁ no RED.

    python provas/prova_mensagem_cliente.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
_tmp = tempfile.mkdtemp(prefix="prova-mensagem-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = os.path.join(_tmp, "uploads")
os.environ.setdefault("SECRET_KEY", "chave-de-prova")

from app.database import Base, engine, SessionLocal                    # noqa: E402
from app.models import Obrigacao, Empresa, Tarefa, StatusTarefa, TarefaEnvio  # noqa: E402
from app.services import whatsapp, email as email_mod, upload as up    # noqa: E402
from app.services import entrega_cliente as ec                         # noqa: E402

Base.metadata.create_all(bind=engine)
TOTAL = 10
falhou = []


def checa(n, descricao, condicao):
    if condicao:
        print(f"  ok  {n:>3}. {descricao}")
    else:
        print(f"FALHA  {n:>3}. {descricao}")
        falhou.append(n)


EMAILS, ZAPS = [], []


def email_falso(to, subject, body, cfg, anexos=None, html=None, imagens=None):
    EMAILS.append({"to": to, "assunto": subject, "texto": body, "anexos": anexos,
                   "html": html, "imagens": imagens})
    return {"success": True}


async def zap_falso(phone, message, cfg, user_id=None):
    ZAPS.append({"to": phone, "texto": message})
    return {"success": True}


async def carregar_zap_falso(cfg):
    return {}

whatsapp.send_whatsapp_message = zap_falso
whatsapp.carregar_zap = carregar_zap_falso
email_mod.send_email = email_falso

db = SessionLocal()
emp = Empresa(razao_social="A & B <COMERCIO> LTDA", cnpj="11.222.333/0001-81",
              email="financeiro@cliente.com", telefone="21999998888")
o_min = Obrigacao(nome="das_simples", mininome="DAS do Simples Nacional", sentido="entregar")
o_sem = Obrigacao(nome="guia_iss_prestado", sentido="entregar")
db.add_all([emp, o_min, o_sem])
db.commit()


def tarefa_com_guia(obr, comp, venc):
    t = Tarefa(titulo=obr.nome, empresa_id=emp.id, obrigacao_id=obr.id, competencia=comp,
               status=StatusTarefa.PENDENTE, data_vencimento=venc)
    db.add(t)
    db.commit()
    t.saida_nome = up.salvar_saida(t.id, "guia.pdf", b"%PDF guia")
    db.commit()
    return t


def enviar(t):
    EMAILS.clear()
    ZAPS.clear()
    return asyncio.run(ec.entregar_saida(db, t, origem="prova"))


t1 = tarefa_com_guia(o_min, "08/2026", datetime(2026, 9, 20))
enviar(t1)
e = EMAILS[0] if EMAILS else {}
z = ZAPS[0] if ZAPS else {}
envs = {x.canal: x for x in db.query(TarefaEnvio).filter(TarefaEnvio.tarefa_id == t1.id).all()}
link_email = f"/api/publico/baixar/{envs['email'].token}" if "email" in envs else "?"
link_zap = f"/api/publico/baixar/{envs['whatsapp'].token}" if "whatsapp" in envs else "?"

checa(1, f"e-mail sem anexo: {e.get('anexos')!r}", e and not e.get("anexos"))
html = e.get("html") or ""
checa(2, "HTML com o logo por CID e o botão com o link DESTE destinatário",
      "cid:" in html and link_email in html and "Baixar a guia" in html and link_zap not in html)
imgs = e.get("imagens") or []
checa(3, f"logo embutido: {[(c, len(b)) for c, b in imgs]}",
      len(imgs) == 1 and imgs[0][1][:8] == b"\x89PNG\r\n\x1a\n" and f"cid:{imgs[0][0]}" in html)
from app.services.razao_social import formatar           # noqa: E402
nome_emp = formatar(emp.razao_social)
checa(4, f"assunto: {e.get('assunto')!r}",
      e.get("assunto") == f"BPS4 | DAS do Simples Nacional, agosto/2026, {nome_emp}")
texto = e.get("texto") or ""
checa(5, "texto com nome legível, competência por extenso, vencimento e link",
      "DAS do Simples Nacional" in texto and "agosto/2026" in texto
      and "Vencimento: 20/09/2026" in texto and link_email in texto and "das_simples" not in texto)
zt = z.get("texto") or ""
checa(6, "WhatsApp com o mesmo texto e o PRÓPRIO link",
      "DAS do Simples Nacional" in zt and "agosto/2026" in zt and link_zap in zt and link_email not in zt)
checa(7, "nome da empresa escapado no HTML",
      "&amp;" in html and "&lt;" in html and "<COMERCIO>" not in html)

t2 = tarefa_com_guia(o_sem, "12/2025", None)
enviar(t2)
e2 = EMAILS[0] if EMAILS else {}
checa(8, f"sem mininome usa o nome; sem vencimento a linha some: {e2.get('assunto')!r}",
      e2.get("assunto") == f"BPS4 | guia_iss_prestado, dezembro/2025, {nome_emp}"
      and "Vencimento" not in (e2.get("texto") or ""))

checa(9, "não-regressão: um envio por destinatário, com tokens distintos",
      len(envs) == 2 and envs.get("email") and envs.get("whatsapp")
      and envs["email"].token != envs["whatsapp"].token)

# 10. o send_email de verdade monta texto + HTML + imagem inline, com SMTP falso
import smtplib                                           # noqa: E402
ENVIADAS = []


class SmtpFalso:
    def __init__(self, *a, **k): pass
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def starttls(self): pass
    def login(self, *a): pass
    def send_message(self, msg): ENVIADAS.append(msg)


smtplib.SMTP = SmtpFalso
cfg = {"email_ativo": "1", "smtp_host": "smtp.falso", "smtp_from": "x@bps4.com.br"}
import importlib                                         # noqa: E402
real = importlib.reload(email_mod)
r1 = real.send_email("a@a.com", "assunto", "texto puro", cfg)
r2 = real.send_email("a@a.com", "assunto", "texto", cfg, html="<p>oi <img src='cid:logo'></p>",
                     imagens=[("logo", b"\x89PNG\r\n\x1a\nxx")])
tipos = [p.get_content_type() for p in ENVIADAS[1].walk()] if len(ENVIADAS) > 1 else []
checa(10, f"SMTP: só texto continua funcionando; com HTML sai {tipos}",
      r1.get("success") and r2.get("success") and ENVIADAS[0].get_content_type() == "text/plain"
      and "text/html" in tipos and "image/png" in tipos and "text/plain" in tipos)

db.close()
print()
if falhou:
    print(f"PROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print(f"PROVA OK: {TOTAL} checagens verdes")
