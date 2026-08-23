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
emp_id, dono_id = emp.id, dono.id   # guardados antes de fechar: depois os objetos desanexam
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

print("\n=== 7. a consulta de documentos ===")
def docs(email, **params):
    return client.get("/api/documentos", params=params, headers=cabeca(email)).json()

r = docs("admin@x.com")
# Três das quatro tarefas têm anexo_nome — inclusive a de nome malicioso, que
# existe para provar a travessia de caminho.
checa("lista só quem TEM comprovante", r["mostrando"] == 3, f"({r['mostrando']} de {r['total']})")
titulos = {d["titulo"] for d in r["documentos"]}
checa("a tarefa sem anexo não aparece", "Sem comprovante" not in titulos, str(titulos))
checa("a que aponta para arquivo sumido APARECE, marcada",
      any(d["titulo"] == "Arquivo sumiu" and d["no_volume"] is False for d in r["documentos"]))
checa("e a que tem arquivo vem marcada como presente",
      any(d["titulo"] == "Com comprovante" and d["no_volume"] is True for d in r["documentos"]))
checa("o nome exposto não traz o token do link público",
      all("tok123" not in d["arquivo"] for d in r["documentos"]))

if escopo_analista != "todas":
    checa("quem não enxerga a tarefa não acha o documento dela",
          docs("alheio@x.com")["mostrando"] == 0)

checa("filtro por empresa", docs("admin@x.com", empresa_id=emp_id)["mostrando"] == 3)
checa("empresa que não é a da tarefa devolve vazio",
      docs("admin@x.com", empresa_id=emp_id + 999)["mostrando"] == 0)
checa("busca por parte do título", docs("admin@x.com", texto="comprova")["mostrando"] == 1)
checa("busca pelo nome do arquivo", docs("admin@x.com", texto="darf")["mostrando"] == 1)
checa("busca sem resultado não quebra", docs("admin@x.com", texto="zzzz")["mostrando"] == 0)
checa("filtro por extensão", docs("admin@x.com", extensao="pdf")["mostrando"] == 2)  # o /etc/passwd não é .pdf
checa("extensão que ninguém tem", docs("admin@x.com", extensao="docx")["mostrando"] == 0)
checa("data inválida no filtro é ignorada, não derruba a consulta",
      docs("admin@x.com", entrega_de="não-é-data")["mostrando"] == 3)

r = docs("admin@x.com", limite=1)
checa("limite corta", r["mostrando"] == 1)
checa("e o corte é declarado, não silencioso", r["cortou"] is True and r["total"] == 3)
checa("sem corte, cortou é falso", docs("admin@x.com")["cortou"] is False)

sem_sessao = client.get("/api/documentos")
checa("sem sessão não lista", sem_sessao.status_code in (401, 403))

print("\n=== 8. excluir documento: só com a flag apagar_anexo ===")
def apagar(email, tid, tipo="recebido"):
    return client.delete(f"/api/tarefas/{tid}/documento", params={"tipo": tipo},
                         headers=cabeca(email))

# O analista enxerga a tarefa dele, mas não tem a flag: ver não é apagar.
r = apagar("dono@x.com", ids["Com comprovante"])
checa("sem a flag, 403 — e é 403 mesmo, não 404", r.status_code == 403, f"({r.status_code})")
checa("a mensagem diz qual permissão falta", "apagar_anexo" in r.text, r.text[:80])
checa("e o arquivo continua lá",
      client.get(f"/api/tarefas/{ids['Com comprovante']}/anexo",
                 headers=cabeca("dono@x.com")).status_code == 200)

r = apagar("admin@x.com", ids["Com comprovante"])
checa("com a flag, apaga", r.status_code == 200, f"({r.status_code} {r.text[:60]})")
checa("diz que o arquivo existia mesmo", r.json().get("arquivo_existia") is True)
checa("o arquivo sai do volume", up.caminho_do_anexo(guardado) is None)
checa("e a rota de download passa a devolver 404",
      client.get(f"/api/tarefas/{ids['Com comprovante']}/anexo",
                 headers=cabeca("admin@x.com")).status_code == 404)
checa("some do acervo", docs("admin@x.com")["mostrando"] == 2)

checa("a resposta avisa que a tarefa foi reaberta", r.json().get("tarefa_reaberta") is True)
db = SessionLocal()
t = db.query(Tarefa).get(ids["Com comprovante"])
checa("o vínculo no banco é limpo", t.anexo_nome is None)
# Foi o documento que baixou a tarefa: sem ele, ela não está comprovada.
checa("a tarefa VOLTA para pendente", t.status == StatusTarefa.PENDENTE, str(t.status))
checa("e a data de conclusão é limpa", t.data_conclusao is None)
checa("junto com o protocolo, que veio do documento", t.protocolo_entrega is None)
db.close()

checa("apagar duas vezes devolve 404",
      apagar("admin@x.com", ids["Com comprovante"]).status_code == 404)
checa("tarefa sem documento devolve 404",
      apagar("admin@x.com", ids["Sem comprovante"]).status_code == 404)
checa("banco apontando para arquivo já sumido ainda limpa o vínculo",
      apagar("admin@x.com", ids["Arquivo sumiu"]).status_code == 200)
checa("sem sessão não apaga",
      client.delete(f"/api/tarefas/{ids['Nome malicioso']}/documento").status_code in (401, 403))

# Cancelada não foi concluída por documento nenhum: reabri-la ressuscitaria
# trabalho que alguém decidiu não fazer.
db = SessionLocal()
tc = Tarefa(titulo="Cancelada com anexo", empresa_id=emp_id, responsavel_id=dono_id,
            status=StatusTarefa.CANCELADA,
            anexo_nome=up.salvar_arquivo("tokC", "x.pdf", b"%PDF"))
db.add(tc); db.commit(); id_canc = tc.id; db.close()
r = apagar("admin@x.com", id_canc)
checa("cancelada: apaga o documento", r.status_code == 200)
checa("mas NÃO é reaberta", r.json().get("tarefa_reaberta") is False, r.text[:80])
db = SessionLocal()
checa("continua cancelada no banco",
      db.query(Tarefa).get(id_canc).status == StatusTarefa.CANCELADA)
db.close()

import shutil                                        # noqa: E402
shutil.rmtree(_tmp, ignore_errors=True)
print("\n" + ("TUDO VERDE" if ok else "VERMELHO") + "\n")
sys.exit(0 if ok else 1)
