"""
prova_gestor_setor.py — supervisor da tarefa preenchido pelo gestor do setor.

Antes, o supervisor saía só do `gestor_id` da pessoa responsável. Quem não
tivesse gestor preenchido gerava tarefa SEM supervisor -- e ninguém era avisado
do atraso dela. Preencher gestor_id pessoa a pessoa é trabalho que se refaz a
cada admissão.

Agora o SETOR tem gestor, e ele entra como degrau do meio numa escada do mais
específico ao mais geral -- a mesma lógica que o app já usa no responsável, onde
a matriz empresa×setor vence o padrão da obrigação:

    1. gestor da própria pessoa
    2. gestor do SETOR          <- novo, um cadastro cobre a equipe inteira
    3. supervisor padrão da obrigação

Rodar:  python provas/prova_gestor_setor.py
"""
import os, sys, tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("DATABASE_URL", "sqlite:///" + tempfile.mktemp(suffix=".db"))

from app.database import SessionLocal, Base, engine                 # noqa: E402
from app.models import (Empresa, Setor, Usuario, Obrigacao, Tarefa,  # noqa: E402
                        tarefa_responsaveis)
from app.services.gerador import gerar_tarefas                      # noqa: E402

ok = True
def check(nome, cond, extra=""):
    global ok
    print(("  OK   " if cond else "  FALHA ") + nome + (f"  {extra}" if extra else ""))
    ok = ok and bool(cond)

Base.metadata.create_all(bind=engine)


def cenario(resp_tem_gestor, setor_tem_gestor, obrig_tem_sup):
    """Monta do zero e devolve o supervisor da tarefa gerada."""
    db = SessionLocal()
    # a associação primeiro: apagar só a tarefa deixa órfão e o id é reusado
    db.execute(tarefa_responsaveis.delete())
    for m in (Tarefa, Obrigacao, Empresa, Setor, Usuario):
        db.query(m).delete()
    db.commit()

    chefe   = Usuario(nome="Chefe Direto", email="chefe@x.com", senha_hash="x", grupo="gestor")
    do_setor = Usuario(nome="Gestor do Setor", email="setor@x.com", senha_hash="x", grupo="gestor")
    da_obrig = Usuario(nome="Supervisor da Obrigação", email="obr@x.com", senha_hash="x", grupo="gestor")
    db.add_all([chefe, do_setor, da_obrig]); db.commit()

    analista = Usuario(nome="Analista", email="an@x.com", senha_hash="x", grupo="colaborador",
                       gestor_id=chefe.id if resp_tem_gestor else None)
    db.add(analista); db.commit()

    setor = Setor(nome="Contábil", gestor_id=do_setor.id if setor_tem_gestor else None)
    db.add(setor); db.commit()

    emp = Empresa(razao_social="ACME", cnpj="1", regime_tributario="lucro_real", ativo=True)
    db.add(emp); db.commit()

    o = Obrigacao(nome="Balancete", setor_id=setor.id, responsavel_id=analista.id,
                  supervisor_id=da_obrig.id if obrig_tem_sup else None,
                  regra_prazo_tipo="ultimo_dia_util", meses_ativos="1,2,3,4,5,6,7,8,9,10,11,12",
                  competencia_ref="mes_anterior", ativa=True)
    db.add(o); db.commit()

    gerar_tarefas(db, 9, 2026)
    t = db.query(Tarefa).first()
    nome = None
    if t and t.supervisor_id:
        nome = db.query(Usuario.nome).filter(Usuario.id == t.supervisor_id).first()[0]
    db.close()
    return nome


print("\n=== 1. gestor da pessoa vence — o mais específico ===")
n = cenario(resp_tem_gestor=True, setor_tem_gestor=True, obrig_tem_sup=True)
check("com as três fontes, ganha o gestor direto", n == "Chefe Direto", f"({n})")

print("\n=== 2. sem gestor próprio, entra o gestor do SETOR ===")
n = cenario(resp_tem_gestor=False, setor_tem_gestor=True, obrig_tem_sup=True)
check("o setor cobre quem não tem gestor", n == "Gestor do Setor", f"({n})")
check("e não caiu direto no supervisor da obrigação", n != "Supervisor da Obrigação")

print("\n=== 3. sem gestor e sem setor, o padrão da obrigação ===")
n = cenario(resp_tem_gestor=False, setor_tem_gestor=False, obrig_tem_sup=True)
check("último degrau da escada", n == "Supervisor da Obrigação", f"({n})")

print("\n=== 4. o caso que gerava tarefa órfã ===")
n = cenario(resp_tem_gestor=False, setor_tem_gestor=False, obrig_tem_sup=False)
check("sem nenhuma fonte, segue sem supervisor (e a tarefa nasce)", n is None, f"({n})")
n = cenario(resp_tem_gestor=False, setor_tem_gestor=True, obrig_tem_sup=False)
check("mas basta o gestor do setor para deixar de ser órfã",
      n == "Gestor do Setor", f"({n})")

print("\n" + ("TODAS AS PROVAS PASSARAM" if ok else "HOUVE FALHA"))
sys.exit(0 if ok else 1)
