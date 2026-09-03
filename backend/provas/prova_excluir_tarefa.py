"""
prova_excluir_tarefa.py — cancelar e, depois, excluir de vez.

A lixeira nunca excluiu: ela marcava a tarefa como CANCELADA. Tarefa avulsa
(criada à mão, sem obrigação) ficava então sem saída nenhuma -- "Excluir
competência" só apaga o que veio de obrigação, e clicar na lixeira de novo
apenas cancelava outra vez. Sobravam para sempre na lista.

Agora são dois passos: a primeira lixeira cancela (reversível, mantém o
histórico); a segunda, numa tarefa já cancelada, exclui de vez -- e leva o
comprovante do volume junto, para não virar arquivo órfão.

Rodar:  python provas/prova_excluir_tarefa.py
"""
import os, sys, tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("DATABASE_URL", "sqlite:///" + tempfile.mktemp(suffix=".db"))
os.environ.setdefault("UPLOAD_DIR", tempfile.mkdtemp())

from sqlalchemy import event                                          # noqa: E402
from app.database import SessionLocal, Base, engine                     # noqa: E402

# SQLite so checa chave estrangeira se mandarem. Producao e Postgres, que checa
# sempre: sem este PRAGMA a prova roda em um banco mais permissivo que o real e
# deixa passar exatamente o erro que derrubou a exclusao por competencia.
@event.listens_for(engine, "connect")
def _liga_fk(dbapi_con, _rec):
    dbapi_con.execute("PRAGMA foreign_keys=ON")

from app.models import (Empresa, Setor, Usuario, Tarefa,                # noqa: E402
                        StatusTarefa, tarefa_responsaveis,
                        TarefaEnvio, SaidaAcesso)
from app.routes.tarefas import (delete_tarefa,                          # noqa: E402
                                excluir_tarefas_competencia,
                                ExcluirCompetenciaBody)
from app.services import upload as up                                   # noqa: E402

ok = True
def check(nome, cond, extra=""):
    global ok
    print(("  OK   " if cond else "  FALHA ") + nome + (f"  {extra}" if extra else ""))
    ok = ok and bool(cond)

Base.metadata.create_all(bind=engine)
db = SessionLocal()
db.execute(tarefa_responsaveis.delete())
for m in (Tarefa, Empresa, Setor, Usuario):
    db.query(m).delete()
db.commit()

admin = Usuario(nome="Admin", email="a@x.com", senha_hash="x", grupo="admin")
db.add(admin); db.commit()
emp = Empresa(razao_social="ACME", ativo=True); db.add(emp); db.commit()


def nova(titulo, anexo=None):
    t = Tarefa(titulo=titulo, empresa_id=emp.id, status=StatusTarefa.PENDENTE,
               anexo_nome=anexo)
    db.add(t); db.commit()
    return t


print("\n=== 1. a primeira lixeira cancela, não apaga ===")
t = nova("Tarefa avulsa")
r = delete_tarefa(t.id, db=db, current_user=admin)
db.expire_all()
viva = db.query(Tarefa).filter(Tarefa.id == t.id).first()
check("continua existindo", viva is not None)
check("agora está cancelada", viva and viva.status == StatusTarefa.CANCELADA)
check("a resposta diz que não excluiu", r.get("excluida") is False, f"({r})")
check("e explica o próximo passo", "de novo" in r.get("message", ""), f"({r.get('message')})")

print("\n=== 2. a segunda, na cancelada, exclui de vez ===")
r2 = delete_tarefa(t.id, db=db, current_user=admin)
check("some do banco", db.query(Tarefa).filter(Tarefa.id == t.id).first() is None)
check("a resposta confirma a exclusão", r2.get("excluida") is True, f"({r2})")

print("\n=== 3. o comprovante sai do volume junto ===")
nome_arq = up.salvar_arquivo("tok123", "recibo.pdf", b"%PDF-1.4 conteudo")
caminho = os.path.join(up.UPLOAD_DIR, nome_arq)
check("arquivo existe antes", os.path.isfile(caminho))
t2 = nova("Com comprovante", anexo=nome_arq)
delete_tarefa(t2.id, db=db, current_user=admin)      # cancela
r3 = delete_tarefa(t2.id, db=db, current_user=admin) # exclui
check("tarefa excluída", db.query(Tarefa).filter(Tarefa.id == t2.id).first() is None)
check("arquivo apagado do volume", not os.path.isfile(caminho), f"({caminho})")
check("a resposta registra a remoção", r3.get("anexo_removido") is True, f"({r3})")

