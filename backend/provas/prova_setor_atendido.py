"""Prova da Fase 54: setor que a empresa não atende não fica com tarefa aberta.

Pedido de 2026-10-01: "tem empresa que só é atendida pelo fiscal". A matriz
de setores da empresa (Atende) já impedia o gerador de criar tarefa nova, mas
desmarcar um setor deixava abertas as tarefas que já tinham nascido, e as de
outubro nasceram antes de a matriz ser ajustada. Decisões do usuário:

  (a) desmarcar o setor cancela, como "não se aplica", as tarefas EM ABERTO
      da empresa naquele setor, geradas por obrigação. Concluída não muda,
      avulsa não muda. Vale para a tela e para a planilha;
  (b) uma rota de admin aplica a matriz atual ao que já foi gerado, com
      ensaio (lista sem mudar) antes do valer;
  (c) obrigação passa a exigir setor: sem ele, ela fura a matriz e gera para
      todas as empresas.

    cd backend && ./venv/bin/python provas/prova_setor_atendido.py
"""

from __future__ import annotations  # producao e 3.12, a maquina local e 3.9

import io
import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_setor_atendido_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["SECRET_KEY"] = "chave-de-prova-nao-usar-em-producao"
os.environ["ZOARIA_SSO_SECRET"] = ""

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient                          # noqa: E402
from app.auth import get_password_hash, create_access_token        # noqa: E402
from app.database import Base, engine, SessionLocal                # noqa: E402
from app.models import (Empresa, EmpresaSetorResponsavel, Obrigacao,  # noqa: E402
                        Setor, StatusTarefa, Tarefa, Usuario)
from app.main import app                                           # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
MESES = "1,2,3,4,5,6,7,8,9,10,11,12"
falhou = []
ids = {}


