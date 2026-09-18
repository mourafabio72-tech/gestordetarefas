"""Prova da Fase 32: a geracao em lote passa a deixar rastro.

`POST /api/obrigacoes/gerar` cria tarefas as centenas e, ate aqui, nao chamava
`log_event`. As rotas vizinhas do mesmo arquivo chamam. A geracao e mutacao
de dado critico feita por uma pessoa, e a `Padrao_Logging_Estruturado` manda:
"mutacao de dado critico SEMPRE entram".

O desenho: UMA linha por chamada, e nao uma por tarefa. Mil linhas por clique
afogariam a aba Logs e nao diriam nada que a contagem nao diga. A linha leva
so contagem, nunca razao social nem CNPJ.

    cd backend && ./venv/bin/python provas/prova_gerar_log.py

Mede o que sai no stdout de verdade, num SQLite temporario.
"""

from __future__ import annotations  # producao e 3.12, a maquina local e 3.9

import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_gerar_log_")
_banco = os.path.join(_tmp, "prova.db")

os.environ["DATABASE_URL"] = f"sqlite:///{_banco}"
os.environ["SECRET_KEY"] = "chave-jwt-de-teste"
os.environ["ZOARIA_SSO_SECRET"] = ""

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient                      # noqa: E402

from app.auth import get_password_hash                         # noqa: E402
from app.database import Base, engine, SessionLocal            # noqa: E402
from app.models import (Empresa, Obrigacao, Tarefa, Usuario,   # noqa: E402
                        tarefa_responsaveis)
from app.main import app                                       # noqa: E402
from app.services.gerador import gerar_tarefas                 # noqa: E402

Base.metadata.create_all(bind=engine)

SENHA = "senha-boa-123"
EMAIL_ADMIN = "chefe@bps4.com.br"
EMAIL_CONSULTA = "olha@bps4.com.br"
CRIACAO = "CRIACAO_REGISTRO_CRITICO"
MESES = "1,2,3,4,5,6,7,8,9,10,11,12"

CAMPOS = ["timestamp", "level", "event", "user_id", "ip", "request_id",
          "path", "method"]

# Razao social e CNPJ do cenario: nenhum deles pode aparecer na linha.
RAZOES = ["ALFA SERVICOS LTDA", "BETA COMERCIO LTDA", "GAMA INDUSTRIA LTDA"]
CNPJS = ["11222333000181", "44555666000172", "77888999000163"]

cliente = TestClient(app)
ids = {}


def semear():
    db = SessionLocal()
    try:
        admin = Usuario(nome="Chefe", email=EMAIL_ADMIN, grupo="admin",
                        senha_hash=get_password_hash(SENHA), ativo=True)
        consulta = Usuario(nome="Olha", email=EMAIL_CONSULTA, grupo="consulta",
                           senha_hash=get_password_hash(SENHA), ativo=True)
        empresas = [Empresa(razao_social=r, cnpj=c, ativo=True,
                            regime_tributario="lucro_real")
                    for r, c in zip(RAZOES, CNPJS)]
        db.add_all([admin, consulta, *empresas])
        db.commit()
        balancete = Obrigacao(nome="Balancete", ativa=True, meses_ativos=MESES,
                              regra_prazo_tipo="ultimo_dia_util")
        ecf = Obrigacao(nome="ECF", ativa=True, meses_ativos=MESES,
                        regra_prazo_tipo="ultimo_dia_util")
        db.add_all([balancete, ecf])
        db.commit()
        ids.update(admin=admin.id, empresas=[e.id for e in empresas],
                   balancete=balancete.id, ecf=ecf.id)
    finally:
        db.close()


def limpar_tarefas():
    db = SessionLocal()
    try:
        db.execute(tarefa_responsaveis.delete())
        db.query(Tarefa).delete()
        db.commit()
    finally:
        db.close()


def entrar(email):
    r = cliente.post("/api/auth/login", json={"email": email, "senha": SENHA})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def capturar(funcao):
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        retorno = funcao()
    linhas = []
    for bruta in buffer.getvalue().splitlines():
        bruta = bruta.strip()
        if not bruta.startswith("{"):
            continue
        try:
            linhas.append(json.loads(bruta))
        except json.JSONDecodeError:
            continue
    return retorno, linhas


def criacoes(linhas):
    return [linha for linha in linhas if linha.get("event") == CRIACAO]


falhou = []


def checa(n, descricao, condicao):
    if condicao:
        print(f"  ok  {n:>3}. {descricao}")
    else:
        print(f"FALHA  {n:>3}. {descricao}")
        falhou.append(n)


semear()
admin = entrar(EMAIL_ADMIN)
consulta = entrar(EMAIL_CONSULTA)


def gerar(body, headers=admin):
    return cliente.post("/api/obrigacoes/gerar", json=body, headers=headers)


# ------------------------------------------------------------ (a) uma linha so
recorte = {"mes": 9, "ano": 2026, "empresa_ids": ids["empresas"][:2],
           "obrigacao_ids": [ids["balancete"], ids["ecf"]]}
limpar_tarefas()
r1, l1 = capturar(lambda: gerar(recorte))
c1 = criacoes(l1)

