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

db.close()
print("\n" + ("TODAS AS PROVAS PASSARAM" if ok else "HOUVE FALHA"))
sys.exit(0 if ok else 1)
