"""
prova_gerar_recorte_empresas.py — gerar o mês de algumas empresas, não de todas.

O botão "Gerar tarefas do mês" já sabia recortar por OBRIGAÇÃO (gerar só a que
acabou de ser cadastrada), mas não por EMPRESA: era o escritório inteiro ou
nada. Isso dói em três momentos reais -- cliente que entra no meio do mês,
regeneração depois de arrumar o cadastro de uma empresa, e conferir o resultado
num cliente antes de soltar para todos.

A regra dura: o recorte é INTERSEÇÃO com o que a obrigação alcança, nunca soma.
Escolher uma empresa aqui não a inscreve na obrigação -- isso é cadastro, e se
faz na obrigação. Se fosse soma, o botão de gerar viraria uma porta lateral para
burlar o alvo, e ninguém entenderia por que a tarefa apareceu.

Rodar:  python provas/prova_gerar_recorte_empresas.py
"""
import os, sys, tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("DATABASE_URL", "sqlite:///" + tempfile.mktemp(suffix=".db"))

from app.database import SessionLocal, Base, engine                      # noqa: E402
from app.models import (Empresa, Obrigacao, Tarefa, Setor, Usuario,      # noqa: E402
                        tarefa_responsaveis)
from app.services.gerador import gerar_tarefas                           # noqa: E402

ok = True
def check(nome, cond, extra=""):
    global ok
    print(("  OK   " if cond else "  FALHA ") + nome + (f"  {extra}" if extra else ""))
    ok = ok and bool(cond)

Base.metadata.create_all(bind=engine)
db = SessionLocal()
db.execute(tarefa_responsaveis.delete())
for m in (Tarefa, Obrigacao, Empresa, Setor, Usuario):
    db.query(m).delete()
db.commit()

MESES = "1,2,3,4,5,6,7,8,9,10,11,12"

alfa  = Empresa(razao_social="ALFA LTDA",  regime_tributario="lucro_real",      segmento="servico",  ativo=True)
beta  = Empresa(razao_social="BETA LTDA",  regime_tributario="lucro_real",      segmento="servico",  ativo=True)
gama  = Empresa(razao_social="GAMA LTDA",  regime_tributario="simples_nacional", segmento="comercio", ativo=True)
db.add_all([alfa, beta, gama]); db.commit()

# Obrigação de perfil: pega quem é lucro_real (alfa e beta), nunca gama.
so_real = Obrigacao(nome="ECF", ativa=True, meses_ativos=MESES,
                    aplica_regimes="lucro_real", regra_prazo_tipo="ultimo_dia_util")
# Obrigação sem regra: alcança todo mundo.
todas = Obrigacao(nome="Balancete", ativa=True, meses_ativos=MESES,
                  regra_prazo_tipo="ultimo_dia_util")
db.add_all([so_real, todas]); db.commit()

def limpar():
    db.execute(tarefa_responsaveis.delete())
    db.query(Tarefa).delete(); db.commit()

def empresas_com_tarefa():
    return {t.empresa_id for t in db.query(Tarefa).all()}

print("\n=== 1. sem recorte, gera para todas (comportamento de sempre) ===")
limpar()
r = gerar_tarefas(db, 9, 2026)
check("as tres empresas receberam", empresas_com_tarefa() == {alfa.id, beta.id, gama.id},
      f"({empresas_com_tarefa()})")
check("5 tarefas: 2 da ECF + 3 do Balancete", r["criadas"] == 5, f"({r['criadas']})")
check("empresas_no_recorte e None quando nao ha recorte",
      r["empresas_no_recorte"] is None, f"({r['empresas_no_recorte']})")

print("\n=== 2. recorte de uma empresa gera so a dela ===")
limpar()
r = gerar_tarefas(db, 9, 2026, empresa_ids=[alfa.id])
check("so a ALFA recebeu", empresas_com_tarefa() == {alfa.id}, f"({empresas_com_tarefa()})")
check("2 tarefas: ECF + Balancete", r["criadas"] == 2, f"({r['criadas']})")
check("a resposta diz o tamanho do recorte", r["empresas_no_recorte"] == 1,
      f"({r['empresas_no_recorte']})")

print("\n=== 3. recorte de duas gera as duas, e so elas ===")
limpar()
gerar_tarefas(db, 9, 2026, empresa_ids=[alfa.id, gama.id])
check("ALFA e GAMA receberam", empresas_com_tarefa() == {alfa.id, gama.id},
      f"({empresas_com_tarefa()})")
check("BETA ficou de fora", beta.id not in empresas_com_tarefa())

print("\n=== 4. o recorte e INTERSECAO, nunca soma ===")
# GAMA e simples_nacional: a ECF nao a alcanca. Escolher GAMA no botao de gerar
# NAO pode inscreve-la na ECF -- se inscrevesse, o botao viraria porta lateral
# para burlar o alvo da obrigacao.
limpar()
gerar_tarefas(db, 9, 2026, empresa_ids=[gama.id])
titulos = {t.titulo for t in db.query(Tarefa).all()}
check("GAMA recebeu o Balancete", any("Balancete" in t for t in titulos), f"({titulos})")
check("GAMA NAO recebeu a ECF", not any("ECF" in t for t in titulos), f"({titulos})")

print("\n=== 5. recorte de empresa que nenhuma obrigacao alcanca nao cria nada ===")
limpar()
fora = Empresa(razao_social="FORA LTDA", regime_tributario="lucro_real",
               segmento="servico", ativo=False)          # inativa: fora do alvo
db.add(fora); db.commit()
r = gerar_tarefas(db, 9, 2026, empresa_ids=[fora.id])
check("nenhuma tarefa criada", r["criadas"] == 0, f"({r['criadas']})")
check("e nao estoura", db.query(Tarefa).count() == 0)

print("\n=== 6. os dois recortes juntos: uma obrigacao numa empresa ===")
limpar()
r = gerar_tarefas(db, 9, 2026, obrigacao_ids=[so_real.id], empresa_ids=[beta.id])
check("uma tarefa so", r["criadas"] == 1, f"({r['criadas']})")
check("da BETA", empresas_com_tarefa() == {beta.id}, f"({empresas_com_tarefa()})")
check("e e a ECF", {t.titulo for t in db.query(Tarefa).all()} and
      all("ECF" in t.titulo for t in db.query(Tarefa).all()))

print("\n=== 7. lista vazia vale como 'todas', igual ao recorte de obrigacao ===")
# A tela manda [] quando o usuario escolhe "todas as empresas". Tratar [] como
# "nenhuma empresa" faria o botao gerar zero tarefas em silencio.
limpar()
r = gerar_tarefas(db, 9, 2026, empresa_ids=[])
check("gerou para as tres", empresas_com_tarefa() == {alfa.id, beta.id, gama.id},
      f"({empresas_com_tarefa()})")

print("\n=== 8. regerar com recorte nao duplica o que ja existe ===")
limpar()
gerar_tarefas(db, 9, 2026, empresa_ids=[alfa.id])
r = gerar_tarefas(db, 9, 2026, empresa_ids=[alfa.id])
check("segunda passada nao cria nada", r["criadas"] == 0, f"({r['criadas']})")
check("e conta as puladas", r["puladas"] == 2, f"({r['puladas']})")
check("continuam 2 tarefas no banco", db.query(Tarefa).count() == 2)

db.close()
print("\n" + ("TODAS AS PROVAS PASSARAM" if ok else "HOUVE FALHA"))
sys.exit(0 if ok else 1)
