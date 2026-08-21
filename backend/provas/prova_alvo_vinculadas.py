"""
prova_alvo_vinculadas.py — obrigação de cliente específico.

O alvo era sempre `regra UNIÃO vinculadas`, e campo de regra vazio significava
TODOS. Consequência: não existia jeito de dizer "esta obrigação é só destes
clientes" -- vincular empresas apenas SOMAVA ao que a regra já pegava.

Na prática isso apareceu gerando um mês de teste: cinco obrigações de teste, com
regime e segmento em branco, alcançaram o escritório inteiro e criaram 7114
tarefas.

Agora a obrigação escolhe entre dois modos:
    'regra'      (padrão, como sempre foi)  regra UNIÃO vinculadas
    'vinculadas'                            somente as vinculadas

Rodar:  python provas/prova_alvo_vinculadas.py
"""
import os, sys, tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("DATABASE_URL", "sqlite:///" + tempfile.mktemp(suffix=".db"))

from app.database import SessionLocal, Base, engine          # noqa: E402
from app.models import Empresa, Obrigacao                    # noqa: E402
from app.services.gerador import empresas_alvo               # noqa: E402

ok = True
def check(nome, cond, extra=""):
    global ok
    print(("  OK   " if cond else "  FALHA ") + nome + (f"  {extra}" if extra else ""))
    ok = ok and bool(cond)

Base.metadata.create_all(bind=engine)
db = SessionLocal()
db.query(Obrigacao).delete(); db.query(Empresa).delete(); db.commit()

# três de teste + duas "reais", como no escritório
teste_a = Empresa(razao_social="TESTE A", regime_tributario="lucro_real", segmento="servico", ativo=True)
teste_b = Empresa(razao_social="TESTE B", regime_tributario="lucro_presumido", segmento="comercio", ativo=True)
teste_c = Empresa(razao_social="TESTE C", regime_tributario="simples_nacional", segmento="servico", ativo=True)
real_1  = Empresa(razao_social="CLIENTE REAL 1", regime_tributario="lucro_real", segmento="servico", ativo=True)
real_2  = Empresa(razao_social="CLIENTE REAL 2", regime_tributario="simples_nacional", segmento="comercio", ativo=True)
db.add_all([teste_a, teste_b, teste_c, real_1, real_2]); db.commit()

def nomes(o):
    return sorted(e.razao_social for e in empresas_alvo(db, o))

print("\n=== 1. o padrão não muda: regra vazia alcança todas ===")
o = Obrigacao(nome="Sem restrição", ativa=True)
db.add(o); db.commit()
check("cinco empresas", len(nomes(o)) == 5, f"({len(nomes(o))})")
check("modo padrão é 'regra'", (o.alvo_modo or "regra") == "regra")

print("\n=== 2. vincular NÃO restringe no modo regra — era a armadilha ===")
o.empresas = [teste_a]
db.commit()
check("continua alcançando as cinco", len(nomes(o)) == 5, f"({nomes(o)})")

print("\n=== 3. 'somente as vinculadas' restringe de verdade ===")
o.alvo_modo = "vinculadas"
o.empresas = [teste_a, teste_b, teste_c]
db.commit()
check("só as três de teste", nomes(o) == ["TESTE A", "TESTE B", "TESTE C"], f"({nomes(o)})")
check("nenhum cliente real entra", all("REAL" not in n for n in nomes(o)))

print("\n=== 4. a regra é ignorada no modo vinculadas ===")
o.aplica_regimes = "lucro_real"      # pegaria TESTE A e CLIENTE REAL 1
db.commit()
check("segue nas três vinculadas, sem o real de lucro real",
      nomes(o) == ["TESTE A", "TESTE B", "TESTE C"], f"({nomes(o)})")

print("\n=== 5. bloqueada e inativa continuam fora, nos dois modos ===")
teste_b.bloqueado = True
teste_c.ativo = False
db.commit()
check("vinculada bloqueada não entra", "TESTE B" not in nomes(o), f"({nomes(o)})")
check("vinculada inativa não entra", "TESTE C" not in nomes(o))
check("sobra só a boa", nomes(o) == ["TESTE A"], f"({nomes(o)})")

print("\n=== 6. modo vinculadas sem vínculo nenhum não gera nada ===")
o.empresas = []
db.commit()
check("lista vazia, e não o escritório inteiro", nomes(o) == [], f"({nomes(o)})")

print("\n=== 7. gerar só as obrigações escolhidas ===")
# Sem recorte, o botão gerava TODAS as ativas -- num escritório com dezenas de
# obrigações e dezenas de clientes, milhares de tarefas de uma vez, mesmo quando
# se quer só a que acabou de ser cadastrada.
from app.models import Tarefa, tarefa_responsaveis                       # noqa: E402
from app.services.gerador import gerar_tarefas                           # noqa: E402
from app.models import StatusTarefa                                      # noqa: E402

db.execute(tarefa_responsaveis.delete()); db.query(Tarefa).delete()
db.query(Obrigacao).delete(); db.commit()
for e in (teste_a, teste_b, teste_c, real_1, real_2):
    e.ativo, e.bloqueado = True, False
db.commit()

meses = "1,2,3,4,5,6,7,8,9,10,11,12"
alvo   = Obrigacao(nome="Só esta", ativa=True, meses_ativos=meses,
                   regra_prazo_tipo="ultimo_dia_util", competencia_ref="mes_anterior")
outra1 = Obrigacao(nome="Outra 1", ativa=True, meses_ativos=meses,
                   regra_prazo_tipo="ultimo_dia_util", competencia_ref="mes_anterior")
outra2 = Obrigacao(nome="Outra 2", ativa=True, meses_ativos=meses,
                   regra_prazo_tipo="ultimo_dia_util", competencia_ref="mes_anterior")
db.add_all([alvo, outra1, outra2]); db.commit()

r = gerar_tarefas(db, 9, 2026, [alvo.id])
criadas = db.query(Tarefa).all()
check("gerou só da obrigação escolhida",
      {t.obrigacao_id for t in criadas} == {alvo.id}, f"({r['criadas']} tarefas)")
check("uma por empresa alcançada (5)", r["criadas"] == 5, f"({r['criadas']})")

db.execute(tarefa_responsaveis.delete()); db.query(Tarefa).delete(); db.commit()
r2 = gerar_tarefas(db, 9, 2026)          # sem recorte
check("sem recorte, gera das três", r2["criadas"] == 15, f"({r2['criadas']})")

db.execute(tarefa_responsaveis.delete()); db.query(Tarefa).delete(); db.commit()
r3 = gerar_tarefas(db, 9, 2026, [])      # lista vazia = sem recorte, não "nenhuma"
check("lista vazia se comporta como 'todas'", r3["criadas"] == 15, f"({r3['criadas']})")

db.close()
print("\n" + ("TODAS AS PROVAS PASSARAM" if ok else "HOUVE FALHA"))
sys.exit(0 if ok else 1)
