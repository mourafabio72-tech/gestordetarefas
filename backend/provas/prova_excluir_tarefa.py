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

from app.database import SessionLocal, Base, engine                     # noqa: E402
from app.models import (Empresa, Setor, Usuario, Tarefa,                # noqa: E402
                        StatusTarefa, tarefa_responsaveis)
from app.routes.tarefas import delete_tarefa                            # noqa: E402
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

db.close()
print("\n" + ("TODAS AS PROVAS PASSARAM" if ok else "HOUVE FALHA"))
sys.exit(0 if ok else 1)
