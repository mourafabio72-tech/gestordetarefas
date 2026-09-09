"""
prova_gerador_multiplos.py — a tarefa gerada nasce com TODOS os responsáveis do
setor daquela empresa, e some da tela só quando todos eles estão bloqueados.

Duas coisas se provam aqui:

1. UMA tarefa por competência, com N responsáveis. Nunca uma tarefa por pessoa:
   três analistas no setor fiscal de um cliente continuam sendo um único
   trabalho, com três donos. O supervisor sai do PRIMEIRO da lista, mantendo a
   escada que já existia (gestor da pessoa, gestor do setor, supervisor padrão
   da obrigação).

2. Bloquear UM responsável não pode fazer a tarefa sumir. A regra antiga
   escondia a tarefa quando o responsável PRINCIPAL estava bloqueado, e com
   vários isso apagaria da tela o trabalho que o outro continua tocando. A
   tarefa some quando TODOS estão bloqueados, e tarefa SEM dono nenhum continua
   aparecendo, porque buraco de cadastro escondido é buraco que ninguém arruma.

Rodar:  cd backend && ./venv/bin/python provas/prova_gerador_multiplos.py
"""
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("DATABASE_URL", "sqlite:///" + tempfile.mktemp(suffix=".db"))

from app.database import SessionLocal, Base, engine                  # noqa: E402
from app.models import (Empresa, Setor, Usuario, Obrigacao, Tarefa,   # noqa: E402
                        EmpresaSetorResponsavel, tarefa_responsaveis,
                        empresa_setor_resp_usuarios)
from app.services import resp_setor                                  # noqa: E402
from app.services.gerador import gerar_tarefas                       # noqa: E402
from app.visibilidade import (responsavel_visivel,                   # noqa: E402
                              tarefas_abertas_do_usuario)
from app.services.whatsapp import destinatarios_alerta               # noqa: E402

ok = True


def check(nome, cond, extra=""):
    global ok
    print(("  OK   " if cond else "  FALHA ") + nome + (f"  {extra}" if extra else ""))
    ok = ok and bool(cond)


Base.metadata.create_all(bind=engine)


def limpar(db):
    db.execute(tarefa_responsaveis.delete())
    db.execute(empresa_setor_resp_usuarios.delete())
    for m in (Tarefa, EmpresaSetorResponsavel, Obrigacao, Empresa, Setor, Usuario):
        db.query(m).delete()
    db.commit()


def montar(quantos_resp, resp_tem_gestor=True, setor_tem_gestor=False,
           obrig_tem_sup=False, obrig_tem_resp=False):
    """Monta o cenário do zero e devolve (db, tarefa, pessoas)."""
    db = SessionLocal()
    limpar(db)

    chefe = Usuario(nome="Chefe da Ana", email="chefe@x.com", senha_hash="x", grupo="gestor")
    do_setor = Usuario(nome="Gestor do Setor", email="gsetor@x.com", senha_hash="x", grupo="gestor")
    da_obrig = Usuario(nome="Supervisor da Obrigação", email="sobr@x.com", senha_hash="x", grupo="gestor")
    padrao = Usuario(nome="Padrão da Obrigação", email="pobr@x.com", senha_hash="x", grupo="analista")
    db.add_all([chefe, do_setor, da_obrig, padrao])
    db.commit()

    pessoas = []
    for i, nome in enumerate(("Ana", "Bruno", "Carla")[:quantos_resp]):
        u = Usuario(nome=nome, email=f"{nome.lower()}@x.com", senha_hash="x",
                    grupo="analista",
                    gestor_id=chefe.id if (i == 0 and resp_tem_gestor) else None)
        db.add(u)
        pessoas.append(u)
    db.commit()

    setor = Setor(nome="Fiscal", ativo=True,
                  gestor_id=do_setor.id if setor_tem_gestor else None)
    db.add(setor)
    db.commit()

    emp = Empresa(razao_social="ACME", cnpj="1", regime_tributario="lucro_real", ativo=True)
    db.add(emp)
    db.commit()

    if quantos_resp:
        vinculo = EmpresaSetorResponsavel(empresa_id=emp.id, setor_id=setor.id)
        db.add(vinculo)
        resp_setor.gravar(db, vinculo, [p.id for p in pessoas])
    db.commit()

    o = Obrigacao(nome="Apuração", setor_id=setor.id,
                  responsavel_id=padrao.id if obrig_tem_resp else None,
                  supervisor_id=da_obrig.id if obrig_tem_sup else None,
                  regra_prazo_tipo="ultimo_dia_util",
                  meses_ativos="1,2,3,4,5,6,7,8,9,10,11,12",
                  competencia_ref="mes_anterior", ativa=True)
    db.add(o)
    db.commit()

    gerar_tarefas(db, 9, 2026)
    t = db.query(Tarefa).first()
    return db, t, {"pessoas": pessoas, "chefe": chefe, "do_setor": do_setor,
                   "da_obrig": da_obrig, "padrao": padrao, "empresa": emp,
                   "setor": setor}


