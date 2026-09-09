"""
prova_responsavel_so_da_matriz.py: quem atende sai da matriz da empresa, e só
dela.

A obrigação serve várias empresas. Ter um responsável nela era dizer que o
mesmo analista atende todo mundo, o que é falso no escritório: cada cliente tem
o seu. Pior, o fallback ESCONDIA a falta de cadastro, porque empresa sem
responsável no setor herdava o da obrigação e ninguém via o buraco.

O que se prova:
· o gerador não cai mais no responsável da obrigação;
· empresa sem responsável no setor gera tarefa SEM dono, em vez de não gerar;
· e a resposta da geração DIZ quantas nasceram assim, e de quais empresas.
  Sem esse número, tirar o fallback só troca um erro visível por um invisível.

Rodar:  cd backend && ./venv/bin/python provas/prova_responsavel_so_da_matriz.py
"""
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("DATABASE_URL", "sqlite:///" + tempfile.mktemp(suffix=".db"))

from app.database import SessionLocal, Base, engine                    # noqa: E402
from app.models import (Empresa, Setor, Usuario, Obrigacao, Tarefa,     # noqa: E402
                        EmpresaSetorResponsavel, tarefa_responsaveis,
                        empresa_setor_resp_usuarios)
from app.services import resp_setor                                    # noqa: E402
from app.services.gerador import gerar_tarefas                         # noqa: E402
from app.services.substituicao import aplicar_definitiva               # noqa: E402

ok = True


def check(nome, cond, extra=""):
    global ok
    print(("  OK   " if cond else "  FALHA ") + nome + (f"  {extra}" if extra else ""))
    ok = ok and bool(cond)


Base.metadata.create_all(bind=engine)


def montar(com_matriz_em, resp_na_obrigacao):
    """`com_matriz_em` = nomes das empresas que têm responsável no setor."""
    db = SessionLocal()
    db.execute(tarefa_responsaveis.delete())
    db.execute(empresa_setor_resp_usuarios.delete())
    for m in (Tarefa, EmpresaSetorResponsavel, Obrigacao, Empresa, Setor, Usuario):
        db.query(m).delete()
    db.commit()

    padrao = Usuario(nome="Padrão da Obrigação", email="p@x.com", senha_hash="x",
                     grupo="analista")
    ana = Usuario(nome="Ana", email="a@x.com", senha_hash="x", grupo="analista")
    db.add_all([padrao, ana])
    db.commit()

    setor = Setor(nome="Fiscal", ativo=True)
    db.add(setor)
    db.commit()

    empresas = {}
    for nome in ("Alfa", "Beta", "Gama"):
        e = Empresa(razao_social=nome, cnpj=nome, regime_tributario="lucro_real", ativo=True)
        db.add(e)
        db.commit()
        empresas[nome] = e
        # Toda empresa precisa da linha do setor, senão ela nem atende o serviço
        # e a obrigação não gera para ela: são duas faltas diferentes.
        v = EmpresaSetorResponsavel(empresa_id=e.id, setor_id=setor.id)
        db.add(v)
        resp_setor.gravar(db, v, [ana.id] if nome in com_matriz_em else [])
    db.commit()

    o = Obrigacao(nome="Apuração", setor_id=setor.id,
                  responsavel_id=padrao.id if resp_na_obrigacao else None,
                  regra_prazo_tipo="ultimo_dia_util",
                  meses_ativos="1,2,3,4,5,6,7,8,9,10,11,12",
                  competencia_ref="mes_anterior", ativa=True)
    db.add(o)
    db.commit()
    return db, o, {"padrao": padrao, "ana": ana, "setor": setor, "empresas": empresas}


def dono(db, razao):
    t = (db.query(Tarefa).join(Empresa, Tarefa.empresa_id == Empresa.id)
         .filter(Empresa.razao_social == razao).first())
    if not t:
        return "sem tarefa"
    return [u.nome for u in t.responsaveis], t.responsavel_id


print("\n=== 1. a matriz manda, e ela sozinha ===")
db, o, c = montar(com_matriz_em={"Alfa"}, resp_na_obrigacao=True)
r = gerar_tarefas(db, 9, 2026)
check("a empresa COM responsável no setor recebe a pessoa da matriz",
      dono(db, "Alfa") == (["Ana"], c["ana"].id), f"({dono(db, 'Alfa')})")
check("a empresa SEM responsável no setor NÃO herda o da obrigação",
      dono(db, "Beta") == ([], None), f"({dono(db, 'Beta')})")
check("mas a tarefa dela nasce assim mesmo", db.query(Tarefa).count() == 3,
      f"({db.query(Tarefa).count()} tarefas)")

print("\n=== 2. a geração DIZ quantas ficaram sem dono, e de quem ===")
check("o contador bate com as duas empresas sem cadastro",
      r.get("sem_responsavel") == 2, f"({r.get('sem_responsavel')})")
check("e nomeia as empresas, que é o que faz alguém ir arrumar",
      r.get("empresas_sem_responsavel") == ["Beta", "Gama"],
      f"({r.get('empresas_sem_responsavel')})")
db.close()

print("\n=== 3. com a matriz completa, ninguém fica sem dono ===")
db, o, c = montar(com_matriz_em={"Alfa", "Beta", "Gama"}, resp_na_obrigacao=True)
r = gerar_tarefas(db, 9, 2026)
check("as três receberam a pessoa da matriz",
      all(dono(db, n) == (["Ana"], c["ana"].id) for n in ("Alfa", "Beta", "Gama")))
check("o contador de sem dono é zero", r.get("sem_responsavel") == 0)
check("e a lista de empresas vem vazia, não ausente",
      r.get("empresas_sem_responsavel") == [])
db.close()

print("\n=== 4. obrigação sem responsável nenhum se comporta igual ===")
db, o, c = montar(com_matriz_em={"Alfa"}, resp_na_obrigacao=False)
r = gerar_tarefas(db, 9, 2026)
check("o resultado não muda: a coluna da obrigação não é lida",
      dono(db, "Alfa") == (["Ana"], c["ana"].id) and dono(db, "Beta") == ([], None))
check("e o contador é o mesmo", r.get("sem_responsavel") == 2)
db.close()

print("\n=== 5. a substituição não mexe mais na obrigação ===")
db, o, c = montar(com_matriz_em={"Alfa"}, resp_na_obrigacao=True)
resultado = aplicar_definitiva(db, c["padrao"].id, c["ana"].id)
db.refresh(o)
check("o responsável legado da obrigação fica onde estava",
      o.responsavel_id == c["padrao"].id,
      f"({o.responsavel_id} vs {c['padrao'].id})")
check("e a substituição não conta obrigação trocada por responsável",
      resultado.get("obrigacoes") == 0, f"({resultado})")
db.close()

print("\n" + ("TODAS AS PROVAS PASSARAM" if ok else "HOUVE FALHA"))
sys.exit(0 if ok else 1)
