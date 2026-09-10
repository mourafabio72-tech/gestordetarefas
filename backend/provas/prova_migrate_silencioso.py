"""Prova da Fase 22: o boot para de escrever erro falso no log do banco.

O `migrate()` roda as migracoes SEMPRE, uma transacao por item, e usa o ERRO do
banco como forma de descobrir que a coluna ja existe. O Postgres registra cada
tentativa como `ERROR: column ... already exists`, e o log de producao nasce com
dezenas de erros falsos a cada deploy. Nao quebra nada. O preco e que erro de
migracao de verdade passa a morar no meio de dezenas iguais, e ninguem olha.

Esta prova mede o STDOUT de duas rodadas seguidas contra um SQLite temporario, e
nao o que o codigo parece fazer.

    cd backend && ./venv/bin/python provas/prova_migrate_silencioso.py

Notas que regem: `Padrao_Logging_Estruturado` (log existe para investigar, e
`except` que engole erro e anti-padrao), `Escada_Preguica_de_Codigo` (degrau 5,
usar o que ja esta instalado: o `inspect` do SQLAlchemy), `TDD_RED_GREEN_REFACTOR`.
"""

from __future__ import annotations  # producao e 3.12, a maquina local e 3.9

import io
import os
import re
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_migrate_")
_banco = os.path.join(_tmp, "prova.db")

os.environ["DATABASE_URL"] = f"sqlite:///{_banco}"
os.environ["SECRET_KEY"] = "chave-jwt-de-teste"
os.environ["ZOARIA_SSO_SECRET"] = ""

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect, text                           # noqa: E402

from app.database import Base, engine                          # noqa: E402
from app import init_db                                        # noqa: E402
from app import models                                         # noqa: E402  (registra as tabelas)

Base.metadata.create_all(bind=engine)

# Colunas que existem no model e vao ser DERRUBADAS de proposito, para o banco
# ficar parecido com um que ainda nao migrou. Sem isso a prova nao mede nada: o
# `create_all` ja cria tudo, e um `migrate` que nao fizesse nada passaria.
# Nenhuma delas pode ter indice: o SQLite recusa o DROP COLUMN de coluna
# indexada, e a prova mediria o proprio tropeco em vez de medir o migrate.
DERRUBAR = [("usuarios", "telefone"), ("tarefas", "anexo_nome"),
            ("obrigacoes", "ancora")]

falhou = []


def checa(n, descricao, condicao):
    if condicao:
        print(f"  ok  {n:>3}. {descricao}")
    else:
        print(f"FALHA  {n:>3}. {descricao}")
        falhou.append(n)


def capturar(funcao):
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        funcao()
    return buffer.getvalue()


def colunas(tabela):
    return {c["name"] for c in inspect(engine).get_columns(tabela)}


derrubou = True
for tabela, coluna in DERRUBAR:
    try:
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {tabela} DROP COLUMN {coluna}"))
    except Exception as e:
        derrubou = False
        print(f"       (nao consegui derrubar {tabela}.{coluna}: {e})")

checa(1, "o cenario de banco desatualizado foi montado de fato, e a prova nao "
         "esta medindo um banco que ja nascia completo",
      derrubou and all(c not in colunas(t) for t, c in DERRUBAR))

# ------------------------------------------------------------- primeira rodada

saida1 = capturar(init_db.migrate)

checa(2, "a 1a rodada cria as colunas que faltavam",
      all(c in colunas(t) for t, c in DERRUBAR))

# --------------------------------------------------------------- segunda rodada

saida2 = capturar(init_db.migrate)

ja_existe = [l for l in saida2.splitlines() if "já existe" in l or "ja existe" in l]

checa(3, f"a 2a rodada nao diz que a coluna ja existe (linhas assim: {len(ja_existe)})",
      not ja_existe)

erros = [l for l in (saida1 + saida2).splitlines() if "Erro na coluna" in l]

checa(4, f"em rodada nenhuma sai 'Erro na coluna' (achadas: {len(erros)})",
      not erros)

checa(5, "a 2a rodada e SILENCIO, e nao apenas silencio sobre 'já existe'",
      saida2.strip() == "")

# --------------------- nenhuma migracao se perdeu no caminho: cada ADD COLUMN
#     da lista tem de corresponder a uma coluna existente no schema final.

lista = getattr(init_db, "MIGRACOES", None)
if lista is None:
    lista = []
faltando = []
for _nome, sql in lista:
    m = re.search(r"ALTER TABLE (\w+) ADD COLUMN (\w+)", sql, re.I)
    if m and m.group(1) in inspect(engine).get_table_names():
        if m.group(2) not in colunas(m.group(1)):
            faltando.append(f"{m.group(1)}.{m.group(2)}")

checa(6, f"a lista de migracoes esta exposta no modulo, para a prova conferir "
         f"o schema final ({len(lista)} migracoes lidas)",
      len(lista) > 0)

checa(7, f"toda coluna de ADD COLUMN existe no schema final (faltando: {faltando})",
      not faltando)

# ------------------- 22.4: o silencio nao pode ter virado silencio sobre TUDO.
#     Uma migracao invalida ainda tem de reportar. Se este item passar por
#     engano, a fase trocou 45 erros falsos por zero erro verdadeiro.

try:
    saida3 = capturar(lambda: init_db.migrate(
        [("migracao_quebrada_de_proposito",
          "ALTER TABLE tabela_que_nao_existe ADD COLUMN nada INTEGER")]))
    aceita_lista = True
except TypeError as e:
    saida3, aceita_lista = f"(migrate nao aceita lista: {e})", False

checa(8, "o migrate aceita uma lista propria, que e como a prova injeta a "
         "migracao quebrada", aceita_lista)

checa(9, f"migracao invalida CONTINUA reportando erro (saida: {saida3.strip()[:80]!r})",
      "Erro na coluna" in saida3 and "migracao_quebrada_de_proposito" in saida3)

# ------------------ 10: o caso que o verificador adversarial achou, e que esta
#     prova nao cobria. `identificadores_maior` e um `ALTER COLUMN ... TYPE`, que
#     o SQLite NAO aceita. Num banco em que a coluna existe com o tamanho ANTIGO,
#     a decisao "precisa rodar" acerta, a execucao falha com erro de sintaxe, e
#     como a coluna nunca cresce o erro se repete em TODO boot, para sempre. Nao
#     acontece em producao, que e Postgres; acontece em quem restaura um banco
#     antigo em SQLite para caçar bug, que e justamente quem esta lendo o log.

with engine.begin() as conn:
    conn.execute(text("ALTER TABLE obrigacoes DROP COLUMN identificadores"))
capturar(init_db.migrate)          # recria a coluna com o VARCHAR(200) da lista

tamanho = {c["name"]: c for c in inspect(engine).get_columns("obrigacoes")}
tamanho = getattr(tamanho["identificadores"]["type"], "length", None)

saidas = [capturar(init_db.migrate) for _ in range(5)]

checa(10, f"a coluna voltou com o tamanho antigo, que e o cenario do caso "
          f"(length={tamanho})", tamanho == 200)

checa(11, "cinco rodadas seguidas contra esse banco ficam em silencio, em vez de "
          "repetir o mesmo erro de sintaxe para sempre",
      all(s.strip() == "" for s in saidas))

for arquivo in Path(_tmp).glob("*"):
    arquivo.unlink()
os.rmdir(_tmp)

if falhou:
    print(f"\nPROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print("\nPROVA OK: 11 checagens verdes")
