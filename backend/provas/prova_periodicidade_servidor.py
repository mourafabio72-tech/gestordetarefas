"""
prova_periodicidade_servidor.py: o servidor valida o que a periodicidade grava.

A tela nova de Periodicidade (Mensal, Trimestral, Anual) não cria coluna: ela
grava `meses_ativos` e `competencia_ref`, que até 2026-09-19 eram texto livre
na entrada. `meses_ativos="a"` gravava e a obrigação parava de gerar sem aviso;
`competencia_ref="qualquer"` gravava e o gerador lia como "mês anterior"
(`gerador.py:44-47`), em silêncio.

A anual passa a usar deslocamento numérico (-14 para entrega em março, que dá
janeiro do ano anterior, a competência que o recibo da DEFIS e da ECF traz:
LOG da fase 38). O Excel da relação só conhecia os quatro apelidos e mostrava
"-14" cru.

Os itens 11 a 15 são não-regressão e passam JÁ no RED, de propósito. O 12 e o
13 guardam a lição da fase 27: obrigação antiga com valor vazio no banco tem de
continuar listando e salvando, senão a validação nova trava a edição dela.

    python provas/prova_periodicidade_servidor.py
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
_tmp = tempfile.mkdtemp(prefix="prova-periodicidade-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ.setdefault("SECRET_KEY", "chave-de-prova")

from fastapi.testclient import TestClient                      # noqa: E402
from app.database import Base, engine, SessionLocal            # noqa: E402
from app.models import Usuario, Obrigacao                      # noqa: E402
from app.auth import get_password_hash, create_access_token    # noqa: E402
from app.main import app                                       # noqa: E402
from app.services.gerador import calc_competencia              # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app, raise_server_exceptions=False)
TOTAL = 18
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


def no_banco(oid):
    s = SessionLocal()
    try:
        o = s.query(Obrigacao).filter(Obrigacao.id == oid).first()
        return (o.meses_ativos, o.competencia_ref, o.nome)
    finally:
        s.close()


def cria(nome, **extra):
    return client.post("/api/obrigacoes", json={"nome": nome, **extra}, headers=cab)


# 1. cenário
r = cria("base")
base_id = r.json().get("id") if r.status_code == 201 else None
checa(1, "cenário: POST de obrigação válida cria (201)", r.status_code == 201 and base_id)
antes = no_banco(base_id) if base_id else None

# 2 e 3. meses_ativos fora do formato
ruins_meses = ["", "13", "0", "a", "1,,2"]
st = [cria(f"m{i}", meses_ativos=v).status_code for i, v in enumerate(ruins_meses)]
checa(2, f"POST com meses_ativos inválido dá 422 nos cinco: {st}", st == [422] * 5)
st = [client.put(f"/api/obrigacoes/{base_id}", json={"meses_ativos": v}, headers=cab).status_code
      for v in ruins_meses]
checa(3, f"PUT com meses_ativos inválido dá 422 nos cinco e o banco não muda: {st}",
      st == [422] * 5 and no_banco(base_id) == antes)

# 4 e 5. repetido e fora de ordem são normalizados
r = cria("normaliza", meses_ativos="3,1,3")
oid = r.json().get("id") if r.status_code == 201 else None
checa(4, "POST com '3,1,3' grava '1,3'", oid and no_banco(oid)[0] == "1,3")
r = client.put(f"/api/obrigacoes/{base_id}", json={"meses_ativos": " 12, 1 "}, headers=cab)
checa(5, "PUT com ' 12, 1 ' grava '1,12'", r.status_code == 200 and no_banco(base_id)[0] == "1,12")

# 6 e 7. competencia_ref fora de apelido ou de inteiro entre -24 e 1
ruins_ref = ["qualquer", "-25", "2", "1.5"]
st = [cria(f"c{i}", competencia_ref=v).status_code for i, v in enumerate(ruins_ref)]
checa(6, f"POST com competencia_ref inválida dá 422 nos quatro: {st}", st == [422] * 4)
antes = no_banco(base_id)
st = [client.put(f"/api/obrigacoes/{base_id}", json={"competencia_ref": v}, headers=cab).status_code
      for v in ruins_ref]
checa(7, f"PUT com competencia_ref inválida dá 422 nos quatro e o banco não muda: {st}",
      st == [422] * 4 and no_banco(base_id) == antes)

# 8. deslocamento numérico da anual e da trimestral
r = cria("defis", meses_ativos="3", competencia_ref="-14")
defis_id = r.json().get("id") if r.status_code == 201 else None
r2 = client.put(f"/api/obrigacoes/{base_id}", json={"competencia_ref": "-3"}, headers=cab)
checa(8, "'-14' aceito no POST e '-3' aceito no PUT",
      defis_id and no_banco(defis_id)[1] == "-14" and r2.status_code == 200
      and no_banco(base_id)[1] == "-3")

# 9. a conta que o recibo exige (LOG da fase 38: DEFIS e ECF em 01/AAAA)
contas = [calc_competencia(3, 2026, "-14"), calc_competencia(7, 2026, "-18"),
          calc_competencia(1, 2026, "-3"), calc_competencia(12, 2026, "-23")]
checa(9, f"competência calculada: {contas}",
      contas == ["01/2025", "01/2025", "10/2025", "01/2025"])

# 10. rótulo do Excel
r = client.get("/api/obrigacoes/relatorio", headers=cab)
rotulo = None
if r.status_code == 200:
    import openpyxl
    ws = openpyxl.load_workbook(io.BytesIO(r.content)).active
    for linha in ws.iter_rows(min_row=2, values_only=True):
        if linha[0] == "defis":
            rotulo = linha[5]
checa(10, f"Excel mostra '14 meses antes' para -14, e não o número cru: {rotulo!r}",
      rotulo == "14 meses antes")

# 11. não-regressão: apelidos e os números que a tela já oferece
bons = ["mes_anterior", "mesmo_mes", "mes_seguinte", "ano_anterior", "-2", "-3", "-6", "0", "1"]
st = [cria(f"b{i}", competencia_ref=v).status_code for i, v in enumerate(bons)]
checa(11, f"os quatro apelidos e -2, -3, -6, 0, 1 continuam aceitos: {st}", st == [201] * len(bons))

# 12 e 13. obrigação legada com valor vazio ou nulo no banco
s = SessionLocal()
leg1 = Obrigacao(nome="legada_nula", competencia_ref=None, meses_ativos="1,2,3")
leg2 = Obrigacao(nome="legada_vazia", competencia_ref="", meses_ativos="7")
s.add_all([leg1, leg2])
s.commit()
leg1_id, leg2_id = leg1.id, leg2.id
s.close()
r = client.get("/api/obrigacoes", headers=cab)
nomes = {o["nome"] for o in r.json()} if r.status_code == 200 else set()
checa(12, "listagem com legada de competência nula e vazia continua 200",
      r.status_code == 200 and {"legada_nula", "legada_vazia"} <= nomes)
r = client.put(f"/api/obrigacoes/{leg2_id}",
               json={"nome": "legada_renomeada", "competencia_ref": "", "meses_ativos": "7"},
               headers=cab)
checa(13, f"PUT na legada reenviando competência vazia salva o nome ({r.status_code})",
      r.status_code == 200 and no_banco(leg2_id)[2] == "legada_renomeada")

# 14. padrão sem os campos
r = cria("padrao")
pid = r.json().get("id") if r.status_code == 201 else None
checa(14, "POST sem os campos grava 12 meses e mes_anterior",
      pid and no_banco(pid)[:2] == ("1,2,3,4,5,6,7,8,9,10,11,12", "mes_anterior"))

# 15. PUT que não manda os campos não toca neles
antes = no_banco(leg1_id)
r = client.put(f"/api/obrigacoes/{leg1_id}", json={"nome": "legada_nula_2"}, headers=cab)
depois = no_banco(leg1_id)
checa(15, "PUT sem os campos não mexe em meses nem competência",
      r.status_code == 200 and depois[:2] == antes[:2])

# 16 e 17. Achado do verificador funcional: obrigação legada com meses VAZIO.
# A tela reenvia o que leu, e recusar o vazio travaria até renomear. Esvaziar
# uma obrigação que TEM meses continua recusado.
s = SessionLocal()
leg3 = Obrigacao(nome="legada_sem_mes", competencia_ref="mes_anterior", meses_ativos="")
s.add(leg3)
s.commit()
leg3_id = leg3.id
s.close()
r = client.put(f"/api/obrigacoes/{leg3_id}",
               json={"nome": "legada_sem_mes_2", "meses_ativos": ""}, headers=cab)
checa(16, f"PUT renomeando legada de meses vazio salva e não inventa mês ({r.status_code})",
      r.status_code == 200 and no_banco(leg3_id)[0] == "" and no_banco(leg3_id)[2] == "legada_sem_mes_2")
antes = no_banco(base_id)
st = [client.put(f"/api/obrigacoes/{base_id}", json={"meses_ativos": v}, headers=cab).status_code
      for v in ["", None]]
checa(17, f"PUT esvaziando obrigação que tem meses dá 422 e o banco não muda: {st}",
      st == [422, 422] and no_banco(base_id) == antes)

# 18. Achado na verificação: competência null gravava NULL e a LISTAGEM
# inteira passava a dar 500 (a resposta exige texto). Existia antes deste
# trabalho; null vira o padrão histórico, como o vazio.
r = client.put(f"/api/obrigacoes/{base_id}", json={"competencia_ref": None}, headers=cab)
lista = client.get("/api/obrigacoes", headers=cab).status_code
checa(18, f"PUT com competência null grava mes_anterior e a listagem segue 200 ({r.status_code}, {lista})",
      r.status_code == 200 and no_banco(base_id)[1] == "mes_anterior" and lista == 200)

print()
if falhou:
    print(f"PROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print(f"PROVA OK: {TOTAL} checagens verdes")