print("\n=== 4. excluir tarefa sem anexo não quebra ===")
t3 = nova("Sem anexo")
delete_tarefa(t3.id, db=db, current_user=admin)
r4 = delete_tarefa(t3.id, db=db, current_user=admin)
check("exclui normalmente", r4.get("excluida") is True)
check("e diz que não havia anexo", r4.get("anexo_removido") is False, f"({r4})")

print("\n=== 5. tarefa com responsáveis sai sem deixar associação órfã ===")
t4 = nova("Com responsáveis")
t4.responsaveis = [admin]
db.commit()
delete_tarefa(t4.id, db=db, current_user=admin)
delete_tarefa(t4.id, db=db, current_user=admin)
sobrou = db.execute(tarefa_responsaveis.select()).fetchall()
check("nenhuma linha órfã na tabela de responsáveis", len(sobrou) == 0, f"({sobrou})")

print("\n=== 6. tarefa inexistente devolve 404, não estoura ===")
from fastapi import HTTPException                                        # noqa: E402
try:
    delete_tarefa(999999, db=db, current_user=admin)
    check("404 em tarefa que não existe", False, "(não levantou)")
except HTTPException as e:
    check("404 em tarefa que não existe", e.status_code == 404, f"({e.status_code})")

print("\n=== 7. tarefa que ja foi enviada ao cliente tambem sai ===")
# Este e o caso que estourava: `tarefa_envios` e `saida_acessos` apontam para
# `tarefas` com FK NOT NULL, e ninguem declarava a relacao no modelo. O ORM
# apagava so a tarefa e o banco recusava.
t5 = nova("Guia entregue ao cliente")
env = TarefaEnvio(tarefa_id=t5.id, canal="whatsapp", endereco="5511999999999",
                  destinatario="Socio", sucesso=True)
db.add(env); db.commit()
db.add(SaidaAcesso(tarefa_id=t5.id, envio_id=env.id, ip="1.2.3.4")); db.commit()
check("envio e acesso existem antes",
      db.query(TarefaEnvio).count() == 1 and db.query(SaidaAcesso).count() == 1)
delete_tarefa(t5.id, db=db, current_user=admin)      # cancela
try:
    delete_tarefa(t5.id, db=db, current_user=admin)  # exclui
    check("exclui sem estourar chave estrangeira", True)
except Exception as e:
    db.rollback()
    check("exclui sem estourar chave estrangeira", False, f"({type(e).__name__})")
check("tarefa some", db.query(Tarefa).filter(Tarefa.id == t5.id).first() is None)
check("historico de envio vai junto", db.query(TarefaEnvio).count() == 0)
check("acessos ao link vao junto", db.query(SaidaAcesso).count() == 0)

print("\n=== 8. excluir competencia leva as ja enviadas e poupa as avulsas ===")
from app.models import Obrigacao                                        # noqa: E402
ob = Obrigacao(nome="DAS"); db.add(ob); db.commit()

def gerada(titulo, comp):
    t = Tarefa(titulo=titulo, empresa_id=emp.id, obrigacao_id=ob.id,
               competencia=comp, status=StatusTarefa.PENDENTE)
    db.add(t); db.commit()
    return t

g1 = gerada("DAS enviado", "08/2026")
e1 = TarefaEnvio(tarefa_id=g1.id, canal="email", endereco="s@x.com", sucesso=True)
db.add(e1); db.commit()
db.add(SaidaAcesso(tarefa_id=g1.id, envio_id=e1.id, ip="9.9.9.9")); db.commit()
gerada("DAS sem envio", "08/2026")
gerada("DAS de outro mes", "07/2026")
avulsa = nova("Avulsa de agosto")
avulsa.competencia = "08/2026"; db.commit()

try:
    r5 = excluir_tarefas_competencia(ExcluirCompetenciaBody(competencia="08/2026"),
                                     db=db, current_user=admin)
    check("a rota responde sem 500", True, f"({r5})")
    check("apagou as duas geradas de 08/2026", r5.get("excluidas") == 2, f"({r5})")
except Exception as e:
    db.rollback()
    check("a rota responde sem 500", False, f"({type(e).__name__}: {str(e)[:120]})")

check("a avulsa de agosto continua viva",
      db.query(Tarefa).filter(Tarefa.id == avulsa.id).first() is not None)
check("a gerada de 07/2026 continua viva",
      db.query(Tarefa).filter(Tarefa.competencia == "07/2026").count() == 1)
check("nao sobrou envio orfao", db.query(TarefaEnvio).count() == 0)
check("nao sobrou acesso orfao", db.query(SaidaAcesso).count() == 0)

db.close()
print("\n" + ("TODAS AS PROVAS PASSARAM" if ok else "HOUVE FALHA"))
sys.exit(0 if ok else 1)
