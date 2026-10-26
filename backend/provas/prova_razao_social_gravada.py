"""Prova da razão social GRAVADA formatada (2026-10-26, pedido do Fábio).

O que ela trava:
  - empresa criada ou editada pelo ORM grava a razão social com só a inicial
    maiúscula; nome com minúscula passa intacto;
  - formatar_razoes_gravadas converte as que já estavam no banco, e rodar de
    novo não muda nada;
  - o importador de cronograma acha a empresa formatada pelo nome da planilha
    em maiúsculas, sem criar outra;
  - a chave de comparação ignora maiúscula, acento e pontuação.

    cd backend && uv run --no-project --python 3.12 --with-requirements requirements.txt python provas/prova_razao_social_gravada.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_razao_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["SECRET_KEY"] = "chave-de-prova-nao-usar-em-producao"
os.environ["ZOARIA_SSO_SECRET"] = ""

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text                                # noqa: E402
from app.database import Base, engine, SessionLocal        # noqa: E402
from app.models import Empresa                             # noqa: E402
import app.main                                            # noqa: E402,F401
from app.init_db import formatar_razoes_gravadas           # noqa: E402
from app.services.importador_cronograma import _get_or_create_empresa  # noqa: E402
from app.services.razao_social import chave                # noqa: E402

Base.metadata.create_all(bind=engine)
falhou = []


def checa(n, descricao, cond, extra=""):
    print(("  ok  " if cond else "FALHA ") + f"{n:>3}. {descricao}"
          + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        falhou.append(n)


db = SessionLocal()
e = Empresa(razao_social="3 EMPTOR PART. E INVEST. LTDA.", cnpj="14.079.434/0001-33")
db.add(e)
db.commit()
db.refresh(e)
checa(1, "criada pelo ORM: gravada formatada", e.razao_social == "3 Emptor Part. e Invest. Ltda",
      e.razao_social)
e.razao_social = "RIO BRAVO COM. DE ARMAS E ACESS. LTDA"
db.commit()
db.refresh(e)
checa(2, "editada pelo ORM: gravada formatada",
      e.razao_social == "Rio Bravo Com. de Armas e Acess. Ltda", e.razao_social)
m = Empresa(razao_social="Mark Building Gerenc. Predial Ltda.")
db.add(m)
db.commit()
db.refresh(m)
checa(3, "nome com minúscula passa intacto", m.razao_social == "Mark Building Gerenc. Predial Ltda.")

# Uma linha antiga, gravada antes da regra, por SQL cru (sem passar pelo ORM).
db.execute(text("INSERT INTO empresas (razao_social, ativo, bloqueado) "
                "VALUES ('GNILEB PARTICIPACOES LTDA.', 1, 0)"))
db.commit()
db.close()
formatar_razoes_gravadas()
db = SessionLocal()
g = db.query(Empresa).filter(Empresa.razao_social.like("Gnileb%")).first()
checa(4, "a já gravada é convertida no boot", g is not None and g.razao_social == "Gnileb Participacoes Ltda",
      g and g.razao_social)
antes = {x.id: x.razao_social for x in db.query(Empresa).all()}
db.close()
formatar_razoes_gravadas()
db = SessionLocal()
depois = {x.id: x.razao_social for x in db.query(Empresa).all()}
checa(5, "rodar de novo não muda nada", antes == depois)

total = db.query(Empresa).count()
achada = _get_or_create_empresa(db, "GNILEB PARTICIPACOES LTDA.", "")
db.commit()
checa(6, "o importador acha a empresa pelo nome da planilha em maiúsculas",
      achada.id == g.id and db.query(Empresa).count() == total)
nova = _get_or_create_empresa(db, "EMPRESA NOVA DO CRONOGRAMA", "")
db.commit()
checa(7, "e a que não existe nasce formatada", nova.razao_social == "Empresa Nova do Cronograma",
      nova.razao_social)
checa(8, "a chave ignora maiúscula, acento e pontuação",
      chave("GNILEB PARTICIPAÇÕES LTDA.") == chave("Gnileb Participacoes Ltda"))
db.close()

print("\nFALHAS:", len(falhou))
sys.exit(1 if falhou else 0)
