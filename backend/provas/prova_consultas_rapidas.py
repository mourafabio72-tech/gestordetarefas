"""
prova_consultas_rapidas.py — trava o custo das consultas de tarefas.

Não mede tempo (que varia com a máquina): mede QUANTAS IDAS AO BANCO cada
endpoint faz. É o número que explica a lentidão contra o Postgres do servidor,
onde cada consulta é um ida-e-volta de rede.

Medido antes de corrigir, com este mesmo script:
    listagem     500 tarefas -> 503 consultas   (uma por tarefa, N+1)
    por setor     6 setores  ->  ~40 consultas  (laço com 5 count() por setor)

A listagem tem de ficar CONSTANTE: 500 tarefas ou 5.000, o mesmo punhado de
consultas. É isso que a prova trava -- se alguém acrescentar um campo no
`TarefaResponse` sem o carregamento correspondente, o N+1 volta e aqui quebra.

Rodar:  python provas/prova_consultas_rapidas.py
"""
import os, sys, tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ.setdefault("DATABASE_URL", "sqlite:///" + tempfile.mktemp(suffix=".db"))

from sqlalchemy import event                                    # noqa: E402
from app.database import engine, SessionLocal, Base             # noqa: E402
from app.models import (Tarefa, Usuario, Empresa, Setor,        # noqa: E402
                        StatusTarefa, tarefa_responsaveis)
from app.init_db import criar_indices                           # noqa: E402
from app.routes.tarefas import (list_tarefas,                   # noqa: E402
                                get_dashboard_stats_por_setor)
from app.schemas import TarefaResponse                          # noqa: E402

ok = True
def check(nome, cond, extra=""):
    global ok
    print(("  OK   " if cond else "  FALHA ") + nome + (f"  {extra}" if extra else ""))
    ok = ok and bool(cond)

consultas = {"n": 0}

@event.listens_for(engine, "before_cursor_execute")
def _conta(conn, cursor, stmt, params, context, executemany):
    consultas["n"] += 1


def povoar(n_tarefas, n_setores=6, n_users=12):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # a associação primeiro: apagar só as tarefas deixa órfão e o id é reusado
    db.execute(tarefa_responsaveis.delete())
    db.query(Tarefa).delete()
    db.commit()
    emp = db.query(Empresa).first()
    if not emp:
        emp = Empresa(razao_social="ACME", cnpj="00000000000191")
        db.add(emp)
        db.add_all([Setor(nome=f"Setor {i}") for i in range(n_setores)])
        db.add_all([Usuario(nome=f"U{i}", email=f"u{i}@x.com", senha_hash="x",
                            grupo="admin" if i == 0 else "colaborador")
                    for i in range(n_users)])
        db.commit()
    setores = db.query(Setor).all()
    users = db.query(Usuario).all()
    lote = []
    for i in range(n_tarefas):
        t = Tarefa(titulo=f"T{i}", empresa_id=emp.id,
                   setor_id=setores[i % len(setores)].id,
                   responsavel_id=users[i % len(users)].id,
                   supervisor_id=users[(i + 1) % len(users)].id,
                   status=StatusTarefa.PENDENTE)
        t.responsaveis = [users[i % len(users)], users[(i + 2) % len(users)]]
        lote.append(t)
    db.add_all(lote)
    db.commit()
    admin = db.query(Usuario).filter(Usuario.grupo == "admin").first()
    return db, admin


def medir(fn):
    consultas["n"] = 0
    resultado = fn()
    return consultas["n"], resultado


print("\n=== 1. listagem de tarefas: custo constante, não por linha ===")
custos = {}
for n in (50, 200, 500):
    db, admin = povoar(n)
    def _listar():
        itens = list_tarefas(db=db, current_user=admin)
        # serializar é parte do custo: é aqui que o N+1 antigo acontecia
        return [TarefaResponse.model_validate(t) for t in itens]
    q, itens = medir(_listar)
    custos[n] = q
    print(f"    {n:>4} tarefas -> {q:>3} consultas  ({len(itens)} itens)")
    db.close()

check("500 tarefas custam o mesmo que 50", custos[500] == custos[50],
      f"({custos[50]} vs {custos[500]})")
check("e são poucas, não uma por tarefa", custos[500] <= 6, f"({custos[500]})")
check("longe das 503 de antes", custos[500] < 50)

print("\n=== 2. resumo por setor: uma consulta, não um laço ===")
db, admin = povoar(300)
q, blocos = medir(lambda: get_dashboard_stats_por_setor(db=db, current_user=admin))
print(f"    6 setores -> {q} consulta(s), {len(blocos)} bloco(s)")
check("no máximo 3 consultas para o painel inteiro", q <= 3, f"({q})")
check("um bloco por setor com tarefa", len(blocos) == 6, f"({len(blocos)})")
check("as contas fecham",
      all(b["total_tarefas"] == b["pendentes"] + b["em_andamento"] + b["concluidas"]
          for b in blocos))
check("soma dos setores = total de tarefas",
      sum(b["total_tarefas"] for b in blocos) == 300,
      f"({sum(b['total_tarefas'] for b in blocos)})")
db.close()

print("\n=== 3. o resumo continua certo com escopo restrito ===")
# Quem não é admin só enxerga as próprias tarefas -- o GROUP BY tem de respeitar
# isso. Um agrupamento que ignorasse o escopo vazaria número de outra equipe.
db, admin = povoar(120)
comum = db.query(Usuario).filter(Usuario.grupo != "admin").first()
comum.permissoes = '{"escopo_tarefas": "proprias"}'
db.commit()
q_adm, blocos_adm = medir(lambda: get_dashboard_stats_por_setor(db=db, current_user=admin))
q_com, blocos_com = medir(lambda: get_dashboard_stats_por_setor(db=db, current_user=comum))
total_adm = sum(b["total_tarefas"] for b in blocos_adm)
total_com = sum(b["total_tarefas"] for b in blocos_com)
print(f"    admin vê {total_adm} tarefas em {q_adm} consulta(s); "
      f"colaborador vê {total_com} em {q_com}")
check("admin vê todas", total_adm == 120, f"({total_adm})")
check("colaborador vê menos que o admin", total_com < total_adm, f"({total_com})")
check("colaborador vê alguma coisa (não zerou por engano)", total_com > 0, f"({total_com})")
check("escopo restrito não custa mais consultas", q_com <= 3, f"({q_com})")
db.close()

print("\n=== 4. os índices são criados e recriar não quebra ===")
criar_indices()
criar_indices()   # idempotente: rodar de novo a cada boot não pode falhar
from sqlalchemy import inspect                                   # noqa: E402
nomes = {i["name"] for i in inspect(engine).get_indexes("tarefas")}
for esperado in ("ix_tarefas_empresa_id", "ix_tarefas_setor_id",
                 "ix_tarefas_responsavel_id", "ix_tarefas_status",
                 "ix_tarefas_data_prazo", "ix_tarefas_status_prazo"):
    check(f"índice {esperado}", esperado in nomes)
resp = {i["name"] for i in inspect(engine).get_indexes("tarefa_responsaveis")}
check("índice por usuário na tabela de responsáveis (a PK começa por tarefa_id)",
      "ix_tarefa_resp_usuario" in resp, f"({resp})")

print("\n" + ("TODAS AS PROVAS PASSARAM" if ok else "HOUVE FALHA"))
sys.exit(0 if ok else 1)
