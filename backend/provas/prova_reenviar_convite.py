"""Prova do reenvio de convite (pedido de 2026-10-05).

O convite de primeiro acesso so aparecia na tela para quem ainda nao tinha
ativado a conta. Pedido do usuario: poder reenviar a qualquer usuario, mesmo
ativo (quem esqueceu a senha, quem trocou de computador). O link e o mesmo da
ativacao: a pessoa define uma senha nova.

    cd backend && ./venv/bin/python provas/prova_reenviar_convite.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_convite_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["SECRET_KEY"] = "chave-de-prova-nao-usar-em-producao"
os.environ["ZOARIA_SSO_SECRET"] = ""

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient                  # noqa: E402
from app.database import Base, engine, SessionLocal        # noqa: E402
from app.models import Usuario                             # noqa: E402
from app.auth import get_password_hash, create_access_token, verify_password  # noqa: E402
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


enviados = []


def mail_falso(para, assunto, corpo, cfg=None, **kw):
    enviados.append({"para": para, "assunto": assunto, "corpo": corpo})
    return {"success": True}


mail.send_email = mail_falso

db = SessionLocal()
h = get_password_hash("senha-antiga")
admin = Usuario(nome="Admin", email="admin@x.com", grupo="admin", senha_hash=h, ativo=True, ativado=True)
analista = Usuario(nome="Analista", email="analista@x.com", grupo="analista", senha_hash=h, ativo=True, ativado=True)
ativa = Usuario(nome="Ana Ativa", email="ana@x.com", grupo="analista", senha_hash=h, ativo=True, ativado=True)
pendente = Usuario(nome="Paulo Pendente", email="paulo@x.com", grupo="analista", senha_hash=h, ativo=True, ativado=False)
bloq = Usuario(nome="Bia Bloqueada", email="bia@x.com", grupo="analista", senha_hash=h, ativo=True, ativado=True, bloqueado=True)
db.add_all([admin, analista, ativa, pendente, bloq]); db.commit()
ids = {u.email: u.id for u in (admin, analista, ativa, pendente, bloq)}
db.close()


def usuario(email):
    s = SessionLocal()
    u = s.query(Usuario).filter(Usuario.email == email).first()
    s.expunge(u); s.close()
    return u


# 1. Reenviar a quem ja esta ativo: 200, sai o e-mail com o link, e a conta
#    continua ativa (ela nao perde o acesso so por receber o link).
r = client.post(f"/api/usuarios/{ids['ana@x.com']}/convite", headers=cab("admin@x.com"))
u = usuario("ana@x.com")
checa(1, "convite para usuario ATIVO responde 200 e envia",
      r.status_code == 200 and len(enviados) == 1 and enviados[0]["para"] == "ana@x.com",
      f"{r.status_code} {r.text[:120]} enviados={len(enviados)}")
checa(2, "a conta continua ativa e ganha token novo",
      u.ativado is True and bool(u.convite_token) and u.convite_token in enviados[0]["corpo"],
      f"ativado={u.ativado} token={u.convite_token!r}")

# 3. O texto para quem ja tem acesso fala em senha nova, e nao em "acesso criado".
corpo = enviados[0]["corpo"].lower()
checa(3, "mensagem para ativo fala em definir nova senha",
      "nova senha" in corpo and "foi criado" not in corpo, enviados[0]["corpo"])

# 4. Reenviar de novo invalida o link anterior.
token_1 = u.convite_token
client.post(f"/api/usuarios/{ids['ana@x.com']}/convite", headers=cab("admin@x.com"))
r_velho = client.get(f"/api/publico/ativar/{token_1}")
checa(4, "o link anterior deixa de valer", r_velho.status_code == 404, f"{r_velho.status_code}")

# 5. O link novo troca a senha.
token_2 = usuario("ana@x.com").convite_token
r = client.post(f"/api/publico/ativar/{token_2}", json={"senha": "senha-nova-123"})
u = usuario("ana@x.com")
checa(5, "o link novo define a senha nova e e de uso unico",
      r.status_code == 200 and verify_password("senha-nova-123", u.senha_hash) and u.convite_token is None,
      f"{r.status_code} {r.text[:120]}")

# 6. Pendente continua recebendo o texto de primeiro acesso.
enviados.clear()
r = client.post(f"/api/usuarios/{ids['paulo@x.com']}/convite", headers=cab("admin@x.com"))
checa(6, "pendente recebe o convite de primeiro acesso, como antes",
      r.status_code == 200 and enviados and "foi criado" in enviados[0]["corpo"],
      f"{r.status_code} {enviados[:1]}")

# 7. Usuario bloqueado nao recebe: o link nem funcionaria (ativar da 403).
enviados.clear()
r = client.post(f"/api/usuarios/{ids['bia@x.com']}/convite", headers=cab("admin@x.com"))
checa(7, "bloqueado: 400 e nada enviado", r.status_code == 400 and not enviados,
      f"{r.status_code} enviados={len(enviados)}")

# 8. Nao-regressao: so admin e gestor enviam convite.
r = client.post(f"/api/usuarios/{ids['ana@x.com']}/convite", headers=cab("analista@x.com"))
checa(8, "analista recebe 403", r.status_code == 403, f"{r.status_code}")

print()
if falhou:
    print(f"PROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print("PROVA OK: 8 checagens verdes")
