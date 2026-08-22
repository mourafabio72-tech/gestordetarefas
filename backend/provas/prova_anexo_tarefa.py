"""
prova_anexo_tarefa.py — quem pode baixar o comprovante de uma tarefa.

O comprovante é a prova da entrega. Servi-lo pela primeira vez abre duas portas
que erram calado: escopo (analista baixando documento de tarefa que não é dele)
e travessia de caminho (nome de arquivo com ".." lendo fora da pasta).

Roda contra a rota real, em SQLite temporário. Não deixa arquivo para trás.

    python provas/prova_anexo_tarefa.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

_tmp = tempfile.mkdtemp(prefix="prova-anexo-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ.setdefault("SECRET_KEY", "chave-de-prova-nao-usar-em-producao")

from fastapi.testclient import TestClient          # noqa: E402
from app.database import Base, engine, SessionLocal  # noqa: E402
from app.models import Usuario, Empresa, Tarefa, StatusTarefa  # noqa: E402
from app.auth import get_password_hash, create_access_token   # noqa: E402
from app.services import upload as up              # noqa: E402
from app.main import app                           # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)

ok = True
def checa(nome, cond, extra=""):
    global ok
    print(("  ok   " if cond else "FALHA  ") + nome + (f"  {extra}" if extra else ""))
    ok = ok and bool(cond)


def cabeca(email):
    return {"Authorization": "Bearer " + create_access_token(data={"sub": email})}


# ── cenário ──────────────────────────────────────────────────────────────────
db = SessionLocal()
admin = Usuario(nome="Admin", email="admin@x.com", grupo="admin", ativo=True,
                senha_hash=get_password_hash("x"))
dono = Usuario(nome="Dono", email="dono@x.com", grupo="analista", ativo=True,
               senha_hash=get_password_hash("x"))
alheio = Usuario(nome="Alheio", email="alheio@x.com", grupo="analista", ativo=True,
                 senha_hash=get_password_hash("x"))
emp = Empresa(razao_social="Cliente Ltda", cnpj="12345678000190")
db.add_all([admin, dono, alheio, emp])
db.commit()

# O escopo do analista é "próprias" no preset; garante isso explicitamente.
from app.auth import permissao_efetiva                # noqa: E402
escopo_analista = permissao_efetiva(dono).get("escopo_tarefas")

os.makedirs(up.UPLOAD_DIR, exist_ok=True)
guardado = up.salvar_arquivo("tok123", "DARF 0220.pdf", b"%PDF-1.4 conteudo de prova")

com_anexo = Tarefa(titulo="Com comprovante", empresa_id=emp.id, responsavel_id=dono.id,
                   status=StatusTarefa.CONCLUIDA, anexo_nome=guardado)
sem_anexo = Tarefa(titulo="Sem comprovante", empresa_id=emp.id, responsavel_id=dono.id,
                   status=StatusTarefa.PENDENTE)
sumido = Tarefa(titulo="Arquivo sumiu", empresa_id=emp.id, responsavel_id=dono.id,
                status=StatusTarefa.CONCLUIDA, anexo_nome="tok999_nao-existe.pdf")
travessia = Tarefa(titulo="Nome malicioso", empresa_id=emp.id, responsavel_id=dono.id,
                   status=StatusTarefa.CONCLUIDA,
                   anexo_nome="../../../../etc/passwd")
db.add_all([com_anexo, sem_anexo, sumido, travessia])
db.commit()
for t in (com_anexo, sem_anexo, sumido, travessia):
    t.responsaveis.append(dono)
db.commit()
ids = {t.titulo: t.id for t in (com_anexo, sem_anexo, sumido, travessia)}
db.close()

print(f"\n(escopo do analista neste preset: {escopo_analista})")

print("\n=== 1. o caminho feliz — sem ele, uma rota que nega tudo passaria ===")
r = client.get(f"/api/tarefas/{ids['Com comprovante']}/anexo", headers=cabeca("dono@x.com"))
checa("o responsável baixa o comprovante", r.status_code == 200, f"({r.status_code})")
checa("vem o conteúdo do arquivo", r.content == b"%PDF-1.4 conteudo de prova")
checa("como PDF", r.headers.get("content-type", "").startswith("application/pdf"))

print("\n=== 2. o token do link público não vaza no nome ===")
disp = r.headers.get("content-disposition", "")
checa("o nome é o do envio, sem o token", "DARF" in disp and "tok123" not in disp, disp)
checa("PDF abre no navegador", disp.startswith("inline"), disp)
r2 = client.get(f"/api/tarefas/{ids['Com comprovante']}/anexo?baixar=true", headers=cabeca("dono@x.com"))
checa("com ?baixar=true vira download", r2.headers.get("content-disposition", "").startswith("attachment"))

print("\n=== 3. escopo: o mesmo da listagem de tarefas ===")
r = client.get(f"/api/tarefas/{ids['Com comprovante']}/anexo", headers=cabeca("admin@x.com"))
checa("o admin baixa", r.status_code == 200, f"({r.status_code})")
r = client.get(f"/api/tarefas/{ids['Com comprovante']}/anexo", headers=cabeca("alheio@x.com"))
esperado = 404 if escopo_analista != "todas" else 200
checa(f"quem não enxerga a tarefa não baixa (esperado {esperado})",
      r.status_code == esperado, f"({r.status_code})")
if escopo_analista != "todas":
    checa("e sai como 404, não 403 — 403 confirmaria que a tarefa existe",
          r.status_code == 404)

print("\n=== 4. sem sessão não passa ===")
checa("sem token: 401 ou 403",
      client.get(f"/api/tarefas/{ids['Com comprovante']}/anexo").status_code in (401, 403))

print("\n=== 5. os casos em que não há o que servir ===")
r = client.get(f"/api/tarefas/{ids['Sem comprovante']}/anexo", headers=cabeca("dono@x.com"))
checa("tarefa sem anexo devolve 404", r.status_code == 404, f"({r.status_code})")
r = client.get(f"/api/tarefas/999999/anexo", headers=cabeca("admin@x.com"))
checa("tarefa inexistente devolve 404", r.status_code == 404)
r = client.get(f"/api/tarefas/{ids['Arquivo sumiu']}/anexo", headers=cabeca("dono@x.com"))
checa("banco aponta para arquivo que sumiu: 410, não 404",
      r.status_code == 410, f"({r.status_code})")
checa("e a mensagem diz que é o arquivo, não a tarefa",
      "armazenamento" in r.text.lower(), r.text[:80])

print("\n=== 6. travessia de caminho ===")
r = client.get(f"/api/tarefas/{ids['Nome malicioso']}/anexo", headers=cabeca("dono@x.com"))
checa("nome com .. não serve arquivo de fora da pasta", r.status_code == 410,
      f"({r.status_code})")
checa("e nada do sistema vaza no corpo", b"root:" not in r.content)
checa("caminho_do_anexo recusa a travessia direto",
      up.caminho_do_anexo("../../../../etc/passwd") is None)
checa("e aceita o arquivo legítimo", up.caminho_do_anexo(guardado) is not None)

import shutil                                        # noqa: E402
shutil.rmtree(_tmp, ignore_errors=True)
print("\n" + ("TUDO VERDE" if ok else "VERMELHO") + "\n")
sys.exit(0 if ok else 1)
