"""Prova: relatório das empresas, com tributação e equipe por setor.

Pedido de 2026-11-04. Excel com uma linha por empresa ativa e uma coluna por
setor, a partir da matriz empresa × setor (a mesma que gera as tarefas).

  (a) regime por extenso, e não o código gravado;
  (b) cada setor com os nomes na ordem da lista, o principal primeiro;
  (c) setor marcado sem ninguém diz "sem responsável"; não atendido fica vazio;
  (d) empresa inativa fica de fora; bloqueada aparece com a situação;
  (e) a rota pede login, e texto com cara de fórmula não vira fórmula.

    cd backend && ./venv/bin/python provas/prova_relatorio_empresas.py
"""
from __future__ import annotations  # producao e 3.11, a maquina local e 3.9

import io
import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="prova_relatorio_empresas_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/prova.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["SECRET_KEY"] = "chave-de-prova-nao-usar-em-producao"
os.environ["ZOARIA_SSO_SECRET"] = ""
os.environ.pop("OPENAI_API_KEY", None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import openpyxl                                                    # noqa: E402
from fastapi.testclient import TestClient                          # noqa: E402
from app.database import Base, engine, SessionLocal                # noqa: E402
from app.models import Empresa, EmpresaSetorResponsavel, Setor, Usuario  # noqa: E402
from app.services import resp_setor                                # noqa: E402
from app.services.relatorio_empresas import gerar                  # noqa: E402
import app.main                                                    # noqa: E402

Base.metadata.create_all(bind=engine)
falhou = []


def checa(n, descricao, cond, extra=""):
    print(("  ok  " if cond else "FALHA ") + f"{n:>3}. {descricao}"
          + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        falhou.append(n)


db = SessionLocal()
fiscal, dp = Setor(nome="Fiscal"), Setor(nome="DP")
ana = Usuario(nome="Ana Paula", email="ana@x.com.br", senha_hash="x", tipo="colaborador", ativo=True)
bia = Usuario(nome="Bia Sá", email="bia@x.com.br", senha_hash="x", tipo="colaborador", ativo=True)
a = Empresa(razao_social="Alfa Ltda", cnpj="11.222.333/0001-81", ativo=True, regime_tributario="lucro_real")
b = Empresa(razao_social="=Beta Ltda", cnpj="11.444.777/0001-61", ativo=True, regime_tributario="simples_nacional", bloqueado=True)
c = Empresa(razao_social="Inativa Ltda", ativo=False, regime_tributario="mei")
db.add_all([fiscal, dp, ana, bia, a, b, c])
db.flush()
v = EmpresaSetorResponsavel(empresa_id=a.id, setor_id=fiscal.id)
w = EmpresaSetorResponsavel(empresa_id=b.id, setor_id=dp.id)
db.add_all([v, w])
db.flush()
resp_setor.gravar(db, v, [bia.id, ana.id])
resp_setor.gravar(db, w, [])
db.commit()

ws = openpyxl.load_workbook(io.BytesIO(gerar(db))).worksheets[0]
linhas = [list(r) for r in ws.iter_rows(values_only=True)]
cab = linhas[0]
print("\nconteudo")
checa(1, "uma coluna por setor, depois dos dados da empresa",
      "Razão social" in cab and "Forma de tributação" in cab and "DP" in cab and "Fiscal" in cab, cab)
por = {str(l[cab.index("Razão social")]): dict(zip(cab, l)) for l in linhas[1:]}
alfa = por.get("Alfa Ltda", {})
checa(2, "regime por extenso", alfa.get("Forma de tributação") == "Lucro Real", alfa)
checa(3, "nomes na ordem da lista, o principal primeiro", alfa.get("Fiscal") == "Bia Sá; Ana Paula", alfa.get("Fiscal"))
checa(4, "setor nao atendido fica vazio", alfa.get("DP") in (None, ""), alfa.get("DP"))
beta = next((v for k, v in por.items() if "Beta" in k), {})
checa(5, "setor marcado sem ninguem diz sem responsavel", beta.get("DP") == "sem responsável", beta)
checa(6, "bloqueada aparece com a situacao", beta.get("Situação") == "Bloqueada", beta.get("Situação"))
checa(7, "inativa fica de fora", not any("Inativa" in k for k in por), list(por))
checa(8, "texto com cara de formula nao vira formula",
      not str(next(k for k in por if "Beta" in k)).startswith("="), list(por))
print("\nacesso")
r = TestClient(app.main.app).get("/api/empresas/relatorio-equipe")
checa(9, "sem login nao entra", r.status_code == 401, r.status_code)
db.close()

if falhou:
    print(f"\nPROVA FALHOU nos itens: {falhou}")
    sys.exit(1)
print("\nPROVA OK: 9 checagens verdes")
