"""
prova_evalidador_interna.py — obrigação interna PODE exigir documento.

Reversão declarada de uma decisão que estava escrita no código com o motivo
errado. O comentário antigo dizia que "interna não troca documento com ninguém,
exigir um travaria a baixa por algo que nunca vai existir". A premissa estava
incompleta: interna tem documento sim, só que quem anexa é o próprio analista,
e não o cliente. O balancete fechado é um arquivo; a conciliação assinada é um
arquivo.

O que se prova, e a terceira é a que protege quem já usa o sistema:
· interna COM a flag ligada passa a exigir documento;
· não interna continua exatamente como era;
· interna SEM flag (`NULL`) continua sem exigir, mesmo tendo identificadores
  cadastrados. É isso que garante que nenhuma obrigação interna de hoje muda de
  comportamento sozinha no deploy.

Rodar:  cd backend && ./venv/bin/python provas/prova_evalidador_interna.py
"""
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("DATABASE_URL", "sqlite:///" + tempfile.mktemp(suffix=".db"))

from app.database import SessionLocal, Base, engine                    # noqa: E402
from app.models import Empresa, Obrigacao, Tarefa, StatusTarefa        # noqa: E402

ok = True


def check(nome, cond, extra=""):
    global ok
    print(("  OK   " if cond else "  FALHA ") + nome + (f"  {extra}" if extra else ""))
    ok = ok and bool(cond)


Base.metadata.create_all(bind=engine)
db = SessionLocal()
for m in (Tarefa, Obrigacao, Empresa):
    db.query(m).delete()
db.commit()

emp = Empresa(razao_social="ACME", cnpj="1", ativo=True)
db.add(emp)
db.commit()


def tarefa_de(sentido, exige, identificadores=""):
    o = Obrigacao(nome=f"{sentido}-{exige}", sentido=sentido, exige_documento=exige,
                  identificadores=identificadores, regra_prazo_tipo="ultimo_dia_util",
                  meses_ativos="1", competencia_ref="mes_anterior", ativa=True)
    db.add(o)
    db.commit()
    t = Tarefa(titulo=o.nome, empresa_id=emp.id, obrigacao_id=o.id,
               status=StatusTarefa.PENDENTE)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


print("\n=== 1. interna com a flag ligada passa a exigir ===")
check("interna + exige_documento=True exige documento",
      tarefa_de("interna", True).exige_documento is True)

print("\n=== 2. interna sem flag continua como sempre foi ===")
check("interna + NULL, sem identificadores, não exige",
      tarefa_de("interna", None).exige_documento is False)
check("interna + NULL, COM identificadores, TAMBÉM não exige",
      tarefa_de("interna", None, "DARF-123").exige_documento is False,
      "(é o caso que impede obrigação interna de hoje mudar sozinha)")
check("interna + exige_documento=False não exige",
      tarefa_de("interna", False).exige_documento is False)

print("\n=== 3. o que não é interna continua inalterado ===")
check("receber + NULL deriva dos identificadores: sem eles, não exige",
      tarefa_de("receber", None).exige_documento is False)
check("receber + NULL com identificadores exige",
      tarefa_de("receber", None, "DARF-123").exige_documento is True)
check("receber + flag ligada exige", tarefa_de("receber", True).exige_documento is True)
check("receber + flag desligada não exige, mesmo com identificadores",
      tarefa_de("receber", False, "DARF-123").exige_documento is False)
check("entregar + flag ligada exige", tarefa_de("entregar", True).exige_documento is True)

print("\n=== 4. tarefa sem obrigação nunca exige ===")
t = Tarefa(titulo="avulsa", empresa_id=emp.id, status=StatusTarefa.PENDENTE)
db.add(t)
db.commit()
db.refresh(t)
check("tarefa avulsa não exige documento", t.exige_documento is False)

db.close()
print("\n" + ("TODAS AS PROVAS PASSARAM" if ok else "HOUVE FALHA"))
sys.exit(0 if ok else 1)
