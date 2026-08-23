"""
prova_editar_modelo.py — editar e excluir modelo acertam o TREINO.

O modelo existe para treinar a obrigação: ao salvar, o identificador dele entra
na lista que o e-validador consulta. Então corrigir um vínculo errado na tela só
serve se o identificador sair da obrigação antiga — senão o erro continua vivo
onde importa, e a tela mente dizendo que foi corrigido.

Foi assim que os vínculos errados sobreviveram: apagar o modelo não tirava o
identificador da obrigação.

    python provas/prova_editar_modelo.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
_tmp = tempfile.mkdtemp(prefix="prova-editar-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ.setdefault("SECRET_KEY", "chave-de-prova")

from app.database import Base, engine, SessionLocal            # noqa: E402
from app.models import Obrigacao, Modelo                       # noqa: E402
from app.services.validador import (salvar_modelo, atualizar_modelo,   # noqa: E402
                                    _esquecer_identificador)

Base.metadata.create_all(bind=engine)

ok = True
def checa(nome, cond, extra=""):
    global ok
    print(("  ok   " if cond else "FALHA  ") + nome + (f"  {extra}" if extra else ""))
    ok = ok and bool(cond)


def idents(db, oid):
    o = db.query(Obrigacao).filter(Obrigacao.id == oid).first()
    return [k.strip() for k in (o.identificadores or "").split(",") if k.strip()]


db = SessionLocal()
ipi = Obrigacao(nome="apuracao_ipi", ativa=True)
pis = Obrigacao(nome="apuracao_pis", ativa=True)
db.add_all([ipi, pis]); db.commit()
id_ipi, id_pis = ipi.id, pis.id

print("\n1. Salvar treina")
m = salvar_modelo(db, {"nome_arquivo": "a.pdf", "cnpj": "12345678000190",
                       "obrigacao_id": id_ipi, "identificador": "IPI 5123"})
mid = m.id
checa("o identificador entra na obrigação", idents(db, id_ipi) == ["IPI 5123"], str(idents(db, id_ipi)))

print("\n2. Editar movendo de obrigação leva o identificador junto")
atualizar_modelo(db, mid, {"nome_arquivo": "a.pdf", "cnpj": "12345678000190",
                           "obrigacao_id": id_pis, "identificador": "PIS 8109"})
checa("sai da antiga", idents(db, id_ipi) == [], str(idents(db, id_ipi)))
checa("entra na nova", idents(db, id_pis) == ["PIS 8109"], str(idents(db, id_pis)))

print("\n3. Editar só o identificador troca dentro da mesma obrigação")
atualizar_modelo(db, mid, {"nome_arquivo": "a.pdf", "cnpj": "12345678000190",
                           "obrigacao_id": id_pis, "identificador": "PIS - DEMAIS"})
checa("o antigo sai", "PIS 8109" not in idents(db, id_pis))
checa("o novo entra", idents(db, id_pis) == ["PIS - DEMAIS"], str(idents(db, id_pis)))

print("\n4. Dois modelos com o mesmo identificador — um sai, o outro segura")
m2 = salvar_modelo(db, {"nome_arquivo": "b.pdf", "cnpj": "99999999000199",
                        "obrigacao_id": id_pis, "identificador": "PIS - DEMAIS"})
checa("o segundo não duplica na lista", idents(db, id_pis) == ["PIS - DEMAIS"], str(idents(db, id_pis)))
_esquecer_identificador(db, id_pis, "PIS - DEMAIS", ignorar_modelo_id=m2.id)
db.commit()
checa("tirar um NÃO apaga: o outro ainda usa",
      idents(db, id_pis) == ["PIS - DEMAIS"], str(idents(db, id_pis)))
db.delete(db.query(Modelo).filter(Modelo.id == mid).first()); db.commit()
_esquecer_identificador(db, id_pis, "PIS - DEMAIS", ignorar_modelo_id=m2.id)
db.commit()
checa("com o último fora, aí sim some", idents(db, id_pis) == [], str(idents(db, id_pis)))

print("\n5. Bordas")
checa("editar modelo que não existe devolve None",
      atualizar_modelo(db, 99999, {"identificador": "x"}) is None)
checa("esquecer sem obrigação não quebra", _esquecer_identificador(db, None, "x") is False)
checa("esquecer identificador vazio não quebra", _esquecer_identificador(db, id_pis, "") is False)
db.close()

import shutil                                                  # noqa: E402
shutil.rmtree(_tmp, ignore_errors=True)
print("\n" + ("TUDO VERDE" if ok else "VERMELHO") + "\n")
sys.exit(0 if ok else 1)
