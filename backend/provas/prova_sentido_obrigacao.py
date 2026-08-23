"""
prova_sentido_obrigacao.py — para que lado o documento anda.

São três respostas, não duas:
  receber  — o cliente manda o comprovante e a tarefa baixa pelo e-validador
  entregar — o escritório anexa a guia e envia; o envio conclui a tarefa
  interna  — não troca documento com ninguém

A terceira faltava, e a falta tinha consequência: obrigação interna herdava
"receber" e, com identificadores cadastrados, passava a EXIGIR um comprovante
que nunca vai existir — travando a baixa de conciliar banco e lançar notas.

    python provas/prova_sentido_obrigacao.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
_tmp = tempfile.mkdtemp(prefix="prova-sentido-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ.setdefault("SECRET_KEY", "chave-de-prova")

from app.database import Base, engine, SessionLocal        # noqa: E402
from app.models import Obrigacao, Tarefa, Empresa          # noqa: E402
from app.services.validador import identificar_obrigacao   # noqa: E402

Base.metadata.create_all(bind=engine)

ok = True
def checa(nome, cond, extra=""):
    global ok
    print(("  ok   " if cond else "FALHA  ") + nome + (f"  {extra}" if extra else ""))
    ok = ok and bool(cond)


def tarefa_com(sentido, **kw):
    t = Tarefa()
    t.obrigacao = Obrigacao(nome="x", sentido=sentido, **kw)
    return t


print("\n1. Exigir documento depende do sentido")
checa("receber com identificadores exige",
      tarefa_com("receber", identificadores="EFD").exige_documento is True)
checa("entregar com identificadores também",
      tarefa_com("entregar", identificadores="EFD").exige_documento is True)
checa("INTERNA nunca exige, mesmo com identificadores",
      tarefa_com("interna", identificadores="EFD").exige_documento is False)
checa("interna nem com a flag ligada — o sentido é mais forte",
      tarefa_com("interna", identificadores="EFD", exige_documento=True).exige_documento is False)
checa("sem obrigação nenhuma, não exige", Tarefa().exige_documento is False)
checa("sentido nulo se comporta como receber (compatível com o que já existe)",
      tarefa_com(None, identificadores="EFD").exige_documento is True)

print("\n2. O e-validador não pode sugerir obrigação interna")
db = SessionLocal()
db.add_all([
    Obrigacao(nome="apuracao_ipi", sentido="receber", identificadores="IPI", ativa=True),
    Obrigacao(nome="conciliar_banco", sentido="interna", identificadores="IPI", ativa=True),
    Obrigacao(nome="legada_sem_sentido", identificadores="LEGADA", ativa=True),
    Obrigacao(nome="desativada", sentido="receber", identificadores="IPI", ativa=False),
])
db.commit()

achadas = [o.nome for o in identificar_obrigacao(db, "documento com IPI dentro")]
checa("a que recebe é sugerida", "apuracao_ipi" in achadas, str(achadas))
checa("a INTERNA fica de fora, mesmo com o mesmo identificador",
      "conciliar_banco" not in achadas)
checa("a desativada continua fora", "desativada" not in achadas)
checa("uma só sobra — sem ambiguidade", len(achadas) == 1, str(achadas))

legada = [o.nome for o in identificar_obrigacao(db, "documento LEGADA")]
checa("obrigação antiga, com sentido NULO, continua sendo sugerida",
      "legada_sem_sentido" in legada, str(legada))
db.close()

import shutil                                              # noqa: E402
shutil.rmtree(_tmp, ignore_errors=True)
print("\n" + ("TUDO VERDE" if ok else "VERMELHO") + "\n")
sys.exit(0 if ok else 1)
