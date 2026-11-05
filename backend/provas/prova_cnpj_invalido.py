"""Prova: lista as empresas com CNPJ que não passa nos dígitos verificadores.

Caso de 2026-11-04: a Redayber estava gravada com CNPJ inválido. A tela barrava
qualquer alteração e o e-validador não casava as guias dela, e nada avisava antes.

  (a) lista CNPJ de dígitos errados, de tamanho errado e vazio, cada um com o motivo;
  (b) CNPJ certo, com ou sem máscara, fica de fora;
  (c) empresa inativa ou bloqueada fica de fora: não gera tarefa;

    cd backend && ./venv/bin/python provas/prova_cnpj_invalido.py
"""
from __future__ import annotations  # producao e 3.11, a maquina local e 3.9

import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_cnpj_invalido_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["SECRET_KEY"] = "chave-de-prova-nao-usar-em-producao"
os.environ["ZOARIA_SSO_SECRET"] = ""
os.environ.pop("OPENAI_API_KEY", None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base, engine, SessionLocal                # noqa: E402
from app.models import Empresa                                     # noqa: E402
from app.services.sem_contato import empresas_cnpj_invalido        # noqa: E402
import app.main                                                    # noqa: E402,F401

Base.metadata.create_all(bind=engine)
falhou = []


def checa(n, descricao, cond, extra=""):
    print(("  ok  " if cond else "FALHA ") + f"{n:>3}. {descricao}"
          + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        falhou.append(n)


db = SessionLocal()
db.add_all([
    Empresa(razao_social="Digito Errado Ltda", cnpj="11.222.333/0001-82", ativo=True),
    Empresa(razao_social="Curto Ltda", cnpj="123456", ativo=True),
    Empresa(razao_social="Vazio Ltda", cnpj=None, ativo=True),
    Empresa(razao_social="Certo Mascara Ltda", cnpj="11.222.333/0001-81", ativo=True),
    Empresa(razao_social="Certo Limpo Ltda", cnpj="11444777000161", ativo=True),
    Empresa(razao_social="Inativa Ltda", cnpj="99.999.999/0001-00", ativo=False),
    Empresa(razao_social="Bloqueada Ltda", cnpj="88.888.888/0001-00", ativo=True, bloqueado=True),
])
db.commit()
linhas = {l["razao_social"]: l for l in empresas_cnpj_invalido(db)}
checa(1, "lista so os tres problemas", sorted(linhas) == ["Curto Ltda", "Digito Errado Ltda", "Vazio Ltda"], sorted(linhas))
checa(2, "digitos errados diz o motivo e mostra o gravado",
      linhas.get("Digito Errado Ltda", {}).get("motivo") == "Dígitos verificadores não conferem"
      and linhas["Digito Errado Ltda"]["cnpj"] == "11.222.333/0001-82", linhas.get("Digito Errado Ltda"))
checa(3, "tamanho errado", linhas.get("Curto Ltda", {}).get("motivo") == "Não tem 14 dígitos", linhas.get("Curto Ltda"))
checa(4, "vazio", linhas.get("Vazio Ltda", {}).get("motivo") == "Sem CNPJ", linhas.get("Vazio Ltda"))
db.close()

if falhou:
    print(f"\nPROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print("\nPROVA OK: 4 checagens verdes")
