"""
prova_transmitir_orgao.py: a obrigação que o escritório transmite ao órgão.

SPED, DCTFWeb e EFD não se encaixavam em nenhum dos três lados do documento:
ninguém recebe do cliente, ninguém entrega guia a ele, e mesmo assim existe um
documento, o recibo, que dá a baixa pelo e-validador. Surgiu o quarto sentido,
`transmitir`, e com ele três defeitos que já existiam:

  1. a edição nunca gravou o sentido: `ObrigacaoUpdate` não declarava o campo, e
     o Pydantic descarta campo não declarado sem erro;
  2. o sentido era texto livre: qualquer palavra entrava pelo POST;
  3. a regra de "exige documento" estava escrita duas vezes, no model e no
     painel, e o painel ficou para trás na reversão de 2026-09-09.

Os itens de não-regressão (15 a 18) passam JÁ no RED, de propósito: são eles
que acusariam uma correção que quebrasse o que funciona.

    python provas/prova_transmitir_orgao.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
_tmp = tempfile.mkdtemp(prefix="prova-transmitir-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ.setdefault("SECRET_KEY", "chave-de-prova")

from fastapi.testclient import TestClient                      # noqa: E402
from app.database import Base, engine, SessionLocal            # noqa: E402
from app.models import Usuario, Empresa, Setor, Tarefa, Obrigacao, StatusTarefa  # noqa: E402
from app.auth import get_password_hash, create_access_token    # noqa: E402
from app.main import app                                       # noqa: E402
from app.routes.painel import _perfil_obrigacao                # noqa: E402
from app.services.validador import identificar_obrigacao       # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
TOTAL = 22
falhou = []


def checa(n, descricao, condicao):
    if condicao:
        print(f"  ok  {n:>3}. {descricao}")
    else:
        print(f"FALHA  {n:>3}. {descricao}")
        falhou.append(n)


cab = {"Authorization": "Bearer " + create_access_token(data={"sub": "admin@x.com"})}
db = SessionLocal()
db.add(Usuario(nome="Admin", email="admin@x.com", grupo="admin", ativo=True,
               senha_hash=get_password_hash("x")))
db.commit()
db.close()


def sentido_no_banco(oid):
    s = SessionLocal()
    try:
        return s.query(Obrigacao.sentido).filter(Obrigacao.id == oid).scalar()
    finally:
        s.close()


def conta_obrigacoes():
    s = SessionLocal()
    try:
        return s.query(Obrigacao).count()
    finally:
        s.close()


print("\n(a) A edição grava o sentido")
r = client.post("/api/obrigacoes", json={"nome": "SPED Contribuições", "sentido": "receber"},
                headers=cab)
checa(1, "cenário: POST cria a obrigação", r.status_code == 201)
oid = r.json().get("id")

r = client.put(f"/api/obrigacoes/{oid}", json={"sentido": "transmitir"}, headers=cab)
g = client.get(f"/api/obrigacoes/{oid}", headers=cab).json()
checa(2, "PUT com sentido=transmitir e o GET devolve transmitir",
      r.status_code == 200 and g.get("sentido") == "transmitir")
checa(3, "o banco guardou transmitir", sentido_no_banco(oid) == "transmitir")

client.put(f"/api/obrigacoes/{oid}", json={"sentido": "interna"}, headers=cab)
checa(4, "trocar de novo, agora para interna, também grava",
      client.get(f"/api/obrigacoes/{oid}", headers=cab).json().get("sentido") == "interna")

print("\n(b) Sentido fora da lista é recusado no servidor")
antes = conta_obrigacoes()
r = client.post("/api/obrigacoes", json={"nome": "Invalida", "sentido": "qualquer"}, headers=cab)
checa(5, "POST com sentido inventado recebe 422", r.status_code == 422)
checa(6, "e nenhuma obrigação nova nasce", conta_obrigacoes() == antes)

gravado = sentido_no_banco(oid)
r = client.put(f"/api/obrigacoes/{oid}", json={"sentido": "qualquer"}, headers=cab)
checa(7, "PUT com sentido inventado recebe 422", r.status_code == 422)
checa(8, "e o sentido gravado não muda", sentido_no_banco(oid) == gravado)

r = client.post("/api/obrigacoes", json={"nome": "DCTFWeb", "sentido": "transmitir"}, headers=cab)
checa(9, "POST com sentido=transmitir é aceito", r.status_code == 201)

print("\n(c) Uma regra de documento: model e painel respondem igual nas 24 combinações")
divergentes, casos = [], 0
for sentido in ("receber", "entregar", "interna", "transmitir"):
    for flag in (None, True, False):
        for ident in ("", "EFD"):
            casos += 1
            o = Obrigacao(nome="m", sentido=sentido, exige_documento=flag, identificadores=ident)
            t = Tarefa()
            t.obrigacao = o
            if t.exige_documento != _perfil_obrigacao(o)[1]:
                divergentes.append((sentido, flag, ident))
checa(10, f"model e painel concordam (divergentes: {divergentes})", not divergentes)
checa(11, "a matriz rodou os 24 casos, e não menos", casos == 24)

# O item 10 compara dois pontos de chamada que hoje usam a MESMA função: ele
# pega duplicação reintroduzida, e não erro da regra. Este aqui é o oráculo,
# escrito à mão e sem chamar o código: flag explícita vence; flag nula deriva
# dos identificadores; interna nula nunca exige.
ESPERADO = {}
for sentido in ("receber", "entregar", "interna", "transmitir"):
    ESPERADO[(sentido, True, "")] = ESPERADO[(sentido, True, "EFD")] = True
    ESPERADO[(sentido, False, "")] = ESPERADO[(sentido, False, "EFD")] = False
    ESPERADO[(sentido, None, "")] = False
    ESPERADO[(sentido, None, "EFD")] = sentido != "interna"
erradas = []
for (sentido, flag, ident), esperado in ESPERADO.items():
    o = Obrigacao(nome="m", sentido=sentido, exige_documento=flag, identificadores=ident)
    t = Tarefa()
    t.obrigacao = o
    if t.exige_documento is not esperado or _perfil_obrigacao(o)[1] is not esperado:
        erradas.append((sentido, flag, ident))
checa(20, f"as 24 combinações batem com a tabela escrita à mão (erradas: {erradas})",
      len(ESPERADO) == 24 and not erradas)


def exige(sentido, flag, ident):
    t = Tarefa()
    t.obrigacao = Obrigacao(nome="m", sentido=sentido, exige_documento=flag, identificadores=ident)
    return t.exige_documento


print("\n(d) Transmitir exige documento como receber")
checa(12, "transmitir com identificadores e flag nula exige documento",
      exige("transmitir", None, "EFD") is True)
checa(13, "transmitir sem identificadores, ou com a flag desligada, não exige",
      exige("transmitir", None, "") is False and exige("transmitir", False, "EFD") is False)

print("\n(e) O e-validador acha a obrigação transmitida")
db = SessionLocal()
db.add(Obrigacao(nome="efd_transmitida", sentido="transmitir", identificadores="RECIBOEFD", ativa=True))
db.commit()
achadas = [o.nome for o in identificar_obrigacao(db, "recibo de entrega RECIBOEFD")]
db.close()
checa(14, f"identificar_obrigacao devolve a transmitir (achadas: {achadas})",
      "efd_transmitida" in achadas)

print("\n(f) Não-regressão, medida antes")
checa(15, "receber, entregar e interna sem flag seguem como hoje",
      exige("receber", None, "EFD") is True and exige("entregar", None, "EFD") is True
      and exige("interna", None, "EFD") is False)

db = SessionLocal()
db.add_all([Obrigacao(nome="legada_nula", sentido=None, ativa=True),
            Obrigacao(nome="legada_vazia", sentido="", ativa=True)])
db.commit()
db.close()
r = client.get("/api/obrigacoes", headers=cab)
checa(16, "a listagem não quebra com sentido legado nulo ou vazio gravado no banco",
      r.status_code == 200 and {"legada_nula", "legada_vazia"} <= {x["nome"] for x in r.json()})

# Achado do verificador funcional: a tela abre a legada com sentido "" e manda
# o "" de volta ao salvar, mesmo que o usuário só tenha mexido no nome. Recusar
# o vazio travaria a edição de QUALQUER campo dessa obrigação, e o Duplicar.
s = SessionLocal()
id_vazia = s.query(Obrigacao.id).filter(Obrigacao.nome == "legada_vazia").scalar()
s.close()
r = client.put(f"/api/obrigacoes/{id_vazia}", json={"nome": "legada_renomeada", "sentido": ""},
               headers=cab)
checa(21, "editar a legada mandando sentido vazio salva o nome, e não devolve 422",
      r.status_code == 200 and r.json().get("nome") == "legada_renomeada")
r = client.post("/api/obrigacoes", json={"nome": "legada (cópia)", "sentido": ""}, headers=cab)
checa(22, "duplicar a legada, com sentido vazio no corpo, cria a cópia", r.status_code == 201)

checa(17, "a coluna comporta 'transmitir' no Postgres, que corta varchar",
      (Obrigacao.__table__.c.sentido.type.length or 0) >= len("transmitir"))

db = SessionLocal()
emp, setor = Empresa(razao_social="Cliente", cnpj="1"), Setor(nome="Fiscal")
tx = Obrigacao(nome="EFD-Reinf", sentido="transmitir", exige_documento=True, ativa=True)
db.add_all([emp, setor, tx])
db.commit()
db.add(Tarefa(titulo="reinf sem recibo", empresa_id=emp.id, setor_id=setor.id,
              obrigacao_id=tx.id, status=StatusTarefa.PENDENTE, competencia="08/2026",
              data_prazo=datetime.utcnow() + timedelta(days=3)))
db.commit()
db.close()
p = client.get("/api/painel", headers=cab).json()
checa(18, "transmitir sem recibo NÃO entra em aguardando cliente: a bola está aqui",
      p["resumo"]["aguardando_cliente"] == 0)

print("\n(g) A regra mora num lugar só")
try:
    from app.models import perfil_documento                    # noqa: E402,F401
    existe = True
except ImportError:
    existe = False
checa(19, "models.py expõe perfil_documento", existe)

import shutil                                                  # noqa: E402
shutil.rmtree(_tmp, ignore_errors=True)

print()
if falhou:
    print(f"PROVA FALHOU nos itens: {sorted(set(falhou))}")
    sys.exit(1)
print(f"PROVA OK: {TOTAL} checagens verdes")