def checa(n, descricao, cond, extra=""):
    print(("  ok  " if cond else "FALHA ") + f"{n:>3}. {descricao}"
          + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        falhou.append(n)


def cab(email):
    return {"Authorization": "Bearer " + create_access_token(data={"sub": email})}


def tarefa(tid):
    db = SessionLocal()
    try:
        t = db.query(Tarefa).filter(Tarefa.id == tid).first()
        return (t.status, bool(t.nao_se_aplica), t.nao_se_aplica_motivo or "")
    finally:
        db.close()


def nova_tarefa(empresa, obrigacao, setor, status=StatusTarefa.PENDENTE, titulo="t"):
    db = SessionLocal()
    t = Tarefa(titulo=titulo, empresa_id=ids[empresa], setor_id=ids[setor] if setor else None,
               obrigacao_id=ids[obrigacao] if obrigacao else None,
               competencia="10/2026", status=status)
    db.add(t)
    db.commit()
    tid = t.id
    db.close()
    return tid


def planilha(cabecalho, linhas):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(cabecalho)
    for linha in linhas:
        ws.append(linha)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ------------------------------------------------------------------ cenário
db = SessionLocal()
h = get_password_hash("x")
admin = Usuario(nome="Admin", email="admin@x.com", grupo="admin", senha_hash=h, ativo=True)
analista = Usuario(nome="Ana", email="ana@x.com", grupo="analista", senha_hash=h, ativo=True)
fiscal = Setor(nome="Fiscal", ativo=True)
dp = Setor(nome="DP", ativo=True)
db.add_all([admin, analista, fiscal, dp])
db.flush()
emps = {k: Empresa(razao_social=f"Empresa {k}", cnpj=f"{n:02d}111111000111", ativo=True)
        for n, k in enumerate(("A", "B", "C", "D"), start=1)}
db.add_all(emps.values())
db.flush()
o_fis = Obrigacao(nome="apuracao_icms", setor_id=fiscal.id, meses_ativos=MESES, ativa=True)
o_dp = Obrigacao(nome="folha", setor_id=dp.id, meses_ativos=MESES, ativa=True)
db.add_all([o_fis, o_dp])
db.flush()
# C atende os dois setores; D foi configurada direto no banco, como o que já
# estava gravado em produção antes desta fase, atendendo só o Fiscal.
db.add_all([EmpresaSetorResponsavel(empresa_id=emps["C"].id, setor_id=fiscal.id),
            EmpresaSetorResponsavel(empresa_id=emps["C"].id, setor_id=dp.id),
            EmpresaSetorResponsavel(empresa_id=emps["D"].id, setor_id=fiscal.id)])
db.commit()
ids.update({"fiscal": fiscal.id, "dp": dp.id, "o_fis": o_fis.id, "o_dp": o_dp.id,
            **{k: e.id for k, e in emps.items()}})
db.close()

t_dp_pend = nova_tarefa("A", "o_dp", "dp")
t_dp_atras = nova_tarefa("A", "o_dp", "dp", StatusTarefa.ATRASADA)
t_dp_concl = nova_tarefa("A", "o_dp", "dp", StatusTarefa.CONCLUIDA)
t_fis = nova_tarefa("A", "o_fis", "fiscal")
t_avulsa = nova_tarefa("A", None, "dp", titulo="avulsa do DP")
t_b = nova_tarefa("B", "o_dp", "dp")
t_c = nova_tarefa("C", "o_dp", "dp")
t_d = nova_tarefa("D", "o_dp", "dp")
t_d_fis = nova_tarefa("D", "o_fis", "fiscal")

A = cab("admin@x.com")

# ------------------------------------------------- (a) desmarcar pela tela
print("\n(a) desmarcar o setor na matriz da empresa")
r = client.put(f"/api/empresas/{ids['A']}/responsaveis-setor", headers=A,
               json={"itens": [{"setor_id": ids["fiscal"], "responsavel_ids": []}]})
checa(1, "PUT da matriz so com Fiscal responde 200", r.status_code == 200, r.text)
st = tarefa(t_dp_pend)
checa(2, "tarefa pendente do DP vira cancelada, nao se aplica, com o setor no motivo",
      st[0] == StatusTarefa.CANCELADA and st[1] and "DP" in st[2], st)
checa(3, "tarefa atrasada do DP tambem cancela",
      tarefa(t_dp_atras)[0] == StatusTarefa.CANCELADA, tarefa(t_dp_atras))
checa(4, "tarefa concluida do DP nao muda",
      tarefa(t_dp_concl)[0] == StatusTarefa.CONCLUIDA, tarefa(t_dp_concl))
checa(5, "tarefa do Fiscal, setor atendido, nao muda",
      tarefa(t_fis)[0] == StatusTarefa.PENDENTE, tarefa(t_fis))
checa(6, "tarefa avulsa (sem obrigacao) do DP nao muda",
      tarefa(t_avulsa)[0] == StatusTarefa.PENDENTE, tarefa(t_avulsa))
checa(7, "empresa B, sem matriz (atende todos), nao muda",
      tarefa(t_b)[0] == StatusTarefa.PENDENTE, tarefa(t_b))
checa(8, "resposta conta as canceladas", r.status_code == 200
      and r.json().get("tarefas_canceladas") == 2, r.text)

t_novo = nova_tarefa("A", "o_dp", "dp")
r = client.put(f"/api/empresas/{ids['A']}/responsaveis-setor", headers=A, json={"itens": []})
checa(9, "matriz vazia (volta a atender todos) nao cancela nada",
      r.status_code == 200 and tarefa(t_novo)[0] == StatusTarefa.PENDENTE, tarefa(t_novo))

# ------------------------------------------------- (a) desmarcar pela planilha
print("\n(a) desmarcar o setor pela planilha")
arq = planilha(["CNPJ", "Fiscal", "DP"], [[f"03111111000111", "Ana", ""]])
r = client.post("/api/empresas/importar-responsaveis", headers=A,
                files={"arquivo": ("m.xlsx", arq,
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
checa(10, "planilha com DP vazio para a empresa C cancela a tarefa aberta do DP",
      r.status_code == 200 and tarefa(t_c)[0] == StatusTarefa.CANCELADA, (r.status_code, tarefa(t_c)))

# ------------------------------------------------- (b) ajuste do que ja nasceu
print("\n(b) aplicar a matriz atual ao que ja foi gerado")
rota = "/api/empresas/aplicar-setores-atendidos"
r = client.post(rota, headers=cab("ana@x.com"), json={"ensaio": True})
checa(11, "analista recebe 403", r.status_code == 403, r.status_code)
r = client.post(rota, headers=A, json={"ensaio": True})
corpo = r.json() if r.status_code == 200 else {}
achadas = [x.get("tarefa_id") for x in corpo.get("tarefas", [])]
checa(12, "ensaio lista a tarefa do DP da empresa D e mais nenhuma",
      r.status_code == 200 and achadas == [t_d], (r.status_code, r.text[:200]))
checa(13, "ensaio nao muda nada", tarefa(t_d)[0] == StatusTarefa.PENDENTE, tarefa(t_d))
checa(14, "sem corpo, a rota fica no ensaio",
      client.post(rota, headers=A).status_code == 200
      and tarefa(t_d)[0] == StatusTarefa.PENDENTE, tarefa(t_d))
r = client.post(rota, headers=A, json={"ensaio": False})
checa(15, "valendo, cancela a tarefa do DP da D e responde 1",
      r.status_code == 200 and r.json().get("tarefas_canceladas") == 1
      and tarefa(t_d)[0] == StatusTarefa.CANCELADA, (r.text[:200], tarefa(t_d)))
checa(16, "a tarefa do Fiscal da D continua aberta",
      tarefa(t_d_fis)[0] == StatusTarefa.PENDENTE, tarefa(t_d_fis))
r = client.post(rota, headers=A, json={"ensaio": False})
checa(17, "segunda rodada nao acha nada (idempotente)",
      r.status_code == 200 and r.json().get("tarefas_canceladas") == 0, r.text[:200])

# ------------------------------------------------- (c) setor obrigatorio
print("\n(c) obrigacao exige setor")
base = {"nome": "nova_sem_setor", "meses_ativos": MESES}
r = client.post("/api/obrigacoes", headers=A, json=base)
checa(18, "criar obrigacao sem setor da 422", r.status_code == 422, r.status_code)
r = client.post("/api/obrigacoes", headers=A, json={**base, "setor_id": None})
checa(19, "criar com setor null da 422", r.status_code == 422, r.status_code)
r = client.post("/api/obrigacoes", headers=A, json={**base, "nome": "nova_com_setor",
                                                    "setor_id": ids["fiscal"]})
checa(20, "criar com setor da 201", r.status_code == 201, r.text[:200])
r = client.put(f"/api/obrigacoes/{ids['o_fis']}", headers=A, json={"setor_id": None})
db = SessionLocal()
setor_agora = db.query(Obrigacao.setor_id).filter(Obrigacao.id == ids["o_fis"]).scalar()
db.close()
checa(21, "tirar o setor de uma obrigacao da 422 e o banco nao muda",
      r.status_code == 422 and setor_agora == ids["fiscal"], (r.status_code, setor_agora))
r = client.put(f"/api/obrigacoes/{ids['o_fis']}", headers=A, json={"nome": "apuracao_icms_2"})
checa(22, "editar sem mandar o setor continua 200", r.status_code == 200, r.text[:200])
r = client.post("/api/cronograma/importar", headers=A,
                json={"grupo": "g", "itens": [{"nome": "cron_sem_setor", "setor": ""}]})
db = SessionLocal()
criou = db.query(Obrigacao).filter(Obrigacao.nome == "cron_sem_setor").count()
db.close()
checa(23, "cronograma com obrigacao nova sem setor da 422 e nao cria",
      r.status_code == 422 and criou == 0, (r.status_code, criou))
r = client.post("/api/cronograma/importar", headers=A,
                json={"grupo": "g", "itens": [{"nome": "cron_com_setor", "setor": "Fiscal"}]})
checa(24, "cronograma com setor importa", r.status_code == 200, r.text[:200])

if falhou:
    print(f"\nPROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print("\nPROVA OK: 24 checagens verdes")