checa(1, "cenario: a geracao com recorte responde 200 e cria 4 tarefas",
      r1.status_code == 200 and r1.json().get("criadas") == 4)
checa(2, "UMA linha CRIACAO_REGISTRO_CRITICO por chamada, e nao uma por tarefa",
      len(c1) == 1)
e1 = c1[0] if c1 else {}
checa(3, "a linha diz tabela=tarefa, lote=True e origem=gerar_mes",
      e1.get("tabela") == "tarefa" and e1.get("lote") is True
      and e1.get("origem") == "gerar_mes")

# ------------------------------------------------- (b) o que a linha carrega
checa(4, "os oito campos obrigatorios, com o usuario autenticado",
      all(c in e1 for c in CAMPOS) and e1.get("user_id") == ids["admin"])
checa(5, "mes_entrega, criadas e puladas iguais aos da resposta",
      bool(e1)
      and e1.get("mes_entrega") == r1.json().get("mes_entrega")
      and e1.get("criadas") == r1.json().get("criadas")
      and e1.get("puladas") == r1.json().get("puladas"))
checa(6, "tamanho do recorte: 2 obrigacoes e 2 empresas",
      e1.get("obrigacoes_no_recorte") == 2 and e1.get("empresas_no_recorte") == 2)

# --------------------------------------------------- (c) sem PII, so contagem
bruta = json.dumps(e1, ensure_ascii=False)
checa(7, "nenhuma razao social nem CNPJ na linha",
      bool(e1) and not any(x in bruta for x in RAZOES + CNPJS))
checa(8, "nenhuma lista de ids de empresa na linha, so a contagem",
      bool(e1) and not any(isinstance(v, list) for v in e1.values()))

# ---------------------------------- (d) zero criadas tambem registra a tentativa
r2, l2 = capturar(lambda: gerar(recorte))
c2 = criacoes(l2)
e2 = c2[0] if c2 else {}
checa(9, "segunda chamada igual: 0 criadas, 4 puladas, e a linha sai mesmo assim",
      r2.status_code == 200 and r2.json().get("criadas") == 0
      and len(c2) == 1 and e2.get("criadas") == 0 and e2.get("puladas") == 4)

# ----------------------------------------------- sem recorte: None, e nao zero
limpar_tarefas()
r3, l3 = capturar(lambda: gerar({"mes": 9, "ano": 2026}))
c3 = criacoes(l3)
e3 = c3[0] if c3 else {}
checa(10, "sem recorte: 6 criadas, e os dois tamanhos de recorte saem None",
      r3.status_code == 200 and r3.json().get("criadas") == 6
      and len(c3) == 1
      and "obrigacoes_no_recorte" in e3 and e3["obrigacoes_no_recorte"] is None
      and "empresas_no_recorte" in e3 and e3["empresas_no_recorte"] is None)

# -------------------------------- (e) nao-regressao, medida antes do codigo
limpar_tarefas()
r4 = gerar(recorte)
limpar_tarefas()
_db = SessionLocal()
try:
    direto = gerar_tarefas(_db, 9, 2026, recorte["obrigacao_ids"],
                           recorte["empresa_ids"])
finally:
    _db.close()
checa(11, "a resposta da rota e igual, campo a campo, a do servico chamado direto",
      r4.status_code == 200 and r4.json() == json.loads(json.dumps(direto)))

r5, l5 = capturar(lambda: gerar({"mes": 9, "ano": 2026}, headers=consulta))
checa(12, "quem nao tem a flag leva 403 e nao gera linha de criacao",
      r5.status_code == 403 and not criacoes(l5))

r6, l6 = capturar(lambda: gerar({"mes": 13, "ano": 2026}))
checa(13, "mes invalido leva 400 e nao gera linha de criacao",
      r6.status_code == 400 and not criacoes(l6))

# ---------------------------- (f) o irmao: cadastrar empresa tambem gera em lote
# `POST /empresas` chama `gerar_empresa_mes_atual`, que cria as tarefas do mes
# pela mesma regra. Achado do verificador de seguranca da fase 32: a linha da
# EMPRESA saia, a das TAREFAS nao.
r7, l7 = capturar(lambda: cliente.post(
    "/api/empresas", headers=admin,
    json={"razao_social": "DELTA NOVA LTDA", "regime_tributario": "lucro_real"}))
c7 = [x for x in criacoes(l7) if x.get("tabela") == "tarefa"]
e7 = c7[0] if c7 else {}
geradas = int(r7.headers.get("X-Tarefas-Geradas", "-1"))
checa(14, "cenario: cadastrar empresa gera as 2 tarefas do mes",
      r7.status_code == 201 and geradas == 2)
checa(15, "e deixa UMA linha de tarefa em lote, com a mesma contagem do header",
      len(c7) == 1 and e7.get("lote") is True and e7.get("criadas") == geradas)
checa(16, "a linha diz a origem, o recorte de 1 empresa, e nada de razao social",
      e7.get("origem") == "cadastro_empresa" and e7.get("empresas_no_recorte") == 1
      and "DELTA" not in json.dumps(e7, ensure_ascii=False))

if falhou:
    print(f"PROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print("PROVA OK: 16 checagens verdes")