def visiveis(db):
    return db.query(Tarefa).filter(responsavel_visivel()).count()


print("\n=== 1. uma tarefa, vários donos ===")
db, t, c = montar(3)
check("gerou UMA tarefa, e não uma por pessoa", db.query(Tarefa).count() == 1,
      f"({db.query(Tarefa).count()})")
check("os três responsáveis estão na tarefa",
      sorted(u.id for u in t.responsaveis) == sorted(p.id for p in c["pessoas"]),
      f"({[u.nome for u in t.responsaveis]})")
check("o principal é o primeiro da lista do setor",
      t.responsavel_id == c["pessoas"][0].id,
      f"({t.responsavel_id} vs {c['pessoas'][0].id})")
check("a ordem do cadastro é a ordem da tarefa",
      [u.id for u in t.responsaveis] == [p.id for p in c["pessoas"]],
      f"({[u.nome for u in t.responsaveis]})")
db.close()

print("\n=== 2. o supervisor sai do primeiro, e a escada continua de pé ===")
db, t, c = montar(3, resp_tem_gestor=True)
check("degrau 1: gestor da primeira pessoa da lista",
      t.supervisor_id == c["chefe"].id, f"({t.supervisor_id})")
db.close()

db, t, c = montar(3, resp_tem_gestor=False, setor_tem_gestor=True)
check("degrau 2: sem gestor na pessoa, entra o gestor do setor",
      t.supervisor_id == c["do_setor"].id, f"({t.supervisor_id})")
db.close()

db, t, c = montar(3, resp_tem_gestor=False, setor_tem_gestor=False, obrig_tem_sup=True)
check("degrau 3: sem os dois, entra o supervisor da obrigação",
      t.supervisor_id == c["da_obrig"].id, f"({t.supervisor_id})")
db.close()

print("\n=== 3. bloquear UM não faz a tarefa sumir ===")
db, t, c = montar(2)
check("com os dois ativos, a tarefa aparece", visiveis(db) == 1)

c["pessoas"][0].bloqueado = True          # o PRINCIPAL, que é o caso do bug
db.commit()
check("bloquear o principal NÃO some com a tarefa, porque o outro responde",
      visiveis(db) == 1, f"({visiveis(db)})")

c["pessoas"][1].bloqueado = True
db.commit()
check("com TODOS bloqueados, aí sim a tarefa some", visiveis(db) == 0,
      f"({visiveis(db)})")

c["pessoas"][1].bloqueado = False
db.commit()
check("desbloquear um traz a tarefa de volta", visiveis(db) == 1)
db.close()

print("\n=== 4. tarefa sem dono nenhum não se esconde ===")
db, t, c = montar(0, obrig_tem_resp=False)
check("empresa sem responsável no setor ainda gera a tarefa",
      db.query(Tarefa).count() == 1, f"({db.query(Tarefa).count()})")
check("a tarefa nasceu sem responsável", t is None or (
      t.responsavel_id is None and not t.responsaveis))
check("e continua aparecendo, porque falta de cadastro escondida não se arruma",
      visiveis(db) == 1, f"({visiveis(db)})")
db.close()

print("\n=== 5. o fallback da obrigação continua valendo (sai na fase 13) ===")
db, t, c = montar(0, obrig_tem_resp=True)
check("sem matriz, a tarefa herda o responsável padrão da obrigação",
      t.responsavel_id == c["padrao"].id, f"({t.responsavel_id})")
check("e ele entra também na lista, não só na coluna",
      [u.id for u in t.responsaveis] == [c["padrao"].id],
      f"({[u.nome for u in t.responsaveis]})")
db.close()

print("\n=== 6. o alerta alcanca a lista, e nao so o principal ===")
db, t, c = montar(2)
ana, bruno = c["pessoas"]
check("o principal recebe cobranca da tarefa dele",
      [x.id for x in tarefas_abertas_do_usuario(db, ana.id)] == [t.id])
check("o SEGUNDO responsavel tambem, que antes nao recebia nada",
      [x.id for x in tarefas_abertas_do_usuario(db, bruno.id)] == [t.id],
      "(filtrar por responsavel_id deixava este de fora)")
check("quem nao responde por ela nao recebe",
      tarefas_abertas_do_usuario(db, c["chefe"].id) == [])

ana.bloqueado = True
bruno.bloqueado = True
db.commit()
check("tarefa escondida na tela tambem nao vira cobranca",
      tarefas_abertas_do_usuario(db, ana.id) == [])
db.close()

print("\n=== 7. tarefa antiga, sem lista, ainda tem quem avisar ===")
db, t, c = montar(1)
t.responsaveis = []                 # como ficou o que foi gravado antes do M2M
db.commit()
db.refresh(t)
nomes = {d["nome"] for d in destinatarios_alerta(t)}
check("sem lista, o alerta cai no responsavel principal",
      c["pessoas"][0].nome in nomes, f"({nomes})")
db.close()

print("\n" + ("TODAS AS PROVAS PASSARAM" if ok else "HOUVE FALHA"))
sys.exit(0 if ok else 1)
